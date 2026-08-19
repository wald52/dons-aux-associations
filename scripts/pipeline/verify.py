"""Contrôles de bout en bout du pipeline canonique.

Sert de garde-fou : toute modification du pipeline doit le laisser vert. Les
contrôles portent sur ce qui peut casser en silence — une ligne perdue, un
montant qui dérive, une valeur hors taxonomie, une géographie incohérente.

Usage :
    python3 scripts/pipeline/verify.py

Code de sortie 1 si un contrôle échoue.
"""

import collections
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow as pa
import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
CANON = os.path.join(ROOT, "data", "canonical", "subventions")
PARTS = os.path.join(ROOT, "data", "canonical", "parts")

DONOR_LEVELS = {"etat", "operateur", "region", "departement", "epci", "commune", "inconnu"}
GRANULARITIES = {"individual", "aggregate"}
KINDS = {"association", "public_body", "company", "individual", "inconnu"}
CONFIDENCES = {"high", "medium", "low"}
FAMILIES = {"plf_jaune", "scdl", "portail", "manuel"}

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'OK ' if ok else 'ÉCHEC'}] {name}" + (f"  — {detail}" if detail else ""))
    return ok


def main():
    print("Vérification du pipeline canonique\n")
    # La table est partitionnée par année : on la relit comme un jeu de
    # données, et l'on remet `year` en int32 (Hive la restitue en catégorie).
    import pyarrow.dataset as ds
    table = ds.dataset(CANON, format="parquet", partitioning="hive").to_table()
    table = table.set_column(table.schema.get_field_index("year"), "year",
                             table.column("year").cast(pa.int32()))
    report = json.load(open(os.path.join(ROOT, "data", "canonical", "quality-report.json"),
                             encoding="utf-8"))
    n = table.num_rows

    # 1. Aucune ligne perdue entre les parties et la table finale ------------
    part_rows = sum(pq.read_metadata(f).num_rows
                    for f in glob.glob(os.path.join(PARTS, "*.parquet")))
    dropped = report["deduplication"]["rows_dropped"]
    check("conservation des lignes",
          part_rows - dropped == n,
          f"{part_rows:,} parties − {dropped:,} dédupliquées = {part_rows - dropped:,} (table : {n:,})")

    # 2. Taxonomies closes ---------------------------------------------------
    for col, allowed in (("donor_level", DONOR_LEVELS), ("granularity", GRANULARITIES),
                         ("beneficiary_kind", KINDS), ("confidence", CONFIDENCES),
                         ("source_family", FAMILIES)):
        vals = set(table.column(col).to_pylist())
        extra = {v for v in vals if v is not None} - allowed
        check(f"taxonomie close : {col}", not extra, f"hors liste : {sorted(extra)}" if extra else
              f"{len(vals)} valeurs")

    # 3. Géographie cohérente ------------------------------------------------
    ref = C.referentiel()
    dep = table.column("beneficiary_dep_code").to_pylist()
    reg = table.column("beneficiary_reg_code").to_pylist()
    unknown = {d for d in dep if d and d not in ref["departements"]}
    check("codes département connus du référentiel", not unknown,
          f"inconnus : {sorted(unknown)[:6]}" if unknown else f"{len({d for d in dep if d})} départements")

    mismatch = sum(1 for i in range(n) if dep[i] and reg[i]
                   and ref["departements"][dep[i]]["reg_code"] != reg[i])
    check("région cohérente avec le département", mismatch == 0, f"{mismatch:,} incohérences")

    orphan = sum(1 for i in range(n) if dep[i] and not reg[i])
    check("aucun département sans région", orphan == 0, f"{orphan:,} lignes")

    insee = table.column("beneficiary_commune_insee").to_pylist()
    bad_insee = {c for c in insee if c and c not in ref["communes"]}
    check("codes commune connus du référentiel", not bad_insee,
          f"inconnus : {sorted(bad_insee)[:6]}" if bad_insee else
          f"{len({c for c in insee if c}):,} communes distinctes")

    # 4. Marqueurs d'absence proscrits (nul plutôt que faux) -----------------
    forbidden_dep = sum(1 for d in dep if d in ("00", "0", ""))
    check("aucun département « 00 » ou vide", forbidden_dep == 0, f"{forbidden_dep:,} lignes")
    years = table.column("year").to_pylist()
    bad_year = sum(1 for y in years if y is not None and not (1990 <= y <= 2100))
    check("aucune année hors bornes", bad_year == 0, f"{bad_year:,} lignes")

    # 5. Identifiants --------------------------------------------------------
    row_ids = table.column("row_id").to_pylist()
    check("row_id unique", len(set(row_ids)) == n,
          f"{n - len(set(row_ids)):,} collisions")
    check("business_key toujours renseignée",
          table.column("business_key").null_count == 0)
    sirets = [s for s in table.column("beneficiary_siret").to_pylist() if s]
    check("SIRET tous valides (longueur et clé de Luhn)",
          all(C.valid_siret(s) for s in sirets[:50000]),
          f"{len(sirets):,} SIRET, contrôle sur les 50 000 premiers")

    # 6. Montants ------------------------------------------------------------
    amt = table.column("amount_eur").to_pylist()
    rej = table.column("amount_rejected_eur").to_pylist()
    flags = table.column("quality_flags").to_pylist()
    # Le contrôle qui compte : `amount_eur` ne doit JAMAIS contenir de valeur
    # invraisemblable, pour qu'une somme naïve reste juste.
    check("amount_eur sommable sans précaution",
          not any(C.amount_is_implausible(a) for a in amt),
          f"{sum(1 for a in amt if C.amount_is_implausible(a))} valeurs aberrantes")
    check("valeurs écartées conservées et signalées",
          all(rej[i] is None or (flags[i] and "amount_implausible" in flags[i]) for i in range(n))
          and all(amt[i] is None for i in range(n) if rej[i] is not None),
          f"{sum(1 for x in rej if x is not None)} lignes dans amount_rejected_eur")

    # 7. Le total publié exclut bien agrégats et invraisemblables ------------
    gran = table.column("granularity").to_pylist()
    recomputed = round(sum(amt[i] or 0 for i in range(n) if gran[i] != "aggregate"), 2)
    check("total individuel reproductible",
          abs(recomputed - report["amount_individual_eur"]) < 1,
          f"{recomputed:,.0f} € = rapport")

    # 8. Provenance ----------------------------------------------------------
    check("toute ligne porte sa source",
          table.column("source_id").null_count == 0 and table.column("source_row_ref").null_count == 0)

    # 9. Doublons entre sources : aucun ne subsiste --------------------------
    bk = table.column("business_key").to_pylist()
    src = table.column("source_id").to_pylist()
    groups = collections.defaultdict(set)
    for i in range(n):
        groups[bk[i]].add(src[i])
    remaining = sum(1 for v in groups.values() if len(v) > 1)
    check("aucun doublon inter-sources résiduel", remaining == 0,
          f"{remaining:,} groupes")

    print()
    failed = [r for r in results if not r[1]]
    print(f"  {len(results) - len(failed)}/{len(results)} contrôles passés")
    if failed:
        print("\n  ÉCHECS :")
        for name, _, detail in failed:
            print(f"    · {name} — {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
