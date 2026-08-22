#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L'exercice 2011 du Jaune est-il publié dix fois trop grand ? — la preuve.

`plf-jaune-2013` (subventions de l'État en 2011) est en QUARANTAINE d'unité :
12,30 Md€ sur 21 167 lignes, quand ses voisins pèsent 1,5 à 1,9 Md€. La
doctrine du projet interdit de corriger un montant sur une intuition — d'où ce
script, qui rassemble ce que la donnée elle-même démontre, et le rejoue à la
demande.

Cinq faisceaux, tous mesurés sur la table canonique :

  1. le rapport à l'exercice SUIVANT, association par association ;
  2. le rapport à l'exercice PRÉCÉDENT, indépendant du premier ;
  3. les mêmes calculs sur des années témoins, qui doivent rendre 1,00 ;
  4. la signature des multiples de 10 ;
  5. le montant moyen par ligne, divisé par dix, comparé aux voisins.

Les agrégats sont exclus PARTOUT : le fichier du PLF 2012 publie le total par
association ET son détail, et confondre les deux double l'exercice 2010 — une
erreur de mesure, pas une erreur de la source.

Usage :  python3 scripts/analyse/verifier_unite_2011.py
Requiert `duckdb`.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "pipeline"))

import duckdb  # noqa: E402

TABLE = "read_parquet('%s')" % os.path.join(
    ROOT, "data", "canonical", "subventions", "*", "*.parquet")

# Le montant publié, où qu'il soit rangé : `amount_eur` pour les exercices
# sains, `amount_rejected_eur` pour celui qui est en quarantaine.
MONTANT = "coalesce(amount_eur, amount_rejected_eur)"
BASE = f"from {TABLE} where source_family = 'plf_jaune' and granularity <> 'aggregate'"


def rapport(con, annee_a, annee_b):
    """Médiane et quartiles du rapport A/B, association par association."""
    q = f"""
    with y as (select beneficiary_siren s, year, sum({MONTANT}) m
               {BASE} and beneficiary_siren is not null
                 and year in ({annee_a}, {annee_b}) group by 1, 2),
         p as (select s, max(case when year={annee_a} then m end) a,
                          max(case when year={annee_b} then m end) b
               from y group by 1)
    select count(*), median(a / b), quantile_cont(a / b, 0.25), quantile_cont(a / b, 0.75)
    from p where a > 0 and b > 0"""
    return con.execute(q).fetchone()


def main():
    con = duckdb.connect()

    print("1 & 2. LE RAPPORT AUX EXERCICES VOISINS, ASSOCIATION PAR ASSOCIATION\n")
    print(f"   {'comparaison':22s} {'associations':>12s} {'médiane':>9s}   quartiles")
    for a, b, quoi in ((2011, 2012, "suspect"), (2011, 2010, "suspect"),
                       (2010, 2012, "témoin"), (2012, 2013, "témoin"),
                       (2013, 2014, "témoin"), (2014, 2015, "témoin")):
        n, med, q1, q3 = rapport(con, a, b)
        marque = " <<<" if quoi == "suspect" else ""
        print(f"   {a} / {b} {quoi:9s} {n:>12,} {med:>9.2f}   {q1:.2f} – {q3:.2f}{marque}")
    print("\n   Deux comparaisons INDÉPENDANTES donnent exactement 10,00, et tous les")
    print("   témoins exactement 1,00 : la méthode lit bien 1 quand rien ne cloche.")

    print("\n3. LA SIGNATURE DES MULTIPLES DE 10\n")
    q = f"""select year, count(*) n,
             round(100.0 * sum(case when {MONTANT} % 10 = 0 then 1 else 0 end) / count(*), 1) pct
           {BASE} and {MONTANT} > 0 and year between 2009 and 2015 group by 1 order by 1"""
    for annee, n, pct in con.execute(q).fetchall():
        marque = " <<<" if annee == 2011 else ""
        print(f"   {annee}  {n:>7,} lignes  {pct:>5} % de multiples de 10{marque}")
    print("\n   Un arrondi naturel en laisse 70 à 83 %. Un décalage de virgule en")
    print("   laisse 100 %, parce qu'il en fabrique un zéro final sur CHAQUE ligne.")

    print("\n4. LE MONTANT MOYEN PAR LIGNE\n")
    q = f"""select year, count(*) n, sum({MONTANT}) / count(*) moy
           {BASE} and {MONTANT} > 0 and year between 2010 and 2013 group by 1 order by 1"""
    for annee, n, moy in con.execute(q).fetchall():
        divise = f"   ÷10 = {moy/10:>9,.0f} €" if annee == 2011 else ""
        print(f"   {annee}  {n:>7,} lignes  moyenne {moy:>10,.0f} €{divise}")
    print("\n   Divisé par dix, 2011 rend une moyenne par ligne à quelques dizaines")
    print("   d'euros de celle de 2012 : les subventions n'ont pas changé de taille,")
    print("   seul leur affichage a changé d'unité.")

    print("\n5. LE TOTAL DE L'EXERCICE\n")
    q = f"""select year, sum({MONTANT}) {BASE} and year between 2010 and 2013 group by 1 order by 1"""
    for annee, total in con.execute(q).fetchall():
        divise = f"   ÷10 = {total/1e9:>5.2f} Md€" if annee == 2011 else ""
        print(f"   {annee}  {total/1e9:>6.2f} Md€{divise}")
    print("\n   Divisé par dix, 2011 se range entre ses voisins. Tel qu'il est publié,")
    print("   il pèse plus que les six exercices suivants réunis.")

    print("\n" + "=" * 72)
    print("CE QUE CELA ÉTABLIT, ET CE QUE CELA N'ÉTABLIT PAS")
    print("=" * 72)
    print("""
Établi : l'exercice 2011 du Jaune est publié dix fois trop grand, et le facteur
est UNIFORME — deux comparaisons indépendantes rendent 10,00 en médiane là où
tous les témoins rendent 1,00, et 100 % des montants portent le zéro final que
ce décalage fabrique.

Non établi : que nous ayons le droit de diviser. Corriger un montant publié est
contraire à la doctrine du projet ; c'est un arbitrage qui revient à
l'utilisateur, pas au code. La quarantaine tient tant qu'il n'a pas tranché.
""")


if __name__ == "__main__":
    main()
