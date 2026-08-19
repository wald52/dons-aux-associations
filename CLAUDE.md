# Dons aux associations — handover pour une nouvelle session

Ce fichier donne tout le contexte pour reprendre le projet à froid.
À lire en entier avant de toucher au code.

Le projet est en **refonte** : l'état actuel du site est celui produit par une
première génération assistée, et il est structurellement en impasse. Le plan de
sortie est dans `ROADMAP.md`. Ne pas « optimiser » l'existant sans l'avoir lu :
la plupart des optimisations évidentes sont du travail jetable.

---

## 1. Vue d'ensemble

Site statique (GitHub Pages, vanilla HTML/CSS/JS) qui cartographie les
subventions publiques versées aux associations en France, par l'État, les
régions, les départements, les communes et les EPCI.

**Doctrine** — reprise du projet frère `wald52/carte-finances-locales` :
**fidélité maximale à la source**. Pas de correction de montant, pas de
bénéficiaire deviné. Tout enrichissement est marqué comme tel. Si une zone
reste grise, on l'assume et on documente pourquoi.

L'utilisateur est expert du métier et débutant en code : lui présenter des
options claires et les arbitrages, il tranche lui-même.

**Branche de travail : `main`, et elle seule.** Consigne explicite de
l'utilisateur (19/08/2026) : il ne travaille que sur `main`. Développer,
commiter et pousser directement dessus ; ne pas ouvrir de branche de
fonctionnalité ni de pull request sauf demande expresse.

**Projet frère à connaître** : `wald52/carte-finances-locales` (carte des
finances locales). On lui emprunte le référentiel INSEE, les patterns
d'architecture (agrégats `.json.gz`, découpage par département, chargement
paresseux, service worker) et la convention des scripts Python. Le cloner en
lecture pour s'en servir : c'est un dépôt public.

---

## 2. État des lieux chiffré (18/08/2026)

Mesuré, pas estimé. Relevé complet dans `bench/v0.json`, méthode dans
`MESURE-PERF.md`.

| Mesure | Valeur |
|---|---|
| Octets transférés (brut / gzippé) | 835 Mo / ~73,6 Mo |
| Premier affichage | 12,96 s |
| Données exploitables | 57,75 s |
| Mémoire JS | **1 965 Mo sur un plafond de 3 586 Mo** |
| Enregistrements | 1 595 805 |
| Balises `<script>` | 170 |

La mesure la plus grave est la mémoire : 55 % du plafond du moteur, en local
sur une machine confortable. Sur mobile, le plafond est plus bas et l'onglet
est tué. C'est pour cela que le site est inutilisable sur téléphone.

Qualité des données (sur 1 578 180 lignes comptées par `grep`) :

| Défaut | Lignes | % |
|---|---|---|
| Sans département exploitable (`"00"`) | 311 471 | 19,7 % |
| Hors taxonomie des donateurs | 174 154 | 11,0 % |
| Sans SIRET | 160 047 | 10,1 % |
| Sans URL de source | 42 364 | 2,7 % |
| Sans année (`0`) | 14 502 | 0,9 % |
| Sans RNA | 1 157 271 | 73,3 % |

Couverture, face au référentiel INSEE :
~60 communes sur 34 936, ~20 EPCI sur 1 335, ~30 départements sur 102,
2 régions sur 18. **375 donateurs distincts** au total, dont l'État pèse 73 %
du volume.

---

## 3. Arborescence

```
.
├── index.html                  # une seule balise <script> (contre 170 en v0)
├── sw.js                       # service worker — bumper CACHE à chaque publication
├── assets/css/style.css
├── assets/js/app.js            # application, ~400 lignes
├── data/
│   ├── aggregates/             # CE QUE LE SITE CHARGE : 103 Ko au premier écran
│   │   ├── meta / cube / top / map-departements  (.json.gz)
│   │   └── departements/<code>.json.gz           # détail au clic, ~2,5 Ko
│   ├── canonical/
│   │   ├── subventions/year=AAAA/*.parquet       # table canonique, 28 partitions
│   │   ├── quality-report.json                   # FAIT FOI
│   │   └── coverage.json
│   ├── referentiel/            # univers INSEE (communes, EPCI, dépts, régions)
│   ├── geo/*.geojson.gz        # contours, source de la carte
│   └── raw/                    # téléchargements bruts — NON versionné
├── scripts/pipeline/           # le pipeline (Python)
├── scripts/bench/measure.js    # banc de mesure
├── bench/v0.json, phase2.json  # relevés
├── ROADMAP.md, SCHEMA.md, MESURE-PERF.md, SOURCES.md
```

**`data/sources/*.js` (835 Mo) et `src/` ont été retirés du dépôt en phase 2.**
Leur contenu est intégralement absorbé dans `data/canonical/`, qui est versionné.
Les garder faisait dépasser la limite de 1 Go de GitHub Pages (981 Mo suivis
avant, 133 Mo après). Pour rejouer `normalize_legacy.py`, les récupérer depuis
l'historique : `git checkout 0b14348 -- data/sources`.

---

## 4. Pièges connus — lire avant de toucher

- **`src/modules/data-loader.js` implémente déjà du chargement paresseux, et il
  ne sert à rien** : les 168 balises `<script>` d'`index.html` chargent tout
  d'office avant lui. Ne pas perdre de temps à le déboguer, il sera supprimé.

- **Les fichiers de données sont des `.js`, pas des `.json`.** Le navigateur
  doit donc les *parser* comme du code, bien plus lent qu'un `JSON.parse`.
  C'est la cause principale des 57 s, pas le transfert.

- **La déduplication de `data/loader.js` compare les identifiants techniques**
  (`seen.has(n.id)`), qui sont préfixés par source. Deux sources décrivant la
  même subvention ne se croisent jamais : **les totaux affichés sont
  surévalués d'un montant inconnu**. Ne pas citer ces totaux comme s'ils
  étaient justes.

- **`culture.js` et `culture-2.js` ne sont pas des doublons** malgré un nombre
  de lignes identique : ce sont deux tranches consécutives (ids `culture-0…`
  et `culture-111532…`). Même chose pour `anct-politique-ville`. Ne pas les
  « nettoyer ».

- **Toutes les lignes ne sont pas des subventions individuelles.**
  `ville-rennes` publie des lignes de budget agrégées (compte M14 `6574.00`).
  Les sommer avec des attributions individuelles compte deux fois. D'où
  `granularity` dans `SCHEMA.md`.

- **`entity.type = "state"` ne signifie pas toujours l'État.**
  `subv-associations-2024` porte `"Source data.gouv.fr"` en donateur : c'est un
  attribuant non récupéré, classé « État » par défaut. Cela gonfle l'État.

- **Le push de tags est refusé** dans les sessions distantes (HTTP 403 du
  proxy). L'état de référence d'avant refonte est `origin/main` @ `0b14348`,
  tag `v0` en local seulement. Le push de branches, lui, fonctionne.

- **`metropole-lyon` est en QUARANTAINE d'unité.** Ses 9 081 lignes totalisent
  48 Md€ quand le budget annuel de la Métropole avoisine 3,8 Md€. La médiane y
  est de 1 584 200 €, le minimum de 100, et 85 % des valeurs sont multiples de
  100 : tout indique des **centimes lus comme des euros**. L'API
  data.grandlyon.com ayant changé, la vérification amont reste à faire — on ne
  divise donc pas par cent de sa propre autorité. Les montants sont mis dans
  `amount_rejected_eur`, les lignes restent comptées. Cette seule quarantaine
  fait passer le total affiché de 163,8 à 115,8 Md€. **À rouvrir en phase 4.**

- **Douglas-Peucker sur un anneau fermé supprime tout.** Ses deux extrémités
  étant confondues, la distance à la corde est nulle partout. Il faut couper
  l'anneau à son point le plus éloigné du départ et simplifier les deux moitiés.
  Sans cela, `build_carte.py` produit une carte vide sans lever d'erreur.

- **Le SVG livré avec l'ancien site ignore l'outre-mer** et nomme la Corse en
  minuscules (`2a`). La carte est donc reconstruite depuis le GeoJSON, avec les
  cinq DOM en médaillons.

- **Le PLF Jaune change de structure tous les 3 ou 4 ans.** Quatre schémas de
  colonnes coexistent (2012 / 2013-2017 / 2018+2020 / 2021 et suivants), avec
  des encodages différents (UTF-8 avec BOM, cp1252) et parfois deux lignes de
  titre avant l'en-tête. Le normaliseur reconnaît les colonnes **par libellé
  plié**, jamais par position : un millésime à venir réutilisant les mêmes
  intitulés passera sans modification.

- **Ne pas se fier au numéro de PLF pour dater les données.** Le PLF 2016
  contient les subventions **2014**, pas 2015. L'année se lit dans le libellé
  de colonne (« Objet 2020 ») ou la colonne MILLESIME, et seulement à défaut
  par la convention « PLF moins deux ».

- **Le NIC perd ses zéros de tête** en passant par un tableur (`88` au lieu de
  `00088`). Il faut le compléter avant de reconstituer le SIRET, sinon la clé
  de Luhn échoue. Les SIRET stockés dans l'ancien site sont tronqués à 11
  caractères pour cette raison.

- **Le référentiel du dépôt frère n'est PAS indexé sur les codes INSEE.**
  Il utilise des codes OFGL : `67A` pour l'Alsace (qui recouvre les
  départements INSEE 67 et 68), `691` pour la Métropole de Lyon, `Corse` pour
  2A + 2B. Les communes, elles, portent bien des codes INSEE. Croiser les deux
  naïvement laisse les 880 communes alsaciennes sans région.
  `build_referentiel.py` reconstruit donc la table des départements à partir
  des codes INSEE des communes, et ne va chercher dans la table OFGL que le
  rattachement régional, via une table d'alias explicite.

- **Des SIRET ont été détruits par un tableur.** 29 214 lignes portent une
  valeur du type `2,19301E+13` : Excel a traité le SIRET comme un nombre et
  n'en a gardé que six chiffres significatifs. **Ce n'est pas réparable.**
  Drapeau `siret_scientific_notation`, à ne pas confondre avec un simple
  `siret_invalid`. Le vrai correctif est de re-moissonner l'amont (phase 4).

- **Trois lignes de `communes-pays-loire` portent un SIRET dans la colonne
  montant** (78 962 milliards d'euros chacune). Sans garde-fou, le total du
  site affiche 237 000 milliards d'euros. D'où le drapeau `amount_implausible`
  au-delà de dix milliards, et l'exclusion de ces lignes de tous les totaux.

- **L'ancien site ingérait certaines communes deux fois** sous deux noms de
  source : `commune-soissons` + `ville-soissons-2018-2021`, `ville-lisieux` +
  `ville-lisieux-2018`, `ville-redon` + `ville-redon-2018`, `commune-bar-le-duc`
  + `ville-bar-le-duc`. Sa déduplication par identifiant technique ne pouvait
  pas les voir. La clé métier en retire 1 477 lignes, soit 10,3 M€ de double
  comptage.

- **Le JSON de trois fichiers sources est invalide** : virgule surnuméraire en
  tête (`anct-politique-ville-2`) ou en queue (`culture`, `culture-2`).
  `extract_js_array` les répare, faute de quoi 350 000 lignes disparaissent
  sans bruit.

- **Détecter l'encodage sur une fenêtre d'octets exige un décodeur
  incrémental.** Une fenêtre de taille fixe coupe un caractère multi-octets en
  deux et fait conclure à tort que le fichier n'est pas en UTF-8. Ce piège a
  fait lire tout le PLF 2025 en latin-1, avec un en-tête illisible et 112 722
  lignes perdues.

- **Les CSV bruts sont désindexés** (`data/*.csv` dans `.gitignore`). Ils sont
  re-téléchargeables, URLs dans `SOURCES.md`, et leurs données sont déjà dans
  `data/sources/`. Ne pas les recommiter.

---

## 5. Décisions d'architecture et leurs raisons

- **Le site doit servir un index, pas une base.** Agrégats précalculés en
  `.json.gz` pour le premier écran ; détail en **Parquet interrogé par
  DuckDB-WASM en requêtes HTTP Range**, pour ne télécharger que les octets
  utiles. C'est ce qui donne du vrai SQL sur 1,6 M de lignes sans backend,
  donc des croisements arbitraires plutôt qu'une liste figée de filtres.

- **On répare la donnée avant la vitesse.** Contre-intuitif quand le site rame,
  mais optimiser le chargement de données fausses oblige à tout refaire une
  fois nettoyé.

- **Un normaliseur par famille de format, pas par source.** Les 167
  convertisseurs manuels sont la raison pour laquelle la couverture stagne.
  Trois familles suffisent : `scdl`, `plf_jaune`, `portail`.

- **Le moissonneur SCDL générique est le levier principal de l'exhaustivité.**
  `SOURCES.md` recense 556 datasets repérés via l'API data.gouv.fr, 167
  intégrés à la main. La plupart des collectivités publient au format
  normalisé SCDL « subventions » : un moissonneur sur ce schéma les prend tous
  et récupère automatiquement les nouveaux.

- **Sept valeurs de `donor_level`, pas cinq.** Les opérateurs de l'État
  (CNDS, ANCT, CNSA, ARS, EFS — 54 497 lignes) ont un budget propre : les
  fondre dans `etat` compterait deux fois. Et `inconnu` doit exister pour ne
  pas rattacher d'office un attribuant non récupéré. Cf. `SCHEMA.md`.

---

## 6. Où en est la refonte

- [x] **Phase 0** — socle et filet de sécurité : banc de mesure, baseline `v0`,
      dépôt nettoyé, schéma canonique arrêté (`SCHEMA.md`), ce handover.
- [x] **Phase 1a** — pipeline canonique sur le PLF Jaune. Référentiel INSEE
      vendu, moissonneur data.gouv.fr, normaliseur de famille, table canonique
      Parquet, rapport de qualité. **808 174 lignes** (contre 654 000 dans
      l'ancien site) sur 13 millésimes, 2010-2023.
- [x] **Phase 1b** — 152 sources héritées rebranchées. Table canonique
      complète : **1 692 962 lignes**, 163,8 Md€ d'attributions individuelles,
      2001-2027, 101 départements sur 101. 20 contrôles automatiques dans
      `scripts/pipeline/verify.py`.
- [x] **Phase 2** — nouvelle architecture de chargement. Agrégats précalculés,
      carte reconstruite depuis le GeoJSON, service worker, dépôt allégé.
      **0,11 s** au premier affichage contre 12,96 s, **10 Mo** de mémoire
      contre 1 965, **0,13 Mo** transférés contre 73,6.
- [ ] **Phase 3** — recherche croisée.
- [ ] **Phase 4** — exhaustivité (moissonneur SCDL, carte de couverture).
- [ ] **Phase 5** — design et lisibilité.

Détail de chaque phase dans `ROADMAP.md`.

---

## 7. Le pipeline

```bash
python3 scripts/pipeline/build_referentiel.py    # référentiel INSEE (une fois)
python3 scripts/pipeline/fetch_plf_jaune.py      # moissonne data.gouv.fr
python3 scripts/pipeline/normalize_plf_jaune.py  # famille plf_jaune
python3 scripts/pipeline/normalize_legacy.py     # 152 sources héritées
python3 scripts/pipeline/build_canonical.py      # assemblage + dédup + rapport
python3 scripts/pipeline/verify.py               # 21 contrôles, doit rester vert
python3 scripts/pipeline/build_carte.py          # carte depuis le GeoJSON
python3 scripts/pipeline/build_aggregates.py     # agrégats servis au navigateur
```

**`normalize_legacy.py` ne peut plus tourner en l'état** : ses entrées
(`data/sources/*.js`) ont été retirées du dépôt. Les récupérer d'abord par
`git checkout 0b14348 -- data/sources`. Idem pour `build_canonical.py`, qui lit
`data/canonical/parts/` (non versionné) : il faut rejouer les normaliseurs.

Tous les scripts sont idempotents : `build_canonical.py` rejoué produit un
Parquet identique octet pour octet. **`verify.py` doit rester vert** après toute
modification du pipeline — c'est le garde-fou contre les régressions
silencieuses.

Le schéma canonique et la clé métier sont définis **une seule fois**, dans
`common.py` (`CANONICAL_SCHEMA`, `business_key`), pour qu'aucun normaliseur ne
puisse diverger des autres.

## 8. Méthode de travail

- **Une phase = une branche = un état déployable.** Si une phase déborde, la
  couper en deux plutôt que de laisser la branche traîner.
- **Le rapport de qualité fait foi.** Tout changement de données se juge sur
  `data/canonical/quality-report.json`, pas à l'œil. C'est ce qui évite les
  régressions silencieuses.
- **Mesurer avant/après** avec `node scripts/bench/measure.js --label <phase>`,
  et poser `window.__DATA_READY = true` dans la nouvelle architecture pour
  garder la comparabilité.
- **Tenir ce fichier à jour.** Toute décision contre-intuitive s'y écrit avec
  sa raison — c'est ce qui permet de reprendre des mois plus tard.
