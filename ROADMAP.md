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
