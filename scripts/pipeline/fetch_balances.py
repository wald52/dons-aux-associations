"""Moissonneur des balances comptables DGFiP — le compte 6574.

POURQUOI CE MOISSONNEUR EST DIFFÉRENT DE TOUS LES AUTRES.

Les quatre familles déjà en place (`plf_jaune`, `scdl`, `portail`, héritée)
moissonnent de l'OPEN DATA VOLONTAIRE : une collectivité publie ses subventions
si elle le veut bien. `RESTE-A-FAIRE.md` §1a établit que ce canal est épuisé —
90 communes sur 34 936, 10,9 % de la population — et qu'aucun moissonnage
supplémentaire ne changera l'échelle.

Les balances comptables, elles, sont la COMPTABILITÉ OFFICIELLE de toutes les
collectivités, transmise à la DGFiP et publiée exercice par exercice. Elles sont
donc exhaustives par construction : 31 797 communes portent un compte 6574 pour
le seul exercice 2020, contre 90 communes couvertes par le site.

CE QU'ELLES NE DONNENT PAS : le bénéficiaire. Une balance dit « cette commune a
passé X € au compte 6574 », jamais « à quelle association ». Ces données
n'entrent donc PAS dans la table canonique des subventions et ne sont jamais
sommées avec elle. Elles servent de DÉNOMINATEUR : « le site connaît Y € des
X € que cette collectivité déclare avoir versés ».

LE CHOIX DE COMPTE, ET SES RÉSERVES. On retient la famille 6574 —
« subventions de fonctionnement aux associations et autres personnes de droit
privé » — dans toutes les nomenclatures (M14 et M57 pour les communes, M52 et
M57 pour les départements, M71 et M57 pour les régions). Trois réserves, à
répéter partout où le chiffre s'affiche :

  - le compte dit « et autres personnes de droit privé » : il n'est pas
    purement associatif, donc il SURESTIME ;
  - une subvention peut être imputée ailleurs — 6568, 657362 vers un CCAS,
    subventions d'investissement en compte 204 — donc 6574 seul SOUS-ESTIME ;
  - les deux effets ne se compensent pas et ne sont pas mesurables ici.

On ne prend PAS la famille 6573 (subventions aux organismes PUBLICS : communes,
régions, groupements, SPIC), qui n'est pas de l'argent associatif.

Usage :
    python3 scripts/pipeline/fetch_balances.py [--force] [--jeu <id>]

Sortie : data/raw/balances/*.csv (non versionné)
       + data/sources-manifest/balances.json (versionné)
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
RAW = os.path.join(ROOT, "data", "raw", "balances")
MANIFEST = os.path.join(ROOT, "data", "sources-manifest", "balances.json")

HOTE = "data.economie.gouv.fr"
LICENCE = "Licence Ouverte 2.0"

# Les jeux à moissonner. Les communes ont UN JEU PAR EXERCICE (7 millions de
# lignes chacun, d'où le découpage) ; les autres échelons tiennent dans un seul
# jeu pluriannuel. Les jeux « syndicats » et « établissements publics locaux »
# ne sont pas repris : le site ne cartographie pas ces échelons, et leur compte
# 6574 mélangerait des budgets sans collectivité de rattachement lisible.
ANNEES_COMMUNES = range(2010, 2026)
JEUX_PLURIANNUELS = [
    ("balances-comptables-des-departements", "departement"),
    ("balances-comptables-des-regions-", "region"),
    ("balances-comptables-des-groupements-a-fiscalite-propre-depuis-2010", "epci"),
]

# Le filtre est posé côté serveur : on ne rapatrie que les lignes utiles, soit
# ~32 000 par exercice au lieu de 7 millions. `startswith` et non `like` : dans
# l'ODSQL d'Opendatasoft, `like '6574%'` n'est PAS un préfixe — le « % » n'est
# pas un joker et la comparaison se fait sur le jeton entier, donc `like` ne
# ramenait que le compte 6574 exact et laissait 65741, 65742, 65748 dehors.
FILTRE = "startswith(compte,'6574')"
# Les millésimes ne portent pas tous les mêmes colonnes : `categ` (« Commune »,
# « Département »…) n'apparaît qu'à partir de 2017, et `insee` est tantôt un
# texte, tantôt un entier — un « 038 » y devient 38. On demande donc
# l'INTERSECTION des colonnes voulues et de celles que le jeu déclare, plutôt
# qu'une liste fixe : sans cela, sept exercices sortaient en HTTP 400.
CHAMPS = ["exer", "ident", "ndept", "lbudg", "insee", "siren", "nomen",
          "cbudg", "categ", "compte", "sd", "sc"]

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "dons-aux-associations/1.0 (+https://github.com/wald52)"
PAUSE = 1.0


def champs_du_jeu(jeu):
    """Colonnes réellement déclarées par ce millésime."""
    url = f"https://{HOTE}/api/explore/v2.1/catalog/datasets/{jeu}"
    r = SESSION.get(url, timeout=90)
    r.raise_for_status()
    presents = {f.get("name") for f in r.json().get("fields", [])}
    return [c for c in CHAMPS if c in presents]


def exporter(jeu, chemin):
    """Export CSV filtré du jeu, en flux."""
    url = f"https://{HOTE}/api/explore/v2.1/catalog/datasets/{jeu}/exports/csv"
    try:
        champs = champs_du_jeu(jeu)
    except Exception as e:
        print(f"      catalogue injoignable : {str(e)[:60]}")
        return False
    params = {"where": FILTRE, "select": ",".join(champs), "delimiter": ";"}
    for essai in range(3):
        try:
            with SESSION.get(url, params=params, stream=True, timeout=900) as r:
                if r.status_code == 429:
                    time.sleep(5 * (essai + 1))
                    continue
                r.raise_for_status()
                tmp = chemin + ".part"
                with open(tmp, "wb") as f:
                    for bloc in r.iter_content(1 << 18):
                        f.write(bloc)
                os.replace(tmp, chemin)
                return True
        except Exception as e:
            if essai == 2:
                print(f"      échec : {str(e)[:70]}")
                return False
            time.sleep(3 * (essai + 1))
    return False


def relire(chemin):
    """Relit un export et en tire de quoi remplir le manifeste.

    On mesure aussi ce qui pourrait faire un DOUBLE COMPTE : un budget qui
    porterait à la fois le compte père 6574 et un compte fils 6574x pour le
    même exercice. La somme de la famille serait alors gonflée. Le chiffre est
    inscrit au manifeste plutôt que corrigé en silence.
    """
    lignes = 0
    total = 0.0
    comptes = {}
    exercices = {}
    vus = {}
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            lignes += 1
            sd = float(r.get("sd") or 0) - float(r.get("sc") or 0)
            total += sd
            compte = (r.get("compte") or "").strip()
            comptes[compte] = comptes.get(compte, 0) + 1
            an = (r.get("exer") or "")[:4]
            exercices[an] = exercices.get(an, 0) + 1
            vus.setdefault((r.get("ident"), an), set()).add(compte)
    peres_et_fils = sum(
        1 for cs in vus.values() if "6574" in cs and len(cs) > 1
    )
    return {
        "lignes": lignes,
        "montant_eur": round(total, 2),
        "comptes": dict(sorted(comptes.items(), key=lambda kv: -kv[1])),
        "exercices": dict(sorted(exercices.items())),
        "budgets_pere_et_fils": peres_et_fils,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-télécharge tout")
    ap.add_argument("--jeu", help="ne traiter que ce jeu")
    args = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)

    cibles = [(f"balances-comptables-des-communes-en-{a}", "commune")
              for a in ANNEES_COMMUNES] + JEUX_PLURIANNUELS
    if args.jeu:
        cibles = [c for c in cibles if c[0] == args.jeu]

    fiches = []
    print(f"Balances comptables DGFiP — compte 6574 ({len(cibles)} jeux)")
    for jeu, echelon in cibles:
        chemin = os.path.join(RAW, jeu + ".csv")
        if os.path.exists(chemin) and not args.force:
            print(f"  {jeu} : en cache")
        else:
            print(f"  {jeu} : export…", flush=True)
            if not exporter(jeu, chemin):
                fiches.append({"dataset": jeu, "echelon": echelon, "erreur": True})
                continue
            time.sleep(PAUSE)
        fiche = {"dataset": jeu, "echelon": echelon,
                 "url": f"https://{HOTE}/explore/dataset/{jeu}/",
                 "licence": LICENCE, "fichier": os.path.relpath(chemin, ROOT)}
        fiche.update(relire(chemin))
        print(f"      {fiche['lignes']:>7} lignes, "
              f"{fiche['montant_eur']/1e6:>10.1f} M€, "
              f"{len(fiche['comptes'])} compte(s)")
        fiches.append(fiche)

    manifeste = {
        "family": "balances",
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hote": HOTE,
        "filtre": FILTRE,
        "licence": LICENCE,
        "jeux": len(fiches),
        "lignes": sum(f.get("lignes", 0) for f in fiches),
        "montant_eur": round(sum(f.get("montant_eur", 0) for f in fiches), 2),
        "datasets": fiches,
    }
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifeste, f, ensure_ascii=False, indent=1)
    print(f"\n{manifeste['lignes']} lignes, "
          f"{manifeste['montant_eur']/1e9:.2f} Md€ → {os.path.relpath(MANIFEST, ROOT)}")


if __name__ == "__main__":
    main()
