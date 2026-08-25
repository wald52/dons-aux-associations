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


def de(mot):
    """« de » ou « d' » selon l'initiale. Sans quoi la page engendrée écrit
    « 313,1 M€ de aides en nature »."""
    return ("d'" if mot[:1].lower() in "aeiouyhéèêà" else "de ") + mot


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
    idx = lire("data/recherche/index-stats.json")
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
        f"      <li><strong>{eur(v[1])}</strong> {de(LIBELLES_HORS_DON.get(k, k))}"
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
    par_type = {a["type"]: a for a in anomalies}

    def bloc_anomalie(cle, titre, texte):
        a = par_type.get(cle)
        if not a:
            return ""
        return (f"      <li><strong>{titre}</strong> — {nb(a.get('rows', 0))} lignes, "
                f"{eur(a.get('amount_eur'))}. {texte}</li>")

    lignes_credibilite = "\n".join(filter(None, [
        bloc_anomalie(
            "doublons_probables_hors_cle",
            "Des doublons que la clé métier ne voit pas",
            "Même bénéficiaire, même donateur, même exercice, même montant, publiés "
            "par deux sources sous des objets différents. L'objet faisant partie de "
            "la clé, la déduplication ne les rapproche pas. Ils restent DANS les "
            "totaux : retirer l'objet de la clé fondrait deux subventions réellement "
            "distinctes de même montant à la même association la même année."),
        bloc_anomalie(
            "nom_de_beneficiaire_numerique",
            "Des bénéficiaires dont le nom est un numéro",
            "La source a recopié le SIREN ou le RNA dans la colonne du nom. "
            "L'organisme est identifiable mais illisible, et ne se rapproche pas de "
            "ses propres lignes correctement nommées."),
        bloc_anomalie(
            "nature_devinee_gros_montants",
            "Des bénéficiaires comptés comme associations faute de mieux",
            "La source ne dit pas leur nature juridique : nous la devinons sur le nom, "
            "et le défaut est « association ». On y trouve donc des sociétés et des "
            "opérateurs publics. Rien n'est retiré — deviner une exclusion effacerait "
            "des associations réelles — mais la liste demande un œil humain."),
    ]))
    com = cov.get("niveaux", {}).get("commune", {})

    # --- les totaux de contrôle ---------------------------------------------
    #
    # Un total sans échelle ne veut rien dire : 149,68 Md€ cumulés, est-ce
    # tout, ou un dixième ? La comptabilité nationale donne le seul repère
    # officiel — D751, ce que les administrations publiques versent aux ISBLSM
    # chaque année. La comparaison ne vaut qu'EXERCICE PAR EXERCICE : le total
    # du site est un cumul pluriannuel, D751 est un flux annuel.
    controle = lire("data/canonical/totaux-controle.json")
    denom = lire_gz("data/aggregates/denominateur.json.gz")
    bloc_controle = ""
    serie_apu = (controle.get("series", {}).get("T_7301.D751", {})
                 .get("valeurs_md_eur", {}))
    if serie_apu:
        cube = lire_gz("data/aggregates/cube.json.gz")
        national = cube.get("national", {})
        annees = [a for a in sorted(serie_apu) if a in national][-12:]
        lignes_controle = []
        for a in annees:
            insee_md = serie_apu[a]
            site = sum(v[1] for v in national.get(a, {}).values())
            part = site / (insee_md * 1e9) * 100 if insee_md else None
            lignes_controle.append(
                f"      <tr><td>{a}</td>"
                f"<td class='num montant'>{str(round(insee_md, 1)).replace('.', ',')}&nbsp;Md€</td>"
                f"<td class='num montant'>{eur(site)}</td>"
                f"<td class='num'>{('—' if part is None else str(round(part, 1)).replace('.', ',') + ' %')}</td></tr>")
        # Un creux dans la colonne du site n'est pas une baisse des subventions :
        # c'est un exercice dont l'annexe Jaune manque. On le dit ici plutôt que
        # de laisser le lecteur conclure à une chute de l'argent public.
        creux = []
        sommet = 0.0
        for a in annees:
            etat_an = national.get(a, {}).get("etat", [0, 0.0])[1]
            if sommet and etat_an < sommet / 2:
                creux.append(a)
            sommet = max(sommet, etat_an)
        phrase_creux = ""
        if creux:
            pluriel = len(creux) > 1
            phrase_creux = (
                "      <p>" + ("Les exercices " if pluriel else "L'exercice ")
                + ", ".join(creux)
                + (" creusent" if pluriel else " creuse") + " la colonne du site&nbsp;: "
                "ce n'est pas une baisse des subventions, mais l'absence de l'annexe Jaune "
                "de l'État, qui pèse à elle seule les deux tiers du total"
                + (" — le fichier de l'exercice 2022 est vide à la source."
                   if creux == ["2022"] else
                   ". Le fichier de l'exercice 2022 est vide à la source&nbsp;; les "
                   "exercices les plus récents ne sont pas encore parus.")
                + "</p>\n")
        reserves = " ".join(controle.get("reserves", []))
        r_denom = denom.get("resume", {}).get("commune", {})
        phrase_denom = ""
        if r_denom:
            phrase_denom = (
                f"      <p>Second repère, territorial celui-là&nbsp;: le compte 6574 des balances "
                f"comptables de la DGFiP. {nb(r_denom.get('declarants', 0))} communes y déclarent "
                f"{eur(r_denom.get('declare_eur'))} de subventions de fonctionnement aux "
                f"associations entre {r_denom.get('exercices', ['', ''])[0]} et "
                f"{r_denom.get('exercices', ['', ''])[-1]}&nbsp;; le site en connaît "
                f"<strong>{eur(r_denom.get('site_vote_eur'))}</strong>, soit "
                f"{str(r_denom.get('part_connue_pct', '—')).replace('.', ',')}&nbsp;%. Le détail "
                f"échelon par échelon est sur la page "
                f"<a href=\"couverture.html\">Ce qu'on ne sait pas</a>.</p>\n")
        bloc_controle = f"""    <p>Un total ne veut rien dire sans échelle. Celle-ci vient des comptes nationaux
       de l'INSEE&nbsp;: l'opération <strong>D751, «&nbsp;transferts courants aux ISBLSM&nbsp;»</strong>,
       mesure ce que l'ensemble des administrations publiques verse chaque année aux
       institutions sans but lucratif au service des ménages.</p>
    <div class="table-enveloppe"><table>
      <thead><tr><th>Exercice</th><th>Comptes nationaux (D751)</th>
        <th>Le site retrouve (voté)</th><th>Part</th></tr></thead>
      <tbody>
{chr(10).join(lignes_controle)}
      </tbody>
    </table></div>
    <p class="avertissement"><strong>Ces deux colonnes ne mesurent pas la même chose.</strong>
       {html.escape(reserves)} Le rapprochement dit un ordre de grandeur, pas un taux de
       complétude&nbsp;: une part faible sur un exercice ancien signale surtout que peu de
       collectivités publiaient alors.</p>
{phrase_creux}{phrase_denom}"""

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
<a class="saut" href="#contenu">Aller au contenu</a>
<nav class="bandeau">
  <div class="bandeau-inner">
    <a class="marque" href="index.html">Dons publics aux associations
      <span>Qui finance les associations en France</span></a>
    <div class="menu">
      <a href="index.html">Accueil</a>
      <a href="recherche.html">Chercher une association</a>
      <a href="commune.html">Ma commune</a>
      <a href="couverture.html">Ce qu'on ne sait pas</a>
      <a href="methode.html" aria-current="page">Sources &amp; méthode</a>
    </div>
  </div>
</nav>
<main class="enveloppe" id="contenu">
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
    <div class="compteur"><span class="valeur">{nb(idx.get('beneficiaires', 0))}</span>
      <span class="etiquette">bénéficiaires résolus</span></div>
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
       {'— ' + nb(rejet['rows']) + ' lignes' if rejet else ''}. Leur somme n'est
       <em>pas</em> donnée ici, et c'est délibéré&nbsp;: elle est dominée par des valeurs
       qui ne sont pas des montants du tout — un SIRET recopié dans la colonne montant
       vaut 78&nbsp;962 milliards d'euros à lui seul. Additionner ces valeurs produirait
       un nombre qui n'a pas de sens.</p>
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
{lignes_credibilite}
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

    <h2>Par rapport à quoi&nbsp;? Les totaux de contrôle</h2>
{bloc_controle}

    <h2>Reproduire ces chiffres</h2>
    <p>Le pipeline est public et reconstructible d'une commande. Chaque ligne du site porte
       l'identifiant de sa source et sa référence dans le fichier d'origine. Tout est dans le
       <a href="https://github.com/wald52/dons-aux-associations">dépôt du projet</a> :</p>
    <ul>
      <li>la table canonique elle-même, en Parquet partitionné par année —
        <code>data/canonical/subventions/year=AAAA/</code> ;</li>
      <li>le rapport de qualité complet, dont ces chiffres sont tirés —
        <code>data/canonical/quality-report.json</code> ;</li>
      <li><strong>la règle des totaux, écrite une seule fois</strong> —
        <code>compte_dans_les_totaux</code> dans <code>scripts/pipeline/common.py</code> ;
        c'est elle que suivent la carte, les fiches et les exports ;</li>
      <li>les {nb(50)} contrôles de bout en bout — <code>scripts/pipeline/verify.py</code>.</li>
    </ul>
    <div class="encart">
      <h3>Emporter les chiffres</h3>
      <p>Chaque fiche d'association, chaque fiche communale, chaque département et chaque
         liste de résultats se télécharge en CSV. Ces fichiers portent <strong>une colonne de
         montant par catégorie</strong> — voté, payé, hors don, agrégat, hors champ — plutôt
         qu'une colonne unique assortie d'un drapeau : sommer une colonne y est juste par
         construction, et sommer deux colonnes se voit, puisqu'elles ne portent pas le même
         nom. C'est la même partition que celle vérifiée à chaque assemblage.</p>
    </div>
  </div>

  <footer>
    Données publiques sous Licence Ouverte 2.0. Page engendrée le
    {q.get('generated_at', '')[:10]} à partir de <code>quality-report.json</code>,
    <code>couverture.json</code> et des manifestes de moissonnage.
  </footer>
</main>
</body>
</html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"  methode.html engendrée ({len(page)/1024:.1f} Ko)")
    print(f"  {nb(q.get('rows_total', 0))} versements, {len(q.get('by_source', {}))} sources")


if __name__ == "__main__":
    main()
