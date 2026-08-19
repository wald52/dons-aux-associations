"""Normaliseur de la famille de format « plf_jaune » vers le schéma canonique.

Un seul normaliseur pour les 13 millésimes, alors que le site en avait un par
source. L'annexe Jaune a changé quatre fois de structure depuis 2012 :

  - PLF 2012        : SIREN, ASSOCIATION, IMPUTATION, Total des subventions.
                      Ce sont des **totaux par association**, pas des
                      attributions individuelles -> granularity = aggregate.
  - PLF 2013 à 2017 : MILLESIME, Ministère, PROGRAMME, DEPARTEMENT, VILLE,
                      « Subvention AAAA ». Département sur 2 caractères, pas
                      de code commune, pas de RNA.
  - PLF 2018 et 2020: Programme, SIREN, NIC, COG code département + commune
                      séparés, nomenclature juridique. RNA en 2018 seulement.
  - PLF 2021 et suiv: COG : code (commune INSEE complet), catégorie juridique,
                      « Répertoire national des associations ».

Les colonnes sont reconnues par libellé plié, pas par position : un millésime
à venir qui réutilise les mêmes intitulés passera sans modification.

Usage :
    python3 scripts/pipeline/normalize_plf_jaune.py [--only 2022]

Entrée  : data/raw/plf-jaune/*.csv (cf. fetch_plf_jaune.py)
Sortie  : data/canonical/parts/plf-jaune-<plf>.parquet + stats par fichier
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow as pa
import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
RAW_DIR = os.path.join(ROOT, "data", "raw", "plf-jaune")
OUT_DIR = os.path.join(ROOT, "data", "canonical", "parts")
MANIFEST = os.path.join(ROOT, "data", "sources-manifest", "plf-jaune.json")

DATASET_HOME = "https://www.data.gouv.fr/datasets/"

# Catégories juridiques INSEE : 92xx = associations. Sert à ne pas présenter
# comme association un bénéficiaire qui n'en est pas (cf. SCHEMA.md).
def beneficiary_kind(categ, name):
    c = re.sub(r"\D", "", C.clean_text(categ) or "")
    if c.startswith("92"):
        return "association"
    if c.startswith(("41", "42", "43", "44", "45", "46", "47", "71", "72", "73", "74")):
        return "public_body"
    if c.startswith(("1", "2", "3", "5", "6")):
        return "company"
    n = C.fold(name)
    if n.startswith(("association", "asso ", "assoc")):
        return "association"
    return "inconnu"


def data_year_for(header, rows_sample, plf_year, millesime_col):
    """Année des subventions décrites par le fichier.

    Trois pistes, de la plus fiable à la moins fiable :
      1. le libellé de la colonne de montant ou d'objet (« Subvention 2013 »,
         « Objet 2020 », ou une colonne nommée simplement « 2014 ») ;
      2. la colonne MILLESIME (« Jaune PLF 2015 - Subventions 2014 ») ;
      3. à défaut, millésime du PLF moins deux — la convention de l'annexe.

    On ne se fie pas au nom du fichier : le PLF 2016 contient les subventions
    2014, et non 2015 comme l'arithmétique naïve le laisserait croire.
    """
    for h in header:
        f = C.fold(h)
        if any(f.startswith(p) for p in ("subvention", "objet", "montant")) or re.fullmatch(r"20\d{2}", f):
            y = C.parse_year(h)
            if y:
                return y, "column_header"
    if millesime_col:
        for row in rows_sample:
            y = None
            m = re.findall(r"subventions?\s+(20\d{2})", C.fold(row.get(millesime_col, "")))
            if m:
                y = int(m[-1])
            if y:
                return y, "millesime_column"
    return (plf_year - 2 if plf_year else None), "plf_minus_2"


# Schéma et clé métier sont définis une seule fois, dans common.py.
SCHEMA = C.CANONICAL_SCHEMA
business_key = C.business_key


def normalize_file(path, entry, ingested_at):
    plf_year = entry["plf_year"]
    source_id = f"plf-jaune-{plf_year}"
    header, rows, meta = C.read_rows(path)

    col = lambda *p: C.pick(header, *p)
    c_siren = col("siren")
    c_nic = col("nic")
    c_name = col("denomination", "association")
    c_amount = (col("montant", "subvention", "total des subventions")
                or next((h for h in header if re.fullmatch(r"20\d{2}", C.fold(h))), None))
    # PLF 2012 entrelace deux natures de lignes dans un même fichier : un total
    # par association (IMPUTATION vide) et les attributions individuelles qui le
    # composent (IMPUTATION renseignée, montant dans « Détail des subventions »).
    # On garde les deux, distinguées par `granularity`, plutôt que d'en jeter une.
    c_amount_detail = col("detail des subventions")
    if c_amount_detail == c_amount:
        c_amount_detail = None
    c_objet = col("objet de la subvention", "objet", "detail des subventions")
    c_prog = col("programme", "imputation")
    c_min = col("ministere")
    c_mission = col("mission")
    c_rna = col("repertoire national des associations", "rna")
    c_categ = col("categorie juridique", "nomenclature juridique")
    c_cog_full = col("cog : code", "cog: code")
    c_cog_dep = col("cog : code departement", "cog : code departement ou pays")
    c_cog_com = col("cog : code commune", "cog : code commune ou pays")
    c_ville = col("cog : libelle", "cog : ville ou pays", "ville")
    c_dep = col("departement")
    c_conv = col("convention")
    c_mill = col("millesime")
    c_date = col("date de creation")

    # « COG : code » est un préfixe de « COG : code département » : si les
    # colonnes séparées existent, elles priment sur la colonne unique.
    if c_cog_dep and c_cog_com:
        c_cog_full = None
    elif c_cog_full and C.fold(c_cog_full).startswith("cog : code departement"):
        c_cog_full = None

    sample = []
    gen = iter(rows)
    for _ in range(50):
        try:
            sample.append(next(gen))
        except StopIteration:
            break
    year, year_prov = data_year_for(header, sample, plf_year, c_mill)

    def all_rows():
        for r in sample:
            yield r
        for r in gen:
            yield r

    # Un fichier « à deux natures » se reconnaît à la présence simultanée d'une
    # colonne de total et d'une colonne de détail.
    split_file = bool(c_amount_detail and c_amount
                      and C.fold(c_amount).startswith("total des subventions"))
    is_aggregate = bool(c_amount and C.fold(c_amount).startswith("total des subventions")
                        and not c_amount_detail)

    out = {f.name: [] for f in SCHEMA}
    stats = {
        "source_id": source_id, "plf_year": plf_year, "data_year": year,
        "year_provenance": year_prov, "file": os.path.relpath(path, ROOT),
        "encoding": meta["encoding"], "header_line": meta["header_line"],
        "granularity": ("mixte (total + détail)" if split_file
                        else "aggregate" if is_aggregate else "individual"),
        "rows_read": 0, "rows_kept": 0, "rows_dropped": 0, "by_granularity": {},
        "drop_reasons": {}, "flags": {},
        "columns_mapped": {k: v for k, v in {
            "siren": c_siren, "nic": c_nic, "nom": c_name, "montant": c_amount,
            "objet": c_objet, "programme": c_prog, "ministere": c_min,
            "rna": c_rna, "categorie": c_categ, "cog_code": c_cog_full,
            "cog_dep": c_cog_dep, "cog_commune": c_cog_com, "departement": c_dep,
        }.items() if v},
        "columns_absent": [k for k, v in {
            "rna": c_rna, "cog_commune": c_cog_full or c_cog_com,
            "categorie_juridique": c_categ, "nic": c_nic, "objet": c_objet,
        }.items() if not v],
    }

    def bump(d, k):
        d[k] = d.get(k, 0) + 1

    for i, r in enumerate(all_rows(), start=1):
        stats["rows_read"] += 1
        flags = []

        name_raw = C.clean_text(r.get(c_name)) if c_name else ""
        amount = C.parse_amount(r.get(c_amount)) if c_amount else None

        # Nature de la ligne : dans un fichier à deux natures, une ligne portant
        # un montant de détail est une attribution individuelle ; sinon c'est le
        # total de l'association, qu'on conserve mais qu'on ne sommera jamais
        # avec les précédentes.
        row_granularity = "aggregate" if is_aggregate else "individual"
        if split_file:
            detail = C.parse_amount(r.get(c_amount_detail))
            if detail is not None:
                amount, row_granularity = detail, "individual"
            elif amount is not None:
                row_granularity = "aggregate"

        if not name_raw:
            stats["rows_dropped"] += 1; bump(stats["drop_reasons"], "sans nom de bénéficiaire"); continue
        if amount is None:
            stats["rows_dropped"] += 1; bump(stats["drop_reasons"], "montant illisible"); continue

        name_norm = C.normalize_name(name_raw)
        siren = C.valid_siren(r.get(c_siren)) if c_siren else None
        siret = C.build_siret(r.get(c_siren), r.get(c_nic)) if (c_siren and c_nic) else None
        if siret and not siren:
            siren = siret[:9]
        rna = C.valid_rna(r.get(c_rna)) if c_rna else None

        # Géographie : code commune complet, sinon recomposé, sinon département seul.
        insee = dep = reg = None
        if c_cog_full:
            insee, dep, reg = C.resolve_commune(re.sub(r"\D", "", C.clean_text(r.get(c_cog_full))))
        elif c_cog_dep and c_cog_com:
            insee, dep, reg = C.resolve_commune(
                C.insee_from_parts(r.get(c_cog_dep), r.get(c_cog_com)))
        if not dep and c_dep:
            d = C.clean_text(r.get(c_dep)).upper().strip()
            d = d.zfill(2) if d.isdigit() and len(d) == 1 else d
            if C.dep_is_known(d):
                dep = d
                reg = (C.referentiel()["departements"].get(d) or {}).get("reg_code")
                flags.append("dep_only")
        if not dep:
            flags.append("dep_unknown")
        if not siret:
            flags.append("no_siret")
        if not rna:
            flags.append("no_rna")
        if amount == 0:
            flags.append("amount_zero")
        elif amount < 0:
            flags.append("amount_negative")
        if C.amount_is_implausible(amount):
            flags.append("amount_implausible")

        # Donateur : l'État. Le programme budgétaire est le grain le plus fin
        # que l'annexe publie ; le ministère n'est présent que 2013-2017.
        prog = C.clean_text(r.get(c_prog)) if c_prog else ""
        prog = re.sub(r"\.0$", "", prog)
        ministere = C.clean_text(r.get(c_min)) if c_min else ""
        # « Santé et sports: 219 - Sport » : le ministère précède le programme.
        if not ministere and ":" in prog:
            ministere, prog = (x.strip() for x in prog.split(":", 1))
        mission = C.clean_text(r.get(c_mission)) if c_mission else ""
        donor_program = " — ".join(x for x in (ministere, prog, mission) if x) or None
        donor_name = f"État — {ministere or prog}" if (ministere or prog) else "État"

        purpose = C.clean_text(r.get(c_objet)) if c_objet else ""
        conv_raw = C.clean_text(r.get(c_conv)) if c_conv else ""
        is_conv = True if conv_raw and C.fold(conv_raw) not in ("non", "0", "n") else (
            None if not conv_raw else False)

        kind = beneficiary_kind(r.get(c_categ) if c_categ else "", name_raw)
        if kind not in ("association", "inconnu"):
            flags.append("beneficiary_not_association")

        conf = "high" if (siret and dep and year) else ("low" if not (siret or rna) and not dep else "medium")
        for fl in flags:
            bump(stats["flags"], fl)

        row_ref = f"{os.path.basename(path)}#L{i}"
        out["row_id"].append(hashlib.sha1(f"{source_id}|{row_ref}".encode()).hexdigest()[:20])
        out["business_key"].append(business_key(siret, name_norm, "ETAT", year, amount, C.normalize_name(purpose)))
        out["beneficiary_name_raw"].append(name_raw)
        out["beneficiary_name_norm"].append(name_norm)
        out["beneficiary_siret"].append(siret)
        out["beneficiary_siren"].append(siren)
        out["beneficiary_rna"].append(rna)
        out["beneficiary_kind"].append(kind)
        out["beneficiary_commune_insee"].append(insee)
        out["beneficiary_dep_code"].append(dep)
        out["beneficiary_reg_code"].append(reg)
        out["beneficiary_address_raw"].append(C.clean_text(r.get(c_ville)) if c_ville else None)
        out["donor_name_raw"].append(donor_name)
        out["donor_name_norm"].append("ETAT")
        out["donor_siren"].append(None)
        out["donor_level"].append("etat")
        out["donor_commune_insee"].append(None)
        out["donor_dep_code"].append(None)
        out["donor_reg_code"].append(None)
        out["donor_program"].append(donor_program)
        # Une valeur invraisemblable n'est pas un montant : elle est écartée de
        # `amount_eur` — que l'on peut donc sommer sans précaution — et conservée
        # verbatim dans `amount_rejected_eur`, pour ne rien perdre.
        rejected = C.amount_is_implausible(amount)
        out["amount_eur"].append(None if rejected else amount)
        out["amount_rejected_eur"].append(amount if rejected else None)
        out["year"].append(year)
        out["year_provenance"].append("published" if year_prov != "plf_minus_2" else "inferred")
        out["date_convention"].append(C.clean_text(r.get(c_date))[:10] if c_date else None)
        out["purpose_raw"].append(purpose or None)
        out["purpose_norm"].append(C.normalize_name(purpose) or None)
        out["granularity"].append(row_granularity)
        out["is_convention"].append(is_conv)
        out["quality_flags"].append(flags)
        out["confidence"].append(conf)
        out["source_id"].append(source_id)
        out["source_label"].append(entry.get("dataset_title") or source_id)
        out["source_url"].append(entry.get("dataset_page") or DATASET_HOME)
        out["source_row_ref"].append(row_ref)
        out["source_family"].append("plf_jaune")
        out["license"].append(entry.get("license") or "lov2")
        out["ingested_at"].append(ingested_at)
        bump(stats["by_granularity"], row_granularity)
        stats["rows_kept"] += 1

    table = pa.table(out, schema=SCHEMA)
    os.makedirs(OUT_DIR, exist_ok=True)
    dest = os.path.join(OUT_DIR, f"{source_id}.parquet")
    pq.write_table(table, dest, compression="zstd")
    stats["parquet"] = os.path.relpath(dest, ROOT)
    stats["parquet_bytes"] = os.path.getsize(dest)
    stats["amount_total"] = round(sum(x for x in out["amount_eur"] if x), 2)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int)
    args = ap.parse_args()

    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
    entries = [e for e in manifest["datasets"] if e.get("file") and not e.get("error")]
    if args.only:
        entries = [e for e in entries if e["plf_year"] == args.only]

    ingested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"Normalisation de la famille plf_jaune — {len(entries)} millésimes\n")
    print(f"  {'PLF':>5} {'année':>6} {'lues':>8} {'gardées':>8} {'écartées':>8}  {'montant':>16}  provenance")
    print("  " + "-" * 78)

    all_stats = []
    for e in sorted(entries, key=lambda x: x["plf_year"]):
        st = normalize_file(os.path.join(ROOT, e["file"]), e, ingested_at)
        all_stats.append(st)
        print(f"  {st['plf_year']:>5} {st['data_year'] or '?':>6} {st['rows_read']:>8} "
              f"{st['rows_kept']:>8} {st['rows_dropped']:>8}  {st['amount_total']:>15,.0f}€  {st['year_provenance']}")

    out = os.path.join(ROOT, "data", "canonical", "normalize-plf-jaune.stats.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"family": "plf_jaune", "normalized_at": ingested_at, "files": all_stats},
                  f, ensure_ascii=False, indent=2)
        f.write("\n")

    kept = sum(s["rows_kept"] for s in all_stats)
    print("  " + "-" * 78)
    print(f"  {kept:,} lignes retenues, {sum(s['rows_dropped'] for s in all_stats):,} écartées")
    print(f"  -> {os.path.relpath(out, ROOT)}")


if __name__ == "__main__":
    main()
