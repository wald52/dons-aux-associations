"""Normaliseur de la famille « ods » — jeux moissonnés sur les portails
Opendatasoft des collectivités.

Ces jeux ne suivent pas le standard SCDL : chaque portail nomme ses colonnes à
sa façon (`nom_beneficiaire` et `montant_vote` à Paris,
`nom_de_l_organisme_beneficiaire` et `montant_de_la_subvention` dans ses annexes
budgétaires). La reconnaissance passe donc par `common.trouver_colonne`,
partagée avec les autres moissonneurs.

Deux précautions propres à ces sources :

  - l'attribuant est rarement une colonne exploitable. Quand elle existe, elle
    contient parfois une valeur générique : la Ville de Paris publie
    « Ville » ou « Département » selon la collectivité qui verse — Paris étant
    les deux à la fois. On se rabat alors sur le PUBLIEUR du jeu, jamais sur
    le portail : sur le fédérateur Opendatasoft, celui-ci ne désigne personne ;
  - plusieurs jeux publient des AIDES EN NATURE dans une colonne voisine
    (`prestations_en_nature`, `mise_a_disposition_locaux`). Seul le montant en
    numéraire est repris ; la valorisation est signalée, jamais sommée.

Usage :
    python3 scripts/pipeline/normalize_ods.py [--limite N]

Entrée : data/raw/ods/*.csv + data/sources-manifest/ods.json
Sortie : data/canonical/parts/ods-*.parquet
"""

import argparse
import collections
import glob
import hashlib
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow as pa
import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
MANIFEST = os.path.join(ROOT, "data", "sources-manifest", "ods.json")
OUT_DIR = os.path.join(ROOT, "data", "canonical", "parts")

# Valeurs d'attribuant qui ne désignent personne : il faut alors se rabattre
# sur le publieur du jeu de données.
ATTRIBUANT_GENERIQUE = {"", "V", "VILLE", "COMMUNE", "DEPARTEMENT", "REGION",
                        "COLLECTIVITE", "EPCI", "NC", "NON RENSEIGNE", "AUTRE"}

ROLES = {
    "benef_nom": "beneficiaire", "benef_id": "siret_beneficiaire",
    "benef_rna": "rna_beneficiaire", "attrib_nom": "attribuant",
    "objet": "objet", "montant": "montant", "date_conv": "date_convention",
    "annee": "annee", "nature": "nature",
    "nature_benef": "nature_beneficiaire",
}


def normaliser(fiche, ingested_at):
    chemin = os.path.join(ROOT, fiche["fichier"])
    source_id = "ods-" + os.path.basename(chemin)[:-4]
    entete, lignes, infos = C.read_rows(chemin)
    col = {k: C.trouver_colonne(entete, r) for k, r in ROLES.items()}

    # Voté ou versé : le titre du jeu le dit, et cela vaut pour tout le fichier.
    mesure = C.measure_of(fiche.get("titre"), os.path.basename(chemin))

    out = {f: [] for f in C.CANONICAL_FIELDS}
    st = {"source_id": source_id, "portail": fiche.get("portail"), "mesure": mesure,
          "editeur": fiche.get("editeur"), "titre": fiche.get("titre"),
          "page": fiche.get("page"), "lues": 0, "gardees": 0, "ecartees": 0,
          "raisons": {}, "drapeaux": {}, "niveaux": {},
          "colonnes_mappees": {k: v for k, v in col.items() if v}}

    def bump(d, k):
        d[k] = d.get(k, 0) + 1

    for i, r in enumerate(lignes, start=1):
        st["lues"] += 1
        nom = C.clean_text(r.get(col["benef_nom"])) if col["benef_nom"] else ""
        montant = C.parse_amount(r.get(col["montant"])) if col["montant"] else None
        if not nom:
            st["ecartees"] += 1; bump(st["raisons"], "sans nom de bénéficiaire"); continue
        if montant is None:
            st["ecartees"] += 1; bump(st["raisons"], "montant illisible"); continue

        flags = []
        siret = C.valid_siret(r.get(col["benef_id"])) if col["benef_id"] else None
        siren = siret[:9] if siret else (C.valid_siren(r.get(col["benef_id"])) if col["benef_id"] else None)
        rna = C.valid_rna(r.get(col["benef_rna"])) if col["benef_rna"] else None
        if not siret:
            flags.append("no_siret")
        if not rna:
            flags.append("no_rna")

        # L'attribuant : la colonne si elle dit quelque chose, sinon le
        # publieur du jeu. Le portail n'est jamais utilisé — « Fédérateur
        # Opendatasoft » n'a versé aucune subvention.
        attrib = C.clean_text(r.get(col["attrib_nom"])) if col["attrib_nom"] else ""
        repli = C.clean_text(fiche.get("publieur") or "")
        if C.normalize_name(attrib) in ATTRIBUANT_GENERIQUE:
            # « Ville » chez un publieur « Ville de Paris » désigne bien Paris.
            attrib = repli or attrib
        niveau, non_attribue = C.donor_level_of(None, attrib)
        if non_attribue:
            flags.append("donor_unattributed")

        date_conv = C.clean_text(r.get(col["date_conv"])) if col["date_conv"] else ""
        annee = C.parse_year(r.get(col["annee"])) if col["annee"] else None
        if not annee and date_conv:
            annee = C.parse_year(date_conv)
        if not annee:
            flags.append("year_missing")

        nature = C.fold(r.get(col["nature"]) or "") if col["nature"] else ""
        if nature and "nature" in nature and "numeraire" not in nature:
            flags.append("aide_en_nature")

        objet = C.clean_text(r.get(col["objet"])) if col["objet"] else ""
        gran = "aggregate" if C.looks_aggregate(objet, nom) else "individual"
        # Quand la source déclare la nature juridique, elle fait foi ; sinon on
        # se rabat sur le nom, en le signalant comme une devinette.
        declaree = C.kind_from_nature(r.get(col["nature_benef"])) if col["nature_benef"] else None
        if declaree:
            kind, kind_prov = declaree, "declared"
        else:
            kind, kind_prov = "association", "guessed"
            n = C.fold(nom)
            if any(w in n for w in ("mairie de", "commune de", "ville de", "centre hospitalier",
                                    "conseil departemental", "etablissement public", "syndicat")):
                kind = "public_body"
        if kind != "association":
            flags.append("beneficiary_not_association")
        if montant == 0:
            flags.append("amount_zero")
        elif montant < 0:
            flags.append("amount_negative")
        rejete = C.amount_is_implausible(montant)
        if rejete:
            flags.append("amount_implausible")

        nom_norm = C.normalize_name(nom)
        donor_norm = C.normalize_name(attrib) or "INCONNU"
        objet_norm = C.normalize_name(objet) or None
        conf = "high" if (siret and annee) else ("low" if not siret and not rna else "medium")
        ref = f"{os.path.basename(chemin)}#L{i}"
        for f in flags:
            bump(st["drapeaux"], f)
        bump(st["niveaux"], niveau)

        vals = dict(
            row_id=hashlib.sha1(f"{source_id}|{ref}".encode()).hexdigest()[:20],
            business_key=C.business_key(siret, nom_norm, donor_norm, annee, montant, objet_norm),
            beneficiary_name_raw=nom, beneficiary_name_norm=nom_norm,
            beneficiary_siret=siret, beneficiary_siren=siren, beneficiary_rna=rna,
            beneficiary_kind=kind, beneficiary_commune_insee=None,
            beneficiary_dep_code=None, beneficiary_reg_code=None,
            beneficiary_address_raw=None,
            donor_name_raw=attrib or None, donor_name_norm=donor_norm,
            donor_siren=None, donor_level=niveau,
            donor_commune_insee=None, donor_dep_code=None, donor_reg_code=None,
            donor_program=None,
            amount_eur=None if rejete else montant,
            amount_rejected_eur=montant if rejete else None,
            year=annee, year_provenance="published" if annee else "unknown",
            date_convention=date_conv[:10] or None,
            purpose_raw=objet or None, purpose_norm=objet_norm,
            granularity=gran, measure=mesure,
            beneficiary_kind_provenance=kind_prov,
            is_convention=True if date_conv else None,
            quality_flags=flags, confidence=conf,
            source_id=source_id, source_label=fiche.get("titre") or source_id,
            source_url=fiche.get("page"), source_row_ref=ref, source_family="portail",
            license=fiche.get("licence") or "lov2", ingested_at=ingested_at)
        for f in C.CANONICAL_FIELDS:
            out[f].append(vals.get(f))
        st["gardees"] += 1

    if not st["gardees"]:
        return st
    table = pa.table(out, schema=C.CANONICAL_SCHEMA)
    os.makedirs(OUT_DIR, exist_ok=True)
    dest = os.path.join(OUT_DIR, f"{source_id}.parquet")
    pq.write_table(table, dest, compression="zstd")
    st["parquet"] = os.path.relpath(dest, ROOT)
    st["montant"] = round(sum(x for x in out["amount_eur"] if x), 2)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int)
    args = ap.parse_args()

    with open(MANIFEST, encoding="utf-8") as f:
        manifeste = json.load(f)
    jeux = manifeste["datasets"][: args.limite] if args.limite else manifeste["datasets"]
    ingested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for vieux in glob.glob(os.path.join(OUT_DIR, "ods-*.parquet")):
        os.remove(vieux)

    print(f"Normalisation de la famille ods — {len(jeux)} jeux\n")
    stats, lues, gardees = [], 0, 0
    for fiche in jeux:
        if not os.path.exists(os.path.join(ROOT, fiche["fichier"])):
            continue
        try:
            st = normaliser(fiche, ingested_at)
        except Exception as e:
            print(f"  ÉCHEC {fiche.get('titre', '')[:40]} : {str(e)[:60]}")
            continue
        stats.append(st)
        lues += st["lues"]
        gardees += st["gardees"]
        if st["gardees"]:
            print(f"  {st['gardees']:>8,} / {st['lues']:>8,}  {(st.get('editeur') or '')[:24]:24s} "
                  f"{(st.get('titre') or '')[:44]}")

    niveaux = collections.Counter()
    for s in stats:
        for k, v in s["niveaux"].items():
            niveaux[k] += v
    out = os.path.join(ROOT, "data", "canonical", "normalize-ods.stats.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"family": "ods", "normalized_at": ingested_at, "jeux": len(stats),
                   "lues": lues, "gardees": gardees, "par_niveau": dict(niveaux),
                   "sources": stats}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\n  {len(stats)} jeux, {lues:,} lignes lues, {gardees:,} retenues")
    print(f"  par niveau : {dict(niveaux.most_common())}")
    print(f"  -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
