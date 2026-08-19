"""Normalise les 152 sources héritées vers le schéma canonique.

Ces fichiers `data/sources/*.js` sont le produit des 167 convertisseurs écrits
à la main de l'ancien site. On les reprend tels quels : ils portent des données
réelles, et re-moissonner chaque portail amont relève de la phase 4.

Trois formes d'enregistrement coexistent :

  - **normalisée** (146 fichiers) : `{association:{...}, entity:{...}, amount,
    year, ...}` — le format que l'ancien loader attendait ;
  - **SCDL brute** (5 fichiers) : `{nomAttribuant, idAttribuant, montant,
    objet, ...}` — laissée non convertie, le navigateur devait s'en charger ;
  - **exercice/libellé** (1 fichier) : `{EXERCICE, LBASSOCIATION, SUBVF,
    SUBVI}` — deux colonnes de montant, fonctionnement et investissement.

Les fichiers `plf-jaune-*.js` sont **volontairement ignorés** : ils sont
remplacés par le moissonnage de la source amont (`fetch_plf_jaune.py`), qui
récupère des colonnes que ces conversions avaient perdues.

Usage :
    python3 scripts/pipeline/normalize_legacy.py [--only <source>]

Sortie : data/canonical/parts/legacy-<source>.parquet + statistiques
"""

import argparse
import glob
import hashlib
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow as pa
import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
SRC_DIR = os.path.join(ROOT, "data", "sources")
OUT_DIR = os.path.join(ROOT, "data", "canonical", "parts")

SKIP_PREFIXES = ("plf-jaune",)      # remplacés par le moissonnage amont
SKIP_NAMES = {"_template"}

# Sources dont l'UNITÉ monétaire est douteuse. Leurs montants sont mis de côté
# (dans `amount_rejected_eur`) plutôt que sommés, tant que l'amont n'a pas été
# revérifié. Les lignes restent comptées : le département montre son activité,
# mais aucun montant faux n'est affiché.
#
# `metropole-lyon` : 9 081 lignes totalisant 48 Md€, quand le budget annuel de
# la Métropole avoisine 3,8 Md€. La médiane y est de 1 584 200 €, le minimum de
# 100, et 85 % des valeurs sont multiples de 100 : tout indique des CENTIMES
# lus comme des euros (48 Md€ de centimes = 480 M€, ordre de grandeur juste).
# L'API data.grandlyon.com ayant changé, la vérification amont reste à faire —
# on ne divise donc pas par cent de notre propre autorité (cf. la doctrine :
# pas de correction de montant non vérifiée).
UNITE_DOUTEUSE = {
    "metropole-lyon": "montants vraisemblablement en centimes, vérification amont à faire",
}

# Plafond de vraisemblance PAR SOURCE, pour les cas où seules quelques lignes
# d'un fichier par ailleurs sain sont absurdes. `ville-boulogne-billancourt` :
# 2 lignes sur 62 portent 750 M€ et 75 M€ — plus du double du budget annuel de
# la ville (~330 M€) pour la première — quand les 60 autres sont plausibles
# (l'ACBB à 2,47 M€ correspond au réel). Même traitement que la quarantaine
# d'unité : montant mis de côté, ligne comptée, à trancher en re-moissonnant.
PLAFOND_DOUTEUX = {
    "ville-boulogne-billancourt": 5e7,
}

# Bénéficiaires de convenance : la source n'a pas identifié l'association.
# En dessous du seuil, la ligne reste une attribution individuelle (anonymisée) ;
# au-delà, c'est un cumul qui ne dit pas son nom — `paris` publie ainsi une
# ligne « Association inconnue » de 257 M€ en 2024, soit l'ordre de grandeur du
# total annuel des subventions du département. La ranger en `aggregate` évite
# qu'elle écrase le classement des bénéficiaires et double des lignes détaillées.
BENEF_PLACEHOLDER = {"INCONNUE", "INCONNU", "ASSOCIATION INCONNUE", "",
                     "DIVERS", "DIVERSES", "NON RENSEIGNE"}
SEUIL_CUMUL_ANONYME = 1e7


def parse_year(value):
    """(année, drapeau) — None si hors bornes plausibles."""
    try:
        y = int(str(value).strip() or 0)
    except (TypeError, ValueError):
        return None, "year_missing"
    if not y:
        return None, "year_missing"
    if not (1990 <= y <= 2100):
        return None, "year_invalid"
    return y, None


def convention_of(value):
    """Seuls les vrais booléens font foi.

    Le champ mélange des booléens et des libellés de modalité de versement
    (« unique », « échelonné ») qui ne disent rien de l'existence d'une
    convention : on ne les interprète pas.
    """
    return value if isinstance(value, bool) else None


def split_source(value):
    """(url, libellé) — le champ `source` mélange les deux dans l'ancien site."""
    s = C.clean_text(value)
    if not s:
        return None, None
    return (s, None) if s.startswith("http") else (None, s)


# Marqueurs d'association, testés EN PREMIER : ils sont plus spécifiques que
# ceux d'établissement public. Sans cette priorité, « Ligue de l'enseignement
# fédération départementale » tombe dans public_body à cause de « départemental ».
_ASSOC_START = ("association", "asso ", "amicale", "club", "comite", "federation",
                "union", "ligue", "fondation", "fed ", "cercle", "societe sportive")
_ASSOC_ANY = ("federation", "association", "amicale", "ligue ", "union sportive")
# Marqueurs d'établissement public : des expressions, jamais un mot isolé comme
# « departement », qui apparaît dans quantité de noms d'associations.
_PUBLIC_ANY = ("mairie de", "commune de", "ville de", "prefecture",
               "centre hospitalier", "chu de", "lycee ", "college ",
               "universite ", "pole emploi", "sdis ", "ccas ",
               "conseil departemental", "conseil general", "conseil regional",
               "departement de", "departement du", "departement des",
               "syndicat intercommunal", "etablissement public")


def kind_of(name, siret):
    n = C.fold(name)
    if n.startswith(_ASSOC_START) or any(w in n for w in _ASSOC_ANY):
        return "association"
    if any(w in n for w in _PUBLIC_ANY):
        return "public_body"
    return "inconnu"


def emit(out, **kw):
    for f in C.CANONICAL_FIELDS:
        out[f].append(kw.get(f))


def normalize_source(path, ingested_at):
    name = os.path.basename(path)[:-3]
    registered_id, label, rows = C.read_legacy_source(path)

    out = {f: [] for f in C.CANONICAL_FIELDS}
    st = {
        "source_id": name, "registered_id": registered_id, "file": os.path.relpath(path, ROOT),
        "rows_read": 0, "rows_kept": 0, "rows_dropped": 0,
        "shapes": {}, "drop_reasons": {}, "flags": {}, "by_granularity": {},
        "donor_levels": {},
    }

    def bump(d, k):
        d[k] = d.get(k, 0) + 1

    for i, r in enumerate(rows, start=1):
        st["rows_read"] += 1
        if not isinstance(r, dict):
            st["rows_dropped"] += 1; bump(st["drop_reasons"], "enregistrement non objet"); continue

        if "association" in r and "entity" in r:
            shape, records = "normalisee", [_from_normalized(r)]
        elif any(k in r for k in ("nomAttribuant", "nomattribuant", "nom_de_l_attribuant")):
            shape, records = "scdl", [_from_scdl(r)]
        elif "EXERCICE" in r or "LBASSOCIATION" in r:
            shape, records = "exercice", _from_exercice(r)
        else:
            st["rows_dropped"] += 1; bump(st["drop_reasons"], "forme inconnue"); continue
        bump(st["shapes"], shape)

        for rec in records:
            if rec is None:
                st["rows_dropped"] += 1; bump(st["drop_reasons"], "champs essentiels absents"); continue
            if not rec["name"]:
                st["rows_dropped"] += 1; bump(st["drop_reasons"], "sans nom de bénéficiaire"); continue
            if rec["amount"] is None:
                st["rows_dropped"] += 1; bump(st["drop_reasons"], "montant illisible"); continue

            flags = list(rec["flags"])
            year, yflag = parse_year(rec["year"])
            if yflag:
                flags.append(yflag)

            dep, dep_prov = C.dep_from_code_or_name(rec["dep"])
            reg = None
            if dep:
                reg = (C.referentiel()["departements"].get(dep) or {}).get("reg_code")
                if dep_prov == "nom":
                    flags.append("dep_from_name")
            else:
                flags.append("dep_unknown")

            siret = C.valid_siret(rec["siret"])
            siren = siret[:9] if siret else C.valid_siren(rec["siret"])
            if not siret:
                flags.append("no_siret")
                raw_siret = C.clean_text(rec["siret"])
                if raw_siret:
                    # « 2,19301E+13 » : le SIRET est passé par un tableur qui l'a
                    # traité comme un nombre. Au-delà de six chiffres significatifs
                    # tout est perdu — ce n'est pas réparable, seulement signalable.
                    flags.append("siret_scientific_notation" if "E+" in raw_siret.upper()
                                 else "siret_invalid")
            rna = C.valid_rna(rec["rna"])
            if not rna:
                flags.append("no_rna")

            level, unattributed = C.donor_level_of(rec["donor_type"], rec["donor_name"],
                                                   rec["donor_siren"])
            if unattributed:
                flags.append("donor_unattributed")

            gran = "aggregate" if C.looks_aggregate(rec["purpose"], rec["name"]) else "individual"
            kind = kind_of(rec["name"], siret)
            if kind == "public_body":
                flags.append("beneficiary_not_association")
            if rec["amount"] == 0:
                flags.append("amount_zero")
            elif rec["amount"] < 0:
                flags.append("amount_negative")
            if C.amount_is_implausible(rec["amount"]):
                flags.append("amount_implausible")
            unite_douteuse = name in UNITE_DOUTEUSE or (
                name in PLAFOND_DOUTEUX and rec["amount"] is not None
                and abs(rec["amount"]) >= PLAFOND_DOUTEUX[name])
            if unite_douteuse:
                flags.append("amount_unit_suspect")
            # Certains fichiers portent des caractères de remplacement (U+FFFD) :
            # l'encodage a été perdu à la conversion d'origine, et les octets
            # d'origine avec. Signalé ici, corrigible seulement en re-moissonnant.
            if "\ufffd" in (rec["name"] or "") or "\ufffd" in (rec["purpose"] or ""):
                flags.append("texte_illisible")

            url, lbl = split_source(rec["source"])
            if not url:
                flags.append("no_source_url")

            name_norm = C.normalize_name(rec["name"])
            if name_norm in BENEF_PLACEHOLDER:
                flags.append("beneficiaire_non_identifie")
                if rec["amount"] is not None and rec["amount"] >= SEUIL_CUMUL_ANONYME:
                    gran = "aggregate"
            donor_norm = C.normalize_name(rec["donor_name"]) or "INCONNU"
            purpose_norm = C.normalize_name(rec["purpose"]) or None
            conf = ("high" if (siret and dep and year) else
                    "low" if (not siret and not rna and not dep) else "medium")

            row_ref = f"{name}.js#{i}" + (f".{rec['slot']}" if rec.get("slot") else "")
            for fl in flags:
                bump(st["flags"], fl)
            bump(st["by_granularity"], gran)
            bump(st["donor_levels"], level)

            emit(out,
                 row_id=hashlib.sha1(f"{name}|{row_ref}".encode()).hexdigest()[:20],
                 business_key=C.business_key(siret, name_norm, donor_norm, year,
                                             rec["amount"], purpose_norm),
                 beneficiary_name_raw=rec["name"], beneficiary_name_norm=name_norm,
                 beneficiary_siret=siret, beneficiary_siren=siren, beneficiary_rna=rna,
                 beneficiary_kind=kind, beneficiary_commune_insee=None,
                 beneficiary_dep_code=dep, beneficiary_reg_code=reg,
                 beneficiary_address_raw=rec["address"] or None,
                 donor_name_raw=rec["donor_name"] or None, donor_name_norm=donor_norm,
                 donor_siren=rec["donor_siren"], donor_level=level,
                 donor_program=rec["program"] or None,
                 amount_eur=(None if (C.amount_is_implausible(rec["amount"]) or unite_douteuse)
                             else rec["amount"]),
                 amount_rejected_eur=(rec["amount"] if (C.amount_is_implausible(rec["amount"])
                                                        or unite_douteuse) else None),
                 year=year,
                 year_provenance="published" if year else "unknown",
                 date_convention=rec["date_convention"],
                 purpose_raw=rec["purpose"] or None, purpose_norm=purpose_norm,
                 granularity=gran, is_convention=rec["convention"],
                 quality_flags=flags, confidence=conf,
                 source_id=name, source_label=label or rec["donor_name"] or name,
                 source_url=url, source_row_ref=row_ref, source_family=rec["family"],
                 license="lov2", ingested_at=ingested_at)
            st["rows_kept"] += 1

    table = pa.table(out, schema=C.CANONICAL_SCHEMA)
    os.makedirs(OUT_DIR, exist_ok=True)
    dest = os.path.join(OUT_DIR, f"legacy-{name}.parquet")
    pq.write_table(table, dest, compression="zstd")
    st["parquet"] = os.path.relpath(dest, ROOT)
    st["amount_total"] = round(sum(x for x in out["amount_eur"] if x), 2)
    return st


def _g(r, *keys):
    for k in keys:
        if r.get(k) not in (None, ""):
            return r[k]
    return ""


def _from_normalized(r):
    a = r.get("association") or {}
    e = r.get("entity") or {}
    return {
        "name": C.clean_text(a.get("name")), "siret": a.get("siret"), "rna": a.get("rna"),
        "dep": a.get("department"), "address": C.clean_text(a.get("address")),
        "purpose": C.clean_text(a.get("object") or r.get("justification")),
        "donor_name": C.clean_text(e.get("name")), "donor_type": e.get("type"),
        "donor_siren": None,
        "program": C.clean_text(e.get("program") or r.get("program") or e.get("direction")),
        "amount": C.parse_amount(r.get("amount")), "year": r.get("year"),
        "convention": convention_of(r.get("convention")), "date_convention": None,
        "source": r.get("source"), "family": "portail", "flags": [],
    }


def _from_scdl(r):
    donor_id = C.clean_text(_g(r, "idAttribuant", "idattribuant", "identification_del_attribuant",
                               "siret_attributaire"))
    date_conv = C.clean_text(_g(r, "dateConvention", "dateconvention", "date_de_la_convention"))
    nature = C.fold(_g(r, "nature", "nature_de_la_subvention"))
    flags = ["aide_en_nature"] if ("nature" in nature and "numeraire" not in nature) else []
    return {
        "name": C.clean_text(_g(r, "nomBeneficiaire", "nombeneficiaire", "nom_du_beneficiaire")),
        "siret": _g(r, "idBeneficiaire", "idbeneficiaire"),
        "rna": "", "dep": "", "address": "",
        "purpose": C.clean_text(_g(r, "objet", "l_objet_de_la_subvention", "objet_descriptif")),
        "donor_name": C.clean_text(_g(r, "nomAttribuant", "nomattribuant",
                                      "nom_de_l_attribuant", "_entityName")),
        "donor_type": r.get("_entityType"),
        "donor_siren": (C.valid_siret(donor_id) or "")[:9] or C.valid_siren(donor_id),
        "program": "",
        "amount": C.parse_amount(_g(r, "montant", "montant_total")),
        "year": C.parse_year(_g(r, "anneeDecision", "annee")) or C.parse_year(date_conv),
        "convention": True if date_conv else None,
        "date_convention": date_conv[:10] or None,
        "source": "", "family": "scdl", "flags": flags,
    }


def _from_exercice(r):
    """Une ligne par montant réellement publié : fonctionnement et
    investissement sont deux subventions distinctes, pas deux colonnes d'une
    même ligne."""
    base = {
        "name": C.clean_text(r.get("LBASSOCIATION")), "siret": "", "rna": "",
        "dep": "", "address": "", "donor_name": C.clean_text(r.get("_entityName")),
        "donor_type": r.get("_entityType"), "donor_siren": None, "program": "",
        "year": r.get("EXERCICE"), "convention": None, "date_convention": None,
        "source": "", "family": "portail", "flags": [],
    }
    out = []
    for field, libelle, slot in (("SUBVF", "Subvention de fonctionnement", "f"),
                                 ("SUBVI", "Subvention d'investissement", "i")):
        amount = C.parse_amount(r.get(field))
        if amount is None:
            continue
        rec = dict(base, amount=amount, purpose=libelle, slot=slot)
        out.append(rec)
    return out or [None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()

    files = []
    for p in sorted(glob.glob(os.path.join(SRC_DIR, "*.js"))):
        n = os.path.basename(p)[:-3]
        if n in SKIP_NAMES or n.startswith(SKIP_PREFIXES):
            continue
        if args.only and n != args.only:
            continue
        files.append(p)

    ingested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"Normalisation des sources héritées — {len(files)} fichiers\n")
    all_st = []
    for p in files:
        st = normalize_source(p, ingested_at)
        all_st.append(st)
        if st["rows_dropped"] or st["rows_kept"] == 0:
            print(f"  {st['source_id']:36s} {st['rows_kept']:>7,} gardées  "
                  f"{st['rows_dropped']:>6,} écartées  {st['drop_reasons']}")

    kept = sum(s["rows_kept"] for s in all_st)
    read = sum(s["rows_read"] for s in all_st)
    dropped = sum(s["rows_dropped"] for s in all_st)
    out = os.path.join(ROOT, "data", "canonical", "normalize-legacy.stats.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"family": "legacy", "normalized_at": ingested_at,
                   "files_total": len(all_st), "rows_read": read,
                   "rows_kept": kept, "rows_dropped": dropped,
                   "sources": all_st}, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\n  {len(all_st)} sources, {read:,} lues, {kept:,} retenues, {dropped:,} écartées")
    print(f"  -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
