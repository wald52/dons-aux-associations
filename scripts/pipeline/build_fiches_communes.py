"""Une fiche pour chaque commune de France — même celles que le site ne couvre pas.

CE QUE ÇA CHANGE. Jusqu'ici, un visiteur qui cherchait sa commune n'obtenait
rien : ou bien elle faisait partie des 90 couvertes, ou bien le site était
muet. Or le dénominateur de la phase 10 dit quelque chose de 34 829 communes
sur 34 936 — leur compte 6574, c'est-à-dire ce qu'elles déclarent avoir mandaté
à des associations, exercice par exercice. Il n'existe donc plus une seule
commune sur laquelle le site n'ait rien à dire.

Ce script découpe ce détail par département, comme `build_aggregates.py` le
fait déjà pour les versements : le navigateur ne charge que le fichier du
département demandé.

CE QUE CES FICHIERS NE SONT PAS, et c'est le piège central de ce chantier.
`data/aggregates/departements/<dep>.json.gz` décrit les associations SITUÉES
dans un département — des BÉNÉFICIAIRES. Les fiches produites ici décrivent la
commune qui PAIE. Ce sont deux géographies opposées : afficher « Rennes :
594 M€ » à côté des bénéficiaires rennais ferait lire de l'argent versé comme
de l'argent reçu. Les deux ne doivent jamais partager un écran sans le dire.

Usage :
    python3 scripts/pipeline/build_fiches_communes.py

Entrée : data/canonical/denominateur.json (cf. build_denominateur.py)
Sortie : data/aggregates/denominateur-communes/<dep>.json.gz  (101 fichiers)
"""

import collections
import glob
import gzip
import io
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import common as C

ROOT = C.ROOT
SOURCE = os.path.join(ROOT, "data", "canonical", "denominateur.json")
OUT = os.path.join(ROOT, "data", "aggregates", "denominateur-communes")


def main():
    print("Fiches communales — le dénominateur, découpé par département\n")
    if not os.path.exists(SOURCE):
        print("  denominateur.json absent : lancer d'abord build_denominateur.py")
        return 1

    denom = json.load(open(SOURCE, encoding="utf-8"))
    communes = denom["niveaux"]["commune"]
    ref = C.referentiel()

    # Les clés sont courtes parce qu'elles se répètent 34 829 fois : `n` le nom,
    # `d` le déclaré au compte 6574, `v` ce que le site connaît de voté, `p` de
    # payé. Mesuré : les écrire en clair coûterait environ 1 Mo sur 2,2.
    par_dep = collections.defaultdict(dict)
    hors_referentiel = []
    for code, e in communes.items():
        meta = ref["communes"].get(code)
        if not meta:
            hors_referentiel.append(code)
            continue
        fiche = {"n": e["nom"], "d": e["declare_par_exercice"]}
        # Les clés vides sont conservées : les omettre ne gagne que 27 Ko sur
        # 2,15 Mo (gzip compresse déjà ces répétitions) et obligerait le
        # navigateur à traiter deux formes du même objet.
        fiche["v"] = e["site_vote_par_exercice"]
        fiche["p"] = e["site_paye_par_exercice"]
        par_dep[meta["dep_code"]][code] = fiche

    os.makedirs(OUT, exist_ok=True)
    for vieux in glob.glob(os.path.join(OUT, "*.json.gz")):
        os.remove(vieux)

    tailles = []
    connues = 0
    for dep, contenu in sorted(par_dep.items()):
        # Le fichier porte de quoi se décrire seul : une fiche affichée doit
        # pouvoir citer sa source et sa période sans charger autre chose.
        charge = {
            "departement": dep,
            "nom_departement": ref["departements"].get(dep, {}).get("nom"),
            "generated_at": denom.get("generated_at"),
            "source": denom.get("source"),
            "reserves": denom.get("reserves"),
            "univers_communes": sum(
                1 for m in ref["communes"].values() if m.get("dep_code") == dep),
            "schema": {"n": "nom", "d": "déclaré au compte 6574",
                       "v": "connu du site, voté", "p": "connu du site, payé"},
            "communes": contenu,
        }
        brut = json.dumps(charge, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        chemin = os.path.join(OUT, dep + ".json.gz")
        with gzip.GzipFile(chemin, "wb", compresslevel=9, mtime=0) as f:
            f.write(brut)
        tailles.append(os.path.getsize(chemin))
        connues += sum(1 for c in contenu.values() if c["v"] or c["p"])

    print(f"  {len(tailles)} fichiers, {sum(len(v) for v in par_dep.values()):,} communes"
          .replace(",", " "))
    print(f"  gzippé : médiane {statistics.median(tailles)/1024:.1f} Ko, "
          f"maximum {max(tailles)/1024:.1f} Ko, total {sum(tailles)/1024:.0f} Ko")
    print(f"  communes dont le site connaît au moins un versement : {connues}")
    if hors_referentiel:
        # Un code INSEE de commune fusionnée depuis : sa balance existe, la
        # commune n'est plus au référentiel. On le dit, on ne le rattache pas
        # au jugé à sa commune nouvelle.
        print(f"  hors référentiel (communes fusionnées depuis) : "
              f"{len(hors_referentiel)}")
    print(f"\n  -> {os.path.relpath(OUT, ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
