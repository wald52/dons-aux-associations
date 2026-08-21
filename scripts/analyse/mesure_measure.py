#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ampleur du défaut de reconnaissance « voté / versé » — mesure, pas correctif.

`RESTE-A-FAIRE.md` signalait que `fold` ne ramène pas « _ » à l'espace, si bien
qu'un fichier nommé `subventions_fonctionnement_versees_2019.csv` n'est pas
reconnu comme une exécution budgétaire. Le corriger déplacerait des montants
hors des totaux : d'où cette mesure, à faire AVANT de toucher au code.

Elle rejoue la détection sur les VRAIS libellés lus par chaque normaliseur —
titre du jeu et titre de la ressource pour `scdl`, titre du jeu pour `ods`, nom
du fichier et libellé enregistré pour `legacy` — selon trois variantes :

  A. la règle actuelle ;
  B. les séparateurs (« _ », « - ») ramenés à l'espace avant appariement ;
  C. la détection par MOTS (« versées », « mandatées », « paiements »…) plutôt
     que par suites contiguës, qui seule attrape le cas de Grenoble.

Et surtout, pour chaque ligne qui basculerait : la même collectivité a-t-elle
publié le MÊME exercice en « attribué » ailleurs ? Sans cette contrepartie,
classer « versé » ne dédouble rien — cela retire de l'argent réel des totaux.

Usage :  python3 scripts/analyse/mesure_measure.py
Requiert `duckdb` (pip install duckdb) et la table canonique reconstruite.
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "pipeline"))

import common as C  # noqa: E402
import duckdb  # noqa: E402

TABLE = "read_parquet('%s')" % os.path.join(
    ROOT, "data", "canonical", "subventions", "*", "*.parquet")


def separateurs(libelle):
    """Le libellé plié, séparateurs compris — `sub_versees` devient `sub versees`."""
    return re.sub(r"[^a-z0-9]+", " ", C.fold(libelle or "")).strip()


def variante_A(*libelles):
    return C.measure_of(*libelles)


def variante_B(*libelles):
    t = " ".join(separateurs(x) for x in libelles)
    return "verse" if any(m in t for m in C._MOTS_VERSE) else "attribue"


# Les formes fléchies de l'exécution budgétaire, prises comme MOTS : « versées »
# apparaît dans « subventions de fonctionnement versées », qu'aucune suite
# contiguë n'attrape.
_MOTS_EXECUTION = frozenset((
    "versee", "versees", "verses", "versement", "versements",
    "mandate", "mandatee", "mandatees", "mandates", "mandatement",
    "paiement", "paiements", "liquidees", "liquidations",
))


def variante_C(*libelles):
    t = " ".join(separateurs(x) for x in libelles)
    if "compte administratif" in t:
        return "verse"
    return "verse" if set(t.split()) & _MOTS_EXECUTION else "attribue"


def libelles_par_source(con):
    """Les libellés que chaque normaliseur passe réellement à `measure_of`."""
    libelles = {}
    scdl = os.path.join(ROOT, "data", "sources-manifest", "scdl.json")
    for ds in json.load(open(scdl, encoding="utf-8"))["datasets"]:
        for f in ds.get("fichiers", []):
            sid = "scdl-" + os.path.basename(f["fichier"])[:-4]
            libelles[sid] = (ds.get("titre"), f.get("titre"))
    ods = os.path.join(ROOT, "data", "sources-manifest", "ods.json")
    for ds in json.load(open(ods, encoding="utf-8"))["datasets"]:
        if ds.get("fichier"):
            sid = "ods-" + os.path.basename(ds["fichier"])[:-4]
            libelles[sid] = (ds.get("titre"), os.path.basename(ds["fichier"]))
    # Les sources héritées lisent `data/sources/*.js`, hors du dépôt : leur
    # libellé se relit dans `source_label`, leur nom dans `source_id`.
    for sid, label in con.execute(
            "select distinct source_id, source_label from %s "
            "where source_family='legacy'" % TABLE).fetchall():
        libelles[sid] = (sid, label)
    return libelles


def cellules(con):
    """(source, identité du donateur, exercice) -> lignes et € comptés aujourd'hui."""
    rows = con.execute("""
        select source_id, donor_name_norm, year, count(*), sum(coalesce(amount_eur,0))
        from %s where %s group by 1,2,3""" % (TABLE, C.SQL_COMPTE_DANS_LES_TOTAUX)).fetchall()
    cel = collections.defaultdict(lambda: [0, 0.0])
    couvert = collections.defaultdict(set)          # (identité, exercice) -> sources
    for sid, dnorm, annee, n, montant in rows:
        ident = C.identite_donateur(dnorm, annee)
        c = cel[(sid, ident, annee)]
        c[0] += n
        c[1] += montant
        couvert[(ident, annee)].add(sid)
    return cel, couvert


def rapport_variante(nom, fn, libelles, cel, couvert):
    bascules = {sid for sid, libs in libelles.items()
                if C.measure_of(*libs) == "attribue" and fn(*libs) == "verse"}
    double_n = double_m = perte_n = perte_m = 0
    pertes = collections.defaultdict(lambda: [0, 0.0])
    for (sid, ident, annee), (n, montant) in cel.items():
        if sid not in bascules:
            continue
        # Une jumelle ne vaut que si elle couvre le même exercice ET qu'elle ne
        # bascule pas elle aussi.
        if couvert[(ident, annee)] - bascules:
            double_n += n
            double_m += montant
        else:
            perte_n += n
            perte_m += montant
            p = pertes[(ident, annee)]
            p[0] += n
            p[1] += montant

    print("\n=== Variante %s ===" % nom)
    print("  %d sources basculeraient « attribué » → « versé »." % len(bascules))
    print("  Vrai double compte (même donateur, même exercice, publié aussi en "
          "« attribué ») :\n      %s lignes, %s €" % (f"{double_n:,}", f"{double_m:,.0f}"))
    print("  SANS contrepartie — sortiraient des totaux à perte :\n"
          "      %s lignes, %s €" % (f"{perte_n:,}", f"{perte_m:,.0f}"))
    for (ident, annee), (n, montant) in sorted(pertes.items(), key=lambda x: -x[1][1])[:12]:
        print("      %-36s %s %7s lignes %16s €"
              % ((ident or "")[:36], annee, f"{n:,}", f"{montant:,.0f}"))
    return bascules


def rapport_regle_actuelle(con):
    """Ce que la règle « versé ⇒ hors totaux » retire déjà, et à quel titre."""
    rows = con.execute("""
        select donor_name_norm, year, measure, count(*), sum(coalesce(amount_eur,0))
        from %s
        where granularity is distinct from 'aggregate'
          and not (beneficiary_kind_provenance='declared'
                   and beneficiary_kind is not null
                   and beneficiary_kind <> 'association')
        group by 1,2,3""" % TABLE).fetchall()
    attribue = collections.defaultdict(lambda: [0, 0.0])
    verse = collections.defaultdict(lambda: [0, 0.0])
    for dnorm, annee, mesure, n, montant in rows:
        cle = (C.identite_donateur(dnorm, annee), annee)
        d = verse if mesure == "verse" else attribue
        d[cle][0] += n
        d[cle][1] += montant

    double_n = double_m = seul_n = seul_m = 0
    seuls = collections.defaultdict(lambda: [0, 0.0])
    for cle, (n, montant) in verse.items():
        if cle in attribue:
            double_n += n
            double_m += montant
        else:
            seul_n += n
            seul_m += montant
            s = seuls[cle[0]]
            s[0] += n
            s[1] += montant

    print("\n=== La règle actuelle, sur les lignes déjà classées « versé » ===")
    print("  Total exclu par la seule règle « versé » : %s lignes, %s €"
          % (f"{double_n + seul_n:,}", f"{double_m + seul_m:,.0f}"))
    print("  · avec un « attribué » du même donateur ET du même exercice "
          "(vrai double compte) :\n      %s lignes, %s €"
          % (f"{double_n:,}", f"{double_m:,.0f}"))
    print("  · sans aucune contrepartie — retirés sans rien dédoubler :\n"
          "      %s lignes, %s €" % (f"{seul_n:,}", f"{seul_m:,.0f}"))
    for ident, (n, montant) in sorted(seuls.items(), key=lambda x: -x[1][1])[:12]:
        print("      %-44s %8s lignes %18s €"
              % ((ident or "")[:44], f"{n:,}", f"{montant:,.0f}"))


def main():
    con = duckdb.connect()
    total = con.execute("select count(*), sum(coalesce(amount_eur,0)) from %s where %s"
                        % (TABLE, C.SQL_COMPTE_DANS_LES_TOTAUX)).fetchone()
    print("Totaux du site : %s lignes, %s €" % (f"{total[0]:,}", f"{total[1]:,.0f}"))

    libelles = libelles_par_source(con)
    cel, couvert = cellules(con)
    rapport_variante("B — séparateurs ramenés à l'espace", variante_B, libelles, cel, couvert)
    rapport_variante("C — détection par mots", variante_C, libelles, cel, couvert)
    rapport_regle_actuelle(con)


if __name__ == "__main__":
    main()
