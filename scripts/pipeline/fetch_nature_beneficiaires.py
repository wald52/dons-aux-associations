"""Référentiel de la NATURE JURIDIQUE des bénéficiaires — SIRENE + Journal officiel.

Le site comptait 49,88 Md€ comme « association » sur une DEVINETTE : quand la
source ne déclarait rien, le défaut était « association ». Mesuré le 26/08/2026
en joignant SIRENE à la table canonique, le prix de cette devinette est de
**37,68 Md€ versés à des bénéficiaires qui ne sont pas des associations** — SNCF
Voyageurs, l'AFP, le Pass Culture, l'ASP, le CNC, France Travail, le musée du
Louvre.

Ce script cesse de deviner là où un registre déclare. Deux sources, deux rôles :

  * **SIRENE**, fichier `StockUniteLegale` (Licence Ouverte, 29 922 486 unités
    légales dont 1 513 037 associations) donne `categorieJuridiqueUniteLegale`,
    c'est-à-dire la FORME JURIDIQUE. C'est lui qui décide de la frontière.
    Il porte aussi `identifiantAssociationUniteLegale`, le numéro RNA — que le
    fichier RNA du ministère de l'Intérieur, lui, ne relie JAMAIS à un SIRET
    (0 sur 3 312 dans l'Allier : vérifié, il ne fait pas le pont).
  * **Le Journal officiel** (dépôts de comptes annuels, `source='dca'`) donne le
    TYPE DÉCLARÉ au dépôt. Lui seul sépare fondation, fondation d'entreprise et
    fonds de dotation, que la catégorie juridique confond dans un seul code
    9300. Il couvre 94,6 % du montant des fondations du site, et type au total
    76,2 % du montant associatif.

**On n'écrit que les SIREN que le site utilise vraiment.** Le fichier SIRENE
complet pèse 705 Mo ; les 216 052 SIREN de bénéficiaires du site en font
quelques Mo, versionnables sans faire dépasser la limite de GitHub Pages. Le
prix : il faut rejouer ce script quand de nouveaux bénéficiaires entrent.

DuckDB lit le Parquet distant en HTTP Range : le fichier de 705 Mo n'est jamais
téléchargé en entier.

Usage :
    python3 scripts/pipeline/fetch_nature_beneficiaires.py [--force]

Sortie : data/referentiel/nature-beneficiaires.parquet
         data/sources-manifest/nature-beneficiaires.json
"""

import argparse
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
SORTIE = os.path.join(ROOT, "data", "referentiel", "nature-beneficiaires.parquet")
MANIFEST = os.path.join(ROOT, "data", "sources-manifest", "nature-beneficiaires.json")
CANONIQUE = os.path.join(ROOT, "data", "canonical", "subventions", "*", "*.parquet")

DGF = "https://www.data.gouv.fr/api/1/datasets/"
JEU_SIRENE = "base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret"

HOTE_JO = "journal-officiel-datadila.opendatasoft.com"
JEU_JO = "jo_associations"
# `dca` = dépôts de comptes annuels (227 738). `joafe`, les 5,4 millions
# d'annonces de création et de dissolution, ne nous apprend pas la nature.
FILTRE_JO = "source='dca'"
CHAMPS_JO = "dca_siren,numero_rna,association_type_libelle"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "dons-aux-associations/pipeline"


def url_sirene():
    """Adresse du StockUniteLegale en Parquet, millésime courant.

    On la redemande à data.gouv.fr à chaque fois plutôt que de la figer : le
    fichier est remplacé tous les mois et son URL porte l'horodatage du dépôt.
    """
    r = SESSION.get(DGF + JEU_SIRENE + "/", timeout=120)
    r.raise_for_status()
    for res in r.json().get("resources", []):
        titre = res.get("title") or ""
        if ("StockUniteLegale" in titre and "parquet" in titre.lower()
                and "Historique" not in titre):
            return res["url"], titre
    raise SystemExit("StockUniteLegale en Parquet introuvable sur data.gouv.fr")


def types_du_journal_officiel():
    """{siren: type}, {rna: type} — le type déclaré au dépôt des comptes.

    L'appariement se fera par SIREN **et** par RNA : SIRENE donne le RNA de
    72,7 % des associations, ce qui rattrape les bénéficiaires que le site ne
    connaît que par un identifiant et pas par l'autre.
    """
    import csv
    url = f"https://{HOTE_JO}/api/explore/v2.1/catalog/datasets/{JEU_JO}/exports/csv"
    params = {"where": FILTRE_JO, "select": CHAMPS_JO, "delimiter": ";"}
    for essai in range(3):
        try:
            r = SESSION.get(url, params=params, timeout=900)
            r.raise_for_status()
            break
        except Exception as e:
            if essai == 2:
                raise
            print(f"  … reprise du Journal officiel ({e})", flush=True)
            time.sleep(4 * (essai + 1))
    par_siren, par_rna = {}, {}
    lecteur = csv.DictReader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";")
    lignes = 0
    for ligne in lecteur:
        lignes += 1
        t = (ligne.get("association_type_libelle") or "").strip()
        if not t:
            continue
        siren = (ligne.get("dca_siren") or "").strip()
        rna = (ligne.get("numero_rna") or "").strip()
        # `setdefault` : un organisme dépose plusieurs exercices, le premier
        # type rencontré suffit — ils ne varient pas d'un dépôt à l'autre.
        if siren:
            par_siren.setdefault(siren, t)
        if rna:
            par_rna.setdefault(rna, t)
    return par_siren, par_rna, lignes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="refait le référentiel même s'il existe déjà")
    args = ap.parse_args()
    if os.path.exists(SORTIE) and not args.force:
        print(f"{SORTIE} existe déjà — --force pour le refaire.")
        return

    import duckdb
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    print("SIREN de bénéficiaires présents dans la table canonique…", flush=True)
    con.execute(f"""
        CREATE TABLE utiles AS
        SELECT DISTINCT beneficiary_siren AS siren
        FROM read_parquet('{CANONIQUE}', hive_partitioning=1)
        WHERE beneficiary_siren IS NOT NULL AND length(beneficiary_siren) = 9
    """)
    n_utiles = con.execute("SELECT count(*) FROM utiles").fetchone()[0]
    print(f"  {n_utiles:,} SIREN à documenter")

    url, titre = url_sirene()
    print(f"SIRENE : {titre}", flush=True)
    t0 = time.time()
    con.execute(f"""
        CREATE TABLE sirene AS
        SELECT s.siren,
               CAST(s.categorieJuridiqueUniteLegale AS INTEGER) AS categorie_juridique,
               s.identifiantAssociationUniteLegale AS rna_insee,
               s.denominationUniteLegale AS denomination_insee
        FROM read_parquet('{url}') s
        JOIN utiles u ON u.siren = s.siren
    """)
    n_sirene = con.execute("SELECT count(*) FROM sirene").fetchone()[0]
    print(f"  {n_sirene:,} SIREN retrouvés dans SIRENE "
          f"({100 * n_sirene / max(n_utiles, 1):.1f} %) en {time.time() - t0:.0f} s")

    print("Journal officiel : dépôts de comptes annuels…", flush=True)
    jo_siren, jo_rna, n_depots = types_du_journal_officiel()
    print(f"  {n_depots:,} dépôts, {len(jo_siren):,} SIREN typés, "
          f"{len(jo_rna):,} RNA typés")

    lignes = con.execute("""
        SELECT siren, categorie_juridique, rna_insee, denomination_insee FROM sirene
    """).fetchall()

    import pyarrow as pa
    import pyarrow.parquet as pq
    siren_c, cj_c, rna_c, nom_c, jo_c, fam_c, asso_c = [], [], [], [], [], [], []
    apparie_siren = apparie_rna = 0
    for siren, cj, rna, nom in lignes:
        type_jo = jo_siren.get(siren)
        if type_jo:
            apparie_siren += 1
        elif rna and jo_rna.get(rna):
            type_jo = jo_rna[rna]
            apparie_rna += 1
        siren_c.append(siren)
        cj_c.append(cj)
        rna_c.append(rna)
        nom_c.append(nom)
        jo_c.append(type_jo)
        asso_c.append(C.est_associatif(cj))
        fam_c.append(C.famille_du_beneficiaire(cj, type_jo))

    table = pa.table({
        "siren": pa.array(siren_c, pa.string()),
        "categorie_juridique": pa.array(cj_c, pa.int32()),
        "rna_insee": pa.array(rna_c, pa.string()),
        "denomination_insee": pa.array(nom_c, pa.string()),
        "type_jo": pa.array(jo_c, pa.string()),
        "est_associatif": pa.array(asso_c, pa.bool_()),
        "famille": pa.array(fam_c, pa.string()),
    })
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    pq.write_table(table, SORTIE, compression="zstd")
    octets = os.path.getsize(SORTIE)

    n_asso = sum(1 for a in asso_c if a is True)
    n_non = sum(1 for a in asso_c if a is False)
    n_rna = sum(1 for r in rna_c if r)
    print(f"\n{SORTIE} — {octets / 1e6:.1f} Mo, {len(siren_c):,} SIREN")
    print(f"  associatifs      : {n_asso:,} ({100 * n_asso / max(len(siren_c), 1):.1f} %)")
    print(f"  NON associatifs  : {n_non:,} ({100 * n_non / max(len(siren_c), 1):.1f} %)")
    print(f"  avec un RNA      : {n_rna:,}")
    print(f"  typés par le JO  : {apparie_siren + apparie_rna:,} "
          f"(dont {apparie_rna:,} par le RNA seul)")

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump({
            "genere_le": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sirene": {"jeu": JEU_SIRENE, "ressource": titre, "url": url,
                       "licence": "Licence Ouverte 2.0",
                       "siren_demandes": n_utiles, "siren_retrouves": n_sirene},
            "journal_officiel": {"hote": HOTE_JO, "jeu": JEU_JO, "filtre": FILTRE_JO,
                                 "licence": "Licence Ouverte 2.0",
                                 "depots": n_depots, "siren_types": len(jo_siren),
                                 "rna_types": len(jo_rna),
                                 "apparies_par_siren": apparie_siren,
                                 "apparies_par_rna": apparie_rna},
            "frontiere": ("associations INSEE 92xx (groupements d'employeurs et "
                          "associations d'utilité publique compris) + fondations 9300 "
                          "(fondations d'entreprise et fonds de dotation) — décision "
                          "de l'utilisateur du 26/08/2026"),
            "associatifs": n_asso, "non_associatifs": n_non,
            "sans_verdict": len(siren_c) - n_asso - n_non,
            "octets": octets,
        }, f, ensure_ascii=False, indent=1)
    print(f"{MANIFEST} écrit.")


if __name__ == "__main__":
    main()
