"""Établit ce que le site sait et ne sait pas, collectivité par collectivité.

Sur un sujet d'argent public, un département gris doit pouvoir dire POURQUOI
il est gris. Trois états, jamais confondus :

  `donnees`        des subventions versées par cette collectivité sont dans la
                   table canonique ;
  `publie_non_lu`  elle publie bien un jeu de subventions sur data.gouv.fr,
                   mais aucun fichier exploitable n'en a été tiré (format,
                   colonnes absentes, lien mort) — la lacune est de notre côté ;
  `sans_donnees`   rien n'a été trouvé. Cela ne veut pas dire qu'elle ne verse
                   rien : le plus souvent, elle ne publie pas.

La couverture se mesure en POPULATION, pas en nombre de collectivités : les
34 936 communes vont de 3 habitants à 2,1 millions, et compter des fichiers
donnerait une image fausse de ce que le site couvre réellement.

Usage :
    python3 scripts/pipeline/build_couverture.py

Sortie : data/canonical/couverture.json (détail) et
         data/aggregates/couverture.json.gz (servi au navigateur)
"""

import collections
import gzip
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow.dataset as ds

import common as C

ROOT = C.ROOT
CANON = os.path.join(ROOT, "data", "canonical", "subventions")
MANIFEST_SCDL = os.path.join(ROOT, "data", "sources-manifest", "scdl.json")
OUT_DETAIL = os.path.join(ROOT, "data", "canonical", "couverture.json")
OUT_WEB = os.path.join(ROOT, "data", "aggregates", "couverture.json.gz")

NIVEAUX = ("commune", "epci", "departement", "region")


def donateurs_connus():
    """Ce que la table canonique contient, par niveau : noms pliés et SIREN."""
    t = ds.dataset(CANON, format="parquet", partitioning="hive").to_table(
        columns=["donor_level", "donor_name_norm", "donor_name_raw", "donor_siren",
                 "amount_eur", "granularity"])
    lvl = t.column("donor_level").to_pylist()
    norm = t.column("donor_name_norm").to_pylist()
    brut = t.column("donor_name_raw").to_pylist()
    siren = t.column("donor_siren").to_pylist()
    amt = t.column("amount_eur").to_pylist()
    gran = t.column("granularity").to_pylist()

    par_niveau = {n: {"noms": collections.defaultdict(lambda: [0, 0.0]),
                      "siren": set()} for n in NIVEAUX}
    hors = collections.defaultdict(lambda: [0, 0.0])
    for i in range(t.num_rows):
        cible = par_niveau.get(lvl[i])
        cle = norm[i] or C.normalize_name(brut[i] or "")
        montant = 0.0 if gran[i] == "aggregate" else (amt[i] or 0.0)
        if cible is None:
            c = hors[lvl[i]]
            c[0] += 1
            c[1] += montant
            continue
        v = cible["noms"][cle]
        v[0] += 1
        v[1] += montant
        if siren[i]:
            cible["siren"].add(siren[i])
    return par_niveau, {k: [v[0], round(v[1], 2)] for k, v in hors.items()}


def publications_reperees():
    """Noms pliés des organisations qui publient, d'après le moissonnage."""
    if not os.path.exists(MANIFEST_SCDL):
        return set(), set()
    m = json.load(open(MANIFEST_SCDL, encoding="utf-8"))
    lues = {C.normalize_name(d.get("organisation") or "") for d in m.get("datasets", [])}
    non_lues = {C.normalize_name(e.get("organisation") or "") for e in m.get("ecartes", [])}
    lues.discard("")
    non_lues.discard("")
    return lues, non_lues - lues


# --- appariement donateur -> collectivité -------------------------------------
#
# On part des DONATEURS (quelques dizaines) vers le référentiel, et non
# l'inverse. Le sens compte : chercher les collectivités dont le nom apparaît
# dans un libellé de donateur faisait apparier « Ville de Neuville-Saint-Rémy »
# aux dix-sept Saint-Rémy de France — la page affichait alors 140 communes
# couvertes pour 79 donateurs réels, soit l'inverse de ce qu'elle promettait.
#
# Règle : un donateur désigne AU PLUS UNE collectivité, celle dont le nom est
# le plus long à figurer dans son libellé. Le nom le plus long gagne parce
# qu'il est le plus spécifique : entre « Saint-Rémy » et « Neuville-Saint-Rémy »,
# c'est le second qui décrit le donateur.

# Comparaison par MOTS ENTIERS, sans seuil de longueur : un seuil éliminait
# l'Aube, le Cher, le Lot, Lyon ou Mèze, tandis qu'une comparaison par
# sous-chaîne aurait reconnu « Lot » dans « Charlotte ». Les mots règlent les
# deux problèmes d'un coup.

# Formes juridiques à retirer avant comparaison : le référentiel écrit
# « CA Grand Chambéry » là où la collectivité signe « Grand Chambéry ».
_FORME = re.compile(
    r"\b(CA|CC|CU|CD|SAN|SIVU|SIVOM|SM|EPT|METROPOLE|METROPOLE DE|COMMUNAUTE"
    r"|COMMUNAUTE D AGGLOMERATION|COMMUNAUTE DE COMMUNES|COMMUNAUTE URBAINE"
    r"|AGGLOMERATION|VILLE DE|VILLE D|COMMUNE DE|COMMUNE D|MAIRIE DE|MAIRIE D"
    r"|DEPARTEMENT DE|DEPARTEMENT DES|DEPARTEMENT DU|DEPARTEMENT D"
    r"|CONSEIL DEPARTEMENTAL DE|CONSEIL DEPARTEMENTAL DES|CONSEIL DEPARTEMENTAL DU"
    r"|CONSEIL GENERAL DE|CONSEIL GENERAL DU|CONSEIL REGIONAL DE|CONSEIL REGIONAL D"
    r"|REGION|GRAND|PAYS DE|PAYS D)\b", re.I)

# Un budget annexe n'est pas une collectivité distincte : « Métropole de Lyon
# budget annexe des eaux » désigne la Métropole de Lyon.
_BUDGET = re.compile(r"\bBUDGET\s+(PRINCIPAL|ANNEXE).*$", re.I)


def _mots(nom):
    """Mots significatifs d'un nom : sans forme juridique ni mots de liaison."""
    cle = C.normalize_name(nom)
    cle = _BUDGET.sub(" ", cle)
    cle = _FORME.sub(" ", cle)
    cle = re.sub(r"\b(DE|DES|DU|D|LA|LE|LES|L|EN|SUR|SOUS|AUX|ET)\b", " ", cle)
    return tuple(m for m in cle.split() if len(m) > 1)


def construire_index(table, champ_nom):
    """mots -> [codes] pour toutes les collectivités d'un échelon."""
    idx = collections.defaultdict(list)
    for code, meta in table.items():
        mots = _mots(meta.get(champ_nom) or "")
        if mots:
            idx[mots].append(code)
    return idx


def meilleure_collectivite(libelle_donateur, index):
    """Code de la collectivité que ce donateur désigne, ou None.

    Une collectivité correspond si TOUS ses mots figurent dans le libellé du
    donateur ; la plus spécifique l'emporte (le plus de mots). Retourne None
    dès que deux collectivités se disputent le même rang : mieux vaut ne rien
    affirmer que se tromper de commune.
    """
    mots = set(_mots(libelle_donateur))
    if not mots:
        return None
    exact = index.get(tuple(_mots(libelle_donateur)))
    if exact and len(exact) == 1:
        return exact[0]
    candidats = [(cle, codes) for cle, codes in index.items() if set(cle) <= mots]
    if not candidats:
        return None
    meilleur = max(len(cle) for cle, _ in candidats)
    finalistes = [(cle, codes) for cle, codes in candidats if len(cle) == meilleur]
    if len(finalistes) != 1 or len(finalistes[0][1]) != 1:
        return None
    return finalistes[0][1][0]


def main():
    print("Construction de la carte de couverture\n")
    ref = C.referentiel()
    par_niveau, hors = donateurs_connus()
    publiants, publiants_non_lus = publications_reperees()

    # Rattachement par SIREN, bien plus sûr que par nom quand il est possible.
    # Le référentiel indexe les EPCI par SIREN ; pour les départements et les
    # régions, la construction du SIREN donne le code (22 + code département,
    # 23 + code région), vérifiée sur le corpus.
    def sirens_du_niveau(niveau):
        return par_niveau[niveau]["siren"]

    def code_depuis_siren(siren, prefixe):
        if not siren or len(siren) != 9 or not siren.startswith(prefixe):
            return None
        return siren[2:4]

    couverts_par_siren = {"epci": set(), "departement": set(), "region": set()}
    for s_ in sirens_du_niveau("epci"):
        if s_ in ref["epci"]:
            couverts_par_siren["epci"].add(s_)
    for s_ in sirens_du_niveau("departement"):
        c = code_depuis_siren(s_, "22")
        if c and c in ref["departements"]:
            couverts_par_siren["departement"].add(c)
    for s_ in sirens_du_niveau("region"):
        c = code_depuis_siren(s_, "23")
        if c and c in ref["regions"]:
            couverts_par_siren["region"].add(c)

    resultat = {}
    resume = {}
    for niveau, table, champ_nom in (
        ("commune", ref["communes"], "nom"),
        ("epci", ref["epci"], "nom"),
        ("departement", ref["departements"], "nom"),
        ("region", ref["regions"], "nom"),
    ):
        noms_donateurs = par_niveau[niveau]["noms"]
        index = construire_index(table, champ_nom)

        # Chaque donateur désigne au plus une collectivité.
        apparies_par_code = collections.defaultdict(list)
        non_apparies = []
        for libelle in noms_donateurs:
            code_trouve = meilleure_collectivite(libelle, index)
            if code_trouve:
                apparies_par_code[code_trouve].append(libelle)
            else:
                non_apparies.append(libelle)

        # Mêmes règles pour savoir qui publie sans être exploité.
        publie_par_code = set()
        for libelle in publiants | publiants_non_lus:
            code_trouve = meilleure_collectivite(libelle, index)
            if code_trouve:
                publie_par_code.add(code_trouve)

        etats = {}
        pop_totale = pop_couverte = 0
        compte = collections.Counter()
        for code, meta in table.items():
            nom = meta.get(champ_nom) or ""
            pop = meta.get("population") or 0
            if isinstance(pop, list):
                pop = next((int(x) for x in reversed(pop) if x), 0)
            pop = int(pop or 0)
            pop_totale += pop

            apparies = apparies_par_code.get(code, [])
            lignes = sum(noms_donateurs[a][0] for a in apparies)
            montant = sum(noms_donateurs[a][1] for a in apparies)
            par_siren = code in couverts_par_siren.get(niveau, ())
            if apparies or par_siren:
                etat = "donnees"
                pop_couverte += pop
            elif code in publie_par_code:
                etat = "publie_non_lu"
            else:
                etat = "sans_donnees"
            compte[etat] += 1
            if etat != "sans_donnees":
                etats[code] = {"nom": nom, "etat": etat, "lignes": lignes,
                               "montant_eur": round(montant, 2), "population": pop}

        resultat[niveau] = {
            "univers": len(table),
            "par_etat": dict(compte),
            "population_totale": pop_totale,
            "population_couverte": pop_couverte,
            "part_population_couverte": round(pop_couverte / pop_totale * 100, 1) if pop_totale else None,
            "detail": etats,
        }
        resultat[niveau]["donateurs_dans_les_donnees"] = len(noms_donateurs)
        resultat[niveau]["donateurs_non_apparies"] = sorted(non_apparies)
        resume[niveau] = {
            "donateurs_dans_les_donnees": len(noms_donateurs),
            "donateurs_non_apparies": len(non_apparies),
            "univers": len(table),
            "avec_donnees": compte["donnees"],
            "publie_non_lu": compte["publie_non_lu"],
            "sans_donnees": compte["sans_donnees"],
            "part_population_couverte": resultat[niveau]["part_population_couverte"],
        }
        pct = resultat[niveau]["part_population_couverte"]
        print(f"  {niveau:12s} {compte['donnees']:>6} / {len(table):<6} avec données"
              f"   ({len(noms_donateurs)} donateurs dans les données,"
              f" {len(non_apparies)} non appariés)"
              + (f"   {pct:>5.1f} % pop." if pct is not None else ""))

    print(f"\n  rattachements par SIREN : "
          f"{len(couverts_par_siren['epci'])} EPCI, "
          f"{len(couverts_par_siren['departement'])} départements, "
          f"{len(couverts_par_siren['region'])} régions")

    charge = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "methode": ("Chaque libellé de donateur est rapproché du référentiel INSEE et "
                    "désigne AU PLUS UNE collectivité — en cas d'homonymie, aucune. "
                    "La couverture affichée est donc un minimum : un libellé inhabituel "
                    "échoue à s'apparier alors que la donnée existe, mais aucune "
                    "collectivité n'est comptée à tort."),
        "etats": {
            "donnees": "des subventions versées par cette collectivité sont présentes",
            "publie_non_lu": "elle publie un jeu de subventions, mais rien d'exploitable n'en a été tiré",
            "sans_donnees": "rien trouvé — le plus souvent, elle ne publie pas",
        },
        "niveaux": resultat,
        "donateurs_hors_referentiel": hors,
    }
    with open(OUT_DETAIL, "w", encoding="utf-8") as f:
        json.dump(charge, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Version servie au navigateur : le résumé et le détail des seuls échelons
    # que la carte peut montrer (départements et régions).
    moisson = {}
    if os.path.exists(MANIFEST_SCDL):
        m = json.load(open(MANIFEST_SCDL, encoding="utf-8"))
        moisson = {"jeux_examines": m.get("jeux_examines"),
                   "jeux_retenus": m.get("jeux_retenus"),
                   "fichiers_retenus": m.get("fichiers_retenus"),
                   "moissonne_le": m.get("fetched_at")}

    web = {
        "generated_at": charge["generated_at"],
        "moisson": moisson,
        "methode": charge["methode"],
        "etats": charge["etats"],
        "resume": resume,
        "departements": {c: [v["etat"], v["lignes"], round(v["montant_eur"])]
                         for c, v in resultat["departement"]["detail"].items()},
        "regions": {c: [v["etat"], v["lignes"], round(v["montant_eur"])]
                    for c, v in resultat["region"]["detail"].items()},
    }
    os.makedirs(os.path.dirname(OUT_WEB), exist_ok=True)
    brut = json.dumps(web, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.GzipFile(OUT_WEB, "wb", compresslevel=9, mtime=0) as f:
        f.write(brut)

    print(f"\n  donateurs hors référentiel : {dict(hors)}")
    print(f"  -> {os.path.relpath(OUT_DETAIL, ROOT)}")
    print(f"  -> {os.path.relpath(OUT_WEB, ROOT)} ({os.path.getsize(OUT_WEB)/1024:.1f} Ko)")


if __name__ == "__main__":
    main()
