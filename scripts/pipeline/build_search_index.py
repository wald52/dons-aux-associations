"""Construit l'index de la recherche croisée (phase 3).

La question que le site doit savoir poser — « qui finance cette association,
tous échelons confondus ? » — exige de reconnaître qu'une association vue chez
l'État et chez sa commune est la même. Résolution d'identité, dans l'ordre :

  1. le SIREN (dérivé du SIRET) quand il existe — 187 227 bénéficiaires ;
  2. à défaut le RNA — marginal (10) mais gratuit ;
  3. à défaut le NOM NORMALISÉ **plus le département**. Le département est
     indispensable : « Centre communal d'action sociale » existe dans 41
     départements, « ADIE » dans 57 — une clé par nom seul fusionnerait tout
     cela en de faux bénéficiaires multi-échelons.

Une limite assumée : une association apparaissant avec SIREN dans une source
et sans identifiant dans une autre reste comptée deux fois. La fusionner par
nom risquerait l'inverse (fusion d'homonymes), qui est pire : un cumul
d'échelons inventé est un mensonge, un cumul manqué est une lacune.

Sorties :
  data/canonical/recherche/beneficiaires.parquet
      une ligne par bénéficiaire résolu, triée par nom normalisé —
      sert la recherche par nom et la vue « cumuls d'échelons » ;
  data/canonical/recherche/versements/NN.parquet   (64 shards)
      les versements, répartis par hachage du bénéficiaire : la fiche d'une
      association télécharge UN shard (~400 Ko) et le requête en local.
      Les lectures HTTP par plages de DuckDB-WASM se replient trop souvent
      sur un téléchargement complet ; 64 petits fichiers sont plus simples
      et fonctionnent sur n'importe quel hébergeur statique.

Usage : python3 scripts/pipeline/build_search_index.py
Idempotent.
"""

import collections
import hashlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    # Uniquement en exécution directe : re-emballer stdout au chargement du
    # module casserait la sortie du script qui l'importe (verify.py).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
CANON = os.path.join(ROOT, "data", "canonical", "subventions")
OUT = os.path.join(ROOT, "data", "canonical", "recherche")

COLS = [
    "beneficiary_siren", "beneficiary_rna", "beneficiary_name_norm",
    "beneficiary_name_raw", "beneficiary_dep_code", "beneficiary_kind",
    "beneficiary_commune_insee",
    "donor_level", "donor_name_raw", "donor_program",
    "amount_eur", "amount_rejected_eur", "year", "granularity",
    "measure", "beneficiary_kind_provenance",
    "purpose_raw", "source_id", "source_label", "source_url", "quality_flags",
]


NB_SHARDS = 64


def shard_of(bid):
    """Numéro de shard d'un bénéficiaire. Somme des octets modulo 64 :
    trivial à reproduire côté navigateur, sans bibliothèque de hachage."""
    return sum(bid.encode("ascii")) % NB_SHARDS


def benef_id(siren, rna, norm, dep):
    """Identifiant stable et court du bénéficiaire résolu."""
    if siren:
        return "S" + siren
    if rna:
        return "R" + rna
    return "N" + hashlib.sha1(f"{norm}|{dep or ''}".encode("utf-8")).hexdigest()[:12]


def main():
    print("Construction de l'index de recherche croisée\n")
    table = ds.dataset(CANON, format="parquet", partitioning="hive").to_table(columns=COLS)
    n = table.num_rows
    col = {c: table.column(c).to_pylist() for c in COLS}

    ids = []
    groups = collections.defaultdict(lambda: {
        "noms": collections.Counter(), "deps": collections.Counter(),
        "kinds": collections.Counter(),
        "n": 0, "montant": 0.0, "ecarte": 0.0, "annees": set(),
        "echelons": set(), "donateurs": set(),
        "siren": None, "rna": None, "norm": None,
    })
    for i in range(n):
        bid = benef_id(col["beneficiary_siren"][i], col["beneficiary_rna"][i],
                       col["beneficiary_name_norm"][i], col["beneficiary_dep_code"][i])
        ids.append(bid)
        g = groups[bid]
        g["noms"][col["beneficiary_name_raw"][i]] += 1
        if col["beneficiary_dep_code"][i]:
            g["deps"][col["beneficiary_dep_code"][i]] += 1
        g["kinds"][col["beneficiary_kind"][i]] += 1
        g["n"] += 1
        # Le cumul d'un bénéficiaire suit la même règle que les totaux du site :
        # ni agrégat, ni exécution déjà comptée au vote, ni hors champ déclaré.
        if C.compte_dans_les_totaux(col["granularity"][i], col["measure"][i],
                                    col["beneficiary_kind"][i],
                                    col["beneficiary_kind_provenance"][i]):
            g["montant"] += col["amount_eur"][i] or 0.0
        g["ecarte"] += col["amount_rejected_eur"][i] or 0.0
        if col["year"][i]:
            g["annees"].add(col["year"][i])
        g["echelons"].add(col["donor_level"][i])
        if col["donor_name_raw"][i]:
            g["donateurs"].add(col["donor_name_raw"][i])
        g["siren"] = g["siren"] or col["beneficiary_siren"][i]
        g["rna"] = g["rna"] or col["beneficiary_rna"][i]
        g["norm"] = g["norm"] or col["beneficiary_name_norm"][i]

    print(f"  {n:,} versements -> {len(groups):,} bénéficiaires résolus")

    # --- table des bénéficiaires --------------------------------------------
    rows = []
    for bid, g in groups.items():
        annees = sorted(g["annees"])
        rows.append({
            "benef_id": bid,
            "nom": g["noms"].most_common(1)[0][0],
            "nom_norm": g["norm"] or "",
            "siren": g["siren"], "rna": g["rna"],
            "dep_code": g["deps"].most_common(1)[0][0] if g["deps"] else None,
            "kind": g["kinds"].most_common(1)[0][0],
            "nb_versements": g["n"],
            "montant_eur": round(g["montant"], 2),
            "montant_ecarte_eur": round(g["ecarte"], 2) or None,
            "annee_min": annees[0] if annees else None,
            "annee_max": annees[-1] if annees else None,
            "nb_echelons": len(g["echelons"]),
            "echelons": ",".join(sorted(g["echelons"])),
            "nb_donateurs": len(g["donateurs"]),
        })
    rows.sort(key=lambda r: r["nom_norm"])

    schema_b = pa.schema([
        ("benef_id", pa.string()), ("nom", pa.string()), ("nom_norm", pa.string()),
        ("siren", pa.string()), ("rna", pa.string()), ("dep_code", pa.string()),
        ("kind", pa.string()), ("nb_versements", pa.int32()),
        ("montant_eur", pa.float64()), ("montant_ecarte_eur", pa.float64()),
        ("annee_min", pa.int32()), ("annee_max", pa.int32()),
        ("nb_echelons", pa.int8()), ("echelons", pa.string()),
        ("nb_donateurs", pa.int32()),
    ])
    tb = pa.Table.from_pylist(rows, schema=schema_b)
    os.makedirs(OUT, exist_ok=True)
    dest_b = os.path.join(OUT, "beneficiaires.parquet")
    pq.write_table(tb, dest_b, compression="zstd", row_group_size=32 * 1024)

    # --- versements shardés par bénéficiaire --------------------------------
    import shutil
    vt = table.append_column("benef_id", pa.array(ids, pa.string()))
    vt = vt.append_column("shard", pa.array([shard_of(x) for x in ids], pa.int32()))
    vt = vt.select(["shard", "benef_id", "year", "amount_eur", "amount_rejected_eur",
                    "donor_level", "donor_name_raw", "donor_program",
                    "purpose_raw", "granularity", "measure", "source_id",
                    "source_label", "source_url"])
    vt = vt.sort_by([("shard", "ascending"), ("benef_id", "ascending"),
                     ("year", "ascending")])
    shard_dir = os.path.join(OUT, "versements")
    if os.path.exists(shard_dir):
        shutil.rmtree(shard_dir)
    os.makedirs(shard_dir)
    tailles = []
    for num in range(NB_SHARDS):
        part = vt.filter(pc.equal(vt.column("shard"), num)).drop_columns(["shard"])
        dest = os.path.join(shard_dir, f"{num:02d}.parquet")
        pq.write_table(part, dest, compression="zstd", row_group_size=32 * 1024)
        tailles.append(os.path.getsize(dest))
    old_single = os.path.join(OUT, "versements.parquet")
    if os.path.exists(old_single):
        os.remove(old_single)

    sb = os.path.getsize(dest_b)
    print(f"  beneficiaires.parquet   {len(rows):>9,} lignes  {sb/1048576:6.1f} Mo")
    print(f"  versements/NN.parquet   {vt.num_rows:>9,} lignes  "
          f"{sum(tailles)/1048576:6.1f} Mo en {NB_SHARDS} shards "
          f"(médiane {sorted(tailles)[NB_SHARDS//2]/1024:.0f} Ko, max {max(tailles)/1024:.0f} Ko)")

    # --- statistiques pour le rapport ---------------------------------------
    ech = collections.Counter(r["nb_echelons"] for r in rows)
    stats = {
        "beneficiaires": len(rows),
        "par_cle": dict(collections.Counter(bid[0] for bid in groups)),
        "par_nb_echelons": {str(k): ech[k] for k in sorted(ech)},
        "multi_echelons_3plus": sum(v for k, v in ech.items() if k >= 3),
    }
    with open(os.path.join(OUT, "index-stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\n  cumuls >=3 échelons : {stats['multi_echelons_3plus']:,}")
    print(f"  -> data/canonical/recherche/")


if __name__ == "__main__":
    main()
