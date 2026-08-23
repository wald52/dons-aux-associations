"""L'angle mort : les associations que le site ne voit pas.

Le site sait dire qui a reçu quoi, parmi ce qu'il a. Il n'a jamais su dire
combien d'associations lui échappent — et une carte de couverture qui ne parle
que de collectivités ne le dit pas non plus.

Les comptes annuels déposés au Journal officiel donnent cette mesure. Toute
association ou fondation recevant plus de 153 000 € de dons et/ou de
subventions publiques doit déposer ses comptes (art. L612-4 et D612-5 du code
de commerce). La liste de ces dépôts est donc, à la fois :

  - une liste d'organismes qui ont manifestement franchi un seuil de
    financement, exhaustive par construction (l'obligation ne dépend d'aucune
    politique d'open data) ;
  - et l'annuaire le plus proche qui existe d'une « liste des associations
    financées ».

CE QU'ON EN FAIT : on croise les SIREN et les RNA de ces dépôts avec l'index
des bénéficiaires du site. Ce qui ne se croise pas est l'angle mort, chiffré.

CE QU'ON N'EN FAIT PAS : aucun montant. Les montants sont dans les PDF
déposés, qui sont pour la plupart des scans (mesuré : 2 sur 24 contiennent le
mot « subvention » en clair). Les lire demanderait un OCR, donc un chiffre
deviné par une machine sur une image.

DEUX RÉSERVES QUI VONT EN SENS CONTRAIRE, et qu'il faut dire ensemble :

  1. le seuil de 153 000 € mélange dons PRIVÉS et subventions PUBLIQUES : une
     association qui dépose ses comptes n'a pas forcément touché d'argent
     public. L'angle mort mesuré est donc un MAJORANT ;
  2. l'appariement ne se fait que sur des identifiants (SIREN, RNA), jamais sur
     le nom — un bénéficiaire du site sans identifiant ne peut pas se
     reconnaître dans un dépôt, et compte donc comme « non vu » à tort. Cela
     tire dans l'autre sens.

Ne jamais présenter le résultat comme « X associations subventionnées
manquent » : c'est « X organismes tenus de déposer leurs comptes n'ont pu être
reconnus dans les données du site ».

Usage :
    python3 scripts/pipeline/build_angle_mort.py

Entrées : data/raw/jo/comptes-annuels.csv (cf. fetch_jo_comptes.py)
          data/recherche/noms.json.gz + data/recherche/ids/
Sorties : data/canonical/angle-mort.json (versionné)
          data/aggregates/angle-mort.json.gz (servi au navigateur)
"""

import collections
import csv
import glob
import gzip
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import common as C

ROOT = C.ROOT
JO = os.path.join(ROOT, "data", "raw", "jo", "comptes-annuels.csv")
MANIFEST_JO = os.path.join(ROOT, "data", "sources-manifest", "jo-comptes.json")
INDEX = os.path.join(ROOT, "data", "recherche")
OUT_DETAIL = os.path.join(ROOT, "data", "canonical", "angle-mort.json")
OUT_WEB = os.path.join(ROOT, "data", "aggregates", "angle-mort.json.gz")

RESERVES = [
    "Le seuil de 153 000 € qui déclenche le dépôt mélange dons privés et "
    "subventions publiques : déposer ses comptes ne prouve pas un financement "
    "public. Le nombre d'organismes « non vus » est donc un majorant.",
    "L'appariement se fait sur les identifiants légaux (SIREN, RNA), jamais sur "
    "le nom : deux organismes homonymes ne sont pas confondus, mais un "
    "bénéficiaire du site dépourvu d'identifiant ne peut pas être reconnu.",
    "Un organisme reconnu ne l'est pas forcément pour le bon exercice : le "
    "croisement porte sur l'identité, pas sur l'année.",
]


CAUSES = [
    ("nom_et_departement",
     "Reconnu par son nom et son département, sans identifiant commun",
     "Le site connaît un bénéficiaire du même nom normalisé dans le même "
     "département. C'est la règle d'identité que le site s'applique déjà à "
     "lui-même quand une source ne donne pas de SIREN."),
    ("financement_prive",
     "Fonds de dotation ou fondation — vit de dons privés",
     "Un fonds de dotation dépose ses comptes quel que soit son financement : "
     "le seuil de 153 000 € compte les DONS autant que les subventions. Qu'il "
     "soit absent d'un site de subventions publiques est normal, pas une lacune."),
    ("nom_connu_ailleurs",
     "Nom connu du site, mais dans un autre département",
     "Le site connaît ce nom, rattaché ailleurs. Le Journal officiel donne le "
     "département du SIÈGE, le site celui de l'adresse publiée par le "
     "financeur : les deux divergent pour les organismes à établissements "
     "multiples. Rapprochement possible, jamais automatique."),
    ("territoire_sans_financeur",
     "Aucun financeur ne publie sur ce territoire",
     "Ni la commune, ni l'intercommunalité, ni le département, ni la région de "
     "cet organisme ne publient de subventions exploitables. Son absence "
     "n'apprend rien sur lui : elle redit la lacune de couverture."),
    ("territoire_peu_couvert",
     "Territoire dont le site connaît moins de 1 % des subventions communales",
     "Un financeur publie quelque part dans ce département, mais pas celui qui "
     "compte : le site y connaît moins d'un centième de ce que les communes "
     "déclarent verser. Une association financée par sa commune y est invisible "
     "par construction."),
    ("inexplique",
     "Aucune explication automatique",
     "Ni fonds de dotation, ni homonyme ailleurs, ni territoire muet. Deux "
     "lectures restent possibles, et AUCUNE DONNÉE PUBLIQUE NE PERMET DE "
     "TRANCHER : l'organisme vit de dons privés — le seuil de 153 000 € les "
     "compte — ou bien il reçoit de l'argent public que personne ne publie. "
     "Ce n'est pas une liste de travail : c'est la mesure de ce qu'on ignore."),
]


def territoires_sans_financeur():
    """Départements où AUCUN échelon ne publie de subventions exploitables.

    Un organisme situé là ne peut pas être connu du site, quel que soit son
    financement : ce n'est pas une information sur lui. La question se pose
    par TERRITOIRE et non par commune, parce qu'un département, une
    intercommunalité ou une région qui publie couvre les associations de tout
    son ressort.
    """
    chemin = os.path.join(ROOT, "data", "canonical", "couverture.json")
    if not os.path.exists(chemin):
        return set()
    cov = json.load(open(chemin, encoding="utf-8"))["niveaux"]
    ref = C.referentiel()

    couverts = set()
    for code in cov["departement"]["detail"]:
        couverts.add(code)
    for code, meta in cov["region"]["detail"].items():
        for dep, m in ref["departements"].items():
            if m.get("reg_code") == code:
                couverts.add(dep)
    # Un EPCI n'a pas de département au référentiel : on le lit dans ses
    # communes membres, qui portent son SIREN.
    dep_de_l_epci = {}
    for insee, m in ref["communes"].items():
        if m.get("siren_epci"):
            dep_de_l_epci.setdefault(m["siren_epci"], m.get("dep_code"))
    for siren in cov["epci"]["detail"]:
        if dep_de_l_epci.get(siren):
            couverts.add(dep_de_l_epci[siren])
    for insee in cov["commune"]["detail"]:
        if ref["communes"].get(insee, {}).get("dep_code"):
            couverts.add(ref["communes"][insee]["dep_code"])

    return {d for d in ref["departements"] if d not in couverts}


def parts_communales():
    """Part des subventions communales que le site connaît, par département."""
    chemin = os.path.join(ROOT, "data", "aggregates", "denominateur.json.gz")
    if not os.path.exists(chemin):
        return {}
    with gzip.open(chemin, "rt", encoding="utf-8") as f:
        d = json.load(f)
    return {dep: v.get("part_connue_pct")
            for dep, v in d.get("communes_par_departement", {}).items()}


def cause_de(o, noms_site, muets, parts):
    """Pourquoi cet organisme n'est-il pas reconnu ? Une cause, la première qui
    s'applique — l'ordre va du plus explicatif au moins explicatif.

    Aucune de ces causes n'est une devinette : chacune se lit dans une donnée
    du site ou du dépôt. La dernière n'explique rien et le dit.
    """
    nom_norm = C.normalize_name(o["titre"])
    dep = o["dep"]
    if nom_norm and dep and dep in noms_site.get(nom_norm, ()):
        return "nom_et_departement"
    if o["type"] and o["type"].startswith(("Fonds de dotation", "Fondation")):
        return "financement_prive"
    if nom_norm in noms_site:
        return "nom_connu_ailleurs"
    if dep and dep in muets:
        return "territoire_sans_financeur"
    part = parts.get(dep)
    if part is not None and part < 1:
        return "territoire_peu_couvert"
    return "inexplique"


def normaliser_rna(v):
    """Un RNA s'écrit W suivi de 9 caractères. Les sources l'écrivent sans le W."""
    v = (v or "").strip().upper()
    if not v:
        return None
    if not v.startswith("W"):
        v = "W" + v
    return v if len(v) == 10 else None


def index_du_site():
    """SIREN, RNA et couples (nom, département) connus du site.

    Lu dans l'index servi au navigateur, pas dans un fichier de travail à part :
    ce que cette page compare à l'angle mort doit être EXACTEMENT ce que le
    site montre, sans quoi le taux de reconnaissance décrirait un index qui
    n'existe plus.

    Le SIREN et le RNA ne sont pas stockés : ils SONT l'identifiant. La règle
    de `build_index_navigateur.benef_id` — « S »+siren, sinon « R »+rna, sinon
    « N »+empreinte — se relit dans l'autre sens sans rien deviner.

    Le RNA, lui, ne se relit pas dans l'identifiant quand le bénéficiaire est
    identifié par son SIREN : il vient de `rna.json.gz`, écrit pour cet usage.

    `nom_norm`, lui, est recalculé depuis le nom affiché. L'index ne le sert
    pas (2,6 Mo économisés sur chaque recherche), et le pliage est celui du
    pipeline, `C.normalize_name`. L'écart possible est marginal et va vers la
    sous-reconnaissance : le nom retenu par l'index est le plus fréquent des
    libellés, quand `nom_norm` venait du premier rencontré.
    """
    with gzip.open(os.path.join(INDEX, "noms.json.gz"), "rt", encoding="utf-8") as f:
        noms = json.load(f)
    with gzip.open(os.path.join(INDEX, "rna.json.gz"), "rt", encoding="utf-8") as f:
        creux = json.load(f)
    rna_par_rang = dict(zip(creux["i"], creux["v"]))
    ids = []
    for b in range(len(glob.glob(os.path.join(INDEX, "ids", "*.json.gz")))):
        with gzip.open(os.path.join(INDEX, "ids", f"{b:03d}.json.gz"),
                       "rt", encoding="utf-8") as f:
            ids.extend(json.load(f)["ids"])

    libelles = noms["n"].split("\n")
    deps = noms["d"].split("\n")
    sirens = {}
    rnas = {}
    par_nom = collections.defaultdict(set)
    for i, bid in enumerate(ids):
        nom = libelles[i]
        dep = deps[i] or None
        fiche = (nom, dep, float(noms["m"][i] or 0), noms["e"][i] or 0)
        nom_norm = C.normalize_name(nom)
        if nom_norm:
            par_nom[nom_norm].add(dep)
        if bid.startswith("S"):
            s = bid[1:]
            if len(s) == 9 and s.isdigit():
                sirens.setdefault(s, fiche)
        # Le RNA vient du fichier creux : un bénéficiaire identifié par son
        # SIREN en a souvent un aussi, et c'est parfois le seul par lequel un
        # déposant du Journal officiel se laisse reconnaître.
        r = normaliser_rna(rna_par_rang.get(i) or (bid[1:] if bid.startswith("R") else None))
        if r:
            rnas.setdefault(r, fiche)
    return sirens, rnas, par_nom


def main():
    print("Angle mort — les comptes déposés au Journal officiel\n")
    if not os.path.exists(JO):
        print("  export absent : lancer d'abord fetch_jo_comptes.py")
        return 1
    if not os.path.isdir(INDEX):
        print("  index absent : lancer d'abord build_index_navigateur.py")
        return 1

    sirens_site, rnas_site, noms_site = index_du_site()
    muets = territoires_sans_financeur()
    parts = parts_communales()
    print(f"  index du site : {len(sirens_site)} SIREN, {len(rnas_site)} RNA, "
          f"{len(noms_site)} noms distincts")
    print(f"  départements où aucun échelon ne publie : {len(muets)}")

    # Un organisme, pas un dépôt : une association qui dépose dix exercices ne
    # compte qu'une fois. La clé est le SIREN, seul identifiant présent sur
    # 99,8 % des dépôts.
    organismes = {}
    depots = 0
    sans_siren = 0
    with open(JO, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            depots += 1
            siren = (r.get("dca_siren") or "").strip()
            if len(siren) != 9 or not siren.isdigit():
                sans_siren += 1
                continue
            o = organismes.get(siren)
            an = (r.get("dca_datecloture") or "")[:4]
            if o is None:
                o = organismes[siren] = {
                    "titre": (r.get("titre") or "").strip(),
                    "rna": normaliser_rna(r.get("numero_rna")),
                    "dep": (r.get("departement_code") or "").strip(),
                    "type": (r.get("association_type_libelle") or "").strip(),
                    "depots": 0, "premier": an, "dernier": an,
                }
            o["depots"] += 1
            if an:
                o["premier"] = min(o["premier"] or an, an)
                o["dernier"] = max(o["dernier"] or an, an)
            if not o["rna"]:
                o["rna"] = normaliser_rna(r.get("numero_rna"))

    print(f"  Journal officiel : {depots} dépôts, {len(organismes)} organismes "
          f"({sans_siren} dépôts sans SIREN exploitable)")

    # --- le croisement -----------------------------------------------------
    vus_par_siren = vus_par_rna = 0
    par_departement = collections.defaultdict(lambda: [0, 0])   # [organismes, vus]
    par_type = collections.defaultdict(lambda: [0, 0])
    par_dernier_depot = collections.defaultdict(lambda: [0, 0])
    manquants_notables = []
    # La ventilation par CAUSE est le vrai produit de ce croisement. Une liste
    # de 12 938 noms n'est traitable par personne ; dire pourquoi chacun est
    # absent l'est, et se calcule sans le moindre arbitrage humain.
    par_cause = collections.Counter()
    exemples_cause = collections.defaultdict(list)
    for siren, o in organismes.items():
        fiche = sirens_site.get(siren)
        if fiche is not None:
            vus_par_siren += 1
        elif o["rna"] and o["rna"] in rnas_site:
            fiche = rnas_site[o["rna"]]
            vus_par_rna += 1
        vu = 1 if fiche is not None else 0
        o["vu"] = bool(vu)
        dep = o["dep"] or "??"
        par_departement[dep][0] += 1
        par_departement[dep][1] += vu
        par_type[o["type"] or "?"][0] += 1
        par_type[o["type"] or "?"][1] += vu
        par_dernier_depot[o["dernier"] or "?"][0] += 1
        par_dernier_depot[o["dernier"] or "?"][1] += vu
        if not vu:
            o["cause"] = cause_de(o, noms_site, muets, parts)
            par_cause[o["cause"]] += 1
            if len(exemples_cause[o["cause"]]) < 12 and o["depots"] >= 8:
                exemples_cause[o["cause"]].append(
                    {"nom": o["titre"], "departement": o["dep"],
                     "depots": o["depots"], "type": o["type"]})
        if not vu and o["depots"] >= 8:
            manquants_notables.append(
                {"siren": siren, "nom": o["titre"], "departement": o["dep"],
                 "depots": o["depots"], "exercices": [o["premier"], o["dernier"]],
                 "type": o["type"], "cause": o["cause"]})

    vus = vus_par_siren + vus_par_rna
    manque = len(organismes) - vus
    print(f"\n  reconnus dans le site : {vus} "
          f"({vus_par_siren} par SIREN, {vus_par_rna} par RNA seul)")
    print(f"  NON reconnus          : {manque} "
          f"({manque / len(organismes) * 100:.1f} % des organismes)")

    manquants_notables.sort(key=lambda m: (-m["depots"], m["nom"]))

    manifeste = json.load(open(MANIFEST_JO, encoding="utf-8"))
    entete = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {
            "hote": manifeste.get("hote"), "dataset": manifeste.get("dataset"),
            "url": manifeste.get("url"), "licence": manifeste.get("licence"),
            "moissonne_le": manifeste.get("fetched_at"),
            "seuil_legal_eur": manifeste.get("seuil_legal_eur"),
            "fondement": manifeste.get("fondement"),
        },
        "reserves": RESERVES,
        "depots": depots,
        "depots_sans_siren": sans_siren,
        "organismes": len(organismes),
        "reconnus": vus,
        "reconnus_par_siren": vus_par_siren,
        "reconnus_par_rna_seul": vus_par_rna,
        "non_reconnus": manque,
        "part_non_reconnus_pct": round(manque / len(organismes) * 100, 1),
        "index_du_site": {"siren": len(sirens_site), "rna": len(rnas_site)},
        "par_departement": {d: {"organismes": v[0], "reconnus": v[1],
                                "part_reconnus_pct": round(v[1] / v[0] * 100, 1)}
                            for d, v in sorted(par_departement.items())},
        "par_type": {t: {"organismes": v[0], "reconnus": v[1]}
                     for t, v in sorted(par_type.items(), key=lambda kv: -kv[1][0])},
        "causes": [
            {"cle": cle, "libelle": libelle, "explication": explication,
             "organismes": par_cause.get(cle, 0),
             "part_pct": round(par_cause.get(cle, 0) / manque * 100, 1) if manque else 0.0,
             "exemples": exemples_cause.get(cle, [])}
            for cle, libelle, explication in CAUSES],
        "departements_sans_financeur": len(muets),
        "par_dernier_exercice_depose": {a: {"organismes": v[0], "reconnus": v[1]}
                                        for a, v in sorted(par_dernier_depot.items())},
    }

    charge = dict(entete)
    charge["non_reconnus_deposant_au_moins_8_exercices"] = manquants_notables
    with open(OUT_DETAIL, "w", encoding="utf-8") as f:
        json.dump(charge, f, ensure_ascii=False, indent=1)
        f.write("\n")

    web = dict(entete)
    web["non_reconnus_deposant_au_moins_8_exercices"] = manquants_notables[:50]
    brut = json.dumps(web, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    os.makedirs(os.path.dirname(OUT_WEB), exist_ok=True)
    with gzip.GzipFile(OUT_WEB, "wb", compresslevel=9, mtime=0) as f:
        f.write(brut)

    print(f"  organismes non reconnus déposant 8 exercices ou plus : "
          f"{len(manquants_notables)}")
    print(f"\n  -> {os.path.relpath(OUT_DETAIL, ROOT)}")
    print(f"  -> {os.path.relpath(OUT_WEB, ROOT)} "
          f"({os.path.getsize(OUT_WEB)/1024:.1f} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
