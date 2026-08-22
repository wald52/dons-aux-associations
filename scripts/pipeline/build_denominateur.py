"""Le dénominateur : ce que les collectivités DÉCLARENT avoir versé.

Depuis la phase 1, le site répond à « qui a reçu quoi ». Il ne sait pas
répondre à « et combien manque-t-il ? », parce qu'il n'a jamais eu de
dénominateur : une commune absente pouvait aussi bien ne rien verser que ne
rien publier. La carte de couverture était binaire.

Les balances comptables DGFiP donnent ce dénominateur. Le compte 6574 —
« subventions de fonctionnement aux associations et autres personnes de droit
privé » — est renseigné par toutes les collectivités, qu'elles publient ou non
en open data. Ce script le rapproche, collectivité par collectivité et exercice
par exercice, de ce que le site connaît réellement.

CE QUI EST COMPARÉ, ET CE QUI NE L'EST PAS

  - Le dénominateur est un montant MANDATÉ (une dépense de l'exercice).
    Les totaux du site sont, eux, très majoritairement des montants VOTÉS.
    Les deux ne coïncident pas, et le site affiche déjà les deux mesures côte à
    côte sans jamais les sommer : le rapprochement montre donc les trois
    colonnes — déclaré, voté, payé — sans en additionner aucune.
  - Le compte 6574 n'entre JAMAIS dans la table canonique des subventions. Il
    ne nomme aucun bénéficiaire ; le mélanger aux versements nominatifs
    compterait deux fois le même argent.

TROIS RÉSERVES, à répéter partout où le chiffre s'affiche :

  1. « et autres personnes de droit privé » : le compte n'est pas purement
     associatif, il SURESTIME la part associative ;
  2. une subvention peut être imputée ailleurs (6568, 657362 vers un CCAS,
     subventions d'investissement au compte 204) : 6574 seul SOUS-ESTIME ;
  3. ces deux effets ne se compensent pas et ne sont pas mesurables ici.

Un ratio « le site connaît Y € sur X € » est donc un ORDRE DE GRANDEUR, jamais
une note. Il peut dépasser 100 % sans que rien ne soit faux : une collectivité
qui publie ses subventions d'investissement, ou qui vote plus qu'elle ne mandate,
dépasse mécaniquement son propre compte 6574.

Usage :
    python3 scripts/pipeline/build_denominateur.py

Entrées : data/raw/balances/*.csv (cf. fetch_balances.py)
Sorties : data/canonical/denominateur.json   (détail, versionné)
          data/aggregates/denominateur.json.gz (servi au navigateur)
"""

import collections
import csv
import gzip
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow.dataset as ds

import common as C
import build_couverture as BC

ROOT = C.ROOT
RAW = os.path.join(ROOT, "data", "raw", "balances")
MANIFEST = os.path.join(ROOT, "data", "sources-manifest", "balances.json")
CANON = os.path.join(ROOT, "data", "canonical", "subventions")
OUT_DETAIL = os.path.join(ROOT, "data", "canonical", "denominateur.json")
OUT_WEB = os.path.join(ROOT, "data", "aggregates", "denominateur.json.gz")

NIVEAUX = ("commune", "epci", "departement", "region")

RESERVES = [
    "Le compte 6574 s'intitule « subventions de fonctionnement aux associations "
    "ET AUTRES PERSONNES DE DROIT PRIVÉ » : il n'est pas purement associatif.",
    "Une subvention peut être imputée ailleurs (6568, 657362 vers un CCAS, "
    "subventions d'investissement au compte 204) : le compte 6574 seul sous-estime.",
    "Le dénominateur est un montant MANDATÉ ; les totaux du site sont très "
    "majoritairement des montants VOTÉS. Les colonnes ne s'additionnent jamais.",
    "Les balances des départements, des régions et des groupements à fiscalité "
    "propre ne remontent qu'à 2019 (2020 pour les régions) dans les jeux par "
    "nature ; seules les communes couvrent 2010-2025.",
]


# --------------------------------------------------------- le dénominateur ---

def _code_commune(ligne):
    """Code INSEE d'une commune, lu dans les colonnes `ndept` et `insee`.

    Attention : `insee` n'est PAS le code INSEE, ce sont ses TROIS DERNIERS
    chiffres. Le préfixe se lit dans `ndept`, qui change de forme d'un
    millésime à l'autre et n'est pas non plus un code INSEE :

      « 59 » (jusqu'en 2015) et « 059 » (depuis 2016) désignent le Nord ;
      « 02A » et « 02B » gardent la lettre de la Corse ;
      « 101 » à « 106 » sont des codes DGFiP d'outre-mer, sans rapport avec les
      codes INSEE 971 à 976 — 103 est la Martinique (972) et 102 la Guyane
      (973), l'ordre lui-même diffère.

    D'où la règle : au-delà de 100, le préfixe INSEE est « 97 » et le troisième
    chiffre est déjà dans `insee` (« 97 » + « 209 » = 97209, Fort-de-France).
    Vérifié sur les cinq collectivités d'outre-mer des exercices 2019 à 2023.
    `insee_from_parts` de common.py ne convient pas ici : il attend de vraies
    colonnes COG, et lisait « 015 » comme un département d'outre-mer.
    """
    dep = (ligne.get("ndept") or "").strip().upper()
    rang = (ligne.get("insee") or "").strip()
    if not dep or not rang:
        return None
    rang = rang.zfill(3)
    if dep.isdigit():
        n = int(dep)
        if n >= 100:
            return "97" + rang
        dep = str(n).zfill(2)
    else:
        dep = dep.lstrip("0")
    return dep + rang


# Les collectivités qui exercent les compétences d'un département sans en
# porter le SIREN. Ce ne sont pas des devinettes : chacune est créée par une loi
# qui dit exactement quel territoire elle couvre. Sans cette table, 1,03 Md€ de
# dépenses associatives d'outre-mer, de Corse et d'Alsace tombaient dans les
# non-rattachés.
#
# Les deux dernières couvrent DEUX départements et ne peuvent pas être coupées
# en deux : leur code est composite, et elles apparaissent comme une
# collectivité à part entière plutôt que réparties au jugé.
COLLECTIVITES_UNIQUES = {
    "229850003": ("976", "Département de Mayotte"),
    "200055507": ("972", "Collectivité territoriale de Martinique "
                         "(loi n° 2011-884)"),
    "200052678": ("973", "Collectivité territoriale de Guyane "
                         "(loi n° 2011-884)"),
    "200076958": ("2A+2B", "Collectivité de Corse — fusion des deux "
                           "départements (loi n° 2015-991, art. 30, "
                           "effet au 1er janvier 2018)"),
    "200094332": ("67+68", "Collectivité européenne d'Alsace — fusion du "
                           "Bas-Rhin et du Haut-Rhin (loi n° 2019-816, "
                           "effet au 1er janvier 2021)"),
}


def _code_departement(siren):
    """Code d'un département : la loi d'abord, sinon la règle du SIREN.

    La règle « 22 + code » est écrite une seule fois, dans `common.py` — elle
    sert aussi à la carte de couverture.
    """
    if siren in COLLECTIVITES_UNIQUES:
        return COLLECTIVITES_UNIQUES[siren][0]
    return C.code_departement_du_siren(siren)


def lire_balances():
    """(niveau, code) -> {exercice: [montant, budgets]}, et ce qui n'est pas rattaché.

    L'APPARIEMENT SE FAIT SUR LE SIREN, JAMAIS SUR LE LIBELLÉ DU BUDGET.
    Un budget annexe s'appelle « ECOLE MUSIQUE-LUDRES », « FEDER REUNION » ou
    « HIPPODROME - MARCQ-EN-BAROEUL » : son libellé ne nomme pas la
    collectivité, et son rang de commune est un pseudo-rang (9xx) qui ne
    correspond à rien dans le référentiel. Mais il porte le SIREN de la
    collectivité, qui figure aussi sur le budget principal, lui identifiable.

    D'où deux passes : la première résout ce qui se résout et note quel SIREN
    désigne quelle collectivité ; la seconde rattache le reste par ce SIREN.
    Rien n'est deviné — c'est la même personne morale, elle le dit elle-même.
    """
    manifeste = json.load(open(MANIFEST, encoding="utf-8"))
    ref = C.referentiel()
    # Le SIREN d'une région ne porte PAS son code INSEE : il est bâti sur le
    # département du chef-lieu (Île-de-France 237500079 → 75, Bretagne
    # 233500016 → 35), et les régions fusionnées de 2016 commencent par 20.
    # Leur identité se lit donc une seule fois dans le libellé, avec
    # l'appariement de la carte de couverture, puis se propage par le SIREN.
    index_region = BC.construire_index(ref["regions"], "nom")

    lignes = []
    for fiche in manifeste.get("datasets", []):
        chemin = os.path.join(ROOT, fiche.get("fichier", ""))
        if fiche.get("erreur") or not os.path.exists(chemin):
            continue
        echelon = fiche["echelon"]
        with open(chemin, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f, delimiter=";"):
                lignes.append((
                    echelon,
                    (r.get("exer") or "")[:4],
                    (r.get("siren") or "").strip(),
                    (r.get("lbudg") or "").strip(),
                    (r.get("ndept") or "").strip(),
                    float(r.get("sd") or 0) - float(r.get("sc") or 0),
                    _code_commune(r) if echelon == "commune" else None,
                ))

    # --- passe 1 : quel SIREN désigne quelle collectivité -------------------
    par_siren = {}
    votes_region = collections.defaultdict(collections.Counter)
    for echelon, an, siren, libelle, ndept, montant, code_commune in lignes:
        if not siren:
            continue
        cle = (echelon, siren)
        if cle in par_siren:
            continue
        if echelon == "commune":
            if code_commune in ref["communes"]:
                par_siren[cle] = code_commune
        elif echelon == "epci":
            if siren in ref["epci"]:
                par_siren[cle] = siren
        elif echelon == "departement":
            code = _code_departement(siren)
            if code in ref["departements"] or "+" in (code or ""):
                par_siren[cle] = code
        else:
            trouve = BC.meilleure_collectivite(libelle, index_region)
            if trouve:
                votes_region[siren][trouve] += 1
    for siren, votes in votes_region.items():
        par_siren[("region", siren)] = votes.most_common(1)[0][0]

    # --- passe 2 : tout rattacher ------------------------------------------
    declare = {n: collections.defaultdict(lambda: collections.defaultdict(
        lambda: [0.0, 0])) for n in NIVEAUX}
    noms = {n: {} for n in NIVEAUX}
    orphelins = collections.Counter()
    montant_orphelin = collections.Counter()
    orphelins_par_dep = collections.defaultdict(lambda: [0, 0.0])
    for echelon, an, siren, libelle, ndept, montant, code_commune in lignes:
        code = par_siren.get((echelon, siren))
        if code is None and echelon == "commune" and code_commune in ref["communes"]:
            code = code_commune
        if not code or not an:
            orphelins[echelon] += 1
            montant_orphelin[echelon] += montant
            # Le département, lui, est toujours connu : un budget non rattaché
            # à sa collectivité reste comptabilisé dans le total du territoire.
            orphelins_par_dep[_dep_de_ndept(ndept)][0] += 1
            orphelins_par_dep[_dep_de_ndept(ndept)][1] += montant
            continue
        case = declare[echelon][code][an]
        case[0] += montant
        case[1] += 1
        noms[echelon].setdefault(code, libelle)

    non_rattaches = {
        "lignes": dict(orphelins),
        "montant_eur": {k: round(v, 2) for k, v in montant_orphelin.items()},
        "par_departement": {d: [n, round(m, 2)]
                            for d, (n, m) in sorted(
                                (k, v) for k, v in orphelins_par_dep.items() if k)},
        "explication": (
            "Budgets dont la collectivité n'a pas pu être nommée sans deviner : "
            "communes fusionnées depuis (leur code INSEE historique n'est plus au "
            "référentiel) et budgets annexes à pseudo-rang dont le SIREN "
            "n'apparaît sur aucun budget principal identifiable. Leur montant "
            "reste compté dans le total du département."),
    }
    return declare, noms, non_rattaches


def _dep_de_ndept(ndept):
    """Code de département INSEE derrière le `ndept` DGFiP, ou None."""
    d = (ndept or "").strip().upper()
    if not d:
        return None
    if d.isdigit():
        n = int(d)
        # Les codes 101 à 106 sont des rangs DGFiP d'outre-mer : ils ne
        # portent pas le code INSEE du département, seul « 97 » est sûr.
        return None if n >= 100 else str(n).zfill(2)
    return d.lstrip("0")


# ------------------------------------------------------- ce que le site sait ---

def connu_du_site():
    """(niveau, code) -> {exercice: [vote, paye, lignes]}.

    Le rapprochement passe par le MÊME appariement que la carte de couverture :
    un donateur désigne au plus une collectivité, et aucune en cas d'homonymie.
    Le dénominateur ne peut donc pas afficher une couverture que la carte
    ignore, ni l'inverse.
    """
    t = ds.dataset(CANON, format="parquet", partitioning="hive").to_table(
        columns=["donor_level", "donor_name_norm", "donor_name_raw", "donor_siren",
                 "year", "amount_eur", "granularity", "measure",
                 "beneficiary_kind", "beneficiary_kind_provenance",
                 "purpose_norm", "quality_flags"])
    cols = {c: t.column(c).to_pylist() for c in t.column_names}

    ref = C.referentiel()
    index = {n: BC.construire_index(ref[cle], "nom") for n, cle in (
        ("commune", "communes"), ("epci", "epci"),
        ("departement", "departements"), ("region", "regions"))}
    cache = {}

    def code_de(niveau, libelle, siren):
        # Le SIREN d'abord quand il désigne le bon échelon : il ne souffre
        # d'aucune homonymie. Le nom ensuite, avec la règle de la couverture.
        if siren and len(siren) == 9:
            if niveau == "epci" and siren in ref["epci"]:
                return siren
            if niveau == "departement":
                code = C.code_departement_du_siren(siren)
                if code in ref["departements"]:
                    return code
            # Rien pour les régions : leur SIREN porte le département du
            # chef-lieu, pas le code de la région (cf. common.py).
        cle = (niveau, libelle)
        if cle not in cache:
            cache[cle] = BC.meilleure_collectivite(libelle, index[niveau])
        return cache[cle]

    connu = {n: collections.defaultdict(lambda: collections.defaultdict(
        lambda: [0.0, 0.0, 0])) for n in NIVEAUX}
    for i in range(t.num_rows):
        niveau = cols["donor_level"][i]
        if niveau not in NIVEAUX:
            continue
        an = cols["year"][i]
        if not an:
            continue
        libelle = cols["donor_name_norm"][i] or C.normalize_name(
            cols["donor_name_raw"][i] or "")
        code = code_de(niveau, libelle, cols["donor_siren"][i])
        if not code:
            continue
        nature = C.nature_du_concours(cols["purpose_norm"][i], cols["quality_flags"][i])[0]
        est_don = C.est_un_don(cols["granularity"][i], cols["beneficiary_kind"][i],
                               cols["beneficiary_kind_provenance"][i], nature)
        if not est_don:
            continue
        montant = cols["amount_eur"][i] or 0.0
        case = connu[niveau][code][str(an)]
        if cols["measure"][i] == "verse":
            case[1] += montant
        else:
            case[0] += montant
        case[2] += 1
    return connu


# ------------------------------------------------------------------ sortie ---

def main():
    print("Dénominateur — compte 6574 des balances DGFiP\n")
    if not os.path.exists(MANIFEST):
        print("  manifeste absent : lancer d'abord fetch_balances.py")
        return 1

    declare, noms, non_rattaches = lire_balances()
    print("  déclaré (balances) :")
    for n in NIVEAUX:
        total = sum(v[0] for codes in declare[n].values() for v in codes.values())
        print(f"    {n:12s} {len(declare[n]):>6} collectivités   {total/1e9:>7.2f} Md€")
    if non_rattaches["lignes"]:
        print(f"    non rattachés : {non_rattaches['lignes']} "
              f"({ {k: round(v/1e6, 1) for k, v in non_rattaches['montant_eur'].items()} } M€)")

    connu = connu_du_site()
    print("\n  connu du site (rapproché par le même appariement que la couverture) :")
    for n in NIVEAUX:
        vote = sum(v[0] for codes in connu[n].values() for v in codes.values())
        print(f"    {n:12s} {len(connu[n]):>6} collectivités   {vote/1e9:>7.2f} Md€ votés")

    ref = C.referentiel()
    univers = {"commune": len(ref["communes"]), "epci": len(ref["epci"]),
               "departement": len(ref["departements"]), "region": len(ref["regions"])}

    # --- détail versionné : une entrée par collectivité qui déclare ----------
    detail = {}
    resume = {}
    par_an_national = {n: collections.defaultdict(lambda: [0.0, 0, 0.0, 0.0])
                       for n in NIVEAUX}
    for niveau in NIVEAUX:
        entrees = {}
        declarants = comparables = 0
        for code, annees in declare[niveau].items():
            d = {a: round(v[0]) for a, v in sorted(annees.items())}
            total = sum(d.values())
            su = connu[niveau].get(code, {})
            vote = {a: round(v[0]) for a, v in sorted(su.items()) if v[0]}
            paye = {a: round(v[1]) for a, v in sorted(su.items()) if v[1]}
            if total > 0:
                declarants += 1
            if su:
                comparables += 1
            # Le rapprochement ne vaut que sur les exercices COMMUNS. Le site
            # cumule 2001-2027, les balances 2010-2025 (2019-2025 hors
            # communes) : comparer les deux totaux bruts ferait dire au site
            # qu'il connaît 160 % de ce que les régions déclarent.
            vote_periode = sum(m for a, m in vote.items() if a in d)
            paye_periode = sum(m for a, m in paye.items() if a in d)
            entrees[code] = {
                "nom": (ref["communes"] if niveau == "commune" else
                        ref["epci"] if niveau == "epci" else
                        ref["departements"] if niveau == "departement" else
                        ref["regions"]).get(code, {}).get("nom") or noms[niveau].get(code),
                "perimetre": (next((raison for _, (c, raison)
                                    in COLLECTIVITES_UNIQUES.items() if c == code), None)
                              if "+" in code else None),
                "declare_eur": total,
                "site_vote_eur_periode": vote_periode,
                "site_paye_eur_periode": paye_periode,
                "declare_par_exercice": d,
                "site_vote_par_exercice": vote,
                "site_paye_par_exercice": paye,
            }
            for a, v in annees.items():
                case = par_an_national[niveau][a]
                case[0] += v[0]
                case[1] += v[1]
            for a, v in su.items():
                if a in annees:
                    case = par_an_national[niveau][a]
                    case[2] += v[0]
                    case[3] += v[1]
        detail[niveau] = entrees
        total_declare = sum(e["declare_eur"] for e in entrees.values())
        total_connu = sum(e["site_vote_eur_periode"] for e in entrees.values())
        total_paye = sum(e["site_paye_eur_periode"] for e in entrees.values())
        exercices = sorted({a for e in entrees.values() for a in e["declare_par_exercice"]})
        resume[niveau] = {
            "univers": univers[niveau],
            "declarants": declarants,
            "part_univers_declarant": round(declarants / univers[niveau] * 100, 1),
            "connus_du_site": comparables,
            "part_declarants_connus": round(comparables / declarants * 100, 1) if declarants else 0.0,
            "exercices": [exercices[0], exercices[-1]] if exercices else [],
            "declare_eur": round(total_declare),
            "site_vote_eur": round(total_connu),
            "site_paye_eur": round(total_paye),
            "part_connue_pct": (round(total_connu / total_declare * 100, 1)
                                if total_declare > 0 else None),
        }
        print(f"    {niveau:12s} {declarants:>6} déclarants, {comparables:>4} connus du site "
              f"({resume[niveau]['part_declarants_connus']:>5.1f} %)")

    manifeste = json.load(open(MANIFEST, encoding="utf-8"))
    entete = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {
            "hote": manifeste.get("hote"),
            "jeux": manifeste.get("jeux"),
            "filtre": manifeste.get("filtre"),
            "licence": manifeste.get("licence"),
            "moissonne_le": manifeste.get("fetched_at"),
            "lignes": manifeste.get("lignes"),
        },
        "comptes": sorted({c for d in manifeste.get("datasets", [])
                           for c in d.get("comptes", {})}),
        "reserves": RESERVES,
        "resume": resume,
        "par_exercice": {n: {a: {"declare_eur": round(v[0]), "budgets": v[1],
                                 "site_vote_eur": round(v[2]),
                                 "site_paye_eur": round(v[3])}
                             for a, v in sorted(par_an_national[n].items())}
                         for n in NIVEAUX},
        "non_rattaches": non_rattaches,
    }
    charge = dict(entete)
    charge["niveaux"] = detail
    with open(OUT_DETAIL, "w", encoding="utf-8") as f:
        json.dump(charge, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")

    # --- version servie : le résumé, les séries nationales, et le département
    # comme grain le plus fin. Le détail commune par commune pèse plusieurs
    # méga-octets : il reste dans data/canonical/, consultable hors ligne.
    par_dep = collections.defaultdict(lambda: {"declare_eur": 0, "site_vote_eur": 0,
                                               "declarants": 0, "connus": 0})
    for code, e in detail["commune"].items():
        dep = ref["communes"].get(code, {}).get("dep_code")
        if not dep:
            continue
        c = par_dep[dep]
        c["declare_eur"] += e["declare_eur"]
        c["site_vote_eur"] += e["site_vote_eur_periode"]
        c["declarants"] += 1 if e["declare_eur"] > 0 else 0
        c["connus"] += 1 if e["site_vote_par_exercice"] else 0
    for dep, c in par_dep.items():
        c["communes"] = sum(1 for m in ref["communes"].values() if m.get("dep_code") == dep)
        c["part_connue_pct"] = (round(c["site_vote_eur"] / c["declare_eur"] * 100, 1)
                                if c["declare_eur"] > 0 else None)

    web = dict(entete)
    web["communes_par_departement"] = dict(sorted(par_dep.items()))
    os.makedirs(os.path.dirname(OUT_WEB), exist_ok=True)
    brut = json.dumps(web, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with gzip.GzipFile(OUT_WEB, "wb", compresslevel=9, mtime=0) as f:
        f.write(brut)

    print(f"\n  -> {os.path.relpath(OUT_DETAIL, ROOT)} "
          f"({os.path.getsize(OUT_DETAIL)/1e6:.1f} Mo)")
    print(f"  -> {os.path.relpath(OUT_WEB, ROOT)} "
          f"({os.path.getsize(OUT_WEB)/1024:.1f} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
