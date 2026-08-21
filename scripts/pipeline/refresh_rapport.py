#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recalcule le rapport de qualité DEPUIS LA TABLE CANONIQUE, sans les parties.

`build_canonical.py` assemble `data/canonical/parts/` — qui n'est pas versionné.
Une session repartie d'un clone frais ne peut donc pas le rejouer, et le rapport
reste figé sur la règle des totaux qui avait cours au dernier assemblage. Dès
que cette règle change, `verify.py` le voit : « total individuel reproductible »
échoue, à juste titre.

Ce script rejoue la SEULE partie du rapport qui se déduit de la table finale, en
appelant les fonctions de `build_canonical.py` — aucune règle n'est réécrite
ici. Les deux blocs qui ne s'y trouvent pas, parce qu'ils décrivent l'assemblage
lui-même, sont repris tels quels du rapport précédent :

    deduplication   ce que la clé métier a écarté en assemblant les parties ;
    parts           la liste des parties assemblées.

Ce n'est donc PAS un raccourci du pipeline : après un vrai
`bash scripts/pipeline/tout_reconstruire.sh`, ce fichier n'a rien à faire.

Usage :  python3 scripts/pipeline/refresh_rapport.py
"""

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyarrow.dataset as ds

import build_canonical as B
import common as C

ROOT = C.ROOT
CANON = os.path.join(ROOT, "data", "canonical", "subventions")
RAPPORT = os.path.join(ROOT, "data", "canonical", "quality-report.json")


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ancien = json.load(open(RAPPORT, encoding="utf-8"))
    table = ds.dataset(CANON, format="parquet", partitioning="hive").to_table()

    report = B.quality_report(table, ancien.get("deduplication", {}),
                              ancien.get("parts", []))
    report["anomalies"] = B.anomalies(table, report)

    with open(RAPPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    cov = B.coverage(table)
    with open(os.path.join(ROOT, "data", "canonical", "coverage.json"),
              "w", encoding="utf-8") as f:
        json.dump(cov, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"  {table.num_rows:,} lignes relues")
    print(f"  avant : {ancien['amount_individual_eur']:,.0f} €")
    print(f"  après : {report['amount_individual_eur']:,.0f} €")
    print("  -> data/canonical/quality-report.json, coverage.json")


if __name__ == "__main__":
    main()
