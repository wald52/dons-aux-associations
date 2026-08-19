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

## 3. Arborescence actuelle (avant refonte)

```
.
├── index.html              # page unique ; contient 168 <script> de données EN DUR
├── src/
│   ├── app.js              # orchestrateur
│   ├── state.js            # état centralisé
│   └── modules/            # filtres, tri, carte, graphiques, export, recherche…
├── data/
│   ├── sources/*.js        # 167 fichiers, 835 Mo — LE problème
│   ├── loader.js           # agrège et normalise au chargement, dans le navigateur
│   ├── sources-index.js    # métadonnées de chargement paresseux — INUTILISÉ
│   ├── departments.js      # référentiel départements maison
│   ├── geo/ svg/           # contours et cartes
├── scripts/convert-*.js    # 15 convertisseurs écrits à la main, un par source
├── scripts/bench/          # banc de mesure (phase 0)
├── bench/v0.json           # relevé de référence
├── ROADMAP.md              # le plan de sortie — À LIRE
├── SCHEMA.md               # schéma canonique cible — À LIRE avant la phase 1
├── MESURE-PERF.md          # méthode de mesure et cibles
└── SOURCES.md              # inventaire des sources (556 repérées, 167 intégrées)
```

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
  proxy : seule la branche de travail est autorisée). L'état de référence
  d'avant refonte est `origin/main` @ `0b14348`, tag `v0` en local seulement.

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
- [ ] **Phase 1** — pipeline canonique. Commencer par le **seul PLF Jaune**
      (654 000 lignes, un format unique et propre), puis rebrancher les autres.
- [ ] **Phase 2** — nouvelle architecture de chargement.
- [ ] **Phase 3** — recherche croisée.
- [ ] **Phase 4** — exhaustivité (moissonneur SCDL, carte de couverture).
- [ ] **Phase 5** — design et lisibilité.

Détail de chaque phase dans `ROADMAP.md`.

---

## 7. Méthode de travail

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
