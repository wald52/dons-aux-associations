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
          data/canonical/recherche/beneficiaires.parquet
Sorties : data/canonical/angle-mort.json (versionné)
          data/aggregates/angle-mort.json.gz (servi au navigateur)
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

import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
JO = os.path.join(ROOT, "data", "raw", "jo", "comptes-annuels.csv")
MANIFEST_JO = os.path.join(ROOT, "data", "sources-manifest", "jo-comptes.json")
INDEX = os.path.join(ROOT, "data", "canonical", "recherche", "beneficiaires.parquet")
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


def normaliser_rna(v):
    """Un RNA s'écrit W suivi de 9 caractères. Les sources l'écrivent sans le W."""
    v = (v or "").strip().upper()
    if not v:
        return None
    if not v.startswith("W"):
        v = "W" + v
    return v if len(v) == 10 else None


def index_du_site():
    """SIREN et RNA connus du site, avec de quoi décrire ce qu'il en sait."""
    t = pq.read_table(INDEX, columns=["siren", "rna", "nom", "dep_code",
                                      "montant_eur", "nb_echelons"])
    sirens = {}
    rnas = {}
    for siren, rna, nom, dep, montant, echelons in zip(
            t.column("siren").to_pylist(), t.column("rna").to_pylist(),
            t.column("nom").to_pylist(), t.column("dep_code").to_pylist(),
            t.column("montant_eur").to_pylist(), t.column("nb_echelons").to_pylist()):
        fiche = (nom, dep, montant or 0.0, echelons or 0)
        s = (siren or "").strip()
        if len(s) == 9 and s.isdigit():
            sirens.setdefault(s, fiche)
        r = normaliser_rna(rna)
        if r:
            rnas.setdefault(r, fiche)
    return sirens, rnas


def main():
    print("Angle mort — les comptes déposés au Journal officiel\n")
    if not os.path.exists(JO):
        print("  export absent : lancer d'abord fetch_jo_comptes.py")
        return 1
    if not os.path.exists(INDEX):
        print("  index absent : lancer d'abord build_search_index.py")
        return 1

    sirens_site, rnas_site = index_du_site()
    print(f"  index du site : {len(sirens_site)} SIREN, {len(rnas_site)} RNA")

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
        if not vu and o["depots"] >= 8:
            manquants_notables.append(
                {"siren": siren, "nom": o["titre"], "departement": o["dep"],
                 "depots": o["depots"], "exercices": [o["premier"], o["dernier"]],
                 "type": o["type"]})

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
