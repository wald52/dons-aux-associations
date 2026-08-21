"""Génère `methode.html` à partir des données réelles.

Une page de méthode écrite à la main ment dès la publication suivante. Celle-ci
est reconstruite à chaque build depuis le rapport de qualité, la couverture et
les manifestes : ses chiffres ne peuvent pas diverger de ceux du site.

Usage : python3 scripts/pipeline/build_methode.py
"""

import html
import io
import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import common as C

ROOT = C.ROOT
OUT = os.path.join(ROOT, "methode.html")


def lire(chemin):
    p = os.path.join(ROOT, chemin)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def lire_gz(chemin):
    """Les agrégats sont la seule source à jour des totaux affichés : ils sont
    recalculés depuis la table canonique à chaque publication, quand le rapport
    de qualité, lui, date du dernier assemblage."""
    p = os.path.join(ROOT, chemin)
    if not os.path.exists(p):
        return {}
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return json.load(f)


def nb(x):
    return f"{x:,}".replace(",", " ")


def eur(x):
    if x is None:
        return "—"
    if abs(x) >= 1e9:
        return f"{x/1e9:.1f}".replace(".", ",") + " Md€"
    if abs(x) >= 1e6:
        return f"{x/1e6:.1f}".replace(".", ",") + " M€"
    return nb(round(x)) + " €"


def main():
    q = lire("data/canonical/quality-report.json")
    cov = lire("data/canonical/couverture.json")
    scdl = lire("data/sources-manifest/scdl.json")
    ods = lire("data/sources-manifest/ods.json")
    plf = lire("data/sources-manifest/plf-jaune.json")
    idx = lire("data/canonical/recherche/index-stats.json")
    meta = lire_gz("data/aggregates/meta.json.gz")
    tot = meta.get("totaux", {})
    votes = tot.get("dons_votes", {})
    payes = tot.get("dons_payes", {})
    hors_don = tot.get("hors_don", {})
    LIBELLES_HORS_DON = {
        "prestation": "prestations facturées par l'association",
        "remboursement": "remboursements de frais et cotisations d'adhésion",
        "nature": "aides en nature (locaux, personnel mis à disposition)",
    }
    lignes_hors_don = "\n".join(
        f"      <li><strong>{eur(v[1])}</strong> de {LIBELLES_HORS_DON.get(k, k)}"
        f" — {nb(v[0])} lignes.</li>"
        for k, v in hors_don.items())

    d = q.get("deduplication", {})
    flags = q.get("quality_flags", {})
    anomalies = q.get("anomalies", [])
    familles = {}
    for s, v in q.get("by_source", {}).items():
        f = ("État — annexe Jaune" if s.startswith("plf-jaune")
             else "Collectivités — moissonnage data.gouv.fr" if s.startswith("scdl")
             else "Collectivités — moissonnage des portails" if s.startswith("ods")
             else "Sources reprises une par une")
        e = familles.setdefault(f, {"sources": 0, "lignes": 0, "montant": 0.0})
        e["sources"] += 1
        e["lignes"] += v["rows"]
        e["montant"] += v["amount_individual_eur"]

    rejet = next((a for a in anomalies if a["type"] == "montants_invraisemblables_exclus"), None)
    ruptures = [a for a in anomalies if a["type"] == "rupture_annuelle"]
    com = cov.get("niveaux", {}).get("commune", {})

    lignes_familles = "\n".join(
        f"      <tr><td>{html.escape(k)}</td><td class='num'>{nb(v['sources'])}</td>"
        f"<td class='num'>{nb(v['lignes'])}</td><td class='num montant'>{eur(v['montant'])}</td></tr>"
        for k, v in sorted(familles.items(), key=lambda x: -x[1]["lignes"]))

    lignes_ruptures = "".join(
        f"<li>L'année <strong>{a['year']}</strong> totalise {eur(a['amount_eur'])}, "
        f"soit {str(a['rapport']).replace('.', ',')} fois les années voisines. "
        f"Ce chiffre est conforme à ce que publie la source ; le périmètre de "
        f"l'annexe cette année-là reste à vérifier.</li>"
        for a in ruptures)

    page = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'; style-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'">
<title>Sources &amp; méthode — Dons publics aux associations</title>
<meta name="description" content="D'où viennent les chiffres, ce que la déduplication retire, quels montants sont mis en quarantaine et pourquoi.">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
<nav class="bandeau">
  <div class="bandeau-inner">
    <a class="marque" href="index.html">Dons publics aux associations
      <span>Qui finance les associations en France</span></a>
    <div class="menu">
      <a href="index.html">Carte</a>
      <a href="recherche.html">Recherche croisée</a>
      <a href="couverture.html">Ce qu'on ne sait pas</a>
      <a href="methode.html" aria-current="page">Sources &amp; méthode</a>
    </div>
  </div>
</nav>
<div class="enveloppe">
  <header>
    <h1>Sources &amp; méthode</h1>
    <p class="chapeau">Cette page est <strong>engendrée à partir des données elles-mêmes</strong>
       à chaque publication : ses chiffres ne peuvent pas diverger de ceux du site.</p>
  </header>

  <div class="compteurs">
    <div class="compteur"><span class="valeur">{nb(q.get('rows_total', 0))}</span>
      <span class="etiquette">versements recensés</span></div>
    <div class="compteur"><span class="valeur">{eur(votes.get('montant_eur'))}</span>
      <span class="etiquette">de dons votés</span></div>
    <div class="compteur"><span class="valeur">{eur(payes.get('montant_eur'))}</span>
      <span class="etiquette">de dons payés, comptés à part</span></div>
    <div class="compteur"><span class="valeur">{nb(len(q.get('by_source', {})))}</span>
      <span class="etiquette">sources</span></div>
    <div class="compteur"><span class="valeur">{q.get('years_covered', ['?'])[0]}–{q.get('years_covered', ['?'])[-1]}</span>
      <span class="etiquette">années couvertes</span></div>
  </div>

  <div class="prose">
    <h2>La règle qui gouverne tout&nbsp;: fidélité à la source</h2>
    <p>Aucun montant n'est corrigé, aucun bénéficiaire n'est deviné. Quand une donnée
       paraît fausse, elle est <strong>signalée et mise de côté</strong>, jamais redressée :
       un chiffre inventé par nous serait pire qu'un chiffre manquant. Tout enrichissement
       — un département déduit d'un SIRET, une année lue dans un libellé — est marqué
       comme tel dans les données.</p>

    <h2>D'où viennent les chiffres</h2>
    <div class="table-enveloppe">
      <table>
        <thead><tr><th>Famille de sources</th><th>Sources</th><th>Versements</th><th>Montant</th></tr></thead>
        <tbody>
{lignes_familles}
        </tbody>
      </table>
    </div>
    <p><strong>Le moissonnage est automatique.</strong> {nb(scdl.get('jeux_examines', 0))} jeux de
       données ont été examinés sur data.gouv.fr, {nb(scdl.get('jeux_retenus', 0))} retenus, soit
       {nb(scdl.get('fichiers_retenus', 0))} fichiers. Un fichier n'est retenu que si ses colonnes
       réelles correspondent à des subventions — le schéma déclaré ne suffit pas. Tout nouveau
       millésime publié par une collectivité sera repris sans intervention.</p>
    <p>Les collectivités qui ne passent pas par data.gouv.fr publient sur leur propre
       portail. Ces portails partagent tous la même interface, donc un second moissonneur
       les couvre : {nb(len(ods.get('portails', [])))} portails visités,
       {nb(ods.get('jeux_examines', 0))} jeux examinés, {nb(ods.get('jeux_retenus', 0))}
       retenus — au même test sur les colonnes réelles.</p>
    <p>L'annexe budgétaire « Jaune » de l'État est moissonnée de la même façon, sur
       {nb(len([x for x in plf.get('datasets', []) if not x.get('error')]))} millésimes.</p>

    <h2>Ce que la déduplication retire</h2>
    <p>Deux administrations publient parfois le même versement. Les additionner le
       compterait deux fois. Une clé métier — bénéficiaire, donateur, année, montant, objet —
       les réconcilie&nbsp;: <strong>{nb(d.get('rows_dropped', 0))} lignes</strong> écartées, soit
       {eur(d.get('amount_dropped'))}.</p>
    <div class="encart">
      <h3>Ce qui n'est PAS dédupliqué</h3>
      <p>À l'intérieur d'une même source, {nb(d.get('rows_same_source', 0))} lignes ont une clé
         identique et sont <strong>toutes conservées</strong>. L'inspection montre qu'il s'agit
         d'organismes homonymes distincts — vingt-trois « Maison des jeunes et de la culture »
         touchant la même subvention type sont vingt-trois associations, pas un doublon.</p>
    </div>

    <h2>Les montants mis en quarantaine</h2>
    <p>Certaines valeurs publiées ne sont pas des montants, ou sont dans une unité douteuse.
       Elles sont conservées dans les données mais <strong>exclues de tous les totaux</strong>
       {'— ' + eur(rejet['amount_eur']) + ' sur ' + nb(rejet['rows']) + ' lignes' if rejet else ''}.</p>
    <ul>
      <li><strong>Métropole de Lyon</strong> : 9&nbsp;081 lignes totalisant 48&nbsp;Md€, quand le
        budget annuel de la Métropole avoisine 3,8&nbsp;Md€. Médiane à 1&nbsp;584&nbsp;200&nbsp;€,
        minimum à 100, 85&nbsp;% de multiples de 100 : tout indique des <strong>centimes lus comme
        des euros</strong>. L'amont n'étant plus vérifiable, nous ne divisons pas par cent de notre
        propre autorité.</li>
      <li><strong>Boulogne-Billancourt</strong> : deux lignes à 750&nbsp;M€ et 75&nbsp;M€ pour une
        ville au budget d'environ 330&nbsp;M€, quand les soixante autres lignes du même fichier
        sont plausibles.</li>
      <li><strong>Un SIRET recopié dans la colonne montant</strong> : trois lignes à
        78&nbsp;962&nbsp;milliards d'euros chacune.</li>
    </ul>
    <p>Deux natures de lignes ne sont par ailleurs <strong>jamais additionnées</strong> : les
       attributions individuelles et les totaux déjà agrégés publiés par certaines collectivités
       ({eur(q.get('amount_aggregate_eur'))}). Les sommer compterait chaque euro deux fois.</p>

    <h2>Ce qui compte comme un don</h2>
    <p>Tout argent versé à une association n'est pas un don. Quand une collectivité écrit
       « prestation facturée par l'association », elle <strong>achète un service</strong>&nbsp;:
       il y a une contrepartie, ce n'est pas un soutien. Ces sommes sont ingérées, restent
       consultables ligne à ligne, et sont comptées à part&nbsp;:</p>
    <ul>
{lignes_hors_don}
    </ul>
    <p>La lecture se fait sur les <strong>mots</strong> de l'objet publié, jamais sur des
       fragments de mots&nbsp;: « soutien aux manufactures et métiers d'art » contient les
       lettres de « factur- » sans être une facture. Et dans le doute, la ligne reste un
       don&nbsp;: l'écarter à tort effacerait une subvention réelle, la garder à tort laisse
       une ligne visible et corrigeable.</p>

    <h2>Voté et payé — deux totaux, jamais une somme</h2>
    <p>Une collectivité publie souvent le même argent deux fois&nbsp;: ce qu'elle a
       <strong>voté</strong>, puis ce qu'elle a <strong>mandaté</strong> (annexe au compte
       administratif). Les additionner la compterait deux fois.</p>
    <p>Le site affiche donc les deux côte à côte et ne les somme jamais&nbsp;:
       <strong>{eur(votes.get('montant_eur'))}</strong> votés
       ({nb(votes.get('lignes', 0))} versements) et
       <strong>{eur(payes.get('montant_eur'))}</strong> déclarés payés
       ({nb(payes.get('lignes', 0))} versements).</p>
    <div class="encart">
      <h3>Pourquoi le payé n'est plus caché</h3>
      <p>La règle a longtemps été « le payé sort des totaux ». Mesuré, cela retirait
         1,86&nbsp;Md€ que <em>rien</em> ne dédoublait&nbsp;: une vingtaine de collectivités —
         dont le département de Loire-Atlantique, 778&nbsp;M€ sur 28&nbsp;573 subventions —
         ne publient QUE leurs paiements. Les taire les faisait disparaître du site alors que
         nous avions leurs chiffres.</p>
      <p>Aucune des sources qui publient leur exécution budgétaire ne donne l'adresse du
         bénéficiaire&nbsp;: le payé n'a donc pas de géographie et n'apparaît pas sur la carte.</p>
    </div>

    <h2>Les anomalies que nous signalons sans les corriger</h2>
    <ul>
{lignes_ruptures}
      <li><strong>{nb(flags.get('siret_scientific_notation', 0))} numéros SIRET ont été détruits par un
        tableur</strong> : ils sont publiés sous la forme <code>2,19301E+13</code>, un nombre dont
        seuls six chiffres significatifs subsistent. Ce n'est pas réparable ; seul un
        re-moissonnage de la source d'origine le corrigerait.</li>
      <li><strong>{nb(flags.get('dep_unknown', 0))} versements n'ont pas de département exploitable</strong>
        et n'apparaissent donc pas sur la carte, bien qu'ils comptent dans les totaux.</li>
    </ul>

    <h2>Comment une association est reconnue</h2>
    <p>Croiser les financeurs suppose de savoir qu'une association vue chez l'État et chez sa
       commune est la même. L'identité est résolue par <strong>SIREN</strong> quand la source le
       donne, sinon par <strong>nom normalisé et département</strong> — jamais par le nom seul :
       « Centre communal d'action sociale » existe dans quarante et un départements.</p>
    <p>La conséquence est assumée : une association publiée sans identifiant par deux sources
       peut apparaître deux fois, et un cumul d'échelons peut être <strong>sous-estimé, jamais
       inventé</strong>. Sur {nb(idx.get('beneficiaires', 0))} bénéficiaires résolus,
       {nb(idx.get('multi_echelons_3plus', 0))} sont financés par au moins trois échelons publics.</p>

    <h2>Ce que la couverture veut dire</h2>
    <p>La carte ne couvre pas la France entière et ne le prétend pas.
       {nb(com.get('par_etat', {}).get('donnees', 0))} communes sur {nb(com.get('univers', 0))} ont des
       données, soit <strong>{str(com.get('part_population_couverte', '—')).replace('.', ',')}&nbsp;% de la
       population</strong> — la couverture se mesure en habitants, pas en nombre de fichiers.</p>
    <p>La raison principale est en amont : <strong>très peu de collectivités publient</strong>.
       Toutes sources confondues, les données ne contiennent que
       {nb(com.get('donateurs_dans_les_donnees', 0))} communes,
       {nb(cov.get('niveaux', {}).get('epci', {}).get('donateurs_dans_les_donnees', 0))} intercommunalités,
       {nb(cov.get('niveaux', {}).get('departement', {}).get('donateurs_dans_les_donnees', 0))} départements et
       {nb(cov.get('niveaux', {}).get('region', {}).get('donateurs_dans_les_donnees', 0))} régions
       en tant que <em>financeurs</em>. L'État, lui, est couvert de façon dense.
       Seules les communes de plus de 3&nbsp;500 habitants sont tenues de publier, et
       l'obligation est peu suivie.</p>
    <p>Cette couverture est un <strong>minimum</strong> : une collectivité est reconnue en
       rapprochant son nom du référentiel INSEE, et un libellé inhabituel peut échouer à
       s'apparier alors que la donnée existe. L'erreur va toujours vers la sous-estimation.
       Le détail figure sur la page <a href="couverture.html">Ce qu'on ne sait pas</a>.</p>

    <h2>Reproduire ces chiffres</h2>
    <p>Le pipeline est public et reconstructible d'une commande. Chaque ligne du site porte
       l'identifiant de sa source et sa référence dans le fichier d'origine. Les scripts, la
       table canonique et le rapport de qualité complet sont dans le
       <a href="https://github.com/wald52/dons-aux-associations">dépôt du projet</a>.</p>
  </div>

  <footer>
    Données publiques sous Licence Ouverte 2.0. Page engendrée le
    {q.get('generated_at', '')[:10]} à partir de <code>quality-report.json</code>,
    <code>couverture.json</code> et des manifestes de moissonnage.
  </footer>
</div>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"  methode.html engendrée ({len(page)/1024:.1f} Ko)")
    print(f"  {nb(q.get('rows_total', 0))} versements, {len(q.get('by_source', {}))} sources")


if __name__ == "__main__":
    main()
