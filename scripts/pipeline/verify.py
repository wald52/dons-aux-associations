"""Contrôles de bout en bout du pipeline canonique.

Sert de garde-fou : toute modification du pipeline doit le laisser vert. Les
contrôles portent sur ce qui peut casser en silence — une ligne perdue, un
montant qui dérive, une valeur hors taxonomie, une géographie incohérente.

Usage :
    python3 scripts/pipeline/verify.py

Code de sortie 1 si un contrôle échoue.
"""

import collections
import glob
import io
import json
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import pyarrow as pa
import pyarrow.parquet as pq

import common as C

ROOT = C.ROOT
CANON = os.path.join(ROOT, "data", "canonical", "subventions")
PARTS = os.path.join(ROOT, "data", "canonical", "parts")

DONOR_LEVELS = {"etat", "operateur", "region", "departement", "epci", "commune", "inconnu"}
GRANULARITIES = {"individual", "aggregate"}
KINDS = {"association", "public_body", "company", "individual", "inconnu"}
CONFIDENCES = {"high", "medium", "low"}
FAMILIES = {"plf_jaune", "scdl", "portail", "manuel"}

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'OK ' if ok else 'ÉCHEC'}] {name}" + (f"  — {detail}" if detail else ""))
    return ok


def main():
    print("Vérification du pipeline canonique\n")
    # La table est partitionnée par année : on la relit comme un jeu de
    # données, et l'on remet `year` en int32 (Hive la restitue en catégorie).
    import pyarrow.dataset as ds
    table = ds.dataset(CANON, format="parquet", partitioning="hive").to_table()
    table = table.set_column(table.schema.get_field_index("year"), "year",
                             table.column("year").cast(pa.int32()))
    report = json.load(open(os.path.join(ROOT, "data", "canonical", "quality-report.json"),
                             encoding="utf-8"))
    n = table.num_rows

    # 1. Aucune ligne perdue entre les parties et la table finale ------------
    part_rows = sum(pq.read_metadata(f).num_rows
                    for f in glob.glob(os.path.join(PARTS, "*.parquet")))
    dropped = report["deduplication"]["rows_dropped"]
    check("conservation des lignes",
          part_rows - dropped == n,
          f"{part_rows:,} parties − {dropped:,} dédupliquées = {part_rows - dropped:,} (table : {n:,})")

    # 2. Taxonomies closes ---------------------------------------------------
    for col, allowed in (("donor_level", DONOR_LEVELS), ("granularity", GRANULARITIES),
                         ("beneficiary_kind", KINDS), ("confidence", CONFIDENCES),
                         ("source_family", FAMILIES)):
        vals = set(table.column(col).to_pylist())
        extra = {v for v in vals if v is not None} - allowed
        check(f"taxonomie close : {col}", not extra, f"hors liste : {sorted(extra)}" if extra else
              f"{len(vals)} valeurs")

    # 3. Géographie cohérente ------------------------------------------------
    ref = C.referentiel()
    dep = table.column("beneficiary_dep_code").to_pylist()
    reg = table.column("beneficiary_reg_code").to_pylist()
    unknown = {d for d in dep if d and d not in ref["departements"]}
    check("codes département connus du référentiel", not unknown,
          f"inconnus : {sorted(unknown)[:6]}" if unknown else f"{len({d for d in dep if d})} départements")

    mismatch = sum(1 for i in range(n) if dep[i] and reg[i]
                   and ref["departements"][dep[i]]["reg_code"] != reg[i])
    check("région cohérente avec le département", mismatch == 0, f"{mismatch:,} incohérences")

    orphan = sum(1 for i in range(n) if dep[i] and not reg[i])
    check("aucun département sans région", orphan == 0, f"{orphan:,} lignes")

    insee = table.column("beneficiary_commune_insee").to_pylist()
    bad_insee = {c for c in insee if c and c not in ref["communes"]}
    check("codes commune connus du référentiel", not bad_insee,
          f"inconnus : {sorted(bad_insee)[:6]}" if bad_insee else
          f"{len({c for c in insee if c}):,} communes distinctes")

    # 4. Marqueurs d'absence proscrits (nul plutôt que faux) -----------------
    forbidden_dep = sum(1 for d in dep if d in ("00", "0", ""))
    check("aucun département « 00 » ou vide", forbidden_dep == 0, f"{forbidden_dep:,} lignes")
    years = table.column("year").to_pylist()
    bad_year = sum(1 for y in years if y is not None and not (1990 <= y <= 2100))
    check("aucune année hors bornes", bad_year == 0, f"{bad_year:,} lignes")

    # 5. Identifiants --------------------------------------------------------
    row_ids = table.column("row_id").to_pylist()
    check("row_id unique", len(set(row_ids)) == n,
          f"{n - len(set(row_ids)):,} collisions")
    check("business_key toujours renseignée",
          table.column("business_key").null_count == 0)
    sirets = [s for s in table.column("beneficiary_siret").to_pylist() if s]
    check("SIRET tous valides (longueur et clé de Luhn)",
          all(C.valid_siret(s) for s in sirets[:50000]),
          f"{len(sirets):,} SIRET, contrôle sur les 50 000 premiers")

    # 6. Montants ------------------------------------------------------------
    amt = table.column("amount_eur").to_pylist()
    rej = table.column("amount_rejected_eur").to_pylist()
    flags = table.column("quality_flags").to_pylist()
    # Le contrôle qui compte : `amount_eur` ne doit JAMAIS contenir de valeur
    # invraisemblable, pour qu'une somme naïve reste juste.
    check("amount_eur sommable sans précaution",
          not any(C.amount_is_implausible(a) for a in amt),
          f"{sum(1 for a in amt if C.amount_is_implausible(a))} valeurs aberrantes")
    # Deux motifs de mise à l'écart : une valeur qui n'est pas un montant, et
    # une source dont l'unité monétaire est douteuse. Dans les deux cas la
    # valeur publiée est conservée et `amount_eur` est nul.
    MOTIFS = ("amount_implausible", "amount_unit_suspect")
    ecartees = [i for i in range(n) if rej[i] is not None]
    check("valeurs écartées conservées et signalées",
          all(any(m in (flags[i] or []) for m in MOTIFS) for i in ecartees)
          and all(amt[i] is None for i in ecartees),
          f"{len(ecartees):,} lignes dans amount_rejected_eur")
    check("aucune valeur écartée sans motif",
          not [i for i in range(n)
               if rej[i] is None and any(m in (flags[i] or []) for m in MOTIFS)],
          "cohérence drapeau / colonne")

    # 7. Le total publié exclut bien agrégats et invraisemblables ------------
    gran = table.column("granularity").to_pylist()
    mesure = table.column("measure").to_pylist()
    bkind = table.column("beneficiary_kind").to_pylist()
    bkprov = table.column("beneficiary_kind_provenance").to_pylist()
    purpose = table.column("purpose_norm").to_pylist()
    # Phase 15 : le verdict de l'INSEE entre dans la règle des totaux.
    bcj = table.column("beneficiary_legal_category").to_pylist()
    concours = [C.nature_du_concours(purpose[i], flags[i])[0] for i in range(n)]
    recomputed = round(sum(
        amt[i] or 0 for i in range(n)
        if C.compte_dans_les_totaux(gran[i], mesure[i], bkind[i], bkprov[i],
                                    concours[i], bcj[i])), 2)
    check("total individuel reproductible",
          abs(recomputed - report["amount_individual_eur"]) < 1,
          f"{recomputed:,.0f} € = rapport")

    # 8. Provenance ----------------------------------------------------------
    check("toute ligne porte sa source",
          table.column("source_id").null_count == 0 and table.column("source_row_ref").null_count == 0)

    # 9. Doublons entre sources : aucun ne subsiste --------------------------
    # Une subvention votée et la même subvention versée ne doivent jamais être
    # sommées ensemble : ce contrôle garde la distinction vivante.
    verses = sum(1 for m in mesure if m == "verse")
    check("mesure renseignée sur toute ligne",
          all(m in ("attribue", "verse") for m in mesure),
          f"{verses:,} lignes d'exécution budgétaire, hors totaux")
    declares = sum(1 for p in bkprov if p == "declared")
    check("provenance de la nature du bénéficiaire renseignée",
          all(p in ("declared", "guessed") for p in bkprov),
          f"{declares:,} natures déclarées par la source")

    bk = table.column("business_key").to_pylist()
    src = table.column("source_id").to_pylist()
    siret = table.column("beneficiary_siret").to_pylist()
    groups = collections.defaultdict(list)
    for i in range(n):
        groups[bk[i]].append(i)

    # Un doublon inter-sources ne peut subsister QUE si les SIRET du groupe se
    # contredisent : la clé porte le nom du bénéficiaire, et deux homonymes de
    # SIRET différents sont deux personnes morales qu'il serait faux de fondre.
    # Tout autre résidu est une déduplication qui n'a pas fait son travail.
    inexplique, homonymes = 0, 0
    for idx in groups.values():
        if len({src[i] for i in idx}) < 2:
            continue
        if len({siret[i] for i in idx if siret[i]}) > 1:
            homonymes += 1
        else:
            inexplique += 1
    check("aucun doublon inter-sources inexpliqué", inexplique == 0,
          f"{inexplique:,} groupes ; {homonymes:,} conservés pour SIRET contradictoires")

    # 9 bis. Les deux totaux servis au navigateur -----------------------------
    # Les agrégats sont ce que le site AFFICHE. S'ils s'écartent de la table, le
    # site ment sans que rien ne le signale : c'est exactement le genre de
    # divergence silencieuse que ce fichier existe pour attraper.
    meta_gz = os.path.join(ROOT, "data", "aggregates", "meta.json.gz")
    if os.path.exists(meta_gz):
        import gzip as _gzip
        with _gzip.open(meta_gz, "rt", encoding="utf-8") as f:
            tot = json.load(f).get("totaux", {})

        def cumul(garde):
            lignes = montant = 0
            for i in range(n):
                if garde(i):
                    lignes += 1
                    montant += amt[i] or 0
            return lignes, round(montant)

        n_vote, m_vote = cumul(lambda i: C.compte_dans_les_totaux(
            gran[i], mesure[i], bkind[i], bkprov[i], concours[i], bcj[i]))
        n_paye, m_paye = cumul(lambda i: mesure[i] == "verse" and C.est_un_don(
            gran[i], bkind[i], bkprov[i], concours[i], bcj[i]))
        check("agrégats : dons votés = table canonique",
              tot.get("dons_votes", {}).get("montant_eur") == m_vote
              and tot.get("dons_votes", {}).get("lignes") == n_vote,
              f"{m_vote:,.0f} € sur {n_vote:,} versements")
        check("agrégats : dons payés = table canonique",
              tot.get("dons_payes", {}).get("montant_eur") == m_paye
              and tot.get("dons_payes", {}).get("lignes") == n_paye,
              f"{m_paye:,.0f} € sur {n_paye:,} versements")

        # Voté, payé, hors-don et agrégats forment une partition : toute ligne
        # tombe dans une case et une seule. Un total qui « fuit » se voit ici.
        hors = sum(v[0] for v in tot.get("hors_don", {}).values())
        n_agg = sum(1 for i in range(n) if gran[i] == "aggregate")
        n_hors_champ = sum(
            1 for i in range(n)
            if gran[i] != "aggregate" and concours[i] == "don"
            and not C.est_un_don(gran[i], bkind[i], bkprov[i], concours[i], bcj[i]))
        check("toute ligne tombe dans une case et une seule",
              n_vote + n_paye + hors + n_agg + n_hors_champ == n,
              f"{n_vote:,} votés + {n_paye:,} payés + {hors:,} hors don "
              f"+ {n_agg:,} agrégats + {n_hors_champ:,} hors champ = {n:,}")

    # 10. Index de navigateur (phase 13) — s'il a été construit -----------
    #
    # Mêmes six garanties qu'à l'époque des Parquet, portées au format servi :
    # rien de ce que le navigateur affiche ne doit pouvoir diverger de la
    # table canonique en silence.
    rech = os.path.join(ROOT, "data", "recherche")
    if os.path.isdir(rech):
        import gzip as _gzip
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from build_index_navigateur import shard_of, NB_SHARDS, NB_BLOCS

        def _lire(chemin):
            with _gzip.open(chemin, "rt", encoding="utf-8") as f:
                return json.load(f)

        noms = _lire(os.path.join(rech, "noms.json.gz"))
        nb_benef = noms["nb"]
        check("index : versements comptés = table canonique",
              sum(noms["v"]) == n, f"{sum(noms['v']):,}")
        somme_idx = sum(noms["m"])
        # Même règle que l'index et que les agrégats — celle de common.py. La
        # recopier ici la ferait diverger au premier changement.
        somme_can = sum(
            amt[i] or 0 for i in range(n)
            if C.compte_dans_les_totaux(gran[i], mesure[i], bkind[i], bkprov[i],
                                        concours[i], bcj[i]))
        # L'index sert des entiers : l'écart admis est d'un euro par
        # bénéficiaire, pas d'un euro en tout.
        check("index : montants = table canonique",
              abs(somme_idx - somme_can) < nb_benef, f"{somme_idx:,.0f} €")

        # Le rang d'un résultat désigne un identifiant par sa POSITION : si un
        # bloc ne commence pas là où le précédent s'arrête, chaque fiche
        # ouverte serait celle d'une autre association.
        bids = []
        desalignes = 0
        for b in range(NB_BLOCS):
            bloc = _lire(os.path.join(rech, "ids", f"{b:03d}.json.gz"))
            if bloc["debut"] != len(bids):
                desalignes += 1
            bids.extend(bloc["ids"])
        check("index : blocs d'identifiants alignés sur les noms",
              desalignes == 0 and len(bids) == nb_benef and len(set(bids)) == nb_benef,
              f"{len(bids):,} identifiants, {len(set(bids)):,} distincts, "
              f"{desalignes} bloc(s) désaligné(s)")
        connus = set(bids)

        fichiers = sorted(glob.glob(os.path.join(rech, "fiches", "*.json.gz")))
        check(f"index : {NB_SHARDS} shards de fiches présents",
              len(fichiers) == NB_SHARDS, f"{len(fichiers)} fichiers")
        vrows = 0
        mal_places = 0
        orphelins = 0
        vus = set()
        for f in fichiers:
            num = int(os.path.basename(f)[:3])
            shard = _lire(f)
            vrows += len(shard["y"])
            dedans = shard["bid"].split("\n") if shard["bid"] else []
            mal_places += sum(1 for b in dedans if shard_of(b) != num)
            orphelins += sum(1 for b in dedans if b not in connus)
            vus.update(dedans)
        check("index : chaque versement dans son shard", mal_places == 0,
              f"{vrows:,} versements répartis")
        check("index : aucun bénéficiaire orphelin", orphelins == 0)
        check("index : total des shards = table canonique", vrows == n)

    # 10 bis. La nature juridique du bénéficiaire (phase 15) ----------------
    #
    # Le site ne devine plus « association » là où l'INSEE déclare autre chose.
    # Trois choses peuvent mal tourner, et chacune a son contrôle : que le
    # verdict diverge du référentiel, qu'une ligne écartée reste sommée, ou
    # qu'un bénéficiaire retenu se retrouve sans famille à afficher — ce
    # dernier viderait la différenciation que la consigne exige.
    bfam = table.column("beneficiary_family").to_pylist()
    basso = table.column("beneficiary_is_associatif").to_pylist()
    bsiren = table.column("beneficiary_siren").to_pylist()

    ref_nature = os.path.join(ROOT, "data", "referentiel", "nature-beneficiaires.parquet")
    if os.path.exists(ref_nature):
        import pyarrow.parquet as _pq
        rt = _pq.read_table(ref_nature)
        attendu = dict(zip(rt.column("siren").to_pylist(),
                           rt.column("categorie_juridique").to_pylist()))
        divergents = sum(1 for i in range(n)
                         if bsiren[i] in attendu and bcj[i] != attendu[bsiren[i]])
        check("nature juridique : la table dit ce que dit le référentiel",
              divergents == 0, f"{len(attendu):,} SIREN documentés")

    # Une ligne que l'INSEE déclare non associative ne doit PLUS peser dans les
    # totaux. C'est l'invariant de la phase, et le seul qui garde les 37,68 Md€
    # dehors.
    fuite = sum(1 for i in range(n)
                if basso[i] is False
                and C.compte_dans_les_totaux(gran[i], mesure[i], bkind[i],
                                             bkprov[i], concours[i], bcj[i]))
    m_dehors = sum(amt[i] or 0 for i in range(n) if basso[i] is False)
    check("nature juridique : rien de non associatif dans les totaux",
          fuite == 0, f"{m_dehors / 1e9:,.2f} Md€ tenus dehors")

    # Toute ligne porte une famille, y compris « nature non vérifiée » : c'est
    # elle que la fiche affiche. Une famille vide serait un trou d'affichage.
    sans_famille = sum(1 for i in range(n) if basso[i] is not False and not bfam[i])
    check("nature juridique : chaque bénéficiaire retenu a une famille affichable",
          sans_famille == 0,
          f"{len(set(f for f in bfam if f))} familles distinctes")

    # 11. Dénominateur, angle mort et totaux de contrôle (phase 10) ----------
    #
    # Ces trois jeux disent ce que le site NE VOIT PAS. Le risque qu'ils font
    # courir est unique en son genre : qu'un de leurs montants finisse par se
    # glisser dans les totaux du site. Le premier contrôle ne vérifie donc pas
    # une somme, il vérifie une SÉPARATION.
    denom_json = os.path.join(ROOT, "data", "canonical", "denominateur.json")
    if os.path.exists(denom_json):
        sources = set(table.column("source_id").to_pylist())
        check("dénominateur : aucune balance DGFiP dans la table canonique",
              not any(s and (s.startswith("balances") or s.startswith("dgfip")
                             or s.startswith("6574")) for s in sources),
              f"{len(sources)} sources")

        dn = json.load(open(denom_json, encoding="utf-8"))
        for niveau, r in dn["resume"].items():
            total_detail = sum(e["declare_eur"] for e in dn["niveaux"][niveau].values())
            if not check(f"dénominateur : {niveau}, résumé = détail",
                         abs(total_detail - r["declare_eur"]) <= 1,
                         f"{total_detail:,} €"):
                break
        somme_exercices = sum(v["declare_eur"]
                              for niveau in dn["par_exercice"]
                              for v in dn["par_exercice"][niveau].values())
        somme_resume = sum(r["declare_eur"] for r in dn["resume"].values())
        # Les deux séries arrondissent à l'euro, l'une par exercice et l'autre
        # par collectivité : sur 36 000 collectivités, quelques centaines
        # d'euros d'écart d'arrondi sont attendus et ne signalent rien.
        tolerance = max(1000, somme_resume * 1e-8)
        check("dénominateur : séries annuelles = totaux par échelon",
              abs(somme_exercices - somme_resume) <= tolerance,
              f"{somme_exercices:,} €, écart {somme_exercices - somme_resume:,} €")
        # Ce que le site connaît d'une collectivité ne peut pas dépasser ce
        # qu'il connaît en tout : un rapprochement qui gonfle serait un
        # double comptage.
        connu_total = sum(r["site_vote_eur"] for r in dn["resume"].values())
        check("dénominateur : connu du site ≤ total voté du site",
              connu_total <= somme_can + 1,
              f"{connu_total:,} € rapprochés sur {somme_can:,.0f} €")

    # Les fiches communales servies au navigateur : le découpage ne doit ni
    # perdre une commune, ni la ranger dans le mauvais département, ni en
    # inventer une que le référentiel ne connaît pas.
    fiches_dir = os.path.join(ROOT, "data", "aggregates", "denominateur-communes")
    if os.path.isdir(fiches_dir) and os.path.exists(denom_json):
        import gzip as _gzip
        servies = {}
        mal_rangees = 0
        for chemin in sorted(glob.glob(os.path.join(fiches_dir, "*.json.gz"))):
            dep_fichier = os.path.basename(chemin).split(".")[0]
            with _gzip.open(chemin, "rt", encoding="utf-8") as f:
                charge = json.load(f)
            for code, fiche in charge["communes"].items():
                servies[code] = fiche
                if ref["communes"].get(code, {}).get("dep_code") != dep_fichier:
                    mal_rangees += 1
        detail = dn["niveaux"]["commune"]
        check("fiches communales : aucune commune perdue au découpage",
              len(servies) == len(detail),
              f"{len(servies):,} servies sur {len(detail):,}")
        check("fiches communales : chacune dans son département", mal_rangees == 0,
              f"{mal_rangees} mal rangées")
        inconnues = [c for c in servies if c not in ref["communes"]]
        check("fiches communales : toutes au référentiel INSEE", not inconnues,
              f"{len(inconnues)} hors référentiel")
        somme_servie = sum(sum(f["d"].values()) for f in servies.values())
        somme_detail = sum(e["declare_eur"] for e in detail.values())
        check("fiches communales : montants = détail canonique",
              abs(somme_servie - somme_detail) <= 1,
              f"{somme_servie:,} €")

    am_json = os.path.join(ROOT, "data", "canonical", "angle-mort.json")
    if os.path.exists(am_json):
        am = json.load(open(am_json, encoding="utf-8"))
        check("angle mort : reconnus + non reconnus = organismes",
              am["reconnus"] + am["non_reconnus"] == am["organismes"],
              f"{am['organismes']:,} organismes")
        check("angle mort : un organisme dépose au moins une fois",
              am["organismes"] <= am["depots"],
              f"{am['depots']:,} dépôts")
        check("angle mort : les reconnus le sont par un identifiant du site",
              am["reconnus_par_siren"] <= am["index_du_site"]["siren"]
              and am["reconnus_par_rna_seul"] <= am["index_du_site"]["rna"])
        somme_types = sum(v["organismes"] for v in am["par_type"].values())
        check("angle mort : ventilation par nature complète",
              somme_types == am["organismes"], f"{somme_types:,}")
        # Le classement par cause doit couvrir TOUS les non reconnus : une
        # cause oubliée ferait disparaître des organismes de la page sans que
        # rien ne le signale.
        somme_causes = sum(c["organismes"] for c in am.get("causes", []))
        check("angle mort : chaque non reconnu a une cause et une seule",
              somme_causes == am["non_reconnus"],
              f"{somme_causes:,} classés sur {am['non_reconnus']:,}")

    tc_json = os.path.join(ROOT, "data", "canonical", "totaux-controle.json")
    if os.path.exists(tc_json):
        tc = json.load(open(tc_json, encoding="utf-8"))
        verse = tc["series"].get("T_7301.D751", {}).get("valeurs_md_eur", {})
        recu = tc["series"].get("T_7501.D751", {}).get("valeurs_md_eur", {})
        communs = sorted(set(verse) & set(recu))
        # Invariant des comptes nationaux : ce que les administrations versent
        # aux ISBLSM est une PART de ce que les ISBLSM reçoivent, le reste
        # venant des ménages et des entreprises. Si l'ordre s'inversait, c'est
        # que la lecture aurait confondu les sections « Emplois » et
        # « Ressources » du tableau.
        inversions = [a for a in communs if verse[a] > recu[a] + 1e-9]
        check("totaux de contrôle : versé par les APU ≤ reçu par les ISBLSM",
              not inversions and len(communs) > 30,
              f"{len(communs)} exercices comparés"
              + (f", inversions : {inversions[:5]}" if inversions else ""))

    # 12. L'application installable (phase 16) --------------------------------
    # Rien ici ne touche aux données : ce sont les quatre pièces qui font qu'un
    # visiteur peut poser le site sur son écran d'accueil, et dont l'absence ne
    # produit AUCUNE erreur visible — le navigateur se contente de ne pas
    # proposer l'installation.
    import re

    manifeste_chemin = os.path.join(ROOT, "manifest.webmanifest")
    if not os.path.exists(manifeste_chemin):
        check("manifeste : présent", False, "manifest.webmanifest absent")
    else:
        man = json.load(open(manifeste_chemin, encoding="utf-8"))
        requis = ["name", "start_url", "scope", "display", "icons",
                  "background_color", "theme_color"]
        manquants = [c for c in requis if not man.get(c)]
        check("manifeste : champs requis", not manquants,
              f"manquants : {manquants}" if manquants else f"{len(requis)} champs")

        # Le site est publié sous un sous-chemin (`/dons-aux-associations/` sur
        # GitHub Pages) : une adresse absolue pointerait à la racine du domaine.
        absolus = [c for c in ("start_url", "scope") if str(man.get(c, "")).startswith("/")]
        check("manifeste : adresses relatives", not absolus,
              f"absolues : {absolus}" if absolus else "start_url et scope relatifs")

        def taille_png(chemin):
            """Largeur et hauteur lues dans l'en-tête IHDR, sans dépendance."""
            with open(chemin, "rb") as fh:
                tete = fh.read(24)
            if tete[:8] != b"\x89PNG\r\n\x1a\n":
                return None
            return (int.from_bytes(tete[16:20], "big"), int.from_bytes(tete[20:24], "big"))

        soucis, dims = [], set()
        for ico in man.get("icons", []):
            chemin = os.path.join(ROOT, ico["src"])
            if not os.path.exists(chemin):
                soucis.append(f"{ico['src']} absente")
                continue
            mesure = taille_png(chemin)
            if mesure is None:
                soucis.append(f"{ico['src']} n'est pas un PNG")
            elif f"{mesure[0]}x{mesure[1]}" != ico.get("sizes"):
                soucis.append(f"{ico['src']} mesure {mesure[0]}x{mesure[1]}, annoncée {ico.get('sizes')}")
            else:
                dims.add(mesure[0])
        check("manifeste : icônes présentes et à la taille annoncée",
              not soucis and {192, 512} <= dims,
              "; ".join(soucis) if soucis else f"{len(man.get('icons', []))} icônes, tailles {sorted(dims)}")

        # Sans icône `maskable`, Android rogne l'icône dans son propre gabarit
        # et coupe la marque.
        check("manifeste : une icône masquable",
              any("maskable" in i.get("purpose", "") for i in man.get("icons", [])))

    # `addAll` est atomique : un seul chemin faux et l'installation du service
    # worker échoue en entier. Le site continue de s'afficher, mais il n'a plus
    # ni hors-ligne ni installation — une panne parfaitement silencieuse.
    sw = open(os.path.join(ROOT, "sw.js"), encoding="utf-8").read()
    bloc = re.search(r"const PRECACHE = \[(.*?)\];", sw, re.S)
    if not bloc:
        check("service worker : liste de préchargement lisible", False)
    else:
        chemins = re.findall(r'"([^"]+)"', bloc.group(1))
        absents = [c for c in chemins
                   if c != "./" and not os.path.exists(os.path.join(ROOT, c[2:]))]
        check("service worker : tous les fichiers préchargés existent",
              not absents and len(chemins) > 10,
              f"absents : {absents}" if absents else f"{len(chemins)} fichiers")

    # `methode.html` étant ENGENDRÉE, elle perdrait le lien à la prochaine
    # publication si `build_methode.py` ne le portait pas lui aussi.
    pages = sorted(glob.glob(os.path.join(ROOT, "*.html")))
    sans_lien = [os.path.basename(p) for p in pages
                 if 'rel="manifest"' not in open(p, encoding="utf-8").read()]
    check("pages : toutes déclarent le manifeste",
          not sans_lien and len(pages) >= 5,
          f"sans lien : {sans_lien}" if sans_lien else f"{len(pages)} pages")

    print()
    failed = [r for r in results if not r[1]]
    print(f"  {len(results) - len(failed)}/{len(results)} contrôles passés")

    # Le compte des contrôles est ÉCRIT, pas laissé à qui voudra le citer.
    # `methode.html` l'annonçait « 50 » en dur, et se trompait dès que la liste
    # bougeait ; le compter dans le source ne marche pas non plus, plusieurs
    # contrôles étant émis dans des boucles (un par échelon, un par découpe).
    # Seule l'exécution sait combien il y en a.
    with open(os.path.join(ROOT, "data", "canonical", "verify-report.json"),
              "w", encoding="utf-8") as f:
        json.dump({
            "genere_le": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "controles": len(results),
            "passes": len(results) - len(failed),
            "echecs": [{"nom": n, "detail": d} for n, _, d in failed],
        }, f, ensure_ascii=False, indent=1)

    if failed:
        print("\n  ÉCHECS :")
        for name, _, detail in failed:
            print(f"    · {name} — {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
