# Dons publics aux associations

Qui finance les associations en France, et combien. Site statique qui rassemble
**2 811 070 subventions** publiées par l'État, ses opérateurs, les régions, les
départements, les intercommunalités et les communes — **698 sources**, aucun
serveur applicatif.

→ **[Voir le site](https://wald52.github.io/dons-aux-associations/)**

## Ce qu'on peut y faire

| | |
|---|---|
| **Chercher une association** | Tous ses financeurs, tous échelons confondus, avec la trajectoire année par année et chaque versement ligne à ligne, sa source et son lien. C'est la question qu'aucun guichet ne sait poser : chaque administration ne connaît que ses propres versements. |
| **Regarder sa commune** | Ce qu'elle a mandaté aux associations depuis 2010, pour **34 829 communes sur 34 936** — y compris celles qui ne publient rien, parce que toutes déclarent leur compte 6574 à la DGFiP. |
| **Parcourir la carte** | Ce que les associations domiciliées dans chaque département ont reçu, en total ou par habitant. |
| **Savoir ce qui manque** | Combien d'argent échappe au site, département par département, et pourquoi. **51,10 Md€** déclarés par les communes, **7,95** que le site connaît nommément. |

Tout a une adresse partageable : un département, une année, une recherche, une
association, une commune.

## La règle qui gouverne tout : fidélité à la source

Aucun montant n'est corrigé, aucun bénéficiaire n'est deviné. Quand une donnée
paraît fausse, elle est **signalée et mise de côté**, jamais redressée — savoir
qu'un chiffre est faux ne dit pas quel est le vrai. Tout enrichissement (un
département déduit d'un SIRET, une année lue dans un libellé) est marqué comme
tel.

Trois conséquences visibles :

- **Voté et payé s'affichent côte à côte et ne s'additionnent jamais.** Quand
  une collectivité publie les deux, c'est le même argent.
- **Tout argent versé à une association n'est pas un don.** Une prestation
  facturée a une contrepartie : elle reste consultable, hors des totaux.
- **La couverture affichée est un minimum.** L'erreur d'appariement va toujours
  vers la sous-estimation, jamais vers l'inverse.

`methode.html` est **engendrée depuis les données** à chaque publication : ses
chiffres ne peuvent pas diverger de ceux du site.

## Architecture

Vanilla HTML/CSS/JS, aucun framework, aucun bundler, aucune police distante.
Le site sert un **index précalculé, pas une base** : l'accueil transfère
0,22 Mo et s'affiche en 0,06 s, quelle que soit la taille de la table derrière.

```
index.html  commune.html  recherche.html  couverture.html  methode.html
assets/js/  commun · lexique · index-recherche · suggest · app · commune · recherche · couverture
data/aggregates/    ce que le premier écran charge (~110 Ko)
data/recherche/     l'index de recherche : noms (5,1 Mo) + 512 shards de fiches (~120 Ko pièce)
data/canonical/     la table canonique en Parquet, source de vérité
scripts/pipeline/   le pipeline Python : moissonnage, normalisation, agrégats, contrôles
```

Faire tourner le site en local :

```bash
python3 -m http.server 8000     # puis http://localhost:8000/
```

Reconstruire toute la chaîne (moissonnages exceptés, ils ont leur cache) :

```bash
bash scripts/pipeline/tout_reconstruire.sh
```

`scripts/pipeline/verify.py` porte **50 contrôles de bout en bout** et doit
rester vert : c'est le garde-fou contre les régressions silencieuses. Hors d'un
assemblage complet, 49/50 est le score normal — un contrôle exige
`data/canonical/parts/`, qui n'est pas versionné.

## Documentation

| Fichier | Contenu |
|---|---|
| `CLAUDE.md` | Le handover : tout le contexte pour reprendre à froid, et **les pièges connus avec leur raison**. À lire en entier avant de toucher au code. |
| `ROADMAP.md` | Ce que chaque phase a fait, et pourquoi. |
| `RESTE-A-FAIRE.md` | Ce qui reste, chiffré et priorisé. |
| `SCHEMA.md` | Le schéma canonique et la clé métier. |
| `SOURCES.md` | Les sources, une par une. |
| `MESURE-PERF.md` | Le banc de mesure et tous les relevés. |

## Licence

Données publiques sous [Licence Ouverte 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/).
Les montants sont ceux publiés par les administrations, sans correction.
