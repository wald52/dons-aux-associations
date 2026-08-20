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

### Phase 4 — Exhaustivité — **fait (premier tour)**

```bash
python3 scripts/pipeline/fetch_scdl.py        # moissonne data.gouv.fr
python3 scripts/pipeline/normalize_scdl.py    # famille scdl
python3 scripts/pipeline/build_couverture.py  # carte de couverture
```

**665 jeux examinés, 92 retenus, 444 fichiers** : +319 366 lignes, la table
passe à **2 012 328 lignes** et 126,6 Md€. La déduplication entre sources a
retiré **50 912 doublons (3,78 Md€)** entre SCDL et sources héritées.
`couverture.html` dit désormais, échelon par échelon, ce que le site sait et
ne sait pas. Le moissonnage étant générique, tout nouveau millésime publié
sera repris sans modification du code.

### Phase 4 — Exhaustivité (continu)
- **Moissonneur SCDL générique** sur l'API data.gouv.fr : les 556 datasets d'un coup,
  et les nouveaux automatiquement.
- **Carte de couverture** à trois états : ne publie pas / publie mais pas ingéré / zéro subvention.
- Prioriser par **population couverte**, pas par nombre de fichiers.
- Afficher la couverture en permanence dans l'interface.

### Phase 5 — Design et compréhension — **fait**

```bash
python3 scripts/pipeline/build_methode.py   # page sources & méthode
```

Système visuel unifié avec `carte-finances-locales` (même bleu institutionnel),
bandeau de navigation commun aux quatre pages, rampe de carte séquentielle à
une seule teinte, `methode.html` engendrée depuis les données elles-mêmes.
Accessibilité : thème sombre pensé pour sa surface et non inversé, relief
obligatoire là où la couleur passe sous le seuil de contraste.

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

---

## Phase 6a — FAITE (20/08/2026)

Les deux premiers gisements ci-dessous ont été exploités. Résultat mesuré :

| | phase 4 | phase 6a |
|---|---|---|
| lignes | 2 012 328 | **2 769 440** |
| sources | 269 | **559** |
| total sommé | 126,6 Md€ | **161,7 Md€** |
| bénéficiaires résolus | ~304 000 | **408 380** |
| cumulant 3 échelons ou + | 4 400 | **9 016** |
| communes couvertes | 70 | **86** |
| contrôles | 28 | **30** |

**6a a coûté une ligne de code.** L'estimation de 328 fichiers récupérables
était juste, mais la cause n'était pas un dictionnaire trop pauvre : c'était
que `porte_des_subventions` découpe le camelCase et ne voyait donc pas
`nombeneficiaire` écrit tout en minuscules collées. Reconnaître aussi le
motif accolé a rouvert 159 jeux Opendatasoft et 346 fichiers SCDL.

**6b a tenu ses promesses.** Paris passe de 76 207 lignes ingérées à ses
202 347 publiées, ce qui recoupe l'estimation de ~195 000. Aix-Marseille et
Clermont, qui ne rendaient rien, contribuent.

**Deux surprises, traitées :**

- Le fédérateur `data.opendatasoft.com` republie les jeux des portails
  territoriaux : chaque jeu arrivait deux fois. La déduplication par clé
  métier les rattrape (771 605 lignes, 53 Md€).
- Paris publie le même argent deux fois — voté, puis versé au compte
  administratif — et son compte administratif ne concerne pas que des
  associations. D'où `measure` et `beneficiary_kind_provenance` : 18,2 Md€
  sont ingérés et consultables mais délibérément hors des totaux.

---

## Phase 6b — Ce qui reste (mesuré le 20/08/2026)

### La priorité : une identité de donateur dans la clé métier

**~7,25 Md€ sur 567 426 lignes** sont des doublons que la clé manque parce
qu'une même collectivité change de libellé d'une publication à l'autre :

| libellés confondus | surcompte |
|---|---|
| `DEPARTEMENT DE PARIS` / `VILLE DE PARIS` | 2 467 M€ |
| direction de la démocratie de la Ville de Paris / `VILLE DE PARIS` | 999 M€ |
| `DGCL DDETS 147` / `ANCT POLITIQUE DE LA VILLE ETAT` | 578 M€ |
| `CONSEIL DEPARTEMENTAL DE LA SOMME` / `DEPARTEMENT DE LA SOMME` | 157 M€ |
| `CONSEIL D PARTEMENTAL DU FINIST RE` (encodage détruit) | 275 M€ |

**Paris est donc encore compté environ deux fois.** Le correctif est de
résoudre le donateur — par SIREN, sinon par la collectivité du référentiel
INSEE — avant de fabriquer la clé, plutôt que de comparer des libellés.

Attention : « Ville de Paris » et « Département de Paris » ont été deux
personnes morales distinctes jusqu'en 2019. Les confondre est juste pour
dédupliquer une même publication, faux pour lire l'échelon. À trancher
explicitement.

### Le reste

- **Dépivoter les tableaux par année** — ~178 fichiers publient une colonne
  par exercice au lieu d'une ligne par versement.
- **Les liens morts en amont** — 236 réponses 404 et 135 échecs de connexion
  chez `datacat.datalocale`. Rien à corriger chez nous ; à re-tenter.
- **`cd-finistere`** — 5 442 lignes au nom de donateur détruit (U+FFFD dans
  le fichier hérité). Irrécupérable ici : il faut re-moissonner l'amont.

---

## Phase 6 — Le gisement, tel que mesuré le 19/08/2026

Ce qui manque n'est pas une inconnue : quatre gisements ont été quantifiés,
classés ici par rapport gain/effort.

### 6a. Élargir le dictionnaire de colonnes du moissonneur — **le moins cher**

Sur les 661 fichiers écartés dont les colonnes sont consignées,
**328 redeviendraient exploitables** avec un dictionnaire mieux fait. Deux
graphies très répandues sont manquées aujourd'hui :

- `Nom association` (le test actuel exige que le libellé *commence* par
  « association ») ;
- `Réalisé (en numéraire)`, la colonne de montant des budgets départementaux.

Attention : un élargissement naïf produit des faux positifs — « Nom ETS
attribuant la **subvention** » serait pris pour un montant, « Nature juridique
de l'**organisme** » pour un bénéficiaire. Il faut comparer des mots entiers et
ordonner les motifs du plus spécifique au plus général, comme le fait déjà
`build_couverture.py`.

### 6b. Moissonner les portails territoriaux — **le plus gros gain**

Les collectivités qui publient le plus ne passent pas par data.gouv.fr : elles
ont leur propre portail. Or **ces portails partagent tous la même API**
(Opendatasoft Explore v2.1), donc un seul moissonneur générique les couvre.

| Portail | Constat |
|---|---|
| `opendata.paris.fr` | **~195 000 lignes** de subventions publiées, contre 76 207 ingérées |
| `data.iledefrance.fr` | 16 jeux de subventions |
| `data.opendatasoft.com` | fédérateur : 211 jeux « subvention » |
| `data.economie.gouv.fr` | déjà exploité pour le PLF Jaune |

Paris à lui seul représente plus de 100 000 lignes manquantes.

### 6c. Dépivoter les tableaux par année

Environ 178 fichiers publient une colonne par exercice
(`2018-Subventions Accordées`, `2019-…`) au lieu d'une ligne par versement.
Le format est régulier, donc automatisable : une colonne dont le libellé
contient une année devient une ligne par année.

### 6d. Ce qui reste hors de portée sans habilitation

- **`api.datasubvention.beta.gouv.fr`** (État) agrège Chorus et les données des
  collectivités — ce serait la source de référence. L'API vit, mais renvoie
  **401** : elle est réservée aux agents publics et aux associations habilitées.
  Une demande de compte est le seul chemin.
- **`data.grandlyon.com`** renvoie lui aussi **401**. C'est la raison pour
  laquelle la quarantaine d'unité de `metropole-lyon` (48 Md€, probablement des
  centimes) **n'a pas pu être levée** : l'amont n'est pas vérifiable sans compte.

### Ce qui manquera toujours

Les communes de moins de 3 500 habitants ne sont pas tenues de publier, et
parmi celles qui le sont, l'obligation est peu suivie. Aucun moissonnage ne
comblera cela : la lacune est légale, pas technique. C'est précisément ce que
la page « Ce que ce site ne sait pas » est là pour dire.
