"""Précalcule ce que le premier écran doit afficher, en quelques centaines de Ko.

Principe de la phase 2 : **le site sert un index, pas une base**. La carte et
les compteurs se contentent d'agrégats déjà calculés ; le détail ligne à ligne
n'est chargé qu'à la demande, depuis les partitions Parquet.

Sorties (toutes en .json.gz, décompressées par le navigateur) :

  meta.json.gz          années, niveaux de donateur, départements et régions,
                        synthèse de qualité et de couverture
  cube.json.gz          cube creux département × année × niveau -> [lignes, montant]
  top.json.gz           principaux bénéficiaires et donateurs, par année

Usage :
    python3 scripts/pipeline/build_aggregates.py

Idempotent. Les .gz sont écrits sans horodatage, donc identiques d'un build à
l'autre tant que les données ne changent pas.
"""

import collections
import glob
import gzip
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow.dataset as ds

import common as C

ROOT = C.ROOT
CANON = os.path.join(ROOT, "data", "canonical", "subventions")
OUT = os.path.join(ROOT, "data", "aggregates")


def write_gz(obj, name):
    os.makedirs(OUT, exist_ok=True)
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path = os.path.join(OUT, name)
    with gzip.GzipFile(path, "wb", compresslevel=9, mtime=0) as f:
        f.write(raw)
    size = os.path.getsize(path)
    print(f"  {name:30s} {len(raw)/1024:8.1f} Ko  ->  {size/1024:7.1f} Ko gzip")
    return size


def main():
    print("Précalcul des agrégats du premier écran\n")
    table = ds.dataset(CANON, format="parquet", partitioning="hive").to_table(columns=[
        "beneficiary_dep_code", "beneficiary_name_raw", "beneficiary_siren",
        "donor_level", "donor_name_raw", "amount_eur", "year", "granularity",
        "measure", "beneficiary_kind", "beneficiary_kind_provenance",
        "source_id", "quality_flags",
    ])
    n = table.num_rows
    dep = table.column("beneficiary_dep_code").to_pylist()
    lvl = table.column("donor_level").to_pylist()
    amt = table.column("amount_eur").to_pylist()
    yr = table.column("year").to_pylist()
    gran = table.column("granularity").to_pylist()
    bname = table.column("beneficiary_name_raw").to_pylist()
    dname = table.column("donor_name_raw").to_pylist()
    src = table.column("source_id").to_pylist()
    mesure = table.column("measure").to_pylist()
    bkind = table.column("beneficiary_kind").to_pylist()
    bkprov = table.column("beneficiary_kind_provenance").to_pylist()

    # Une seule règle décide de ce qui est sommé, définie dans common.py. On la
    # calcule une fois par ligne : elle sert aux trois agrégats ci-dessous.
    sommable = [C.compte_dans_les_totaux(gran[i], mesure[i], bkind[i], bkprov[i])
                for i in range(n)]

    ref = C.referentiel()
    report = json.load(open(os.path.join(ROOT, "data", "canonical",
                                         "quality-report.json"), encoding="utf-8"))

    # --- cube creux : département -> année -> niveau -> [lignes, montant] ----
    # Les lignes agrégées (postes budgétaires) sont exclues : les additionner
    # aux attributions individuelles compterait deux fois.
    cube = collections.defaultdict(lambda: collections.defaultdict(
        lambda: collections.defaultdict(lambda: [0, 0.0])))
    national = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0]))
    sans_dep = collections.defaultdict(lambda: [0, 0.0])

    # Les lignes sans année vont dans un seau dédié plutôt que d'être perdues :
    # elles représentent 14 839 versements, et les taire ferait mentir les
    # compteurs. Même chose pour les lignes dont le montant a été mis de côté :
    # on les COMPTE sans les SOMMER, pour que l'activité reste visible.
    for i in range(n):
        if not sommable[i]:
            continue
        y = str(yr[i]) if yr[i] is not None else "inconnue"
        l, a = lvl[i], amt[i]
        cell = national[y][l]
        cell[0] += 1
        cell[1] += a or 0
        if dep[i]:
            c = cube[dep[i]][y][l]
            c[0] += 1
            c[1] += a or 0
        else:
            sd = sans_dep[y]
            sd[0] += 1
            sd[1] += a or 0

    def compact(d):
        return {k: {y: {l: [v[0], round(v[1])] for l, v in lv.items()}
                    for y, lv in yv.items()} for k, yv in d.items()}

    years = sorted({str(y) for y in yr if y})
    if any(y is None for y in yr):
        years.append("inconnue")
    levels = sorted({l for l in lvl if l})

    write_gz({
        "schema": ["lignes", "montant_eur"],
        "note": ("Cube creux département × année × niveau de donateur. "
                 "Les lignes de granularité « aggregate » (postes budgétaires) "
                 "sont exclues, pour ne pas compter deux fois. L'année « inconnue » "
                 "regroupe les versements dont la source ne donne pas l'exercice. "
                 "Les montants mis en quarantaine comptent pour 0 € mais restent "
                 "comptés en nombre de versements."),
        "departements": compact(cube),
        "national": {y: {l: [v[0], round(v[1])] for l, v in lv.items()}
                     for y, lv in national.items()},
        "sans_departement": {y: [v[0], round(v[1])] for y, v in sans_dep.items()},
    }, "cube.json.gz")

    # --- métadonnées ---------------------------------------------------------
    cov = json.load(open(os.path.join(ROOT, "data", "canonical", "coverage.json"),
                         encoding="utf-8"))
    deps_meta = {code: [m["nom"], m["reg_code"]] for code, m in ref["departements"].items()}
    regs_meta = {code: m["nom"] for code, m in ref["regions"].items()}

    write_gz({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "annees": years,
        "niveaux": levels,
        "niveaux_libelles": {
            "etat": "État", "operateur": "Opérateur de l'État", "region": "Région",
            "departement": "Département", "epci": "Intercommunalité",
            "commune": "Commune", "inconnu": "Donateur non identifié",
        },
        "departements": {"schema": ["nom", "reg_code"], "valeurs": deps_meta},
        "regions": regs_meta,
        "totaux": {
            "lignes": report["rows_total"],
            "montant_individuel_eur": round(report["amount_individual_eur"]),
            "montant_agrege_eur": round(report["amount_aggregate_eur"]),
            "sources": len(report["by_source"]),
            "beneficiaires_distincts": len({b for b in bname if b}),
            "donateurs_distincts": len({d for d in dname if d}),
        },
        "couverture": {
            "departements_avec_donnees": cov["departements"]["avec_donnees"],
            "departements_univers": cov["departements"]["univers"],
            "lignes_sans_departement": cov["lignes_sans_departement"],
            "communes_univers": ref and len(ref["communes"]),
            "note": cov["note"],
        },
        "qualite": {
            "drapeaux": dict(list(report["quality_flags"].items())[:12]),
            "anomalies": report.get("anomalies", []),
            "deduplication": {
                "lignes_ecartees": report["deduplication"]["rows_dropped"],
                "montant_ecarte_eur": report["deduplication"]["amount_dropped"],
            },
        },
    }, "meta.json.gz")

    # --- principaux bénéficiaires et donateurs -------------------------------
    def top(names, k=40):
        acc = collections.defaultdict(lambda: [0, 0.0])
        for i in range(n):
            if not sommable[i] or amt[i] is None or not names[i]:
                continue
            c = acc[names[i]]
            c[0] += 1
            c[1] += amt[i]
        return [[name, v[0], round(v[1])]
                for name, v in sorted(acc.items(), key=lambda x: -x[1][1])[:k]]

    per_source = sorted(
        ((s, v["rows"], round(v["amount_individual_eur"]))
         for s, v in report["by_source"].items()), key=lambda x: -x[2])

    write_gz({
        "schema": ["nom", "lignes", "montant_eur"],
        "beneficiaires": top(bname),
        "donateurs": top(dname),
        "sources": per_source,
    }, "top.json.gz")

    # --- fragments par département ------------------------------------------
    # Chargés au clic, un seul à la fois. Le détail d'un département est une
    # demande prévisible : la précalculer coûte quelques kilo-octets, là où un
    # moteur SQL embarqué coûterait dix mégaoctets au premier usage. Les
    # requêtes vraiment arbitraires relèvent de la phase 3.
    frag_dir = os.path.join(OUT, "departements")
    os.makedirs(frag_dir, exist_ok=True)
    for old in glob.glob(os.path.join(frag_dir, "*.json.gz")):
        os.remove(old)

    by_dep_rows = collections.defaultdict(list)
    for i in range(n):
        if dep[i] and sommable[i]:
            by_dep_rows[dep[i]].append(i)

    frag_total = 0
    for code, idxs in by_dep_rows.items():
        benef = collections.defaultdict(lambda: [0, 0.0])
        donor = collections.defaultdict(lambda: [0, 0.0])
        per_year = collections.defaultdict(lambda: [0, 0.0])
        sources = collections.Counter()
        for i in idxs:
            valeur = amt[i] or 0
            b = benef[bname[i]]
            b[0] += 1
            b[1] += valeur
            d = donor[dname[i] or "—"]
            d[0] += 1
            d[1] += valeur
            p = per_year[str(yr[i]) if yr[i] is not None else "inconnue"]
            p[0] += 1
            p[1] += valeur
            sources[src[i]] += 1

        payload = {
            "code": code,
            "nom": ref["departements"][code]["nom"],
            "region": ref["departements"][code]["reg_nom"],
            "lignes": len(idxs),
            "montant_eur": round(sum(amt[i] or 0 for i in idxs)),
            "par_annee": {y: [v[0], round(v[1])] for y, v in sorted(per_year.items())},
            "beneficiaires": [[k, v[0], round(v[1])] for k, v in
                              sorted(benef.items(), key=lambda x: -x[1][1])[:60]],
            "donateurs": [[k, v[0], round(v[1])] for k, v in
                          sorted(donor.items(), key=lambda x: -x[1][1])[:40]],
            "sources": sources.most_common(20),
            "schema": ["nom", "lignes", "montant_eur"],
        }
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        path = os.path.join(frag_dir, f"{code}.json.gz")
        with gzip.GzipFile(path, "wb", compresslevel=9, mtime=0) as f:
            f.write(raw)
        frag_total += os.path.getsize(path)

    print(f"  departements/*.json.gz  {len(by_dep_rows)} fragments  ->  "
          f"{frag_total/1024:7.1f} Ko gzip au total "
          f"({frag_total/max(len(by_dep_rows),1)/1024:.1f} Ko en moyenne)")

    # Les tracés de la carte sont construits par `build_carte.py`, depuis le
    # GeoJSON officiel : le SVG livré avec l'ancien site ignore l'outre-mer.

    first = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)
                if f.endswith(".json.gz"))
    print(f"\n  Premier écran : {first/1024:.0f} Ko (gzippés), fragments chargés au clic")
    print(f"  -> data/aggregates/")


if __name__ == "__main__":
    main()
