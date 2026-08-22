"""Moissonneur des comptes annuels déposés au Journal officiel (DILA).

CE QUE CETTE SOURCE EST, ET CE QU'ELLE N'EST PAS.

Toute association ou fondation qui reçoit plus de 153 000 € de dons et/ou de
subventions publiques doit déposer ses comptes annuels et les faire publier
(art. L612-4 et D612-5 du code de commerce) ; même obligation pour tous les
fonds de dotation. Le jeu `jo_associations` du portail DILA recense ces dépôts :
227 586 au 22/08/2026, clôtures 2006 → 2026.

**Aucun montant.** Les montants sont dans les PDF déposés, qui sont pour la
plupart des SCANS (mesuré : sur 24 PDF tirés au hasard, 2 contiennent le mot
« subvention » en clair). Les lire demanderait un OCR, donc afficher un chiffre
deviné par une machine sur une image — ce que la doctrine de fidélité à la
source interdit. Cf. `SOURCES-RECEPTION.md` §2b.

**Ce qu'on en tire quand même, et qui n'existe nulle part ailleurs : la liste
exhaustive et datée des associations qui franchissent le seuil.** Croisée avec
l'index des bénéficiaires du site, elle mesure l'ANGLE MORT — combien
d'associations manifestement subventionnées n'apparaissent dans aucune de nos
sources, et dans quels départements.

RÉSERVE À NE JAMAIS OMETTRE : le seuil de 153 000 € mélange dons privés et
subventions publiques. Une association qui dépose ses comptes ne prouve pas
qu'elle a touché de l'argent public — l'angle mort mesuré est donc un
MAJORANT du nombre d'associations publiquement financées que le site rate.

Usage :
    python3 scripts/pipeline/fetch_jo_comptes.py [--force]

Sortie : data/raw/jo/comptes-annuels.csv (non versionné)
       + data/sources-manifest/jo-comptes.json (versionné)
"""

import argparse
import csv
import io
import json
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import common as C

ROOT = C.ROOT
RAW = os.path.join(ROOT, "data", "raw", "jo")
FICHIER = os.path.join(RAW, "comptes-annuels.csv")
MANIFEST = os.path.join(ROOT, "data", "sources-manifest", "jo-comptes.json")

HOTE = "journal-officiel-datadila.opendatasoft.com"
JEU = "jo_associations"
LICENCE = "Licence Ouverte 2.0"

# `source` vaut `joafe` pour les annonces de création / modification /
# dissolution (5,4 millions) et `dca` pour les dépôts de comptes annuels
# (227 586). Seuls les seconds nous intéressent.
FILTRE = "source='dca'"
CHAMPS = ("id,dca_siren,numero_rna,titre,departement_code,departement_libelle,"
          "region_code,dca_datecloture,dca_codepostal,dca_rectificatif_version,"
          "dateparution,association_type,association_type_libelle,url_pdf")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "dons-aux-associations/1.0 (+https://github.com/wald52)"


def exporter(chemin):
    url = f"https://{HOTE}/api/explore/v2.1/catalog/datasets/{JEU}/exports/csv"
    params = {"where": FILTRE, "select": CHAMPS, "delimiter": ";"}
    for essai in range(3):
        try:
            with SESSION.get(url, params=params, stream=True, timeout=1800) as r:
                if r.status_code == 429:
                    time.sleep(10 * (essai + 1))
                    continue
                r.raise_for_status()
                tmp = chemin + ".part"
                octets = 0
                with open(tmp, "wb") as f:
                    for bloc in r.iter_content(1 << 18):
                        f.write(bloc)
                        octets += len(bloc)
                        if octets % (1 << 23) < (1 << 18):
                            print(f"      {octets/1e6:.0f} Mo…", flush=True)
                os.replace(tmp, chemin)
                return True
        except Exception as e:
            print(f"      essai {essai+1} : {str(e)[:70]}")
            if essai == 2:
                return False
            time.sleep(5 * (essai + 1))
    return False


def relire(chemin):
    """Compte ce que le fichier porte réellement, sans rien deviner."""
    lignes = 0
    avec_siren = avec_rna = avec_dep = 0
    sirens = set()
    cloture = {}
    types = {}
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            lignes += 1
            siren = (r.get("dca_siren") or "").strip()
            if len(siren) == 9 and siren.isdigit():
                avec_siren += 1
                sirens.add(siren)
            if (r.get("numero_rna") or "").strip():
                avec_rna += 1
            if (r.get("departement_code") or "").strip():
                avec_dep += 1
            an = (r.get("dca_datecloture") or "")[:4]
            if an:
                cloture[an] = cloture.get(an, 0) + 1
            t = r.get("association_type_libelle") or "?"
            types[t] = types.get(t, 0) + 1
    return {
        "depots": lignes,
        "avec_siren": avec_siren,
        "avec_rna": avec_rna,
        "avec_departement": avec_dep,
        "organismes_distincts_par_siren": len(sirens),
        "exercices_de_cloture": dict(sorted(cloture.items())),
        "types": dict(sorted(types.items(), key=lambda kv: -kv[1])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)

    if os.path.exists(FICHIER) and not args.force:
        print("  export en cache")
    else:
        print(f"  export de {JEU} ({FILTRE})…", flush=True)
        if not exporter(FICHIER):
            print("  ÉCHEC — rien n'est écrit")
            return 1

    fiche = relire(FICHIER)
    manifeste = {
        "family": "jo-comptes",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hote": HOTE,
        "dataset": JEU,
        "url": f"https://{HOTE}/explore/dataset/{JEU}/",
        "filtre": FILTRE,
        "licence": LICENCE,
        "fichier": os.path.relpath(FICHIER, ROOT),
        "seuil_legal_eur": 153000,
        "fondement": "art. L612-4 et D612-5 du code de commerce",
    }
    manifeste.update(fiche)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifeste, f, ensure_ascii=False, indent=1)
    print(f"  {fiche['depots']} dépôts, {fiche['organismes_distincts_par_siren']} "
          f"organismes distincts → {os.path.relpath(MANIFEST, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
