"""Moissonneur des portails Opendatasoft.

Les collectivités qui publient le plus ne passent pas par data.gouv.fr : elles
ont leur propre portail. La Ville de Paris y publie environ 195 000 lignes de
subventions, quand le moissonnage data.gouv.fr n'en ramenait que 76 207.

Ces portails partagent tous la même API (Explore v2.1), si bien qu'un seul
moissonneur les couvre. Deux propriétés en découlent :

  - le catalogue expose les CHAMPS de chaque jeu, donc on valide un jeu sans
    rien télécharger — seuls les jeux réellement pertinents sont rapatriés ;
  - l'export CSV est standard, donc aucun format propriétaire à gérer.

Le débit est volontairement modeste et sérialisé par portail : plusieurs de ces
serveurs répondent en erreur quand on les interroge trop vite.

Usage :
    python3 scripts/pipeline/fetch_ods.py [--portail data.iledefrance.fr] [--force]

Sortie : data/raw/ods/*.csv (non versionné) + data/sources-manifest/ods.json
"""

import argparse
import hashlib
import io
import json
import os
import sys
import time
import urllib.parse

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import common as C

ROOT = C.ROOT
RAW = os.path.join(ROOT, "data", "raw", "ods")
MANIFEST = os.path.join(ROOT, "data", "sources-manifest", "ods.json")

# Portails vérifiés joignables. `data.opendatasoft.com` est le fédérateur : il
# rassemble les jeux de nombreux portails qui n'exposent pas leur propre API —
# mais il est LOIN de tout republier : six portails ajoutés en dernier lieu ne
# lui étaient pas connus.
PORTAILS = [
    ("opendata.paris.fr", "Ville de Paris"),
    ("data.iledefrance.fr", "Région Île-de-France"),
    ("data.rennesmetropole.fr", "Rennes Métropole"),
    ("data.toulouse-metropole.fr", "Toulouse Métropole"),
    ("data.nantesmetropole.fr", "Nantes Métropole"),
    ("data.centrevaldeloire.fr", "Région Centre-Val de Loire"),
    ("data.ampmetropole.fr", "Aix-Marseille-Provence"),
    ("opendata.clermontmetropole.eu", "Clermont Auvergne Métropole"),
    ("data.laregion.fr", "Région Occitanie"),
    ("data.bretagne.bzh", "Région Bretagne"),
    ("data.opendatasoft.com", "Fédérateur Opendatasoft"),
    # Portails repérés en interrogeant le fédérateur sur le domaine d'origine
    # de chacun de ses jeux « subvention » : il les republie, mais jamais tous.
    # Les visiter en direct coûte une ligne et rattrape ce qu'il laisse.
    # Trente ont répondu à l'API Explore v2.1 ; cinq sont morts et ne sont pas
    # inscrits (data.corsica et opendata.sqy.fr en 410, opendata.pau.fr en 404,
    # ville-soissons.fr et opendata.roubaix.fr en défaut de certificat).
    ("data.blois.agglopolys.fr", "Agglopolys — Blois"),
    ("data.loire-atlantique.fr", "Département de Loire-Atlantique"),
    ("data.saint-maur.com", "Ville de Saint-Maur-des-Fossés"),
    ("data.agglo-montargoise.fr", "Agglomération Montargoise"),
    ("data.saintnazaireagglo.fr", "Saint-Nazaire Agglomération"),
    ("opendata.ha-py.fr", "Département des Hautes-Pyrénées"),
    ("saint-louis-agglo.opendatasoft.com", "Saint-Louis Agglomération"),
    ("data.grandparissud.fr", "Grand Paris Sud"),
    ("saint-jean-de-luz-opendatapaysbasque.opendatasoft.com", "Ville de Saint-Jean-de-Luz"),
    ("data.haute-garonne.fr", "Département de la Haute-Garonne"),
    ("data.capatlantique.fr", "Cap Atlantique"),
    ("data.regionreunion.com", "Région Réunion"),
    ("data.maine-et-loire.fr", "Département de Maine-et-Loire"),
    ("data.seinesaintdenis.fr", "Département de Seine-Saint-Denis"),
    ("data.orleans-metropole.fr", "Orléans Métropole"),
    ("data.larochesuryon.fr", "La Roche-sur-Yon Agglomération"),
    ("data.montreuil.fr", "Ville de Montreuil"),
    ("data.sicoval.fr", "Sicoval"),
    ("data.cceg.fr", "Communauté de communes Erdre et Gesvres"),
    ("aix-en-provence.opendatasoft.com", "Ville d'Aix-en-Provence"),
    ("cachan.opendatasoft.com", "Ville de Cachan"),
    ("bayonne-opendatapaysbasque.opendatasoft.com", "Ville de Bayonne"),
    ("data.combs-la-ville.fr", "Ville de Combs-la-Ville"),
    ("data.fleurysurorne.fr", "Ville de Fleury-sur-Orne"),
    ("data.ville-cesson.fr", "Ville de Cesson"),
    ("data.ville-bondoufle.fr", "Ville de Bondoufle"),
    ("data.moissy-cramayel.fr", "Ville de Moissy-Cramayel"),
    ("lisses-grandparissud.opendatasoft.com", "Ville de Lisses"),
    ("nandy-grandparissud.opendatasoft.com", "Ville de Nandy"),
    ("saintgermainlescorbeil-grandparissud.opendatasoft.com", "Ville de Saint-Germain-lès-Corbeil"),
    # Repérés le 21/08/2026 en partant des collectivités ABSENTES du site plutôt
    # que des portails connus : on prend les plus grosses communes sans donnée
    # (Nice, Montpellier, Bordeaux, Lille…) et on teste leur portail. Aucun ne
    # figurait dans le fédérateur ni dans data.gouv.fr sous une forme lisible.
    # Résultat : six portails, dont DEUX DÉPARTEMENTS entiers.
    ("opendata.bordeaux-metropole.fr", "Bordeaux Métropole"),
    ("opendata.hauts-de-seine.fr", "Département des Hauts-de-Seine"),
    ("opendata.aude.fr", "Département de l'Aude"),
    ("data.seineouest.fr", "Grand Paris Seine Ouest"),
    ("data.issy.com", "Ville d'Issy-les-Moulineaux"),
    ("data.bourgesplus.fr", "Bourges Plus"),
]

RECHERCHES = ['search(title,"subvention")', 'search(title,"subventions")',
              'search(dataset_id,"subvention")']

# Le fédérateur Opendatasoft est international : il sert aussi des portails
# belges, suisses ou canadiens. Ce site cartographie les subventions publiques
# EN FRANCE ; les jeux d'autres pays sont écartés au moissonnage plutôt que
# filtrés plus tard, pour ne pas les traîner dans toute la chaîne.
PUBLIEURS_HORS_FRANCE = ("wallonie", "bruxelles", "belgique", "belgium",
                         "suisse", "geneve", "vaud", "quebec", "montreal",
                         "luxembourg", "ontario", "canada")

MAX_LIGNES = 400_000       # au-delà, ce n'est pas une liste de subventions
MIN_OCTETS = 200
PAUSE = 0.7                # respiration entre deux appels au même portail

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json", "User-Agent": "dons-aux-associations/pipeline"})


def api(hote, chemin, **params):
    url = f"https://{hote}/api/explore/v2.1/{chemin}"
    for essai in range(3):
        try:
            r = SESSION.get(url, params=params, timeout=90)
            if r.status_code == 429:
                time.sleep(4 * (essai + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if essai == 2:
                raise
            time.sleep(2 * (essai + 1))
    return {}


def jeux_du_portail(hote):
    """Jeux candidats d'un portail, dédupliqués par identifiant."""
    trouves = {}
    for ou in RECHERCHES:
        depart = 0
        while depart < 300:
            try:
                d = api(hote, "catalog/datasets", where=ou, limit=100, offset=depart)
            except Exception as e:
                print(f"      {ou[:28]} : {str(e)[:50]}")
                break
            resultats = d.get("results", [])
            for r in resultats:
                trouves.setdefault(r["dataset_id"], r)
            if len(resultats) < 100:
                break
            depart += 100
            time.sleep(PAUSE)
        time.sleep(PAUSE)
    return trouves


def champs_de(jeu):
    return [f.get("name") for f in jeu.get("fields", []) if f.get("name")]


def telecharger(hote, jeu_id, chemin):
    """Export CSV du jeu, en flux."""
    url = f"https://{hote}/api/explore/v2.1/catalog/datasets/{urllib.parse.quote(jeu_id)}/exports/csv"
    with SESSION.get(url, params={"delimiter": ";"}, stream=True, timeout=600) as r:
        r.raise_for_status()
        tmp = chemin + ".part"
        with open(tmp, "wb") as f:
            for bloc in r.iter_content(1 << 18):
                f.write(bloc)
        os.replace(tmp, chemin)


def traiter_portail(hote, editeur, force=False, limite=None):
    print(f"\n  {editeur} ({hote})")
    try:
        jeux = jeux_du_portail(hote)
    except Exception as e:
        print(f"      injoignable : {str(e)[:60]}")
        return []
    print(f"      {len(jeux)} jeux candidats")

    fiches = []
    for jeu_id, jeu in list(jeux.items())[:limite]:
      try:
        meta = jeu.get("metas", {}).get("default", {})
        champs = champs_de(jeu)
        nb = meta.get("records_count") or 0

        publieur = C.fold(meta.get("publisher") or "")
        if any(m in publieur for m in PUBLIEURS_HORS_FRANCE):
            fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                           "titre": meta.get("title"), "retenu": False,
                           "raison": "hors de France", "lignes": nb})
            continue

        # Validation SUR LES CHAMPS DU CATALOGUE : rien n'est téléchargé tant
        # que le jeu n'a pas prouvé qu'il décrit des subventions.
        valide, raison = C.porte_des_subventions(champs)
        if not valide:
            fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                           "titre": meta.get("title"), "retenu": False,
                           "raison": raison, "champs": champs[:16], "lignes": nb})
            continue
        if not nb:
            fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                           "titre": meta.get("title"), "retenu": False,
                           "raison": "jeu vide", "champs": champs[:16], "lignes": 0})
            continue
        if nb > MAX_LIGNES:
            fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                           "titre": meta.get("title"), "retenu": False,
                           "raison": f"trop volumineux ({nb} lignes)", "lignes": nb})
            continue

        nom = hashlib.sha1(f"{hote}|{jeu_id}".encode()).hexdigest()[:12] + ".csv"
        chemin = os.path.join(RAW, nom)
        if not (os.path.exists(chemin) and not force and os.path.getsize(chemin) > MIN_OCTETS):
            try:
                telecharger(hote, jeu_id, chemin)
                time.sleep(PAUSE)
            except Exception as e:
                fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                               "titre": meta.get("title"), "retenu": False,
                               "raison": "téléchargement : " + str(e)[:60], "lignes": nb})
                continue

        # Un export peut réussir en HTTP et ne rien produire : on ne suppose
        # jamais que le fichier est là.
        if not os.path.exists(chemin) or os.path.getsize(chemin) < MIN_OCTETS:
            if os.path.exists(chemin):
                os.remove(chemin)
            fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                           "titre": meta.get("title"), "retenu": False,
                           "raison": "export vide", "lignes": nb})
            continue

        # Second contrôle sur l'en-tête réel : le catalogue peut mentir.
        try:
            entete, _, infos = C.read_rows(chemin)
        except Exception as e:
            fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                           "titre": meta.get("title"), "retenu": False,
                           "raison": "illisible : " + str(e)[:50], "lignes": nb})
            continue
        valide, raison = C.porte_des_subventions(entete)
        if not valide:
            if os.path.exists(chemin):
                os.remove(chemin)
            fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                           "titre": meta.get("title"), "retenu": False,
                           "raison": "en-tête réel : " + raison, "champs": entete[:16], "lignes": nb})
            continue

        with open(chemin, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        fiches.append({
            "portail": hote, "editeur": editeur, "dataset_id": jeu_id,
            "publieur": meta.get("publisher"),
            "titre": meta.get("title"), "retenu": True,
            "page": f"https://{hote}/explore/dataset/{jeu_id}/",
            "licence": meta.get("license"), "modifie": meta.get("modified"),
            "fichier": os.path.relpath(chemin, ROOT), "octets": os.path.getsize(chemin),
            "sha256": sha, "encodage": infos["encoding"], "separateur": infos["delimiter"],
            "lignes": nb, "colonnes": entete,
        })
        print(f"      + {nb:>7} lignes  {(meta.get('title') or '')[:56]}")
      except Exception as e:
        # Un jeu défaillant ne doit pas emporter le portail entier.
        fiches.append({"portail": hote, "editeur": editeur, "dataset_id": jeu_id,
                       "retenu": False, "raison": "erreur : " + str(e)[:70]})
    return fiches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portail", help="n'en moissonner qu'un")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limite", type=int, help="borner le nombre de jeux par portail")
    args = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)
    portails = [(h, e) for h, e in PORTAILS if not args.portail or h == args.portail]
    print(f"Moissonnage Opendatasoft — {len(portails)} portails")

    toutes = []
    for hote, editeur in portails:
        toutes.extend(traiter_portail(hote, editeur, args.force, args.limite))

    # UN MOISSONNAGE PARTIEL NE DOIT PAS EFFACER LE RESTE. `--portail` écrivait
    # un manifeste ne contenant que le portail demandé : les 46 autres
    # disparaissaient du manifeste, donc de la normalisation, donc du site —
    # sans erreur ni avertissement. On fusionne désormais avec l'existant, en
    # remplaçant seulement ce qui vient des portails effectivement visités.
    ancien = {}
    if args.portail and os.path.exists(MANIFEST):
        ancien = json.load(open(MANIFEST, encoding="utf-8"))
    visites = {h for h, _ in portails}
    garde = lambda x: (x.get("portail") not in visites)
    toutes = ([x for x in ancien.get("datasets", []) if garde(x)]
              + [x for x in ancien.get("ecartes", []) if garde(x)]
              + toutes)
    portails_manifeste = ({(p["hote"], p["editeur"]) for p in ancien.get("portails", [])}
                          | set(portails)) if ancien else set(portails)

    retenus = [f for f in toutes if f.get("retenu")]
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({
            "family": "ods",
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "portails": [{"hote": h, "editeur": e} for h, e in sorted(portails_manifeste)],
            "jeux_examines": len(toutes),
            "jeux_retenus": len(retenus),
            "lignes_annoncees": sum(f.get("lignes") or 0 for f in retenus),
            "datasets": sorted(retenus, key=lambda x: -(x.get("lignes") or 0)),
            "ecartes": [f for f in toutes if not f.get("retenu")],
        }, f, ensure_ascii=False, indent=2)
        f.write("\n")

    raisons = {}
    for f in toutes:
        if not f.get("retenu"):
            raisons[f["raison"][:44]] = raisons.get(f["raison"][:44], 0) + 1
    print(f"\n  jeux examinés .... {len(toutes)}")
    print(f"  jeux retenus ..... {len(retenus)}")
    print(f"  lignes annoncées . {sum(f.get('lignes') or 0 for f in retenus):,}")
    print("\n  principales raisons d'écarter :")
    for r, n in sorted(raisons.items(), key=lambda x: -x[1])[:6]:
        print(f"    {n:>4}  {r}")
    print(f"\n  -> {os.path.relpath(MANIFEST, ROOT)}")


if __name__ == "__main__":
    main()
