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

## Phase 6b — L'identité des donateurs (faite le 20/08/2026)

### Ce qui a été corrigé

**1. Une même collectivité, plusieurs graphies.** 13 familles sur 142 libellés
de collectivités : `CONSEIL DEPARTEMENTAL DE LA SOMME` / `DEPARTEMENT DE LA
SOMME`, `VILLE DE TOULOUSE` / `MAIRIE DE TOULOUSE`, `COMMUNE D IFFENDIC` /
`COMMUNE DE IFFENDIC`. La clé comparait ces libellés tels quels, donc deux
publications d'une même collectivité ne se croisaient jamais.
`identite_donateur` lit la forme juridique pour en tirer le niveau, les mots
restants pour le noyau — `donor_name_raw` n'est jamais retouché.

**2. Les directions prises pour des donateurs.** « Direction des Finances et
des Achats — Ville de Paris » est un service, pas une personne morale. La
coupe se fait au DERNIER mot de forme, et seulement sur « direction » : un
CCAS, une régie ou un syndicat sont des entités distinctes de leur commune.

**3. Paris, avant et après la fusion.** La loi n° 2017-257 du 28 février 2017
fusionne la commune et le département de Paris dans la collectivité unique
« Ville de Paris » — art. 8 pour l'entrée en vigueur au 1er janvier 2019,
art. 10 pour la substitution dans tous les droits et obligations. La donnée
publiée le confirme : la colonne `collectivite` de la Ville porte les deux
collectivités jusqu'en 2018, puis une seule. **Avant 2019, les distinguer est
la vérité de l'époque** : chacune avait son budget. `FUSIONS_COLLECTIVITES`
porte la règle avec sa date d'effet.

**4. La clé prenait le SIRET avant le nom.** Deux sources ne publiant pas les
mêmes identifiants, la même subvention recevait deux clés : le Théâtre Musical
de Paris, 17 446 000 € en 2013, était compté deux fois. Le nom passe en
premier, le SIRET ne servant qu'à défaut.

**5. Le garde-fou des homonymes.** Ce choix a un revers, mesuré avant d'être
adopté : 5 605 groupes réunissent des organismes HOMONYMES mais distincts —
« MAISON FAMILIALE RURALE » en Mayenne, plusieurs OGEC « Collège Saint-Joseph »
en Maine-et-Loire — même année, même montant rond, même objet générique. La
déduplication ne fond donc jamais un groupe aux SIRET contradictoires : les
fondre EFFACERAIT une subvention réelle. `verify.py` exige que tout doublon
résiduel s'explique ainsi.

**6. Les articles ne sont pas des formes juridiques.** Les retirer fondait
`COMMUNE DE BAULE` (Loiret) et `COMMUNE DE LA BAULE` (La Baule-Escoublac,
Loire-Atlantique) en une seule commune. Seules les prépositions sont retirées,
pour l'élision ; l'article reste dans le nom.

**7. La source héritée `paris` est retirée.** Elle déclarait son propre amont
— `opendata.paris.fr`, subventions votées — que le moissonneur reprend
désormais en entier (107 693 lignes contre 76 207). Mais sa conversion
écrasait le donateur : « Département de Paris » sur toutes les années jusqu'à
2023, quand la Ville n'écrit plus jamais « Département » après 2018. 87,6 % de
ses 30 422 lignes de 2013-2018 avaient une jumelle exacte étiquetée « Ville »
dans le jeu moissonné. L'erreur portant sur le donateur, qui FAIT PARTIE de la
clé, la déduplication ne pouvait pas la voir.

### Ce que cela change, mesuré

| | phase 6a | phase 6b |
|---|---|---|
| Lignes conservées | 2 769 440 | 2 690 242 |
| Total individuel | 161,67 Md€ | 157,68 Md€ |
| Doublons rattrapés | 757 411 | 760 402 |
| Homonymes protégés d'une fusion abusive | — | 2 480 groupes |

Le symptôme qui trahissait le double comptage a disparu : Paris tombait de
490 M€ en 2018 à 291 M€ en 2019, pile à la date de la fusion. La série est
maintenant continue — 271 M€ puis 291 M€ — et la répartition colle à ce que
publie la Ville, 1 213 à 1 376 lignes « département » par an contre 1 232 à
1 408 publiées.

### Ce qui reste

- **Dépivoter les tableaux par année** — ~178 fichiers publient une colonne
  par exercice au lieu d'une ligne par versement.
- **Les liens morts en amont** — 236 réponses 404 et 135 échecs de connexion
  chez `datacat.datalocale`. Rien à corriger chez nous ; à re-tenter.
- **`cd-finistere`** — 5 442 lignes au nom de donateur détruit (U+FFFD dans
  le fichier hérité). Irrécupérable ici : il faut re-moissonner l'amont.
- **Les quarantaines Lyon et Boulogne** — `data.grandlyon.com` renvoie 401,
  l'amont n'est pas vérifiable sans habilitation.

---

## Phase 7 — L'unité, les doublons de ressources et les portails (20/08/2026)

Phase courte, née d'une relecture de `RESTE-A-FAIRE.md` : trois de ses
estimations ne tenaient pas devant les manifestes, et l'ordre qu'il
recommandait envoyait droit sur le chantier le moins rentable. Les mesures
d'abord, le code ensuite.

### 1. L'anomalie 2011 : la virgule de la source

L'exercice 2011 pesait **12,54 Md€, soit 6,7 fois ses voisins** — 8 % du total
affiché, jamais élucidé depuis la phase 1a. C'est le Jaune PLF 2013, et lui
seul : 21 167 lignes, 12,30 Md€.

Quatre indices concordants, tous internes à la donnée :

| Indice | Constat |
|---|---|
| Terminaison | **100,0 %** des 21 127 montants sont multiples de 10, contre 75,9 % au millésime suivant |
| Rapport par SIREN | le rapport 2011/2012 pique **exactement à 10,0** (654 SIREN) |
| Un cas nominal | l'Orchestre de Paris : 9 278 494 € en 2010, **92 784 940 €** en 2011, 9 278 494 € en 2012 |
| Une unité connue | un poste Fonjep (~7 107 €) y figure à **71 070 €** |

Divisé par dix, le montant moyen par ligne tombe à 58 102 € contre 58 240 € en
2012. Tout dit le facteur dix.

**L'erreur n'est pas la nôtre** : interrogée directement, l'API amont
(`data.economie.gouv.fr`, champ `subvention_2011_en_euros`, type `double`)
stocke bien 92 784 940. Ce n'est ni notre conversion, ni un artefact d'export.

Mais savoir qu'un chiffre est faux ne dit pas quel est le vrai. Diviser par dix
resterait une correction de montant décidée par nous, ce que la doctrine
interdit. **Quarantaine, donc, exactement comme `metropole-lyon`** : montants
dans `amount_rejected_eur`, lignes conservées et consultables, drapeau
`amount_unit_suspect`, `UNITE_DOUTEUSE` dans `normalize_plf_jaune.py`.
Réversible le jour où le publieur corrige son millésime.

### 2. Le même fichier ingéré cent fois

Le jeu de Grenoble-Alpes Métropole porte chez data.gouv.fr **1 044 ressources
pour neuf fichiers réels** : le moissonnage du portail les ré-inscrit à chaque
passage. `fetch_scdl.py` les prenait une par une — 524 téléchargements, puis
524 entrées dans la table sous 524 `source_id` distincts. Après déduplication
il en restait **91 sources fantômes, dont 85 ne portant plus qu'une ligne**.

Deux effets, tous deux invisibles jusqu'ici :
- le décompte « 630 sources » était gonflé d'une centaine de fantômes ;
- surtout, ces copies n'avaient **aucune année** (Grenoble ne la met que dans
  le nom du fichier), donc leur clé métier ne pouvait pas rencontrer celle de
  la source héritée `metropole-grenoble`, qui l'a. **72,5 M€ comptés deux fois.**

`ressources_csv` regroupe désormais les ressources par nom de fichier — mais
seulement pour les fichiers hébergés par la collectivité : sur
`static.data.gouv.fr`, chaque ressource est un dépôt distinct et deux
millésimes y portent souvent le même nom. Une empreinte SHA-256 sert de dernier
filet.

### 3. Les adresses périmées, essayées dans l'ordre

235 des 371 « liens morts » du backlog étaient des 404 chez
`data.metropolegrenoble.fr`. Le portail répond pourtant : il a réorganisé ses
chemins et data.gouv.fr garde les anciens. Plutôt que de deviner la règle de
réécriture, `telecharger()` essaie **toutes les adresses connues du fichier**,
de la plus récente à la plus ancienne. Aucune n'est privilégiée — la plus
récente n'est pas forcément la bonne.

Neuf fichiers Grenoble récupérés sur neuf, et au passage un jeu de
**236 842 lignes** qui échouait depuis la phase 4.

### 4. Quatre graphies de colonnes en plus

Toutes dans `common.py`, donc partagées par les trois familles :

| Motif | Ce qu'il rouvre |
|---|---|
| `("total", "euros")` | `total_en_euros`, `total_euros` — trois millésimes de Grenoble |
| `("tiers",)` | le bénéficiaire nommé `tiers` tout court |
| `("bp", EXERCICE)`, `("ca", EXERCICE)` | `bp_2012`, `ca_2013` — 24 jeux rennais, 4 070 lignes |
| `("avantages", "nature")` | dit la vraie raison d'écarter une valorisation |

`EXERCICE` est un jeton de motif qui n'apparie que les mots formant une année
plausible. C'est ce qui rend `("ca", EXERCICE)` sûr là où `("ca",)` seul
attraperait n'importe quoi.

### 5. L'année lue dans le libellé

**160 sources, 160 210 lignes et 4,1 Md€ n'avaient aucune année** : leur
publieur sort un fichier par exercice et ne répète pas l'année dans les lignes.
`annee_du_libelle` la lit dans le nom du fichier puis dans le titre du jeu, et
**n'accepte qu'une seule année distincte** — « Subventions 2008-2012 » reste
sans année, deviner serait inventer. `year_provenance` passe à `inferred` et
le drapeau `year_from_label` marque les lignes.

Effet : **120 796 lignes** datées, `year_missing` de 169 105 à 45 107. Et
comme l'année fait partie de la clé métier, la déduplication voit enfin des
rapprochements qu'elle manquait.

### 6. Trente portails Opendatasoft de plus — et un résultat négatif

`fetch_ods.py` passe de 11 à 41 portails, repérés en demandant au fédérateur le
domaine d'origine de chacun de ses jeux « subvention ». Cinq domaines sont
morts et ne sont pas inscrits (`data.corsica` et `opendata.sqy.fr` en 410,
`opendata.pau.fr` en 404, `ville-soissons.fr` et `opendata.roubaix.fr` en
défaut de certificat).

Gain : 463 → 574 jeux examinés, **273 → 371 retenus**.

**Gain de couverture : zéro.** Pas une commune, pas un EPCI, pas un département
de plus — le fédérateur republiait déjà tout ce que ces portails publient. Les
communes de Grand Paris Sud, par exemple, ont bien leur portail, mais le
donateur y est l'agglomération, pas la commune. C'est un résultat négatif, et
il vaut d'être écrit : **le gisement Opendatasoft est épuisé**, il ne faut plus
en attendre de couverture.

### Le bilan chiffré

| | phase 6b | phase 7 |
|---|---|---|
| Lignes | 2 690 242 | **2 687 791** |
| Total individuel | 157,68 Md€ | **144,71 Md€** |
| Sources | 630 | **548** |
| dont ≤ 2 lignes | 114 | **40** |
| Jeux ODS retenus | 273 | **371** |
| Fichiers SCDL retenus | 788 | **272** |
| Lignes sans année | 169 105 | **45 107** |
| Bénéficiaires résolus | 406 280 | **406 846** |
| Cumulant ≥ 3 échelons | 6 739 | **6 783** |
| Contrôles `verify.py` | 30/30 | **30/30** |

Les 13 Md€ de baisse sont la quarantaine 2011, et rien d'autre : ce sont des
euros qui n'auraient jamais dû être affichés. La vitesse ne bouge pas
(banc `phase7` : 0,14 Mo, 0,07 s au premier affichage, 3 Mo de mémoire).

---

## Phase 8 — Ce qui est un don, et ce qui ne l'est pas (21/08/2026)

Deux décisions de doctrine, prises par l'utilisateur après mesure. Aucune
donnée n'a été moissonnée : tout vient de ce que le corpus disait déjà.

### 8a. Deux totaux plutôt qu'un arbitrage caché

La règle « versé ⇒ hors totaux » évitait de compter deux fois l'argent d'une
collectivité qui publie ce qu'elle a voté PUIS ce qu'elle a mandaté. Mesurée,
elle retirait **1,86 Md€ que rien ne dédoublait** : sur les 99 837 lignes
écartées, 46 202 n'avaient aucune contrepartie « attribué » du même donateur et
du même exercice. Le département de Loire-Atlantique — 778,3 M€, 28 573
subventions, toute sa présence dans le corpus — n'apparaissait donc nulle part.

Le site affiche maintenant **142,59 Md€ de dons votés** et **7,45 Md€ de dons
payés**, côte à côte, jamais additionnés. `compte_dans_les_totaux` reste le
voté ; `est_un_don`, sans la mesure, donne les deux.

Limite assumée : aucune des sources d'exécution budgétaire ne donne l'adresse
du bénéficiaire. Les 99 771 versements « payés » sont TOUS sans département —
ils se lisent au national, pas sur la carte.

### 8b. Quatre natures de concours, une seule est un don

« Prestation facturée par l'association » — 89 948 lignes, 1,12 Md€ — n'est pas
un don : la collectivité achète un service, il y a une contrepartie.
`nature_du_concours` distingue `don`, `prestation`, `remboursement` et `nature`
(aides en nature : locaux, personnel). **128 700 lignes et 2,19 Md€** sortent
des totaux, restent ingérées et consultables, et affichent leur motif sur la
fiche de l'association.

L'appariement se fait sur des **suites de mots**, jamais sur des sous-chaînes :
« SOUTIEN AUX MANUFACTURES ET MÉTIERS D'ART » contient les lettres de
« factur- », « DÉMARCHE QUALITÉ » celles de « marche ». Trois motifs ont été
écartés après relecture du corpus — « achat » (« subvention pour achat d'actif
immobilisé » finance un achat FAIT PAR l'association), « honoraires », et
« délégation » seul (« 2ᵉ délégation » est une tranche de crédits).

### 8c. Ce qui n'a PAS été fait, et pourquoi

Le correctif qui motivait ce chantier — ramener « _ » et « - » à l'espace dans
`measure_of` — **n'a pas été appliqué**. Mesuré : 2 sources, 8 lignes,
850 244 €, toutes sans contrepartie, donc toutes à perte. Et il n'attrapait même
pas le cas de Grenoble qui l'avait motivé, le motif étant un bigramme et non un
mot. Détail dans `RESTE-A-FAIRE.md` §4.

### 8d. Contrôles

33 contrôles dans `verify.py`, dont trois nouveaux : les deux totaux servis au
navigateur sont comparés à la table canonique, et une partition vérifie que
chaque ligne tombe dans une case et une seule (2 382 140 votés + 99 771 payés
+ 128 700 hors don + 20 973 agrégats + 56 207 hors champ = 2 687 791).

---

## Phase 9 — Le gisement rouvert par le bon bout (22/08/2026)

La phase 7 avait conclu que les deux canaux de moissonnage étaient épuisés.
Elle avait tort, et la raison est une leçon de méthode : **elle cherchait à
partir des portails connus**. En cherchant à partir des collectivités
ABSENTES — les 30 plus grosses communes sans aucune donnée, dont on fabrique
les adresses de portail plausibles — on trouve tout autre chose.

### 9a. Trois blocages, trouvés en cherchant autrement

1. **Six portails Opendatasoft inconnus du fédérateur** : Bordeaux Métropole,
   les départements des Hauts-de-Seine et de l'Aude, Grand Paris Seine Ouest,
   Issy-les-Moulineaux, Bourges Plus. 185 domaines sondés pour les trouver.
2. **Un filtre d'adresse perdait 333 jeux de 63 organisations**, sans laisser
   de trace ni dans les retenus ni dans les écartés. `ressources_csv` exigeait
   qu'une adresse finisse par « .csv » ; les points d'export d'API
   (`.../exports/csv`, `.../download/`) n'y répondent pas et servent pourtant
   de vrais fichiers.
3. **`openpyxl` n'était pas installé** sur la machine de moissonnage : 110
   fichiers XLSX écartés sous un motif noyé au milieu des vraies raisons.

### 9b. Ce que ça donne, pipeline entièrement rejoué

| | phase 8 | phase 9 |
|---|---|---|
| Jeux retenus data.gouv.fr | 148 | **377** (504 fichiers) |
| Jeux retenus Opendatasoft | 371 | **407** |
| Sources | 548 | **655** |
| Lignes | 2 687 791 | 2 540 282 |
| Dons votés | 142,59 Md€ | **127,80 Md€** |
| Dons payés | 7,45 Md€ | **10,02 Md€** |
| Communes / EPCI / départements / régions | 86 / 29 / 31 / 5 | **90 / 31 / 34 / 7** |
| Associations à 3 échelons ou plus | 6 783 | **9 613** |
| Contrôles | 32/33 | **33/33** |

**Le total baisse en gagnant 107 sources, et c'est le signe que ça marche** :
la déduplication passe de 580 321 à 1 064 346 lignes retirées (85,86 Md€). Les
jeux rouverts republient en grande partie ce que le site avait déjà ; la clé
métier les rapproche au lieu de les compter deux fois.

### 9c. Trois millésimes du Jaune récupérés

`openpyxl` manquant coûtait aussi trois millésimes de l'annexe Jaune : PLF 2019,
2021 et 2023, soit les exercices **2017, 2019 et 2021** — 23,6 Md€ de
subventions d'État absentes du site. Installé puis remoissonné, le Jaune passe
de 10 à **13 millésimes sur 14**, et sa série devient continue de 2010 à 2023
(2 110 M€ en 2014, 5 322 en 2017, 7 735 en 2019, 10 543 en 2021, 11 766 en
2023). Seul l'exercice 2022 manque : le fichier du PLF 2024 est vide à la
source.

C'est ce qui explique que le total remonte à **149,68 Md€** après être descendu
à 127,80 : la déduplication retire d'un côté ce que les millésimes retrouvés
ajoutent de l'autre.

### 9d. Ce qui n'est pas un défaut de moissonnage

Nice, Montpellier, Strasbourg et Toulon ne publient pas leurs subventions —
vérifié sur leur portail ET sur data.gouv.fr. Strasbourg et Angers ont un
portail ouvert avec zéro jeu de subventions. Leur absence est une absence de
publication, et c'est à ce titre que le site doit la dire.

---

## Phase 10 — Le dénominateur, l'angle mort et l'échelle (22/08/2026)

**Le problème que cette phase règle.** Depuis la phase 1, le site répond à
« qui a reçu quoi » parmi ce qu'il a trouvé. Il ne savait répondre ni à
« combien manque-t-il ? » ni à « par rapport à quoi ? ». La carte de couverture
était binaire — une commune absente pouvait aussi bien ne rien verser que ne
rien publier — et le total affiché, 149,68 Md€ cumulés, n'avait aucune échelle.

La phase 9 avait établi que le moissonnage de l'open data volontaire était
épuisé. La sortie n'était donc pas de chercher plus de subventions nominatives,
mais de changer de question : **mesurer ce qui manque**.

**Règle qui gouverne toute la phase : aucun de ces chiffres n'entre dans les
totaux du site.** Aucun ne nomme de bénéficiaire ; les sommer avec les
versements nominatifs compterait deux fois le même argent. `verify.py` ne
vérifie donc pas ici une somme mais une SÉPARATION.

### 10a. Le dénominateur — compte 6574 des balances comptables DGFiP

La comptabilité officielle de toutes les collectivités, publiée exercice par
exercice sur `data.economie.gouv.fr`, qu'elles fassent de l'open data ou non.
19 jeux, 565 916 lignes, licence ouverte.

| Échelon | Exercices | Déclarent | Déclaré | Le site en connaît |
|---|---|---|---|---|
| Communes | 2010-2025 | **34 829** / 34 936 | **51,10 Md€** | 7,60 Md€ — **14,9 %**, par 82 communes |
| Intercommunalités | 2019-2025 | 1 278 / 1 335 | 16,84 Md€ | 1,91 Md€ — 11,4 % |
| Départements | 2019-2025 | 100 / 101 | 11,81 Md€ | 4,32 Md€ — 36,6 % |
| Régions | 2020-2025 | 14 / 18 | 14,23 Md€ | 12,96 Md€ — 91,1 % |

Trois réserves indissociables du chiffre : le compte dit « et autres personnes
de droit privé » (il surestime), une subvention peut être imputée ailleurs —
6568, 657362 vers un CCAS, investissement au 204 — (il sous-estime), et le
déclaré est MANDATÉ quand les totaux du site sont VOTÉS. Une part au-dessus de
100 % est donc normale.

Quatre pièges, tous documentés dans `CLAUDE.md` : `like '6574%'` n'est pas un
préfixe en ODSQL ; la colonne `insee` n'est pas le code INSEE ; un budget
annexe ne nomme pas sa collectivité mais porte son SIREN (d'où un appariement
en deux passes, 12 002 lignes non rattachées au lieu de 227 038) ; et les
collectivités uniques — Corse, CTU, Alsace, Mayotte — n'ont pas de SIREN en 22.

**Résultat négatif à retenir** : la présentation croisée nature-fonction ne
peut pas prolonger la série avant 2019. Vérifié sur 2020, où les deux
présentations coexistent — elle ne couvre que les collectivités au-dessus du
seuil de la présentation fonctionnelle (communes : 2 438 M€ contre 3 044).

### 10b. L'angle mort — les comptes annuels déposés au Journal officiel

227 586 dépôts, **31 683 organismes** tenus de déposer parce qu'ils franchissent
153 000 € de dons et/ou de subventions (art. L612-4 et D612-5 du code de
commerce). Croisés par SIREN et RNA avec l'index des bénéficiaires :
**18 745 reconnus, 12 938 non reconnus** — 40,8 %.

Le croisement se valide lui-même, et c'est ce qui rend le chiffre publiable :

| Nature | Organismes | Reconnus |
|---|---|---|
| Associations loi 1901 | 26 843 | **67,9 %** |
| Fonds de dotation | 3 669 | **3,5 %** |
| Fondations | 740 | 40,4 % |

Les fonds de dotation vivent de dons privés : qu'ils soient invisibles du site
est la preuve que le seuil de 153 000 € mélange argent privé et argent public.
Le nombre d'organismes non reconnus est donc un **majorant**, jamais « les
associations subventionnées que le site rate ». Les plus gros déposants non
reconnus sont des comités de la Ligue contre le cancer et des associations
diocésaines.

Aucun montant n'est lu : ils sont dans des PDF scannés (2 sur 24 contiennent le
mot « subvention » en clair), et les extraire par OCR afficherait un chiffre
deviné par une machine sur une image.

### 10c. L'échelle — D751 des comptes nationaux

| Exercice | Comptes nationaux (D751) | Le site retrouve | Part |
|---|---|---|---|
| 2015 | 32,3 Md€ | 3,8 Md€ | 11,8 % |
| 2019 | 35,8 Md€ | 15,5 Md€ | 43,2 % |
| 2021 | 40,0 Md€ | 21,6 Md€ | 53,9 % |
| 2023 | **45,6 Md€** | **24,0 Md€** | **52,6 %** |

Exercice par exercice, jamais en bloc : le total du site est un cumul, D751 un
flux annuel. La page de méthode signale d'elle-même le creux de 2022 — l'annexe
Jaune y manque, ce n'est pas une baisse des subventions.

### 10d. Un faux positif corrigé au passage

En construisant le dénominateur, le même appariement a buté sur les SIREN de
régions. `build_couverture.py` en déduisait un code de région, ce qui n'existe
pas : le SIREN d'une région est bâti sur son chef-lieu. La Nouvelle-Aquitaine
s'affichait « données présentes » avec zéro versement et zéro euro. **Le site
couvre 6 régions, pas 7.** La règle des départements, elle, est juste et ne
vit plus qu'à un seul endroit (`code_departement_du_siren`), où elle gagne
l'outre-mer et Mayotte : 15 départements rattachés par SIREN au lieu de 3.

### 10e. Ce que le site en montre

- « Ce qu'on ne sait pas » : deux sections nouvelles — le dénominateur par
  échelon, par exercice et par département ; l'angle mort avec sa ventilation
  par nature d'organisme.
- « Sources & méthode » : la section « Par rapport à quoi ? ».
- L'accueil : une phrase, chargée après le premier écran pour ne rien coûter
  au chemin critique.
- `verify.py` : 11 contrôles de plus, **44/45**.
- Et la carte elle-même (10f).

### 10f. La carte cesse d'être binaire (22/08/2026)

Le dénominateur était calculé et tabulé, mais la carte continuait de peindre
trois états. Elle a désormais deux vues sous une bascule : « ce qui est
publié » et « ce qui nous échappe ».

**Six paliers, pas un dégradé continu** — et la raison est dans la donnée : sur
101 départements, **59 sont à zéro**, 13 sous 1 %, trois au-dessus de 50 %. Une
échelle linéaire aurait rendu 85 départements de la même teinte pâle. Les
bornes suivent la distribution mesurée, elles ne sont pas rondes par esthétique.

**Le zéro n'est pas le bas de l'échelle** : il garde un gris récessif, comme
« aucune donnée » dans l'autre vue. Dire « le site n'en connaît rien » avec le
bleu le plus clair l'aurait fait passer pour un petit quelque chose.

**Le tableau bascule avec la carte.** La règle d'accessibilité de la page —
une couleur ne porte jamais seule l'information — vaut aussi pour la vue
nouvelle : sans cela, l'échelle continue n'aurait pas eu d'équivalent écrit.
L'infobulle et l'`aria-label` portent le montant déclaré, le montant connu et
le nombre de communes.

Ce que la carte montre et qu'aucun tableau ne disait aussi vite : la Bretagne
et l'Ille-et-Vilaine bien couvertes, Paris et les Bouches-du-Rhône au-dessus de
45 %, et tout un quart nord-est à zéro.

### 10g. Une fiche pour chaque commune de France (22/08/2026)

Le dénominateur disait « ce département est à 3 % » ; il ne disait rien d'une
commune en particulier. Les 34 829 communes déclarantes sont désormais
consultables une par une, sur `couverture.html`.

**Il n'existe plus une seule commune sur laquelle le site n'ait rien à dire.**
34 829 sur 34 936 déclarent un compte 6574 ; 82 seulement sont connues
nommément. Pour les 34 751 autres, la fiche dit ce que personne ne disait :
« cette commune a mandaté X € à des associations, et nous n'en connaissons
aucune ligne — la lacune est du côté de la publication, pas du versement ».

101 fichiers, médiane 21,8 Ko gzippés, chargés à la demande : le premier écran
n'en porte rien. Sélection en deux temps (département puis commune) plutôt
qu'une recherche par nom, dont l'index pèserait 274 Ko mesurés.

**Le piège que ce chantier existe pour éviter.** Les fragments
`data/aggregates/departements/` décrivent les associations SITUÉES dans un
département — des bénéficiaires. La fiche communale décrit la commune qui
PAIE. Afficher les deux au même endroit ferait lire de l'argent versé comme de
l'argent reçu ; c'est pourquoi la fiche n'est pas sur la carte d'accueil.

Deux corrections que la spécification n'avait pas prévues :

- **« 0 M€ » là où il y avait une subvention.** Le formatage arrondissait tout
  en millions : Rennes 2016 (10 k€ connus) et 2017 (125 k€) s'affichaient
  comme rien. Il descend maintenant au millier puis à l'euro.
- **Une année absente n'est pas une fusion.** Il était prévu d'écrire « la
  série commence en 2019, le plus souvent parce que la commune est née d'une
  fusion » — une devinette, et le plus souvent fausse. La balance ne porte une
  ligne que si le compte a servi. La fiche énonce les trois causes possibles
  au lieu d'en choisir une.

Quatre contrôles de plus : aucune commune perdue au découpage, chacune dans son
département, toutes au référentiel, et la somme des fichiers servis égale le
détail canonique. **48/49.**

### 10h. L'angle mort, classé plutôt qu'énuméré (22/08/2026)

`RESTE-A-FAIRE.md` §5c demandait d'examiner 3 220 déposants non reconnus un par
un. L'utilisateur a répondu ce qu'il fallait répondre : « je ne peux pas traiter
à la main 3 200 éléments ». **Le chantier était mal posé** — une liste n'était
pas le livrable.

Les 12 938 organismes non reconnus sont désormais rangés sous six causes,
toutes lues dans une donnée existante, aucune devinée :

| Cause | Organismes | Part |
|---|---|---|
| Reconnu par nom + département, sans identifiant commun | 157 | 1,2 % |
| Fonds de dotation ou fondation — vit de dons privés | 3 967 | 30,7 % |
| Nom connu du site, mais dans un autre département | 531 | 4,1 % |
| Aucun financeur ne publie sur ce territoire | 755 | 5,8 % |
| Territoire dont le site connaît moins de 1 % du 6574 communal | 3 430 | 26,5 % |
| Aucune explication automatique | 4 098 | 31,7 % |

**68,3 % des absences s'expliquent seules.** Le reste est présenté pour ce
qu'il est : la mesure de ce qu'on ignore, avec la phrase qui va avec — aucune
donnée publique ne permet de savoir si un organisme donné reçoit de l'argent
public.

Deux résultats négatifs mesurés en chemin : apparier sur NOM + DÉPARTEMENT ne
récupère que 157 organismes (1,2 %), donc l'angle mort n'est pas un artefact
d'appariement ; et les jeux `osop-*` du portail DILA ne couvrent que les
syndicats, leur champ `ressources` étant une tranche et non une origine.

Un piège de raisonnement évité au passage : classer une absence en « le site
devrait le connaître » parce qu'un financeur publie dans le département
sur-affirme — la Région publie, mais c'est la commune qui verse. D'où le palier
« moins de 1 % du 6574 communal », qui explique à lui seul 3 430 absences.

---

## Phase 12 — Rennes : le voté cesse d'être son propre compte administratif (23/08/2026)

La phase 11 laissait une trentaine de jeux de la Ville de Rennes écartés,
~20 000 lignes, annoncés comme « du gain en profondeur ». **Les fichiers étaient
déjà dans le site, et mal classés.**

### Deux défauts, tous deux dans la lecture, pas dans le moissonnage

**« CA 2014 » est un compte administratif.** `measure_of` ne reconnaissait
« compte administratif » qu'en toutes lettres, et la Ville de Rennes ne l'écrit
jamais autrement. Le site comptait donc le budget primitif ET son exécution du
même exercice comme deux subventions VOTÉES : Rennes 2012 pesait 74,56 M€ pour
un budget associatif d'environ 54 M€. Mesuré sur tout le corpus : **1 828
lignes, 227,2 M€**, chez Rennes, Lorient Agglomération et la CC du Val
d'Essonne. Le sigle seul serait bien trop court — c'est l'exercice accolé qui
fait la preuve, comme pour le motif de colonne `("ca", EXERCICE)`.

**Un compte de publication servait de donateur.** Les fichiers budgétaires de la
Ville de Rennes sont déposés sur data.gouv.fr par un compte nommé « Rennes
Métropole en accès libre ». Faute de colonne d'attribuant, le site créditait
**l'EPCI de 396 M€ versés par la COMMUNE**, et ces lignes ne se dédupliquaient
pas avec la même donnée publiée sur le portail : deux donateurs, donc deux clés
métier. `collectivite_du_libelle` lit le titre du jeu et ne retient QUE ce qui
correspond exactement à un nom du référentiel INSEE ; un titre qui ne nomme
personne laisse le donateur non attribué.

| | phase 11 | phase 12 |
|---|---|---|
| Lignes | 2 817 042 | **2 811 070** |
| Sources | 681 | **698** |
| Communes | 94 | **95** |
| EPCI | 32 | **31** |
| Dons votés | 148,34 Md€ | **148,40 Md€** |
| Dons payés | 10,04 Md€ | **10,43 Md€** |
| Cumuls ≥ 3 échelons | 10 128 | **9 566** |
| Contrôles | 50/50 | **50/50** |

### La couverture perd un EPCI, et c'est juste

Rennes Métropole n'a **jamais rien publié en propre** : tout ce qui lui était
crédité était l'argent de la Ville. Elle repasse de « données présentes » à
« publie mais non exploité ». Le site affirmait couvrir la métropole quand il ne
couvrait que sa ville-centre.

Les cumuls à trois échelons tombent de 562 pour la même raison. Comparaison
**exacte** des deux index de recherche : 567 bénéficiaires passent sous trois
échelons, dont **554 (97,7 %) en perdant précisément leur échelon EPCI**, avec
pour motifs dominants « commune,epci,inconnu » (328) et « commune,epci,etat »
(177). Ces cumuls n'existaient pas.

La série rennaise est enfin lisible : 53,78 M€ votés en 2012, 55,32 en 2013,
56,24 en 2014, 56,34 en 2015, 59,60 en 2016, 63,91 en 2017, 50,20 en 2018 — avec
leur exécution à côté. Avant, 2011, 2013 et 2014 n'existaient que par leur compte
administratif compté comme du voté, et 2015 et 2018 manquaient tout à fait.

### Effets de bord, tous des corrections

Besançon entre dans la couverture (4 050 lignes, 148,59 M€), rendu à sa commune
au lieu de rester chez « Open Data Bourgogne ». Et **421,54 M€ de la DRAC des
Pays de la Loire** repassent de « région » à « État » : le repli par nom
cherchait « region » en sous-chaîne, et « Direction **région**ale des affaires
culturelles » l'attrapait. Une région ne s'appelle jamais « direction ».

### Un invité imprévu, gardé

Le motif `libelle` — strict, en dernier recours — est nécessaire aux budgets
primitifs de Rennes. Il ouvre du même coup les financements de la DRAC des Pays
de la Loire : **9 988 lignes, 363,66 M€** d'État. Son bénéficiaire est concaténé
avec l'objet (« O CAPITAINE MON CAPITAINE - Aide au projet Arts de la Rue
pour… »), donc inutilisable pour le rapprochement. Gardé : l'erreur va vers la
fragmentation d'une association en plusieurs, qui est une lacune, et non vers la
fusion de deux organismes, qui serait un mensonge.

### Ce qui reste dehors, mesuré

Les comptes administratifs 2008-2010 de Rennes, ~13 000 lignes. **Deux
millésimes du même publieur donnent aux mêmes noms de colonnes des sens
opposés** : en 2009, `provisions_par_tiers` porte le détail et
`total_des_mandats_emis` l'agrégat, proprement séparés (les 93 lignes de détail
commencent par « . », les 52 lignes de total non) ; en 2010, **414 des 461**
lignes de `total_des_mandats_emis` sont au contraire des versements individuels,
pour 125 M€ sur un fichier de 1 920 lignes. Aucun choix de colonne unique n'est
défendable.

---

## Phase 11 — Les jeux écartés, et ce qu'ils ont cassé en entrant (23/08/2026)

`RESTE-A-FAIRE.md` §1d désignait le dernier gisement qui ne dépende de
personne : les fichiers que les moissonneurs ont déjà vus et rejetés. Trois
correctifs de reconnaissance, annonçait-il, pour ~91 jeux dont 69 seraient la
Ville de Rennes — « du gain en profondeur, pas en couverture ».

**L'énoncé était faux sur ses trois points.** Deux des trois correctifs
(`beneficiare`, `organismes`) avaient été appliqués par la phase 9 sans que le
paragraphe soit relu. Son inventaire datait du 21/08, avant le re-moissonnage.
Et ses « deux communes de Haute-Garonne vraiment nouvelles », Fronton et
Labarthe-sur-Lèze, publient **zéro ligne** : le jeu est vide à la source.

### Ce qui a été fait

Inventaire refait sur les manifestes du jour, candidats **vérifiés sur la donnée
téléchargée** et non sur le seul libellé de colonne, puis mesurés sur les 824
en-têtes connus des deux manifestes. Sept graphies ajoutées : `liborgabenef` et
`mtsubv` (Région Île-de-France), `mandate` (Maine-et-Loire, GrandSoissons, Grand
Paris Sud), `organisation` (Montreuil), `destinataire(s)` (Saint-Maur-des-Fossés)
et `associations` — le singulier était reconnu depuis toujours, le pluriel non.

| | phase 10 | phase 11 |
|---|---|---|
| Lignes | 2 809 711 | **2 817 042** |
| Sources | 658 | **681** |
| Communes | 90 | **94** |
| EPCI | 31 | **32** |
| Départements | 34 | **35** |
| Cumuls ≥ 3 échelons | 9 800 | **10 128** |
| Contrôles | 49/50 | **50/50** |

Nouvelles : Aix-en-Provence (12,66 M€), Saint-Maur-des-Fossés (3,71 M€),
Fleury-sur-Orne, Moissy-Cramayel, GrandSoissons Agglomération (2,18 M€) et le
**département de la Seine-Maritime** (973 lignes, 33,74 M€).

### Le total voté baisse de 1,34 Md€, et c'est une correction

Une même colonne ne peut pas être à la fois le bénéficiaire et le montant.
Six fichiers déjà retenus l'étaient ainsi — le titre du rapport lu comme un
en-tête. La Chambre de Commerce Seine Mer Normandie publiait un bénéficiaire
« 911671485 » pour 911 671 485 € et « W761003097 » pour 761 003 097 € : un SIREN
et un RNA lus comme des euros, **1,67 Md€ de faux**. C'était l'origine du cas que
le rapport de qualité signalait depuis la phase 6b sans en connaître la cause ;
`nom_de_beneficiaire_numerique` tombe de 1 798 M€ à 125 M€.

### Trois autres défauts, révélés par l'ouverture

Rouvrir des jeux fait entrer des fichiers que le reste de la chaîne n'avait
jamais eu à lire.

- **Un en-tête lu sur une ligne de données.** `organisation;montant;thematique;type`
  (Montreuil) ne porte qu'un mot-repère quand chacune de ses lignes en porte deux.
  La première ligne, quand elle est déjà un en-tête valide, gagne désormais —
  mesuré sur les 935 fichiers bruts, 4 changent, tous des corrections.
- **Un donateur lu dans une colonne de code.** `Code Collectivité` chez
  GrandSoissons ne contient que « 1 ». Corrige au passage la Ville de Soissons,
  déjà présente.
- **Un publieur qui est un service.** Saint-Maur publie sous « Direction des
  sports » ; le repli du donateur remonte maintenant à l'éditeur du portail.

Et une contradiction levée : le même fichier de Fleury-sur-Orne était « voté »
côté portail (`subventions_versees`) et « payé » côté data.gouv.fr
(« Subventions versées »). Les séparateurs sont ramenés à l'espace dans
`measure_of`, et là seulement.

### Deux correctifs écartés, et un arbitrage renvoyé

`total` nu ferait entrer Blois 2020-2022, dont la colonne de noms s'appelle
littéralement `empty` et dont la colonne `associations` ne porte que le code
« P1 ». `somme` nu n'ouvre que des comptes administratifs de Rennes, que
`measure_of` étiquetterait « voté » alors qu'un CA est de l'exécution.

Enfin, le Département de Maine-et-Loire **ne publie plus le nom de ses
bénéficiaires depuis 2017** : 1 781 lignes, 22,1 M€, dont 96,9 % ont un SIRET et
aucune raison sociale. Le pipeline écarte les lignes sans nom ; les récupérer sur
le seul SIRET est un arbitrage de doctrine, laissé à l'utilisateur.

### Le gisement de reconnaissance est épuisé

Sur les 172 jeux ODS encore écartés, **8 passeraient les règles actuelles et
tous portent zéro ligne**. Ce qui reste tient en trois familles, aucune
récupérable sans deviner : les comptes administratifs de la Ville de Rennes
(~20 000 lignes, montants nommés `total_des_mandats_emis` ou `bp_2013`,
bénéficiaire dans un `libelle`), des statistiques qui ne nomment personne, et
19 échecs réseau chez `datacat.datalocale.fr`.

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
