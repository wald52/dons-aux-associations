"""Construit le référentiel INSEE des collectivités, vendu dans ce dépôt.

Source : le projet frère `wald52/carte-finances-locales`, qui le tient déjà à
jour depuis OFGL/BANATIC/INSEE. On le recopie ici plutôt que de le refabriquer,
et on le versionne pour que le pipeline soit autonome (le clone du dépôt frère
est un plan de travail, pas une dépendance d'exécution).

À quoi il sert :
  - donner l'univers exact des collectivités, donc mesurer la couverture
    (phase 4) : « ce département est gris parce qu'on n'a pas sa donnée »
    et non « parce qu'il ne verse rien » ;
  - rattacher un code commune INSEE à son département et sa région ;
  - fournir le SIREN des collectivités, qui permettra plus tard de joindre
    les subventions versées aux finances de la collectivité qui les verse.

Usage :
    python3 scripts/pipeline/build_referentiel.py [--src <chemin du clone>]

Idempotent. Sortie : data/referentiel/*.json.gz
"""

import argparse
import gzip
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(ROOT, "data", "referentiel")
DEFAULT_SRC = "/workspace/wald52/carte-finances-locales"


def read_gz_json(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_gz_json(obj, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # mtime=0 : en-tête déterministe, donc pas de bruit dans git quand rien ne change.
    with gzip.GzipFile(path, "wb", compresslevel=9, mtime=0) as f:
        f.write(raw)
    print(f"  {name:28s} {len(raw)/1024:8.1f} Ko brut -> {os.path.getsize(path)/1024:7.1f} Ko gzip")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC, help="clone de carte-finances-locales")
    args = ap.parse_args()

    src = args.src
    need = [
        "data/communes/meta-communes-2024.json.gz",
        "data/departements/synthese-departements-2024.json.gz",
        "data/regions/synthese-regions-2024.json.gz",
        "data/intercommunalites/synthese-intercommunalites-2024.json.gz",
    ]
    missing = [p for p in need if not os.path.exists(os.path.join(src, p))]
    if missing:
        print("Référentiel amont introuvable. Cloner d'abord le dépôt frère :")
        print("  git clone --depth 1 https://github.com/wald52/carte-finances-locales "
              f"{DEFAULT_SRC}")
        for p in missing:
            print("  manquant :", p)
        sys.exit(1)

    print("Construction du référentiel INSEE")
    print(f"  source : {src}\n")

    # --- départements : code -> nom, région ---------------------------------
    dep_raw = read_gz_json(os.path.join(src, need[1]))["entities"]
    departements = {}
    for e in dep_raw:
        meta = e.get("meta") or {}
        departements[e["code"]] = {
            "nom": e["name"],
            "reg_code": meta.get("reg_code") or None,
            "reg_nom": meta.get("reg_name") or None,
            "outre_mer": (meta.get("outre_mer") or "").strip().lower() == "oui",
        }

    # --- régions -------------------------------------------------------------
    reg_raw = read_gz_json(os.path.join(src, need[2]))["entities"]
    regions = {e["code"]: {"nom": e["name"]} for e in reg_raw}

    # --- EPCI ----------------------------------------------------------------
    epci_raw = read_gz_json(os.path.join(src, need[3]))["entities"]
    epci = {}
    for e in epci_raw:
        epci[e["siren"]] = {
            "nom": e.get("nom") or "",
            "categ": e.get("categ") or None,
            "dep_code": e.get("dep_code") or None,
            "reg_code": e.get("reg_code") or None,
        }

    # --- communes ------------------------------------------------------------
    # Amont positionnel : [nom, insee, dep_code, dep_name, population, siren_epci, siren_ept]
    com_raw = read_gz_json(os.path.join(src, need[0]))
    idx = {k: i for i, k in enumerate(com_raw["schema"])}
    communes = {}
    for row in com_raw["communes"]:
        insee = row[idx["insee"]]
        dep = row[idx["dep_code"]]
        communes[insee] = {
            "nom": row[idx["nom"]],
            "dep_code": dep,
            "reg_code": (departements.get(dep) or {}).get("reg_code"),
            "population": row[idx["population"]],
            "siren_epci": row[idx["siren_epci"]] or row[idx["siren_ept"]] or None,
        }

    print(f"  communes ......... {len(communes):>6}")
    print(f"  EPCI ............. {len(epci):>6}")
    print(f"  départements ..... {len(departements):>6}")
    print(f"  régions .......... {len(regions):>6}\n")

    write_gz_json(communes, "communes.json.gz")
    write_gz_json(epci, "epci.json.gz")
    write_gz_json(departements, "departements.json.gz")
    write_gz_json(regions, "regions.json.gz")

    meta = {
        "source": "wald52/carte-finances-locales (OFGL / BANATIC / INSEE)",
        "millesime": 2024,
        "counts": {
            "communes": len(communes),
            "epci": len(epci),
            "departements": len(departements),
            "regions": len(regions),
        },
    }
    with open(os.path.join(OUT_DIR, "referentiel.meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("\n  -> data/referentiel/")


if __name__ == "__main__":
    main()
