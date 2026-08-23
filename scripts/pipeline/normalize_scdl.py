"""Normaliseur de la famille de format « scdl » vers le schéma canonique.

Un seul normaliseur pour toutes les collectivités moissonnées par
`fetch_scdl.py`, quelles que soient leurs graphies de colonnes. Le standard
SCDL « subventions » fixe les intitulés, mais les publications réelles s'en
écartent constamment (casse, accents, tirets, fautes) : les colonnes sont donc
reconnues par libellé plié, jamais par position.

Ce que le normaliseur sait faire de mieux que les conversions héritées :
  - l'attribuant porte son propre SIRET (`idAttribuant`), ce qui permet de le
    rattacher au référentiel INSEE et donc de connaître le NIVEAU du donateur
    (commune, EPCI, département, région) sans se fier à son nom ;
  - le bénéficiaire porte souvent son SIRET et parfois son RNA ;
  - les aides en nature sont distinguées des versements en numéraire.

Usage :
    python3 scripts/pipeline/normalize_scdl.py [--limite N]

Entrée : data/raw/scdl/*.csv + data/sources-manifest/scdl.json
Sortie : data/canonical/parts/scdl-*.parquet
"""

import argparse
import collections
import hashlib
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow as pa
import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
MANIFEST = os.path.join(ROOT, "data", "sources-manifest", "scdl.json")
OUT_DIR = os.path.join(ROOT, "data", "canonical", "parts")

# Les rôles de colonnes sont reconnus par `common.trouver_colonne`, partagé
# avec les moissonneurs : une graphie ajoutée là profite immédiatement ici.
ROLES = {
    "benef_nom": "beneficiaire", "benef_id": "siret_beneficiaire",
    "benef_rna": "rna_beneficiaire", "attrib_nom": "attribuant",
    "objet": "objet", "montant": "montant", "date_conv": "date_convention",
    "annee": "annee", "nature": "nature",
    "nature_benef": "nature_beneficiaire",
}


def niveau_par_siren(siren, nom):
    """(niveau, siren, insee, dep, reg) — rattache l'attribuant au référentiel.

    Le SIREN d'une collectivité est la clé la plus sûre : un nom peut être
    ambigu (« Commune de Sainte-Marie » existe plusieurs fois), un SIREN non.
    """
    ref = C.referentiel()
    epci = ref["epci"].get(siren) if siren else None
    lvl, _ = C.donor_level_of(None, nom or "", siren)
    if epci:
        return lvl, siren, None, epci.get("dep_code") or None, epci.get("reg_code") or None
    return lvl, siren, None, None, None


def normaliser_fichier(fiche, fichier, ingested_at):
    chemin = os.path.join(ROOT, fichier["fichier"])
    source_id = "scdl-" + os.path.basename(chemin)[:-4]
    entete, lignes, meta = C.read_rows(chemin, valide=C.porte_des_subventions)
    col = {k: C.trouver_colonne(entete, r) for k, r in ROLES.items()}
    col["attrib_id"] = C.pick(entete, "idAttribuant", "siret attribuant", "id attribuant")
    col["reference"] = C.pick(entete, "referenceDecision", "reference decision")
    # Voté ou versé : lu au titre du jeu, au nom du fichier et au libellé de la
    # colonne de montant, une fois pour tout. La colonne tranche quand le titre
    # se tait : `Mandaté` porte de l'argent payé.
    mesure = C.measure_of(fiche.get("titre"), fichier.get("titre"), col.get("montant"))
    # Un fichier par exercice, sans colonne d'année : l'exercice n'est alors
    # écrit que dans le nom du fichier. On le lit une fois pour tout le fichier,
    # du plus précis (le fichier) au plus général (le jeu).
    annee_repli = C.annee_du_libelle(fichier.get("titre"), fiche.get("titre"))

    out = {f: [] for f in C.CANONICAL_FIELDS}
    st = {
        "source_id": source_id, "dataset": fiche.get("titre"),
        "organisation": fiche.get("organisation"), "page": fiche.get("page"),
        "fichier": fichier["fichier"], "encodage": meta["encoding"],
        "lues": 0, "gardees": 0, "ecartees": 0,
        "raisons": {}, "drapeaux": {}, "niveaux": {},
        "colonnes_mappees": {k: v for k, v in col.items() if v},
    }

    def bump(d, k):
        d[k] = d.get(k, 0) + 1

    # L'attribuant est le plus souvent constant dans un fichier : on le résout
    # une fois, en repli sur l'organisation qui publie le jeu.
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

        attrib_nom = (C.clean_text(r.get(col["attrib_nom"])) if col["attrib_nom"] else "") \
            or (fiche.get("organisation") or "")
        attrib_siret = C.valid_siret(r.get(col["attrib_id"])) if col["attrib_id"] else None
        attrib_siren = attrib_siret[:9] if attrib_siret else (
            C.valid_siren(r.get(col["attrib_id"])) if col["attrib_id"] else None)
        niveau, dsiren, dinsee, ddep, dreg = niveau_par_siren(attrib_siren, attrib_nom)
        if niveau == "inconnu":
            flags.append("donor_unattributed")

        date_conv = C.clean_text(r.get(col["date_conv"])) if col["date_conv"] else ""
        annee = None
        if col["annee"]:
            annee = C.parse_year(r.get(col["annee"]))
        if not annee and date_conv:
            annee = C.parse_year(date_conv)
        annee_deduite = False
        if not annee and annee_repli:
            annee, annee_deduite = annee_repli, True
        if not annee:
            flags.append("year_missing")
        elif annee_deduite:
            flags.append("year_from_label")

        nature = C.fold(r.get(col["nature"]) or "") if col["nature"] else ""
        if nature and "nature" in nature and "numeraire" not in nature:
            flags.append("aide_en_nature")

        objet = C.clean_text(r.get(col["objet"])) if col["objet"] else ""
        gran = "aggregate" if C.looks_aggregate(objet, nom) else "individual"
        # La nature déclarée par la source prime sur la devinette sur le nom.
        declaree = C.kind_from_nature(r.get(col["nature_benef"])) if col["nature_benef"] else None
        if declaree:
            kind, kind_prov = declaree, "declared"
        else:
            kind, kind_prov = "association", "guessed"
            n = C.fold(nom)
            if any(w in n for w in ("mairie de", "commune de", "ville de", "centre hospitalier",
                                    "conseil departemental", "etablissement public")):
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
        donor_norm = C.normalize_name(attrib_nom) or "INCONNU"
        objet_norm = C.normalize_name(objet) or None
        conf = "high" if (siret and annee) else ("low" if not siret and not rna else "medium")
        ref_ligne = f"{os.path.basename(chemin)}#L{i}"
        for f in flags:
            bump(st["drapeaux"], f)
        bump(st["niveaux"], niveau)

        vals = dict(
            row_id=hashlib.sha1(f"{source_id}|{ref_ligne}".encode()).hexdigest()[:20],
            business_key=C.business_key(siret, nom_norm, donor_norm, annee, montant, objet_norm),
            beneficiary_name_raw=nom, beneficiary_name_norm=nom_norm,
            beneficiary_siret=siret, beneficiary_siren=siren, beneficiary_rna=rna,
            beneficiary_kind=kind, beneficiary_commune_insee=None,
            beneficiary_dep_code=None, beneficiary_reg_code=None,
            beneficiary_address_raw=None,
            donor_name_raw=attrib_nom or None, donor_name_norm=donor_norm,
            donor_siren=dsiren, donor_level=niveau,
            donor_commune_insee=dinsee, donor_dep_code=ddep, donor_reg_code=dreg,
            donor_program=None,
            amount_eur=None if rejete else montant,
            amount_rejected_eur=montant if rejete else None,
            year=annee,
            year_provenance=("inferred" if annee_deduite else
                             "published" if annee else "unknown"),
            date_convention=date_conv[:10] or None,
            purpose_raw=objet or None, purpose_norm=objet_norm,
            granularity=gran, measure=mesure,
            beneficiary_kind_provenance=kind_prov,
            is_convention=True if date_conv else None,
            quality_flags=flags, confidence=conf,
            source_id=source_id, source_label=fiche.get("titre") or source_id,
            source_url=fiche.get("page"), source_row_ref=ref_ligne,
            source_family="scdl", license=fiche.get("licence") or "lov2",
            ingested_at=ingested_at,
        )
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

    # Purge des parties SCDL d'un build précédent : sans cela, un fichier retiré
    # de l'amont resterait dans la table canonique.
    import glob
    for vieux in glob.glob(os.path.join(OUT_DIR, "scdl-*.parquet")):
        os.remove(vieux)

    print(f"Normalisation de la famille scdl — {len(jeux)} jeux\n")
    stats, gardees, lues = [], 0, 0
    for fiche in jeux:
        for fichier in fiche["fichiers"]:
            if not os.path.exists(os.path.join(ROOT, fichier["fichier"])):
                continue
            try:
                st = normaliser_fichier(fiche, fichier, ingested_at)
            except Exception as e:
                print(f"  ÉCHEC {fichier['fichier']}: {str(e)[:70]}")
                continue
            stats.append(st)
            gardees += st["gardees"]
            lues += st["lues"]

    niveaux = collections.Counter()
    for s in stats:
        for k, v in s["niveaux"].items():
            niveaux[k] += v
    out = os.path.join(ROOT, "data", "canonical", "normalize-scdl.stats.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"family": "scdl", "normalized_at": ingested_at,
                   "fichiers": len(stats), "lues": lues, "gardees": gardees,
                   "par_niveau": dict(niveaux), "sources": stats},
                  f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"  {len(stats)} fichiers, {lues:,} lignes lues, {gardees:,} retenues")
    print(f"  par niveau de donateur : {dict(niveaux.most_common())}")
    print(f"  -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
