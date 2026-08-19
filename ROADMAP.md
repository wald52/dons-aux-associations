# Feuille de route — remise à plat du site

> Diagnostic établi le 2026-08-18 sur l'état `main`.
> Chiffres mesurés sur 1 578 180 enregistrements, 167 fichiers sources, 168 balises `<script>`.

## 1. Diagnostic

Tout part de la même racine : **les données ont été traitées comme du code**.
167 fichiers `.js` écrits à la main, chargés en bloc, sans étape de construction.

### 1.1 Chargement (bloquant)

| Mesure | Valeur |
|---|---|
| Poids servi à l'ouverture | **835 Mo** |
| Balises `<script>` de données | **168**, sans `defer` |
| Objets en mémoire | **1 578 180** (> 1 Go de tas) |
| Filtrage | balayage linéaire du tableau complet |

- Les scripts sont téléchargés et exécutés séquentiellement avant tout affichage.
- Ce sont des `.js`, pas des `.json` : le moteur doit les *parser* (bien plus lent que `JSON.parse`).
- Tout est concaténé dans `window.ALL_SUBVENTIONS`, un tableau unique d'objets imbriqués.
- `src/modules/data-loader.js` implémente déjà du chargement paresseux — **il est court-circuité**
  par les balises en dur dans `index.html`.

### 1.2 Justesse des données (bloquant)

| Défaut | Lignes | % |
|---|---|---|
| Sans département exploitable (`"00"`) | 311 471 | 19,7 % |
| Hors taxonomie des donateurs | 174 154 | 11,0 % |
| Sans SIRET | 160 047 | 10,1 % |
| Sans URL de source | 42 364 | 2,7 % |
| Sans année (`0`) | 14 502 | 0,9 % |
| Sans RNA | 1 157 271 | 73,3 % |

- **Déduplication par identifiant technique uniquement** (`data/loader.js`, `seen.has(n.id)`).
  Les ids sont préfixés par source : deux sources décrivant la même subvention
  (fichier propre d'une commune + agrégat SCDL) ne se croisent jamais.
  → **les totaux affichés sont gonflés d'un montant inconnu**.
- **Taxonomie éclatée** : 10 valeurs de `entity.type` là où il en faut 5.
  `state`/`ministere`, `department`/`departement`, `commune`/`city`, `epci`/`metropole`.
  `src/modules/filters.js` n'en connaît que 5 → l'État apparaît en deux entrées
  distinctes dans le menu déroulant.

### 1.3 Recherche croisée (structurel)

Croiser suppose de reconnaître qu'une association vue chez l'État et chez sa commune
est la même. Cela demande un identifiant stable : SIRET, ou mieux RNA.
73 % des lignes n'ont pas de RNA, 10 % pas de SIRET.
Le rapprochement se fait donc par nom brut, non normalisé. Aucun index de noms.

### 1.4 Exhaustivité (structurel)

Univers de référence issu de `wald52/carte-finances-locales` (référentiel INSEE) :

| Échelon | Univers INSEE | Couvert (ordre de grandeur) | Reste |
|---|---|---|---|
| Communes | 34 936 | ~60 | 99,8 % |
| Intercommunalités | 1 335 | ~20 | 98,5 % |
| Départements | 102 | ~30 | 70 % |
| Régions | 18 | 2 | 89 % |

- 375 donateurs distincts au total.
- **73 % du volume vient de l'État** : le site raconte surtout l'État tout en se
  présentant comme une vue de tous les échelons.
- Rien ne distingue « ne verse rien » de « donnée absente » : le gris est ambigu.
- `SOURCES.md` recense **556 datasets repérés via l'API data.gouv.fr, 167 intégrés à la main**.

### 1.5 Hygiène du dépôt

- Arbre de travail : 976 Mo (`.git` : 88 Mo) — la limite indicative GitHub Pages est de 1 Go.
- Captures d'écran versionnées (868 Ko), CSV bruts doublonnant leurs fichiers générés (37 Mo).

## 2. Décision d'architecture

**Le site doit cesser d'expédier ses données et servir un index.**

- **Agrégats précalculés** en `.json.gz` (quelques centaines de Ko) pour la carte et les compteurs.
- **Parquet + DuckDB-WASM en requêtes HTTP Range** pour le détail : le navigateur ne
  télécharge que les octets des colonnes et blocs utiles. Vrai SQL sur 1,58 M de lignes,
  sans backend, compatible hébergement statique gratuit.
- C'est le prolongement direct de `carte-finances-locales` (agrégats gzip, découpage par
  département, chargement paresseux, service worker), avec une couche SQL en plus
  parce que le croisement l'exige.

## 3. Les phases

L'ordre est contraint : **on répare la donnée avant la vitesse**. Optimiser le
chargement de données fausses obligerait à tout refaire une fois nettoyé.

### Phase 0 — Socle et filet de sécurité (1-2 j)
- Taguer l'état actuel (`v0`).
- Écrire un **CLAUDE.md** de reprise, sur le modèle de `carte-finances-locales`.
- Sortir du dépôt captures d'écran et CSV bruts ; compléter `.gitignore`.
- Poser un banc de mesure (premier affichage, poids transféré, mémoire).
- **Arrêter le schéma canonique** : la liste explicite des colonnes.

**Livrable** — dépôt propre, point de référence chiffré, schéma cible écrit.

### Phase 1a — Pipeline canonique sur le PLF Jaune — **fait**

```bash
python3 scripts/pipeline/build_referentiel.py    # référentiel INSEE (une fois)
python3 scripts/pipeline/fetch_plf_jaune.py      # moissonne data.gouv.fr
python3 scripts/pipeline/normalize_plf_jaune.py  # -> data/canonical/parts/
python3 scripts/pipeline/build_canonical.py      # -> subventions.parquet
```

Résultat : **808 174 lignes** sur 13 millésimes (2010-2023), en **55,7 Mo** de
Parquet — contre 654 000 lignes et ~450 Mo de JavaScript auparavant.
Interrogeable en SQL en 13 à 151 ms.

### Phase 1b — Les 152 sources héritées — **fait**

```bash
python3 scripts/pipeline/normalize_legacy.py
python3 scripts/pipeline/build_canonical.py
python3 scripts/pipeline/verify.py
```

Table canonique complète : **1 692 962 lignes**, 163,8 Md€ d'attributions
individuelles, 2001-2027, **101 départements sur 101**. La déduplication par
clé métier retire 1 477 lignes de double comptage (10,3 M€) que l'ancien site
ne pouvait pas voir. 20 contrôles automatiques.

### Phase 1 — Pipeline canonique (1-2 semaines, le gros morceau)
- Scripts Python idempotents avec cache local, même convention que `carte-finances-locales`.
- Un normaliseur **par famille de format** (SCDL, PLF Jaune, portails maison), pas par source.
- Importer le référentiel INSEE de l'autre dépôt (34 936 communes, 1 335 EPCI, 102 dépts, 18 régions).
- Rattraper les 311 471 lignes sans département via SIRET → SIRENE → code INSEE.
- Enrichir l'identité des associations par le **RNA** (base ouverte).
- Dédupliquer sur **clé métier** (bénéficiaire + donateur + année + montant + objet).
- Unifier la taxonomie des donateurs sur 5 valeurs.
- Produire un **rapport de qualité par source**, versionné.

**Livrable** — `data/canonical/subventions.parquet` + `quality-report.json`,
reconstructibles d'une commande.

### Phase 2 — Nouvelle architecture de chargement — **fait**

```bash
python3 scripts/pipeline/build_carte.py       # carte depuis le GeoJSON officiel
python3 scripts/pipeline/build_aggregates.py  # agrégats du premier écran
```

Premier écran : **103 Ko gzippés** (carte 77, cube 19, méta 2,5, top 4,3).
Détail d'un département : un fragment de **2,5 Ko en moyenne**, chargé au clic.
Premier affichage **0,11 s**, données exploitables **0,63 s**, mémoire **10 Mo**.
Dépôt ramené de 981 Mo à 133 Mo suivis.

### Phase 2 — Nouvelle architecture de chargement (~1 semaine)
- Précalculer les agrégats (département × année × type de donateur, régions, totaux).
- **Supprimer les 168 balises `<script>`**.
- Brancher DuckDB-WASM sur le Parquet en requêtes Range.
- Reprendre le service worker de `carte-finances-locales`.

**Cible** — premier affichage < 1 s, quelques centaines de Ko au lieu de 835 Mo, utilisable sur mobile.

### Phase 3 — Recherche croisée — **fait**

```bash
python3 scripts/pipeline/build_search_index.py   # index bénéficiaires + shards
```

`recherche.html` : DuckDB-WASM embarqué (versionné, chargé seulement sur cette
page), 261 444 bénéficiaires résolus par SIREN puis nom+département,
**4 400 associations financées par au moins 3 échelons**. Recherche locale
instantanée ; la fiche d'une association télécharge un shard d'environ 400 Ko.
La carte du premier écran reste à 0,13 Mo / 0,05 s.

### Phase 3 — Recherche croisée (1-2 semaines)
- Association → tous ses financeurs, tous échelons, toutes années.
- Financeur → toutes ses associations, avec évolution.
- Cumuls : associations financées par ≥ 3 échelons.
- Trajectoires temporelles.
- Index de noms normalisé (accents pliés, formes juridiques retirées, sigles)
  pour rattraper les 73 % sans RNA.

### Phase 4 — Exhaustivité (continu)
- **Moissonneur SCDL générique** sur l'API data.gouv.fr : les 556 datasets d'un coup,
  et les nouveaux automatiquement.
- **Carte de couverture** à trois états : ne publie pas / publie mais pas ingéré / zéro subvention.
- Prioriser par **population couverte**, pas par nombre de fichiers.
- Afficher la couverture en permanence dans l'interface.

### Phase 5 — Design et compréhension (~1 semaine, en dernier)
- Identité visuelle cohérente avec `carte-finances-locales`.
- Rendre l'incertitude lisible (couverture partielle, doublons possibles, années absentes).
- Parcours pensés par question posée plutôt que barre de filtres.
- Page méthodologie sur le modèle de `sources.html`.

## 4. Par où commencer

**Phase 0, puis phase 1 sur le seul PLF Jaune** (654 000 lignes, 40 % du volume,
un format unique et déjà propre).

En une semaine, le site est entièrement reconstruit sur l'architecture cible avec
une seule source : il fonctionne, il est rapide, il est vérifiable de bout en bout.
Ensuite on rebranche les 166 autres sources dans un pipeline qui marche déjà.

Avantage décisif sur un marathon : **aucun travail jetable**, et un site utilisable
dès la deuxième semaine plutôt qu'au bout de deux mois.

## 5. Méthode d'itération

- **Une phase = une branche = un état déployable.** Si une phase déborde, on la coupe en deux.
- **Le rapport de qualité fait foi.** Tout changement de données se juge sur le rapport
  chiffré, pas à l'œil — c'est ce qui évite les régressions silencieuses.
- **Le CLAUDE.md se met à jour en continu.** Toute décision contre-intuitive s'y écrit
  avec sa raison.
