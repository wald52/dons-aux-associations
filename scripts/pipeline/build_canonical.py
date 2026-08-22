"""Assemble les parties normalisées en une table canonique unique, déduplique
entre sources, et produit le rapport de qualité qui fait foi.

Doctrine de déduplication (cf. SCHEMA.md) — un point important :

  On ne déduplique **qu'entre sources différentes**. Si une même source publie
  deux lignes de clé métier identique, on les conserve toutes les deux : c'est
  ce que l'administration a publié, et rien ne dit qu'il s'agit d'une erreur
  plutôt que de deux versements réellement identiques. On se contente de le
  signaler. En revanche, deux sources décrivant la même subvention sont
  réconciliées, car c'est là qu'est le double comptage.

Usage :
    python3 scripts/pipeline/build_canonical.py

Entrée : data/canonical/parts/*.parquet
Sortie : data/canonical/subventions.parquet
         data/canonical/quality-report.json
         data/canonical/coverage.json
"""

import collections
import glob
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyarrow as pa
import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
PARTS = os.path.join(ROOT, "data", "canonical", "parts")
OUT_DIR = os.path.join(ROOT, "data", "canonical")

# Ordre de préséance quand deux sources décrivent la même subvention : le
# portail de la collectivité connaît mieux son versement que l'agrégat national.
FAMILY_RANK = {"portail": 0, "plf_jaune": 1, "scdl": 2, "manuel": 3}
CONF_RANK = {"high": 0, "medium": 1, "low": 2}


def load_parts():
    files = sorted(glob.glob(os.path.join(PARTS, "*.parquet")))
    if not files:
        raise SystemExit("Aucune partie dans data/canonical/parts/ — lancer d'abord un normaliseur.")
    tables = [pq.read_table(f) for f in files]
    return pa.concat_tables(tables), files


def dedupe(table):
    """Réconcilie les lignes de même clé métier issues de sources différentes."""
    cols = {n: table.column(n).to_pylist() for n in
            ("business_key", "source_id", "source_family", "confidence",
             "beneficiary_siret", "amount_eur")}
    n = table.num_rows

    groups = collections.defaultdict(list)
    for i in range(n):
        groups[cols["business_key"][i]].append(i)

    keep = [True] * n
    stats = {
        "groups_total": len(groups),
        "collisions_same_source": 0, "rows_same_source": 0,
        "collisions_cross_source": 0, "rows_dropped": 0, "amount_dropped": 0.0,
        "collisions_homonymes": 0, "rows_homonymes": 0,
        "dropped_by_source": collections.Counter(),
    }

    def fondre(idx):
        """Ne garde qu'une ligne du lot, la mieux renseignée."""
        stats["collisions_cross_source"] += 1
        best = min(idx, key=lambda i: (
            CONF_RANK.get(cols["confidence"][i], 9),
            FAMILY_RANK.get(cols["source_family"][i], 9),
            0 if cols["beneficiary_siret"][i] else 1,
        ))
        for i in idx:
            if i != best:
                keep[i] = False
                stats["rows_dropped"] += 1
                stats["amount_dropped"] += cols["amount_eur"][i] or 0.0
                stats["dropped_by_source"][cols["source_id"][i]] += 1

    for key, idx in groups.items():
        if len(idx) == 1:
            continue
        sources = {cols["source_id"][i] for i in idx}
        if len(sources) == 1:
            # Doublon interne à une source : on garde, on signale.
            stats["collisions_same_source"] += 1
            stats["rows_same_source"] += len(idx)
            continue

        # La clé porte le NOM du bénéficiaire, pas son SIRET — sans quoi elle
        # serait instable entre deux sources qui ne publient pas les mêmes
        # identifiants. Mais des homonymes existent : « MAISON FAMILIALE
        # RURALE » désigne plusieurs établissements distincts d'un même
        # département, qui reçoivent la même année le même montant rond pour le
        # même objet générique. Quand les SIRET se contredisent, ce sont des
        # personnes morales différentes : les fondre EFFACERAIT une subvention
        # réelle. On ne fond alors qu'à SIRET égal, et on laisse les lignes
        # sans SIRET tranquilles — rien ne dit à laquelle elles appartiennent.
        sirets = {cols["beneficiary_siret"][i] for i in idx
                  if cols["beneficiary_siret"][i]}
        if len(sirets) > 1:
            stats["collisions_homonymes"] += 1
            stats["rows_homonymes"] += len(idx)
            par_siret = collections.defaultdict(list)
            for i in idx:
                if cols["beneficiary_siret"][i]:
                    par_siret[cols["beneficiary_siret"][i]].append(i)
            for lot in par_siret.values():
                if len(lot) > 1 and len({cols["source_id"][i] for i in lot}) > 1:
                    fondre(lot)
            continue

        fondre(idx)

    stats["dropped_by_source"] = dict(stats["dropped_by_source"])
    stats["amount_dropped"] = round(stats["amount_dropped"], 2)
    return table.filter(pa.array(keep)), stats


def fill_rate(table, column):
    col = table.column(column)
    return round((table.num_rows - col.null_count) / table.num_rows * 100, 1) if table.num_rows else 0.0


def quality_report(table, dedup_stats, part_files):
    rejected = table.column("amount_rejected_eur").to_pylist()
    src = table.column("source_id").to_pylist()
    amt = table.column("amount_eur").to_pylist()
    gran = table.column("granularity").to_pylist()
    flags = table.column("quality_flags").to_pylist()
    years = table.column("year").to_pylist()
    dep = table.column("beneficiary_dep_code").to_pylist()
    kind = table.column("beneficiary_kind").to_pylist()
    mesure = table.column("measure").to_pylist()
    kind_prov = table.column("beneficiary_kind_provenance").to_pylist()
    purpose = table.column("purpose_norm").to_pylist()
    # La nature du concours se lit dans l'objet : elle n'est pas stockée, elle
    # se recalcule partout depuis la même fonction de `common.py`.
    concours = [C.nature_du_concours(purpose[i], flags[i])[0]
                for i in range(table.num_rows)]

    per_source = collections.defaultdict(lambda: {
        "rows": 0, "amount_individual": 0.0, "amount_aggregate": 0.0,
        "amount_not_summed": 0.0, "rows_not_summed": 0,
        "flags": collections.Counter(), "years": set(), "kinds": collections.Counter(),
    })
    for i, s in enumerate(src):
        d = per_source[s]
        d["rows"] += 1
        if gran[i] == "aggregate":
            d["amount_aggregate"] += amt[i] or 0
        elif not C.compte_dans_les_totaux(gran[i], mesure[i], kind[i], kind_prov[i],
                                          concours[i]):
            # Écartée des totaux, jamais de la table : elle reste consultable.
            d["amount_not_summed"] += amt[i] or 0
            d["rows_not_summed"] += 1
        else:
            d["amount_individual"] += amt[i] or 0
        for f in flags[i] or []:
            d["flags"][f] += 1
        if years[i]:
            d["years"].add(years[i])
        d["kinds"][kind[i]] += 1

    sources = {}
    for s, d in sorted(per_source.items()):
        sources[s] = {
            "rows": d["rows"],
            "amount_individual_eur": round(d["amount_individual"], 2),
            "amount_aggregate_eur": round(d["amount_aggregate"], 2),
            "amount_not_summed_eur": round(d["amount_not_summed"], 2),
            "rows_not_summed": d["rows_not_summed"],
            "years": sorted(d["years"]),
            "flags": dict(d["flags"].most_common()),
            "beneficiary_kinds": dict(d["kinds"].most_common()),
        }

    total_flags = collections.Counter()
    for f in flags:
        for x in f or []:
            total_flags[x] += 1

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "parts": [os.path.relpath(p, ROOT) for p in part_files],
        "rows_total": table.num_rows,
        # `amount_eur` est nul pour les valeurs qui ne sont pas des montants :
        # une somme simple est donc juste, sans filtre à ne pas oublier.
        "amount_individual_eur": round(sum(
            a or 0 for a, g, m, k, kp, co in zip(amt, gran, mesure, kind, kind_prov, concours)
            if C.compte_dans_les_totaux(g, m, k, kp, co)), 2),
        "amount_aggregate_eur": round(sum(a or 0 for a, g in zip(amt, gran) if g == "aggregate"), 2),
        # Individuelles mais non sommées : exécution budgétaire déjà comptée au
        # vote, ou bénéficiaire que la source déclare hors du champ associatif.
        "amount_not_summed_eur": round(sum(
            a or 0 for a, g, m, k, kp, co in zip(amt, gran, mesure, kind, kind_prov, concours)
            if g != "aggregate" and not C.compte_dans_les_totaux(g, m, k, kp, co)), 2),
        "rows_not_summed": sum(
            1 for g, m, k, kp, co in zip(gran, mesure, kind, kind_prov, concours)
            if g != "aggregate" and not C.compte_dans_les_totaux(g, m, k, kp, co)),
        # Les quatre natures de concours, dont une seule est un don.
        "by_concours": {
            nat: {"rows": sum(1 for c in concours if c == nat),
                  "amount_eur": round(sum(a or 0 for a, c in zip(amt, concours)
                                          if c == nat), 2)}
            for nat in C.NATURES_DU_CONCOURS},
        "amount_rejected_eur": round(sum(x or 0 for x in rejected), 2),
        "rows_rejected": sum(1 for x in rejected if x is not None),
        "years_covered": sorted({y for y in years if y}),
        "fill_rates_percent": {
            c: fill_rate(table, c) for c in (
                "beneficiary_siret", "beneficiary_siren", "beneficiary_rna",
                "beneficiary_commune_insee", "beneficiary_dep_code", "year",
                "purpose_raw", "donor_program")
        },
        "departments_present": len({d for d in dep if d}),
        "quality_flags": dict(total_flags.most_common()),
        "deduplication": dedup_stats,
        "by_source": sources,
    }


def anomalies(table, report):
    """Signale ce qui mérite un œil humain, sans rien corriger.

    La doctrine interdit de retoucher un montant : on se contente donc de
    pointer les écarts qui ressemblent à un problème de source, pour qu'ils
    soient tranchés en connaissance de cause plutôt que découverts par un
    lecteur sur la carte.
    """
    import statistics
    y = table.column("year").to_pylist()
    a = table.column("amount_eur").to_pylist()
    g = table.column("granularity").to_pylist()

    fl = table.column("quality_flags").to_pylist()
    per_year = collections.defaultdict(float)
    for i in range(len(y)):
        if y[i] and g[i] != "aggregate":
            per_year[y[i]] += a[i] or 0

    out = []
    # On compare chaque année à ses voisines plutôt qu'à la médiane globale :
    # la série croît fortement sur la période, si bien qu'une médiane
    # d'ensemble masquerait une rupture locale.
    years = sorted(per_year)
    for i, year in enumerate(years):
        voisins = [per_year[years[j]] for j in (i - 1, i + 1) if 0 <= j < len(years)]
        if not voisins:
            continue
        ref = statistics.median(voisins)
        total = per_year[year]
        if ref and total > 3 * ref:
            out.append({
                "type": "rupture_annuelle",
                "year": year,
                "amount_eur": round(total, 2),
                "mediane_annees_voisines_eur": round(ref, 2),
                "rapport": round(total / ref, 1),
                "commentaire": ("Total sans commune mesure avec les années voisines. "
                                "Conforme à ce que publie la source — non corrigé. "
                                "À vérifier : périmètre de l'annexe cette année-là "
                                "(quelques très grosses subventions y pèsent lourd)."),
            })

    d = report["deduplication"]
    if d["rows_same_source"]:
        out.append({
            "type": "doublons_internes_conserves",
            "rows": d["rows_same_source"],
            "groupes": d["collisions_same_source"],
            "commentaire": ("Lignes de clé métier identique au sein d'une même source. "
                            "Conservées volontairement : l'inspection montre qu'il s'agit "
                            "majoritairement d'organismes homonymes distincts (23 « Maison "
                            "des jeunes et de la culture » recevant la même subvention type), "
                            "et non de doublons."),
        })

    # DOUBLONS QUE LA CLÉ MÉTIER NE VOIT PAS — l'objet fait partie de la clé,
    # si bien que deux publications d'une même subvention sous deux libellés
    # d'objet différents produisent deux clés. `ville-grenoble` écrit
    # « SUBVENTION PROJET » là où `ville-grenoble-2016` écrit « MUSIQUES » :
    # même bénéficiaire, même montant, même exercice, même donateur.
    #
    # On les COMPTE sans les retirer. Retirer l'objet de la clé fondrait deux
    # subventions réellement distinctes de même montant à la même association la
    # même année — la même asymétrie que pour les homonymes, et du mauvais côté :
    # fondre EFFACE une subvention réelle, garder en laisse une de trop, visible
    # et corrigeable.
    bn = table.column("beneficiary_name_norm").to_pylist()
    dn = table.column("donor_name_norm").to_pylist()
    src = table.column("source_id").to_pylist()
    po = table.column("purpose_norm").to_pylist()
    kind_a = table.column("beneficiary_kind").to_pylist()
    prov_a = table.column("beneficiary_kind_provenance").to_pylist()
    me = table.column("measure").to_pylist()
    familles = collections.defaultdict(lambda: [set(), set(), 0, 0.0])
    for i in range(len(y)):
        nat = C.nature_du_concours(po[i], fl[i])[0]
        if not C.compte_dans_les_totaux(g[i], me[i], kind_a[i], prov_a[i], nat):
            continue
        if not a[i] or a[i] <= 0:
            continue
        cle = (bn[i], C.identite_donateur(dn[i], y[i]), y[i], round(a[i], 2))
        f = familles[cle]
        f[0].add(src[i])
        f[1].add(po[i] or "")
        f[2] += 1
        f[3] += a[i]
    groupes = lignes = 0
    montant = 0.0
    for (_, _, _, valeur), (sources, objets, compte, somme) in familles.items():
        # Plusieurs sources ET plusieurs objets : la marque d'une même
        # subvention republiée sous un autre libellé.
        if len(sources) > 1 and len(objets) > 1:
            groupes += 1
            lignes += compte - 1
            montant += valeur * (compte - 1)
    if groupes:
        out.append({
            "type": "doublons_probables_hors_cle",
            "groupes": groupes,
            "rows": lignes,
            "amount_eur": round(montant, 2),
            "commentaire": ("Même bénéficiaire, même donateur, même exercice et même "
                            "montant, publiés par plusieurs sources sous des objets "
                            "différents. L'objet faisant partie de la clé métier, la "
                            "déduplication ne les rapproche pas. COMPTÉS DANS LES TOTAUX "
                            "et signalés ici : retirer l'objet de la clé fondrait deux "
                            "subventions réellement distinctes de même montant à la même "
                            "association la même année, ce qui effacerait de l'argent réel."),
        })

    # UN NOM QUI EST UN NUMÉRO — la source a recopié le SIREN ou le RNA dans la
    # colonne du nom. Le bénéficiaire est identifiable, mais il est illisible
    # pour un humain, et deux lignes du même organisme ne se rapprochent pas si
    # l'une porte le nom et l'autre le numéro.
    import re as _re
    numerique = _re.compile(r"^(?:[0-9]{9,14}|W[0-9]{9})$")
    n_num = 0
    m_num = 0.0
    for i in range(len(y)):
        nat = C.nature_du_concours(po[i], fl[i])[0]
        if not C.compte_dans_les_totaux(g[i], me[i], kind_a[i], prov_a[i], nat):
            continue
        if bn[i] and numerique.match(bn[i]):
            n_num += 1
            m_num += a[i] or 0
    if n_num:
        out.append({
            "type": "nom_de_beneficiaire_numerique",
            "rows": n_num,
            "amount_eur": round(m_num, 2),
            "commentaire": ("Le nom du bénéficiaire est un identifiant (SIREN ou RNA) "
                            "recopié dans la colonne du nom. Conservé tel quel — c'est "
                            "ce que la source publie — mais ces organismes sont "
                            "illisibles sur le site et ne se rapprochent pas de leurs "
                            "propres lignes correctement nommées."),
        })

    # LES PLUS GROS BÉNÉFICIAIRES DONT LA NATURE EST DEVINÉE. Le site classe
    # « association » par défaut, faute de mieux : c'est le bon côté où se
    # tromper (exclure à tort efface une association réelle). Mais quand la
    # devinette porte des centaines de millions d'euros, elle mérite un œil.
    par_benef = collections.defaultdict(float)
    for i in range(len(y)):
        nat = C.nature_du_concours(po[i], fl[i])[0]
        if not C.compte_dans_les_totaux(g[i], me[i], kind_a[i], prov_a[i], nat):
            continue
        if prov_a[i] == "guessed" and kind_a[i] == "association" and bn[i]:
            par_benef[bn[i]] += a[i] or 0
    gros = sorted(par_benef.items(), key=lambda x: -x[1])[:20]
    if gros:
        out.append({
            "type": "nature_devinee_gros_montants",
            "rows": len(par_benef),
            "amount_eur": round(sum(par_benef.values()), 2),
            "principaux": [[nom, round(v, 2)] for nom, v in gros],
            "commentaire": ("Bénéficiaires comptés comme associations parce que la "
                            "source ne dit pas le contraire, jamais parce qu'elle "
                            "l'affirme. La liste demande un œil humain : on y trouve "
                            "des sociétés (SNCF Voyageurs), des opérateurs publics "
                            "(Centre national du cinéma) et des organismes "
                            "internationaux. Rien n'est retiré — deviner une exclusion "
                            "effacerait des associations réelles."),
        })

    rej = table.column("amount_rejected_eur").to_pylist()
    impl = [i for i in range(len(rej)) if rej[i] is not None]
    if impl:
        out.append({
            "type": "montants_invraisemblables_exclus",
            "rows": len(impl),
            "amount_eur": round(sum(rej[i] or 0 for i in impl), 2),
            "commentaire": ("Valeurs supérieures à dix milliards d'euros pour une "
                            "attribution unique : ce ne sont pas des montants. Cas "
                            "constaté, un SIRET recopié dans la colonne montant par un "
                            "convertisseur défaillant. Conservées dans la table avec le "
                            "drapeau amount_implausible ; la valeur publiée est conservée "
                            "dans `amount_rejected_eur`, et `amount_eur` est nul — une somme "
                            "sur `amount_eur` est donc juste sans précaution particulière."),
        })

    zero = sum(1 for i in range(len(a)) if a[i] == 0)
    if zero:
        out.append({"type": "montants_nuls", "rows": zero,
                    "commentaire": "Montant à zéro publié tel quel par la source."})
    return out


def coverage(table):
    """Couverture face au référentiel INSEE — la base de la carte de la phase 4.

    Distingue explicitement « pas de donnée » de « zéro euro » : un département
    gris doit pouvoir dire lequel des deux il est.
    """
    ref = C.referentiel()
    dep = table.column("beneficiary_dep_code").to_pylist()
    amt = table.column("amount_eur").to_pylist()
    gran = table.column("granularity").to_pylist()

    seen = collections.defaultdict(lambda: {"rows": 0, "amount": 0.0})
    for i, d in enumerate(dep):
        if not d:
            continue
        seen[d]["rows"] += 1
        if gran[i] != "aggregate":
            seen[d]["amount"] += amt[i] or 0

    departements = {}
    for code, meta in ref["departements"].items():
        s = seen.get(code)
        departements[code] = {
            "nom": meta["nom"], "reg_code": meta["reg_code"],
            "statut": "avec_donnees" if s else "sans_donnees",
            "rows": s["rows"] if s else 0,
            "amount_eur": round(s["amount"], 2) if s else 0.0,
        }

    with_data = sum(1 for v in departements.values() if v["statut"] == "avec_donnees")
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "referentiel": ref_meta(),
        "note": ("La carte situe les associations qui REÇOIVENT, pas les collectivités "
                 "qui versent : un département se colore dès qu'une association qui y "
                 "siège a touché une subvention, d'où qu'elle vienne."),
        "departements": {
            "univers": len(ref["departements"]),
            "avec_donnees": with_data,
            "sans_donnees": len(ref["departements"]) - with_data,
            "detail": departements,
        },
        "lignes_sans_departement": sum(1 for d in dep if not d),
    }


def ref_meta():
    p = os.path.join(ROOT, "data", "referentiel", "referentiel.meta.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def corriger_niveau_apres_fusion(table):
    """Remet au bon niveau les lignes qui nomment une collectivité disparue.

    Une subvention de 2021 attribuée au « département de Paris » désigne une
    entité supprimée le 1er janvier 2019 : la classer en `departement` ferait
    dire au site qu'un département de Paris versait encore des subventions.
    Le LIBELLÉ publié n'est pas retouché — seul notre classement l'est, et la
    règle qui le décide est celle de `common.FUSIONS_COLLECTIVITES`.
    """
    noms = table.column("donor_name_norm").to_pylist()
    annees = table.column("year").to_pylist()
    niveaux = table.column("donor_level").to_pylist()
    touches = 0
    for i, (nom, an, niv) in enumerate(zip(noms, annees, niveaux)):
        neuf = C.fusion_de_collectivite(nom, an)
        if neuf and neuf != niv:
            niveaux[i] = neuf
            touches += 1
    if not touches:
        return table, 0
    j = table.schema.get_field_index("donor_level")
    return table.set_column(j, "donor_level", pa.array(niveaux, pa.string())), touches


def main():
    # Ré-emballer la sortie au CHARGEMENT du module détacherait le flux de
    # l'importeur : tout `print` de `refresh_rapport.py` lèverait ensuite
    # « I/O operation on closed file ». Cf. CLAUDE.md.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print("Assemblage de la table canonique\n")
    table, part_files = load_parts()
    print(f"  {len(part_files)} parties, {table.num_rows:,} lignes lues")

    table, fusions = corriger_niveau_apres_fusion(table)
    if fusions:
        print(f"  fusions de collectivités : {fusions:,} lignes dont le niveau "
              f"nommait une entité disparue à leur date")

    table, dedup_stats = dedupe(table)
    print(f"  déduplication entre sources : {dedup_stats['rows_dropped']:,} lignes écartées "
          f"({dedup_stats['amount_dropped']:,.0f} €)")
    print(f"  doublons internes à une source, conservés et signalés : "
          f"{dedup_stats['rows_same_source']:,} lignes "
          f"dans {dedup_stats['collisions_same_source']:,} groupes")

    # Écriture PARTITIONNÉE par année. Deux raisons :
    #   - GitHub refuse tout fichier de plus de 100 Mo, et la table complète en
    #     fait 110 ; le hook de pré-réception rejette le push ;
    #   - c'est de toute façon ce que la phase 2 attend : DuckDB élague les
    #     partitions inutiles, donc une requête sur une année ne touche qu'un
    #     fichier au lieu de la table entière.
    import pyarrow.dataset as ds
    import shutil
    dest_dir = os.path.join(OUT_DIR, "subventions")
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    ds.write_dataset(
        table, dest_dir, format="parquet",
        partitioning=ds.partitioning(pa.schema([("year", pa.int32())]), flavor="hive"),
        existing_data_behavior="overwrite_or_ignore",
        file_options=ds.ParquetFileFormat().make_write_options(compression="zstd"),
        max_rows_per_group=64 * 1024,
    )
    parts_written = sorted(glob.glob(os.path.join(dest_dir, "**", "*.parquet"), recursive=True))
    size = sum(os.path.getsize(f) for f in parts_written)
    biggest = max((os.path.getsize(f) for f in parts_written), default=0)
    # Ancien fichier unique : on le retire pour ne pas laisser deux vérités.
    legacy_single = os.path.join(OUT_DIR, "subventions.parquet")
    if os.path.exists(legacy_single):
        os.remove(legacy_single)

    report = quality_report(table, dedup_stats, part_files)
    report["anomalies"] = anomalies(table, report)
    with open(os.path.join(OUT_DIR, "quality-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    cov = coverage(table)
    with open(os.path.join(OUT_DIR, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(cov, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\n  Table canonique : {table.num_rows:,} lignes, {size/1048576:.1f} Mo "
          f"en {len(parts_written)} partitions (la plus grosse : {biggest/1048576:.1f} Mo)")
    print(f"  Montant (attributions individuelles) : {report['amount_individual_eur']:,.0f} €")
    print(f"  Montant (totaux agrégés, jamais sommés avec) : {report['amount_aggregate_eur']:,.0f} €")
    print(f"  Montant écarté des totaux (versé, ou hors associations) : "
          f"{report['amount_not_summed_eur']:,.0f} € sur {report['rows_not_summed']:,} lignes")
    print(f"  Années : {report['years_covered'][0]}-{report['years_covered'][-1]}")
    print(f"  Départements représentés : {report['departments_present']} / {cov['departements']['univers']}")
    print("\n  Taux de remplissage :")
    for k, v in report["fill_rates_percent"].items():
        print(f"    {k:28s} {v:5.1f} %")
    if report["anomalies"]:
        print("\n  Anomalies signalées (non corrigées) :")
        for an in report["anomalies"]:
            detail = (f"année {an['year']} — {an['amount_eur']:,.0f} € "
                      f"(x{an['rapport']} les années voisines)" if an["type"] == "rupture_annuelle"
                      else f"{an.get('rows', 0):,} lignes"
                      + (f" — {an['amount_eur']:,.0f} € écartés" if an["type"] == "montants_invraisemblables_exclus" else ""))
            print(f"    · {an['type']:32s} {detail}")

    print(f"\n  -> data/canonical/subventions/ (partitionné par année)")
    print(f"  -> data/canonical/quality-report.json")
    print(f"  -> data/canonical/coverage.json")


if __name__ == "__main__":
    main()
