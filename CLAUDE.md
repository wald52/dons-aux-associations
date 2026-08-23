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

## 2. État des lieux chiffré

Mesuré, pas estimé. Relevés dans `bench/`, méthode dans `MESURE-PERF.md`.

### Aujourd'hui (phase 13, 23/08/2026)

| Mesure | v0 | aujourd'hui |
|---|---|---|
| Octets transférés (accueil) | ~73,6 Mo | **0,22 Mo** |
| Premier affichage | 12,96 s | **0,06 s** |
| Données exploitables | 57,75 s | **0,59 s** |
| Mémoire JS (accueil) | 1 965 Mo | **3 Mo** |
| Balises `<script>` | 170 | **1** |
| Lignes dans la table | 1 595 805 | **2 811 070** |

**La page de recherche a cessé de faire attendre.** Elle téléchargeait 34,2 Mo
de DuckDB-WASM puis 17,7 Mo de Parquet AVANT d'afficher un champ de saisie :
4,5 s en local, sans latence, derrière une phrase grise immobile. Elle sert
maintenant un index précalculé : **6,06 Mo au total, champ utilisable en
~0,3 s, recherche en 14–51 ms, fiche en 16–20 ms**, et un lien partagé vers une
association s'ouvre avec **une seule requête de ~120 Ko**, sans charger l'index.
Détail et méthode dans `MESURE-PERF.md`.

Données : **698 sources**, **148,40 Md€ de dons VOTÉS** et **10,43 Md€ de dons
PAYÉS** affichés côte à côte et jamais additionnés ; 1,57 Md€ ingérés mais hors
des totaux parce que ce ne sont pas des dons (prestations facturées,
remboursements, aides en nature), 2,08 Md€ de lignes agrégées, et la quarantaine
d'unité. 427 451 bénéficiaires résolus, dont **9 566 cumulent au moins trois
échelons**. (La phase 10 en annonçait 439 803 : chiffre jamais mesuré,
`index-stats.json` en portait 415 207.)

**Deux mouvements opposés, tous deux normaux.** La déduplication est passée de
580 321 à plus d'un million de lignes retirées : les jeux rouverts par la phase 9
republient en grande partie ce que le site avait déjà, et la clé métier les
rapproche au lieu de les compter deux fois. En sens inverse, trois millésimes du
Jaune récupérés grâce à `openpyxl` (PLF 2019, 2021, 2023 — exercices 2017, 2019
et 2021) ajoutent 23,6 Md€ d'État qui manquaient. La série du Jaune est
désormais continue de 2010 à 2023, sauf l'exercice 2022 (fichier vide à la
source).

Couverture face au référentiel INSEE, et c'est un MINIMUM : **95 communes**
sur 34 936, **31 EPCI** sur 1 335, **35 départements** sur 101, **6 régions**
sur 18. Bordeaux, Bourges, les Hauts-de-Seine et l'Aude sont entrés en phase 9 ;
Aix-en-Provence, Saint-Maur-des-Fossés, Fleury-sur-Orne, Moissy-Cramayel,
GrandSoissons Agglomération et la Seine-Maritime en phase 11 ; Besançon en
phase 12, qui RETIRE en revanche Rennes Métropole — cf. le piège du compte de
publication.

(**Six régions, pas sept** : la phase 10 a retiré un faux positif. La
Nouvelle-Aquitaine était comptée couverte à cause du SIREN de la Région
Île-de-France, bâti sur son chef-lieu — cf. les pièges.)

**Et depuis la phase 10, le site sait dire ce qui lui manque** — sans qu'aucun
de ces chiffres n'entre jamais dans ses totaux :

| Repère | Valeur |
|---|---|
| Communes déclarant un compte 6574 à la DGFiP (2010-2025) | **34 829** sur 34 936 |
| Ce qu'elles déclarent | **51,10 Md€** |
| Ce que le site en connaît | **7,60 Md€**, soit 14,9 %, par 82 communes |
| Idem EPCI / départements / régions (2019-2025) | 11,4 % / 36,6 % / 91,1 % |
| Organismes déposant leurs comptes au Journal officiel | **31 683** |
| Reconnus dans l'index du site | **18 745** (59,2 %) |
| D751 INSEE — versé par les APU aux ISBLSM en 2023 | **45,60 Md€** |
| Ce que le site retrouve sur le même exercice | **24,0 Md€** (52,6 %) |

**50 contrôles sur 50 dans `verify.py`** au dernier assemblage complet. Hors
d'un assemblage, « conservation des lignes » échoue faute de
`data/canonical/parts/`, qui n'est pas versionné : 49/50 est donc le score
normal quand on n'a pas rejoué les normaliseurs.

**Ce qui reste à faire est dans `RESTE-A-FAIRE.md`**, chiffré et priorisé.

### L'état d'origine, pour mémoire (18/08/2026)

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
├── index.html                  # champ unique + carte ; une seule balise <script>
├── commune.html                # « ma commune » — page à part entière
├── sw.js                       # service worker — bumper CACHE à chaque publication
├── assets/css/style.css
├── assets/js/
│   ├── commun.js               # utilitaires, état d'URL, états de page
│   ├── lexique.js              # les mots du site, définis là où ils s'affichent
│   ├── index-recherche.js      # l'index côté navigateur (remplace DuckDB)
│   ├── suggest.js              # le champ unique, partagé accueil / commune
│   └── app.js / recherche.js / commune.js / couverture.js
├── data/
│   ├── aggregates/             # CE QUE LE SITE CHARGE : 103 Ko au premier écran
│   │   ├── meta / cube / top / map-departements  (.json.gz)
│   │   ├── suggest.json.gz                       # rang 1 de l'autocomplétion
│   │   ├── departements/<code>.json.gz           # détail au clic, ~2,5 Ko
│   │   └── denominateur-communes/<dep>.json.gz   # fiches communales, ~22 Ko
│   ├── recherche/              # L'INDEX DU NAVIGATEUR (phase 13)
│   │   ├── noms.json.gz                          # 427 451 bénéficiaires, 5,1 Mo
│   │   ├── rna.json.gz                           # creux — lu par build_angle_mort
│   │   ├── ids/BBB.json.gz                       # 512 blocs d'identifiants
│   │   └── fiches/NNN.json.gz                    # 512 shards, ~120 Ko pièce
│   ├── canonical/
│   │   ├── subventions/year=AAAA/*.parquet       # table canonique, 28 partitions
│   │   ├── quality-report.json                   # FAIT FOI
│   │   ├── coverage.json
│   │   ├── denominateur.json                     # 6574 DGFiP, JAMAIS sommé
│   │   ├── angle-mort.json                       # comptes déposés au JO
│   │   └── totaux-controle.json                  # D751 des comptes nationaux
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

- **La page `methode.html` est ENGENDRÉE, jamais écrite à la main.**
  `build_methode.py` la reconstruit depuis `quality-report.json`,
  `couverture.json` et les manifestes : ses chiffres ne peuvent pas diverger
  de ceux du site. Une page de méthode écrite à la main ment dès la
  publication suivante.

- **Deux couleurs de la couverture passent sous 3:1 sur fond clair** (l'ocre
  « publie mais non exploité » et le gris « aucune donnée »). C'est assumé —
  un gris de « pas de donnée » DOIT lire gris — mais impose un relief :
  légende visible, hachures sur l'état intermédiaire, et tableau reprenant la
  carte en toutes lettres. Ne pas retirer l'un des trois.

- **Un style en ligne `background` écrase le `background-image` d'une classe.**
  Poser `backgroundColor` pour que les hachures survivent. Sur un tracé SVG,
  la texture demande un `<pattern>` dans `<defs>`, pas du CSS.

- **Le SIREN d'une collectivité dit son niveau, par construction INSEE** :
  `21…` commune, `22…` département, `23…` région, `24…` à `27…` groupement,
  `20…` établissement public de coopération. Vérifié sur le corpus. C'est
  infiniment plus sûr que le nom, et `donor_level_of` s'en sert en priorité.
  Sans cette règle, 277 616 lignes SCDL restaient en `inconnu` ; avec, il en
  reste 1 085.

- **Les préfectures et directions départementales versent des crédits d'ÉTAT.**
  Les données de la politique de la ville nomment leurs attribuants
  `DGCL - PREF-147`, `CGET - DDCS VAL D'OISE-147`, `DDETS`, `DREETS`… Les
  laisser en `inconnu` faisait disparaître 130 000 versements de la lecture
  par échelon. Liste de sigles dans `common.py` (`_SIGLES_ETAT`).

- **Le moissonneur SCDL valide les COLONNES RÉELLES, pas le schéma déclaré.**
  Seuls 53 jeux déclarent `scdl/subventions` ; les tags en ramènent 665, dont
  beaucoup ne sont pas des subventions aux associations (écritures comptables,
  bourses de recherche). D'où la validation par en-tête. Deux pièges :
  la mairie de Villejuif publie `nomBeneficiere` (faute d'orthographe, dans
  ses six millésimes) ; la ville de Lyon publie des AIDES EN NATURE
  (valorisations de locaux et de personnel) qu'il ne faut pas sommer avec des
  euros décaissés — écartées explicitement.

- **La couverture affichée est un MINIMUM.** Elle apparie le référentiel INSEE
  aux libellés de donateurs. Un libellé inhabituel échoue à s'apparier alors
  que la donnée existe : l'erreur va toujours vers la sous-estimation. Ne pas
  « corriger » en assouplissant l'appariement — un faux positif ferait dire au
  site qu'il couvre une collectivité qu'il ne couvre pas.

- **L'identité d'un bénéficiaire se résout par SIREN, sinon par nom PLUS
  département.** Jamais par nom seul : « Centre communal d'action sociale »
  existe dans 41 départements, « ADIE » dans 57 — une clé par nom fusionnerait
  des organismes distincts et INVENTERAIT des cumuls d'échelons. L'inverse
  (une association sans identifiant comptée deux fois) est une lacune, pas un
  mensonge : c'est le bon côté où se tromper. Cf. `build_search_index.py`.

- **DuckDB-WASM a été RETIRÉ (phase 13), et il ne faut pas le reproposer.**
  Il coûtait 34,2 Mo de moteur plus 17,7 Mo de Parquet AVANT que le champ de
  saisie n'existe — 4,5 s en local, sans latence, derrière une phrase grise
  immobile ; des dizaines de secondes sur un téléphone. Un moteur SQL
  généraliste est un prix très élevé pour deux questions : « quelles
  associations portent ce nom ? » et « qui finance celle-ci ? ». Un index
  précalculé y répond en 14–51 ms pour 6 Mo. Les problèmes que l'ancienne
  architecture traînait (repli sur le téléchargement complet malgré les
  requêtes Range, bundle esbuild à maintenir, extension Parquet à versionner
  parce que la CSP interdit le CDN duckdb.org) ont disparu avec elle. Ne pas y
  revenir sans un besoin de VRAI SQL arbitraire, qu'aucune page n'a aujourd'hui.

- **Le hachage de répartition doit être un VRAI hachage.** L'ancien
  (`sum(octets) % 64`) était trivial à reproduire en JavaScript, et mal
  distribué : la somme des codes d'un identifiant comme `S853318459` tient dans
  une bande d'environ 80 valeurs. Mesuré sur les fichiers en place : des shards
  de 233 Ko face à des shards de 1,66 Mo, un facteur 7. Modulo 512, il se
  serait effondré sur un dixième des fichiers. FNV-1a 32 bits tient en huit
  lignes des deux côtés — en JavaScript, **`Math.imul`, pas `*`** : au-delà de
  2^53 la multiplication passe par un double et perd des bits. La règle « la
  fonction de répartition existe en double, Python et JS, et DOIT rester
  identique » vaut toujours : `shard_of` dans `build_index_navigateur.py`,
  `shardDe` dans `assets/js/index-recherche.js`, et `verify.py` le vérifie.

- **Ne pas découper 427 451 chaînes quand on n'en affiche que cinquante.**
  L'index de noms gardé en tableaux de chaînes JavaScript faisait un tas de
  156 Mo. La même donnée en UNE grande chaîne plus un `Int32Array` de bornes,
  découpée à la demande, tient en 70 Mo après ramassage — et la recherche est
  un `indexOf` natif sur la grande chaîne, quelques millisecondes sur 427 451
  noms. Même règle pour les colonnes numériques : `Float64Array`/`Uint8Array`
  plutôt que des tableaux JavaScript.
  **Corollaire de mesure** : `usedJSHeapSize` relevé juste après `JSON.parse`
  est dominé par des déchets non ramassés — 163 Mo contre 70 réels. Forcer
  deux passes de `HeapProfiler.collectGarbage` avant de conclure.

- **Un préchargement « en tâche de fond » se paie quand même.** L'index de
  suggestion (0,85 Mo) chargé à l'inactivité de la page faisait passer
  l'accueil de 0,22 à **1,05 Mo** — pour un fichier dont la plupart des
  visiteurs n'ont pas l'usage. Il se charge maintenant à l'INTENTION : le
  pointeur qui entre dans le champ, un doigt qui s'y pose, ou le focus. Ces
  signaux précèdent la première lettre de quelques centaines de millisecondes,
  ce qui suffit — mesuré : première suggestion 502 ms après le survol, frappe
  de trois lettres comprise.

- **Un balayage partiel trie ce qu'il a trouvé, pas ce qu'il fallait trouver.**
  L'autocomplétion s'arrêtait aux douze premières communes appariées avant de
  les classer par population : comme le référentiel est ordonné par code INSEE,
  taper « bes » proposait Bessay-sur-Allier, Besson et Besny-et-Loizy, et
  **pas Besançon**. Balayer les 34 936 noms coûte deux millisecondes. Trier
  d'abord, couper ensuite — jamais l'inverse.

- **Le pliage de recherche s'applique au nom AFFICHÉ, pas à la clé du
  pipeline.** `normalize_name` retire les formes juridiques : comparer la
  saisie à `beneficiary_name_norm` faisait échouer « association des amis
  de X » sur une association qui s'affiche exactement sous ce nom. Le
  navigateur plie ce que le lecteur voit. Et **les ligatures ne se décomposent
  pas en NFD** : « cœur » se pliait en « c ur », si bien que « restos du
  coeur » — l'exemple donné par le champ lui-même — ne trouvait rien. On
  développe œ, æ et ß avant de plier. Cela ne touche que l'appariement, jamais
  la donnée stockée.

- **`white-space: nowrap` s'hérite.** `td.num` l'impose pour que les montants
  ne se coupent pas ; la phrase explicative placée dans la même cellule en
  héritait et poussait la page à 821 px de large sur un écran de 375. Une
  règle de mise en forme posée sur une cellule vaut pour tout ce qu'on y met
  ensuite.

- **Un sélecteur écrit pour `li` ne suit pas quand la ligne devient un `a`.**
  Les classements de l'accueil sont devenus des liens (ils étaient inertes,
  c'était le cul-de-sac le plus visible du site) et la grille CSS, écrite
  `.classement li`, les a laissés retomber en texte courant. Rien n'avait
  d'erreur : la page était simplement illisible.

- **Une explication dans un attribut `title` n'existe pas.** Quels échelons
  derrière un badge, pourquoi un montant est grisé : ces informations
  portaient la moitié du sens de la fiche et étaient inatteignables au doigt,
  au clavier et à l'impression. Elles sont écrites.

- **Deux géographies opposées ne partagent jamais un écran — la page commune
  aussi.** `commune.html` dit ce que la commune PAIE ; la carte de l'accueil
  dit ce que les associations DOMICILIÉES dans un territoire ont REÇU. Le lien
  de l'une vers l'autre existe, étiqueté « l'autre bout de la question », avec
  la phrase qui dit que ces montants ne s'additionnent jamais. Retirer cette
  phrase ferait lire de l'argent versé comme de l'argent reçu.

- **Un module de pipeline ne doit re-emballer `sys.stdout` que sous
  `if __name__ == "__main__"`** : au chargement du module (import depuis
  `verify.py`), le re-emballage détache le flux de l'importeur et tout
  `print` ultérieur lève « I/O operation on closed file ».

- **Trois nouvelles mises à l'écart de montants** (phase 3), même doctrine que
  `metropole-lyon` : 2 lignes de `ville-boulogne-billancourt` à 750 M€ et
  75 M€ (plafond par source, budget de la ville ~330 M€) ; la ligne « TOTAL
  AAAA » de `commune-bar-le-duc` traitée en agrégat (7 lignes, 196,9 M€) ; la
  ligne « Association inconnue » de `paris` à 257 M€ en 2024 traitée en
  agrégat (un cumul qui ne dit pas son nom). Total individuel : 114,46 Md€.

- **Le push de tags est refusé** dans les sessions distantes (HTTP 403 du
  proxy). L'état de référence d'avant refonte est `origin/main` @ `0b14348`,
  tag `v0` en local seulement. Le push de branches, lui, fonctionne.

- **Une colonne écrite en minuscules collées n'est pas reconnue par le
  découpage camelCase.** Opendatasoft, et une partie de data.gouv.fr,
  publient `nombeneficiaire`, `idattribuant`, `dateconvention`. Le libellé
  reste un seul mot, aucun motif ne le trouve, et le fichier est écarté pour
  « aucune colonne de bénéficiaire » — un rejet qui a l'air légitime dans le
  manifeste. `_correspond` reconnaît donc AUSSI le motif accolé. Cette seule
  ligne rouvrait 159 jeux ODS et 346 fichiers SCDL. Quand la couverture
  stagne, suspecter la reconnaissance avant de chercher de nouvelles sources.

- **Le repli `("tiers",)` du rôle bénéficiaire attrapait
  `tiers_commune_insee`** : la Région Bretagne voyait son bénéficiaire lu
  dans un code INSEE. D'où les disqualifiants `insee`, `commune`, `ville`,
  `adresse`, `postal`. Un motif de repli très général a besoin d'une liste de
  disqualifiants à sa mesure.

- **Le fédérateur `data.opendatasoft.com` REPUBLIE les jeux des portails
  territoriaux.** Bretagne, Paris votées, les deux comptes administratifs de
  Paris : chacun arrive deux fois. La déduplication par clé métier les
  rattrape (771 605 lignes, 53 Md€ retirés), mais le gagnant entre le portail
  et le fédérateur est arbitraire — l'attribution de source l'est donc aussi.
  Ne pas s'étonner de voir une donnée parisienne portée par un `source_id`
  du fédérateur.

- **Une collectivité publie souvent le même argent deux fois : ce qu'elle a
  VOTÉ et ce qu'elle a VERSÉ** (annexe au compte administratif). Paris pesait
  19,6 Md€ pour des subventions réelles de l'ordre de 350 M€ par an. D'où
  `measure` : seul `attribue` entre dans les totaux, `verse` est ingéré et
  consultable mais jamais sommé. Le titre du jeu suffit à trancher
  (`measure_of`).

- **`api.datasubvention.beta.gouv.fr` est ABANDONNÉ** — décision de
  l'utilisateur, 21/08/2026 : il n'aura pas l'habilitation. Ne pas le
  reproposer, ne pas bâtir de plan qui en dépende. Conséquence à assumer et à
  dire : **le plafond de couverture du site est celui d'aujourd'hui**, et sa
  valeur se déplace vers ce qu'il fait de ce qu'il a.

- **Les manifestes de moissonnage enregistrent les COLONNES des fichiers
  écartés** (`ecartes[].champs` pour ODS, `ecartes[].ecartes[].colonnes` pour
  data.gouv.fr). Un inventaire de ce qui reste récupérable se mesure donc hors
  ligne, sans rien re-télécharger. Fait le 21/08/2026, résultat dans
  `RESTE-A-FAIRE.md` §1d : ~91 jeux rouvrables, mais **69 sont la Ville de
  Rennes**, déjà présente — le gain serait en profondeur, pas en couverture.

- **Voté et payé s'affichent CÔTE À CÔTE, et ne s'additionnent jamais**
  (phase 8). La règle « versé ⇒ hors totaux » retirait 1,86 Md€ que rien ne
  dédoublait : mesuré le 21/08/2026, sur les 99 837 lignes qu'elle écartait,
  46 202 n'avaient aucune contrepartie « attribué » du même donateur et du même
  exercice — le département de Loire-Atlantique (778 M€) n'existait dans le site
  que par ses paiements, et n'apparaissait donc nulle part. Le site affiche
  maintenant deux totaux : `compte_dans_les_totaux` reste le voté, et
  `est_un_don` sans la mesure donne le payé. **Ne jamais les sommer** : quand une
  collectivité publie les deux, c'est le même argent. Aucune source de payé ne
  donne l'adresse du bénéficiaire — le payé n'a donc pas de géographie et ne peut
  pas colorer la carte.

- **Tout argent versé à une association n'est pas un don** (phase 8).
  « Prestation facturée par l'association » (89 948 lignes, 1,12 Md€) est un
  ACHAT : il y a une contrepartie. `nature_du_concours` distingue quatre natures
  — `don`, `prestation`, `remboursement`, `nature` — et seul le don entre dans
  les totaux. Mesuré : 128 700 lignes et 2,19 Md€ sortent des totaux, restent
  ingérées, consultables et affichées avec leur motif.
  **L'appariement se fait sur des SUITES DE MOTS, jamais sur des sous-chaînes** :
  « SOUTIEN AUX MANUFACTURES ET MÉTIERS D'ART » contient les lettres de
  « factur- », « DÉMARCHE QUALITÉ » celles de « marche ». Une sous-chaîne aurait
  effacé des subventions bien réelles.
  Volontairement ABSENTS des motifs, après relecture du corpus : « achat »
  (« SUBVENTION POUR ACHAT D'ACTIF IMMOBILISÉ » finance un achat FAIT PAR
  l'association — 215 lignes sorties à tort), « honoraires », et « délégation »
  seul (« 2ᵉ délégation » est une tranche de crédits). Dans le doute, c'est un
  don : écarter à tort efface une subvention, garder à tort laisse une ligne
  visible et corrigeable.

- **`data/canonical/parts/` n'étant pas versionné, `quality-report.json` se
  fige** sur la règle des totaux du dernier assemblage, et `verify.py` le voit
  (« total individuel reproductible » échoue). `refresh_rapport.py` le recalcule
  depuis la table canonique en appelant les fonctions de `build_canonical.py` —
  aucune règle n'y est réécrite ; seuls `deduplication` et `parts`, qui décrivent
  l'assemblage, sont repris du rapport précédent. Après un vrai
  `tout_reconstruire.sh`, ce script n'a rien à faire.

- **Ramener les séparateurs à l'espace dans `measure_of` ne suffit pas, et coûte
  plus que ça ne rapporte.** `fold` ne rend ni « _ » ni « - » : c'est vrai, et
  ça ne bouge que 8 lignes (850 k€, Ville de Chatou). Grenoble, le cas qui
  motivait le correctif, N'EST PAS attrapé pour autant :
  `subventions_fonctionnement_versees_associations_2019.csv` donne « subventions
  fonctionnement versees associations », qui ne contient toujours pas le
  bigramme « subventions versees ». Et passer à une détection par MOTS, qui
  l'attrape, ferait sortir des totaux 48,05 M€ sans contrepartie contre 6,36 M€
  de vrai double compte — dont trois exercices entiers de Grenoble-Alpes
  Métropole (2017, 2018, 2021, 41,49 M€) qui n'existent que par ces fichiers.
  Résultat négatif à retenir : ne pas « corriger » `fold` ici.

- **La clé métier laisse passer les doublons que seul l'OBJET distingue.**
  `ville-grenoble` et `ville-grenoble-2016` publient la même subvention sous
  « SUBVENTION PROJET » et « MUSIQUES » : même bénéficiaire, même donateur, même
  exercice, même montant, deux clés. **18 369 groupes, 22 867 lignes,
  442,62 M€** — signalés dans le rapport (`doublons_probables_hors_cle`), jamais
  retirés : ôter l'objet de la clé fondrait deux subventions réellement
  distinctes de même montant à la même association la même année.
  **Mesurer avec la même clé que le code, sinon on sous-estime** : une première
  mesure appariait les donateurs sur leur libellé et trouvait 144,84 M€, trois
  fois moins, parce que la clé métier apparie sur `identite_donateur`.

- **Le nom d'un bénéficiaire est parfois son numéro** — 7 121 lignes, 1,80 Md€,
  dont un « 911671485 » à 911,7 M€. La source a recopié le SIREN ou le RNA dans
  la colonne du nom. Signalé (`nom_de_beneficiaire_numerique`), pas corrigé.

- **49,88 Md€ sont comptés comme « association » sur une DEVINETTE.** Quand la
  source ne déclare pas la nature juridique, le défaut est « association » —
  c'est le bon côté où se tromper, et c'est assumé. Mais la liste des vingt plus
  gros (`nature_devinee_gros_montants`) contient SNCF Voyageurs, SNCF Réseau,
  l'AFP, le CNC et l'Association internationale de développement. Ne pas
  « corriger » sur le nom : ce serait deviner une exclusion, et effacer des
  associations réelles. C'est un arbitrage métier, pas un correctif.

- **Le compte administratif ne parle pas que d'associations.** Celui de Paris
  donne 5,5 Md€ à des établissements publics, 2,1 Md€ à des entreprises et
  38 878 lignes à des personnes physiques. Quand la source DÉCLARE la nature
  juridique, elle fait foi et la ligne sort des totaux ; quand nous ne faisons
  que la deviner sur le nom, la ligne reste comptée. L'asymétrie est
  délibérée : exclure à tort efface une association réelle, inclure à tort
  laisse une ligne visible et corrigeable. `beneficiary_kind_provenance`
  garde la distinction.

- **La règle des totaux est écrite UNE SEULE FOIS**, `compte_dans_les_totaux`
  dans `common.py`, comme le schéma et la clé métier. `verify.py` en portait
  une copie en ligne : c'était le germe d'une divergence silencieuse entre le
  rapport de qualité et l'index de recherche. Ne jamais la réécrire ailleurs.

- **L'identité du donateur se résout dans la clé, pas son libellé** (phase 6b).
  Une même collectivité change de graphie d'une publication à l'autre —
  « CONSEIL DEPARTEMENTAL DE LA SOMME » / « DEPARTEMENT DE LA SOMME »,
  « VILLE DE TOULOUSE » / « MAIRIE DE TOULOUSE », « COMMUNE D IFFENDIC » /
  « COMMUNE DE IFFENDIC » : 13 familles sur 142 libellés de collectivités.
  `identite_donateur` lit la forme juridique pour en tirer le niveau, et les
  mots restants pour le noyau. `donor_name_raw` n'est jamais retouché.
  Une DIRECTION est un service, pas une personne morale : le donateur est la
  collectivité qu'elle sert, et la coupe se fait au DERNIER mot de forme.
  On ne coupe que sur « direction » — un CCAS, une régie ou un syndicat sont
  des entités distinctes de leur commune.
  **Les articles restent dans le noyau**, seules les prépositions sautent :
  les retirer fondait `COMMUNE DE BAULE` (Loiret) et `COMMUNE DE LA BAULE`
  (La Baule-Escoublac, 44) en une seule commune. Ils n'apportaient rien par
  ailleurs — « DEPARTEMENT DE LA SOMME » et « CONSEIL DEPARTEMENTAL DE LA
  SOMME » gardent l'article tous les deux.
  Effet de bord assumé : `communes-pays-loire` étiquette « Commune de La
  Baule » ce qui est en réalité **Baule dans le Loiret** — le jeu ODS jumeau
  est publié sur le portail `@centrevaldeloire` et ses bénéficiaires sont le
  Mémorial des Loirétains et les Pupilles de l'Enseignement Public du Loiret.
  Les 182 lignes non nulles sont identiques de part et d'autre (le jeu ODS en
  porte 362, dont 180 à zéro). Elles restent donc comptées deux fois, pour
  365 k€ sur 157,7 Md€. On ne corrige PAS le libellé hérité : deviner qu'un
  « La Baule » veut dire « Baule » ailleurs fondrait deux communes réelles.
  La couverture, elle, ne compte bien qu'une commune (45024).

- **Paris : deux collectivités jusqu'en 2018, une seule à partir de 2019.**
  La loi n° 2017-257 du 28 février 2017 fusionne la commune et le département
  de Paris dans la collectivité unique « Ville de Paris » (art. 8 pour
  l'entrée en vigueur au 1er janvier 2019, art. 10 pour la substitution dans
  tous les droits et obligations). Ce que publie la Ville le confirme ligne à
  ligne : sa colonne `collectivite` porte les deux jusqu'en 2018, puis une
  seule. **Avant 2019, les distinguer n'est pas une erreur : chacune avait son
  budget.** La règle est dans `FUSIONS_COLLECTIVITES`, avec sa date d'effet ;
  y ajouter une fusion demande de vérifier la loi ET la donnée.

- **`business_key` prend le NOM du bénéficiaire, le SIRET seulement à défaut.**
  L'ordre inverse rendait la clé instable entre sources : la Ville de Paris
  publie le SIRET dans un jeu et pas dans l'autre, si bien que le Théâtre
  Musical de Paris (17 446 000 € en 2013) recevait deux clés pour une seule
  subvention. Revers mesuré : 5 605 groupes réunissent des HOMONYMES qui sont
  des personnes morales distinctes — « MAISON FAMILIALE RURALE » en Mayenne,
  plusieurs OGEC « Collège Saint-Joseph » en Maine-et-Loire, même année, même
  montant rond, même objet générique. La déduplication ne fond donc jamais un
  groupe aux SIRET contradictoires : les fondre EFFACERAIT une subvention
  réelle. `verify.py` exige que tout doublon résiduel s'explique ainsi.

- **La source héritée `paris` a été retirée : c'était une copie fautive.**
  Elle déclarait son propre amont (`opendata.paris.fr` — subventions votées),
  que le moissonneur reprend maintenant en entier (107 693 lignes contre
  76 207). Mais sa conversion écrasait le donateur : « Département de Paris »
  sur toutes les années jusqu'à 2023, quand la Ville n'écrit plus jamais
  « Département » après 2018. 87,6 % de ses 30 422 lignes de 2013-2018 avaient
  une jumelle exacte étiquetée « Ville » dans le jeu moissonné. L'erreur
  portant sur le donateur, qui FAIT PARTIE de la clé, la déduplication ne
  pouvait pas la voir. Symptôme qui l'a trahie : Paris tombait de 490 M€ en
  2018 à 291 M€ en 2019, pile à la date de la fusion. La série est désormais
  continue (271 puis 291 M€). Voir `REMPLACEES_PAR_MOISSONNAGE`.

- **`cd-finistere` porte 5 442 lignes au nom de donateur détruit.** Les
  octets du fichier hérité sont `\xef\xbf\xbd` (U+FFFD) : « Conseil
  D<?>partemental du Finist<?>re ». La lettre a été perdue par la conversion
  d'origine, elle n'est PAS récupérable depuis ce fichier — même cas que les
  SIRET passés au tableur. On le signale, on ne le devine pas. Effet de bord :
  ces lignes ne se dédupliquent pas avec leurs jumelles bien encodées.

- **L'année du compte administratif est dans la colonne `publication`**
  (« CA 2018 »), nulle part ailleurs. Sans elle, 67 413 lignes n'avaient
  aucune année. Le motif `("publication",)` vient EN DERNIER dans le rôle
  `annee` : c'est un libellé trop générique pour primer sur `exercice` ou
  `millesime`.

- **Le banc de mesure a besoin de `CHROMIUM_PATH`** quand la version de
  Playwright installée attend une révision de Chromium absente de la machine.
  Elle cherche un dossier numéroté précis et échoue alors qu'un Chromium
  utilisable est là.

- **Le Jaune PLF 2013 publie ses montants dix fois trop grands.** Son exercice
  2011 pesait 12,54 Md€, 6,7 fois ses voisins. Quatre indices concordants :
  100,0 % de ses 21 127 montants sont multiples de 10 (75,9 % au millésime
  suivant) ; le rapport 2011/2012 par SIREN pique EXACTEMENT à 10,0 ;
  l'Orchestre de Paris reçoit 9 278 494 € en 2010, 92 784 940 € en 2011, puis
  9 278 494 € en 2012 ; un poste Fonjep, dont l'unité est d'environ 7 107 €,
  y figure à 71 070 €. Divisé par dix, le montant moyen par ligne tombe à
  58 102 € contre 58 240 € en 2012.
  **L'erreur est du publieur** : l'API amont (`data.economie.gouv.fr`, champ
  `subvention_2011_en_euros`, type `double`) stocke bien la valeur gonflée.
  Mais savoir qu'un chiffre est faux ne dit pas quel est le vrai : on met en
  quarantaine (`UNITE_DOUTEUSE` dans `normalize_plf_jaune.py`), on ne divise
  pas. Même doctrine que Lyon, ci-dessous.

- **data.gouv.fr ré-inscrit le même fichier à chaque moissonnage du portail.**
  Le jeu de Grenoble-Alpes Métropole porte **1 044 ressources pour neuf
  fichiers réels**. Les prendre une par une, c'est ingérer le même CSV cent
  fois sous cent `source_id` : 91 sources fantômes, dont 85 ne portant plus
  qu'une ligne après déduplication. Pire, ces copies n'ont pas d'année
  (Grenoble ne la met que dans le nom du fichier), donc leur clé métier ne
  rencontre jamais celle de la source héritée qui l'a — 72,5 M€ comptés deux
  fois. `ressources_csv` regroupe donc par nom de fichier, **mais seulement
  pour les fichiers hébergés par la collectivité** : sur `static.data.gouv.fr`
  chaque ressource est un dépôt distinct, et deux millésimes y portent souvent
  le même nom de fichier — les fondre effacerait une année entière.

- **Une adresse périmée n'est pas un portail mort.** 235 des « liens morts »
  étaient des 404 chez `data.metropolegrenoble.fr`, qui répond parfaitement :
  il a réorganisé ses chemins et data.gouv.fr garde les anciens. `telecharger()`
  essaie toutes les adresses connues du fichier, de la plus récente à la plus
  ancienne — la plus récente n'est PAS forcément la bonne, ne pas s'arrêter à
  elle.

- **Un fichier par exercice ne répète pas l'année dans ses lignes.**
  160 sources, 160 210 lignes et 4,1 Md€ n'avaient aucune année pour cette
  seule raison. `annee_du_libelle` la lit dans le nom du fichier puis dans le
  titre du jeu, et **n'accepte qu'une seule année distincte** : « Subventions
  2008-2012 » reste sans année, deviner serait inventer. L'année fait partie de
  la clé métier, donc une source sans année ne se déduplique avec rien.
  `year_provenance` passe à `inferred`, drapeau `year_from_label`.

- **`EXERCICE` est un jeton de motif, pas un mot.** Il n'apparie que les mots
  formant une année plausible, ce qui rend `("ca", EXERCICE)` sûr là où
  `("ca",)` seul attraperait n'importe quoi. Il sert aux colonnes qui datent
  leur propre montant : `bp_2012`, `ca_2013` chez la Ville de Rennes.

- **Le gisement Opendatasoft n'était PAS épuisé — la phase 7 cherchait mal.**
  Elle partait des portails connus et concluait à l'épuisement (passer de 11 à
  41 portails n'avait apporté aucune collectivité). En partant des
  collectivités ABSENTES — les 30 plus grosses communes sans donnée, dont on
  fabrique les adresses de portail plausibles — on trouve **six portails
  inconnus du fédérateur** : Bordeaux Métropole, les départements des
  Hauts-de-Seine et de l'Aude, Grand Paris Seine Ouest, Issy-les-Moulineaux,
  Bourges Plus. Mesuré en bac à sable : 18 jeux, 12 870 lignes, une dizaine de
  collectivités nouvelles. **Le fédérateur est loin de tout republier.**
  Leçon de méthode : chercher à partir de ce qui MANQUE, pas de ce qu'on a.

- **`openpyxl` absent de la machine coûte 110 fichiers, et le manifeste le dit
  mal.** Le moissonnage du 22/08/2026 a d'abord écarté 110 XLSX pour
  « No module named 'openpyxl' » — un motif noyé au milieu des vraies raisons
  d'écarter. `pip install openpyxl`, puis relancer `fetch_scdl.py` : le cache
  ne reprend que ce qui manque, et les 110 fichiers entrent. Vérifier ce motif
  AVANT de conclure quoi que ce soit sur un moissonnage.

- **Un filtre d'adresse perdait 333 jeux de 63 organisations, sans trace.**
  `ressources_csv` exigeait qu'une adresse finisse par « .csv ». Les points
  d'export d'API (`.../datasets/<jeu>/exports/csv`, `.../resource/493/download/`)
  n'y répondent pas et servent pourtant de vrais fichiers. Ces jeux
  n'apparaissaient NI dans `datasets` NI dans `ecartes` : invisibles. Corrigé en
  faisant confiance au format déclaré quand l'adresse ressemble à un
  téléchargement ; ce qui répond du HTML est écarté en le disant.
  À retenir : **un rejet qui ne laisse pas de trace est pire qu'un mauvais
  rejet** — on ne peut même pas le mesurer.

- **`fetch_ods.py --portail` écrasait le manifeste** avec le seul portail
  demandé : les 46 autres disparaissaient du manifeste, donc de la
  normalisation, donc du site, sans une erreur. Il fusionne désormais.

- **Nice, Montpellier, Strasbourg et Toulon ne publient pas leurs subventions.**
  Vérifié des deux côtés le 21/08/2026 : ni sur leur portail (Strasbourg et
  Angers ont un portail ouvert avec ZÉRO jeu de subventions), ni sur
  data.gouv.fr. Leur absence n'est pas un défaut de moissonnage, c'est une
  absence de publication — et c'est à ce titre qu'elle doit être dite.

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

- **L'exercice 2011 du Jaune : le dossier est complet, la décision ne l'est
  pas.** `scripts/analyse/verifier_unite_2011.py` établit le facteur dix par
  cinq faisceaux indépendants — 2011/2012 et 2011/2010 rendent une médiane de
  **exactement 10,00** par association, quand les quatre années témoins rendent
  **exactement 1,00** ; 100,0 % des montants sont multiples de 10 ; la moyenne
  par ligne divisée par dix vaut 58 212 € contre 58 251 € en 2012. Le publieur,
  lui, n'a pas corrigé (l'API sert toujours 71 070 € pour un poste Fonjep à
  7 107 €). **Cela ne nous donne pas le droit de diviser** : « pas de correction
  de montant » est la doctrine, et réécrire 21 167 lignes publiées par un
  ministère est un arbitrage qui revient à l'utilisateur. La quarantaine tient.

- **Mesurer le PLF Jaune SANS exclure les agrégats donne des résultats faux.**
  Le fichier du PLF 2012 publie le total par association ET son détail, pour le
  même montant exactement (2 967 990 048 € des deux côtés). Le pipeline le sait
  et marque les totaux en `aggregate` ; une requête d'analyse qui l'oublie
  double l'exercice 2010 et fait conclure à une seconde anomalie qui n'existe
  pas. Toute mesure sur cette famille doit porter `granularity <> 'aggregate'`.

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

- **Le SIREN d'une RÉGION ne porte pas son code** — il est bâti sur le
  département de son CHEF-LIEU. `237500079` est la Région Île-de-France, et
  lire « 75 » comme un code de région en fait la Nouvelle-Aquitaine. C'est
  exactement ce qui se passait : la carte de couverture affichait la
  Nouvelle-Aquitaine « données présentes » avec zéro versement et zéro euro,
  le faux positif que cette page existe pour empêcher. Les régions fusionnées
  de 2016 commencent en plus par 20 (Normandie, 200053403). **Une région se
  reconnaît par son nom.** La règle des départements, elle, est vraie
  (22 + code) et n'est écrite qu'une fois, dans `code_departement_du_siren`.

- **`like '6574%'` n'est PAS un préfixe dans l'ODSQL d'Opendatasoft.** Le
  « % » n'y est pas un joker : la comparaison porte sur le jeton entier, donc
  la requête ne ramenait que le compte 6574 exact et laissait 65741, 65742 et
  65748 dehors — soit tout le compte associatif des départements et des
  régions en nomenclature M57. `startswith(compte,'6574')` est la bonne
  écriture. Symptôme trompeur : la requête ne renvoie pas d'erreur, elle
  renvoie un résultat plausible mais amputé.

- **Dans les balances DGFiP, la colonne `insee` n'est pas le code INSEE** :
  ce sont ses trois derniers chiffres. Le préfixe est dans `ndept`, qui n'est
  pas non plus un code INSEE et change de forme selon le millésime : « 59 »
  jusqu'en 2015 puis « 059 », « 02A » et « 02B » pour la Corse, et **101 à 106
  pour l'outre-mer, dans un ordre qui n'est pas celui de l'INSEE** (103 est la
  Martinique, 972 ; 102 la Guyane, 973). Au-delà de 100, le préfixe est
  simplement « 97 » et le troisième chiffre est déjà dans `insee`.
  `insee_from_parts` de `common.py` ne convient pas ici : il attend de vraies
  colonnes COG et lit « 015 » comme un département d'outre-mer.

- **Un budget annexe ne nomme pas sa collectivité, mais il porte son SIREN.**
  « ECOLE MUSIQUE-LUDRES », « FEDER REUNION », « HIPPODROME - MARCQ-EN-BAROEUL »
  sont des budgets de communes ou de régions, avec un pseudo-rang (9xx) qui ne
  correspond à rien au référentiel. D'où l'appariement en DEUX PASSES de
  `build_denominateur.py` : la première note quel SIREN désigne quelle
  collectivité, la seconde rattache le reste par ce SIREN. 12 002 lignes non
  rattachées au lieu de 227 038 — et rien n'est deviné, c'est la même personne
  morale qui le dit elle-même.

- **Les collectivités uniques n'ont pas de SIREN en 22.** Collectivité de
  Corse, CTU de Martinique et de Guyane, Collectivité européenne d'Alsace,
  Mayotte : 1,03 Md€ tombaient dans les non-rattachés. Chacune est créée par
  une loi qui dit son territoire, d'où la table `COLLECTIVITES_UNIQUES`. Les
  deux qui couvrent DEUX départements (Corse, Alsace) gardent un code
  composite — « 2A+2B », « 67+68 » — plutôt qu'une répartition inventée.

- **La présentation croisée nature-fonction ne peut pas prolonger le
  dénominateur avant 2019.** Tentant, puisque les jeux par nature ne
  remontent qu'à 2019 pour les départements, les régions et les EPCI. Vérifié
  sur 2020, où les deux présentations coexistent : les régions concordent au
  million près, mais les communes n'y pèsent que 2 438 M€ contre 3 044, et les
  groupements 1 413 contre 2 255 — seules les collectivités au-dessus du seuil
  produisent une présentation fonctionnelle. Résultat négatif à retenir.

- **Le seuil de 153 000 € du dépôt de comptes mélange dons privés et
  subventions publiques.** L'angle mort mesuré (12 938 organismes non reconnus)
  est donc un MAJORANT, jamais « le nombre d'associations subventionnées que
  le site rate ». La donnée le prouve elle-même : 3,5 % des fonds de dotation
  sont reconnus contre 67,9 % des associations loi 1901, et les plus gros
  déposants non reconnus sont des comités de la Ligue contre le cancer et des
  associations diocésaines — financés par des dons.

- **Un même code apparaît deux fois dans les tableaux des comptes nationaux**,
  une fois en « Ressources » et une fois en « Emplois ». Prendre la première
  occurrence venue, c'est lire ce que les associations REÇOIVENT là où on
  croyait lire ce que l'État VERSE (63,8 contre 45,6 Md€ en 2023). D'où la
  lecture qui suit la section en descendant les lignes. Le contrôle
  correspondant dans `verify.py` est l'invariant : le versé par les APU reste
  sous le reçu par les ISBLSM, toutes années confondues.

- **Les montants du dénominateur ne sont JAMAIS sommés avec ceux du site.**
  Le compte 6574 ne nomme aucun bénéficiaire ; l'ajouter aux versements
  nominatifs compterait deux fois le même argent. `verify.py` ne vérifie pas
  ici une somme mais une SÉPARATION : qu'aucune source `balances` n'ait pu se
  glisser dans la table canonique. Et une part « connue » peut dépasser 100 %
  sans que rien ne soit faux — le déclaré est un montant MANDATÉ, les totaux
  du site des montants VOTÉS (les Régions sont à 91 %, Rennes à 123 %).

- **Un chantier qui se formule « vérifier N éléments à la main » est mal posé.**
  `RESTE-A-FAIRE.md` §5c demandait d'éplucher 3 220 déposants non reconnus :
  personne ne le fera. Le livrable n'était pas la liste mais la CAUSE de chaque
  absence — six causes, toutes lues dans une donnée existante, qui expliquent
  **68,3 %** des 12 938 organismes. Le reste est une mesure de ce qu'on ignore,
  pas un arriéré de travail.

- **L'angle mort n'est pas un artefact d'appariement — mesuré.** On pouvait
  croire les 12 938 non-reconnus gonflés par des organismes connus du site sans
  identifiant. Apparier sur NOM + DÉPARTEMENT, la règle que le site s'applique
  déjà, n'en récupère que **157, soit 1,2 %**. Ne pas relancer cette piste.

- **Les jeux `osop-*` du portail DILA ne servent à rien ici.**
  `osop-comptes-de-resultats` (68 477 lignes) ne couvre que les SYNDICATS de
  salariés et d'employeurs, et son champ `ressources` est une tranche (1 à 4),
  pas une origine de financement. Aucune source ne dit, organisme par
  organisme, s'il vit d'argent public ou de dons privés.

- **Un financeur qui publie dans un département n'est pas celui qui finance
  l'association.** Classer une absence en « le site devrait le connaître » sur
  ce seul motif sur-affirme : la Région publie, mais c'est la commune qui verse,
  et elle ne publie pas. D'où le palier intermédiaire « territoire dont le site
  connaît moins de 1 % du 6574 communal », qui à lui seul explique 3 430
  absences de plus.

- **Deux géographies opposées ne partagent jamais un écran.** Les fragments
  `data/aggregates/departements/` décrivent les associations SITUÉES dans un
  département — des BÉNÉFICIAIRES. Les fiches `denominateur-communes/`
  décrivent la commune qui PAIE. Afficher « Rennes : 594 M€ » à côté des
  bénéficiaires rennais ferait lire de l'argent versé comme de l'argent reçu.
  C'est la raison pour laquelle la fiche communale est sur `couverture.html`
  et non sur la carte d'accueil.

- **Arrondir en millions efface les petites communes.** Un village déclare
  1 680 € au compte 6574, Rennes 2016 ne compte que 10 k€ de subventions
  connues : affichés « 0 M€ », ils se lisent comme « rien ». Le formatage des
  montants descend donc au millier puis à l'euro. Sur une page qui va du
  milliard au millier, une seule unité ment quelque part.

- **Une année absente d'une balance n'est pas un zéro, et encore moins une
  fusion.** La balance ne porte une ligne que si le compte a servi : la
  commune peut n'avoir rien versé, avoir imputé ailleurs, ou ne pas encore
  exister. 159 communes ne déclarent qu'à partir de 2019 — écrire « née d'une
  fusion » serait une devinette, fausse la plupart du temps. On énonce les
  trois causes.

- **Une échelle continue sur une distribution en L écrase tout.** La part
  connue par département va de 0 à 84 %, mais **59 départements sur 101 sont à
  ZÉRO** et trois seulement dépassent 50 % : un dégradé linéaire aurait rendu
  85 départements dans la même teinte pâle. D'où six paliers dont les bornes
  suivent la distribution mesurée. Et le zéro garde un gris à lui, récessif :
  « le site n'en connaît rien » est une absence, pas le bas d'une échelle de
  bleus — le peindre du bleu le plus clair le ferait passer pour un petit
  quelque chose.

- **Quand la carte bascule, le tableau bascule avec elle.** La règle de la page
  — une couleur ne porte jamais seule l'information — ne vaut pas que pour la
  vue d'origine. Ajouter une échelle sans donner son équivalent écrit
  reviendrait à la perdre pour qui ne distingue pas les teintes, lit au clavier
  ou imprime.

- **Une même colonne ne peut pas être à la fois le bénéficiaire ET le montant.**
  Quand elle l'est, ce n'est pas un en-tête : c'est le titre du rapport lu comme
  une ligne de colonnes. Six fichiers entraient ainsi, dont la Chambre de
  Commerce Seine Mer Normandie, qui publiait un bénéficiaire « 911671485 » pour
  911 671 485 € et « W761003097 » pour 761 003 097 € — un SIREN et un RNA lus
  comme des euros, **1,67 Md€ de faux dans le total voté**. C'était l'origine du
  `nom_de_beneficiaire_numerique` que le rapport signalait sans en connaître la
  cause. `porte_des_subventions` refuse maintenant ce cas, avec un motif explicite
  au manifeste.

- **Un motif de colonne très général ne vaut que si la colonne ne s'appelle QUE
  comme lui.** `associations` désigne bien la colonne des associations — mais
  dans « Subv.d'équipement - provision pour associations sportives », le mot
  n'est qu'un mot d'une phrase, et cette phrase est une LIGNE DE DONNÉES prise
  pour un en-tête. D'où `MOTIFS_STRICTS` : `associations`, `organisation`,
  `destinataire(s)`, `liborgabenef`. Sans cette réserve, le correctif qui rouvre
  Fleury-sur-Orne fait entrer deux fichiers dont les colonnes n'en sont pas.

- **La PREMIÈRE ligne, quand elle est déjà un en-tête valide, gagne.** Le
  repérage par mots-repères de `read_rows` peut préférer une ligne de données :
  l'en-tête de Montreuil, `organisation;montant;thematique;type`, ne porte qu'un
  mot-repère quand chacune de ses lignes en porte deux. Ses 270 lignes étaient
  toutes écartées pour « montant illisible ». `read_rows` prend donc un prédicat
  facultatif, et **les quatre lecteurs de subventions lui passent tous
  `porte_des_subventions`** — sans quoi moissonneur et normaliseur liraient deux
  en-têtes différents du même fichier.

- **Un motif de montant qui désigne un PAIEMENT vient en dernier.** Grand Paris
  Sud publie `MONTANT ATTRIBUE` et `MANDATE` dans le même fichier : `mandate`
  placé en tête faisait lire le payé là où l'attribué était disponible.

- **Le libellé de la colonne de montant entre dans `measure_of`.** Une colonne
  qui s'appelle `Mandaté` porte de l'argent PAYÉ, quoi que dise le titre du jeu.
  Les séparateurs y sont ramenés à l'espace — et **là seulement**, jamais dans
  `fold`, dont dépend toute la reconnaissance : le même fichier de Fleury-sur-Orne
  s'appelle `subventions_versees` côté portail et « Subventions versées » côté
  data.gouv.fr, et se lisait « voté » d'un côté, « payé » de l'autre.

- **« code » disqualifie l'attribuant.** GrandSoissons publie un `Code
  Collectivité` qui ne contient que « 1 » : 172 subventions entraient au nom d'un
  donateur appelé « 1 ». Même piège chez la Ville de Soissons avec `Code INSEE
  collectivité`.

- **Un publieur Opendatasoft est parfois un SERVICE, pas une personne morale.**
  Saint-Maur-des-Fossés publie ses subventions sportives sous « Direction des
  sports » : 3,7 M€ chez un donateur « inconnu ». Le repli remonte au publieur
  PUIS à l'éditeur du portail, qui dit la collectivité.

- **Une collectivité peut être dans la table sans être sur la carte de
  couverture.** Montreuil y entre avec 276 lignes et 10,89 M€, mais **trois
  communes françaises s'appellent « Montreuil »** (28267, 85148, 93048) :
  l'appariement refuse de deviner et le libellé reste dans
  `donateurs_non_apparies`. Ce n'est pas un bogue, c'est la doctrine — la
  couverture est un MINIMUM, l'erreur va vers la sous-estimation.

- **Le Département de Maine-et-Loire ne publie plus le nom de ses
  bénéficiaires depuis 2017.** Son fichier de 17 756 mandatements se déduplique
  entièrement contre la source héritée qui les portait déjà ; ses exercices
  2017-2019 échappent pour une autre raison : 1 781 lignes, 22,1 M€, dont 96,9 %
  ont un SIRET et aucune raison sociale. Le pipeline écarte les lignes sans nom.
  Les récupérer sur le seul SIRET est un arbitrage de doctrine, pas un correctif.

- **Un chantier daté doit être re-mesuré avant d'être OUVERT, pas seulement
  avant d'être écrit.** Le §1d de `RESTE-A-FAIRE.md` a été écrit avec méthode le
  21/08, puis a vieilli en une journée : la phase 9 a appliqué deux de ses trois
  correctifs sans qu'il soit relu, et son inventaire décrivait un moissonnage
  périmé. Ses « deux communes vraiment nouvelles » publiaient zéro ligne.

- **« CA 2014 » est un compte administratif, donc de l'argent PAYÉ.** La Ville de
  Rennes ne l'écrit jamais en toutes lettres, si bien que `measure_of` ne le
  voyait pas et que le site comptait le budget primitif ET son exécution du même
  exercice comme deux subventions VOTÉES : Rennes 2012 pesait 74,56 M€ pour un
  budget associatif d'environ 54 M€. Mesuré sur tout le corpus : **1 828 lignes,
  227,2 M€**, chez Rennes, Lorient Agglomération et la CC du Val d'Essonne. Le
  sigle seul serait bien trop court — c'est l'exercice accolé qui fait la preuve,
  comme pour le motif de colonne `("ca", EXERCICE)`.

- **Un compte de publication n'est pas un donateur.** Les fichiers budgétaires
  de la Ville de Rennes sont déposés sur data.gouv.fr par un compte nommé
  « Rennes Métropole en accès libre ». Faute de colonne d'attribuant, le site
  créditait **l'EPCI de 396 M€ versés par la COMMUNE**, et ces lignes ne se
  dédupliquaient pas avec les mêmes données publiées sur le portail — deux
  donateurs, donc deux clés métier. `collectivite_du_libelle` lit alors le titre
  du jeu et ne retient QUE ce qui correspond exactement à un nom du référentiel
  INSEE ; un titre qui ne nomme personne laisse le donateur NON ATTRIBUÉ, ce qui
  se voit et se corrige, quand un donateur faux se propage jusque dans la
  couverture. Conséquence assumée : **Rennes Métropole sort de la couverture**,
  n'ayant jamais rien publié en propre.

- **Un nom nu ne dit pas son échelon.** « Besançon » trouvé dans un titre est
  une commune, mais `donor_level_of` le laisse en `inconnu` faute de forme
  juridique. On lui ajoute la catégorie que le référentiel donne à ce nom
  (« Commune de Besançon ») — rien n'est inventé, le nom vient d'y être trouvé.

- **Une région ne s'appelle jamais « direction ».** Le repli par nom cherche
  « region » en SOUS-CHAÎNE : « Direction régionale des affaires culturelles des
  Pays de la Loire » devenait une région, et 421,54 M€ d'argent d'État étaient
  crédités à un échelon régional. Les services déconcentrés écrits en toutes
  lettres sont donc dans `_SIGLES_ETAT`, testé avant le repli.

- **Un motif de bénéficiaire ne vaut en dernier recours que s'il est STRICT.**
  `libelle` désigne l'objet presque partout — c'est même un disqualifiant du rôle
  « montant » — mais c'est la seule colonne de bénéficiaire des budgets primitifs
  de Rennes et des financements de la DRAC des Pays de la Loire. Le motif ne vaut
  donc que si la colonne s'appelle exactement ainsi. Effet mesuré sur les 824
  en-têtes connus : +26, zéro régression.

- **La DRAC des Pays de la Loire concatène le bénéficiaire et l'objet.**
  « O CAPITAINE MON CAPITAINE - Aide au projet Arts de la Rue pour la reprise du
  spectacle "Quenn-a-Man" » est un seul champ. 9 988 lignes et 363,66 M€ d'État
  entrent avec un nom d'organisme inutilisable pour le rapprochement. On les
  garde : l'erreur va vers la FRAGMENTATION d'une association en plusieurs, qui
  est une lacune, et non vers la fusion de deux organismes, qui serait un
  mensonge. Ne pas « corriger » en coupant au premier tiret — ce serait un
  traitement par source, que le projet refuse.

- **Deux millésimes du même publieur peuvent donner aux mêmes noms de colonnes
  des sens opposés.** Comptes administratifs de Rennes : en 2009,
  `provisions_par_tiers` porte le détail et `total_des_mandats_emis` l'agrégat,
  proprement séparés (93 lignes de détail commencent par « . », 52 lignes de
  total non) ; en 2010, **414 des 461** lignes de `total_des_mandats_emis` sont
  au contraire des versements individuels, pour 125 M€ sur 1 920 lignes. Aucun
  choix de colonne unique n'est défendable : ces ~13 000 lignes restent dehors.

- **Les CSV bruts sont désindexés** (`data/*.csv` dans `.gitignore`). Ils sont
  re-téléchargeables, URLs dans `SOURCES.md`, et leurs données sont déjà dans
  `data/sources/`. Ne pas les recommiter.

---

## 5. Décisions d'architecture et leurs raisons

- **Le site doit servir un index, pas une base.** Agrégats précalculés en
  `.json.gz` pour le premier écran ; détail en fragments **shardés, calculés
  d'avance**, pour ne télécharger que les octets utiles. Le principe n'a pas
  changé depuis la phase 2 ; sa mise en œuvre, si.
  La phase 3 l'avait confiée à **DuckDB-WASM sur du Parquet en requêtes HTTP
  Range**, pour avoir du vrai SQL sans backend. C'était payer 52 Mo — dont
  34,2 de moteur — avant d'afficher un champ de saisie, et la couche HTTP se
  repliait de toute façon sur le téléchargement complet. **La phase 13 l'a
  retiré** : les deux questions que le site pose réellement (« quelles
  associations portent ce nom ? », « qui finance celle-ci ? ») se répondent en
  14–51 ms sur un index de 6 Mo. Le SQL arbitraire était une capacité, pas un
  besoin ; il n'a jamais servi. Ne le réintroduire que le jour où une page en
  aura vraiment l'usage.

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
- [x] **Phase 3** — recherche croisée. Page `recherche.html` : moteur SQL
      DuckDB-WASM embarqué, index de 261 444 bénéficiaires résolus,
      versements shardés en 64 fichiers. 4 400 associations cumulent
      au moins 3 échelons. 28 contrôles dans `verify.py`.
- [x] **Phase 4** — exhaustivité, premier tour. Moissonneur SCDL générique
      (665 jeux examinés, 92 retenus, 444 fichiers), famille `scdl`,
      `couverture.html`. **2 012 328 lignes**, 126,6 Md€, 269 sources.
      Reste à faire : les 100 fichiers XLSX encore écartés, les tableaux
      pivotés par année, et la levée des quarantaines Lyon / Boulogne.
- [x] **Phase 6a** — le gisement rouvert. Moissonneur Opendatasoft
      (11 portails, 463 jeux examinés, 273 retenus) et reconnaissance de
      colonnes corrigée, qui à elle seule rouvre 159 jeux ODS et 346 fichiers
      SCDL écartés à tort. **2 769 440 lignes**, 161,7 Md€, 559 sources,
      408 380 bénéficiaires résolus, 9 016 cumulant 3 échelons ou plus.
      30 contrôles. Paris passe de 76 207 lignes à ses 202 347 publiées.
      Nouvelles colonnes `measure` (voté / versé) et
      `beneficiary_kind_provenance` (déclaré / deviné), avec la règle des
      totaux écrite une seule fois dans `compte_dans_les_totaux`.
- [x] **Phase 6b** — l'identité des donateurs. `identite_donateur` résout la
      collectivité derrière le libellé (13 familles de graphies sur 142) ;
      `FUSIONS_COLLECTIVITES` porte les fusions datées, Paris en tête —
      deux collectivités jusqu'en 2018, une seule ensuite (loi n° 2017-257).
      La clé métier passe au NOM du bénéficiaire, le SIRET n'étant plus qu'un
      recours, avec un garde-fou qui refuse de fondre des homonymes aux SIRET
      contradictoires. La source héritée `paris`, copie fautive d'un jeu que
      le moissonneur reprend en entier, est retirée. **2 690 242 lignes,
      157,7 Md€, 630 sources.** Paris ne rompt plus à la fusion : 271 M€ en
      2018, 291 M€ en 2019.
      Restent : dépivotage des tableaux annuels (~178 fichiers), liens morts
      en amont (236 404 et 135 échecs `datacat.datalocale`).
      `api.datasubvention.beta.gouv.fr` et `data.grandlyon.com` renvoient
      401 : hors de portée sans habilitation, d'où l'impossibilité de lever
      la quarantaine Lyon.
- [x] **Phase 5** — design et lisibilité. Système visuel unifié (bleu
      institutionnel commun avec `carte-finances-locales`), bandeau de
      navigation, `methode.html` engendrée depuis les données, tableau de
      couverture et hachures comme relief d'accessibilité.

- [x] **Phase 7** — l'unité et les doublons de ressources. Anomalie 2011
      élucidée (virgule décalée à la source) et mise en quarantaine ;
      déduplication des ressources data.gouv.fr et essai des adresses connues
      dans l'ordre ; quatre graphies de colonnes de plus ; année lue dans le
      libellé quand aucune colonne ne la porte (120 796 lignes datées,
      `year_missing` de 169 105 à 45 107) ; `fetch_ods.py` de 11 à 41 portails,
      sans gain de couverture — résultat négatif à retenir.
      **2 687 791 lignes, 144,71 Md€, 548 sources.** 30 contrôles.

- [x] **Phase 8** — ce qui est un don, et ce qui ne l'est pas. Quatre natures
      de concours (`nature_du_concours`), une seule est un don : 128 700 lignes
      et 2,19 Md€ de prestations facturées, remboursements et aides en nature
      sortent des totaux, restent consultables et affichent leur motif. Voté et
      payé s'affichent côte à côte au lieu que le payé disparaisse — la
      Loire-Atlantique, 778 M€, redevient visible. **142,59 Md€ votés,
      7,45 Md€ payés.** 33 contrôles, dont trois nouveaux qui comparent les
      agrégats servis au navigateur à la table canonique.

- [x] **Phase 9** — le gisement rouvert par le bon bout. En cherchant à partir
      des collectivités ABSENTES plutôt que des portails connus : six portails
      Opendatasoft inconnus du fédérateur (Bordeaux Métropole, Hauts-de-Seine,
      Aude, Grand Paris Seine Ouest, Issy, Bourges Plus). Et un filtre d'adresse
      qui perdait **333 jeux de 63 organisations sans laisser de trace**. Plus
      `openpyxl` absent de la machine, qui coûtait 110 fichiers XLSX.
      data.gouv.fr passe de 148 à **377 jeux retenus** (504 fichiers),
      Opendatasoft de 371 à **407**, et le Jaune de 10 à **13 millésimes sur 14**.
      **2 809 711 lignes, 658 sources, 149,68 Md€ votés**, 90 communes,
      34 départements, 7 régions. **33/33 contrôles.** (Sept régions était le
      chiffre du jour : la phase 10 en a retiré un faux positif, il y en a
      **six** — cf. le piège du SIREN des régions.)

- [x] **Phase 10** — le dénominateur, l'angle mort et l'échelle. Le site
      savait « qui a reçu quoi » ; il sait maintenant dire ce qui lui manque.
      Compte 6574 des balances comptables DGFiP (565 916 lignes, 19 jeux) :
      **34 829 communes déclarent 51,10 Md€**, le site en connaît 7,60 Md€.
      Comptes annuels déposés au Journal officiel (227 586 dépôts) :
      **31 683 organismes**, dont 18 745 reconnus. D751 des comptes nationaux :
      **45,60 Md€ versés aux ISBLSM en 2023**, dont le site retrouve 24,0 Md€.
      Aucun de ces montants n'entre dans les totaux du site. Corrige au passage
      un faux positif de la couverture : 6 régions, pas 7. **44/45 contrôles.**
      Depuis le 22/08/2026, la carte de couverture porte ce dénominateur : deux
      vues sous une bascule, « ce qui est publié » et « ce qui nous échappe »,
      et **chacune des 34 829 communes déclarantes a sa fiche** (48/49
      contrôles). Enfin, les 12 938 organismes non reconnus sont rangés sous
      **six causes lues dans une donnée existante**, qui en expliquent
      **68,3 %** — une liste de 3 220 noms à éplucher n'était pas un livrable.
      **49/50 contrôles**, le compte d'aujourd'hui.

- [x] **Phase 11** — les jeux écartés, et ce qu'ils ont cassé en entrant. Sept
      graphies de colonnes de plus (`liborgabenef`, `mtsubv`, `mandate`,
      `organisation`, `destinataire(s)`, `associations`), toutes relevées dans
      les manifestes puis **vérifiées sur la donnée téléchargée**. Quatre
      collectivités nouvelles, un EPCI et **un département entier** —
      Aix-en-Provence, Saint-Maur-des-Fossés, Fleury-sur-Orne, Moissy-Cramayel,
      GrandSoissons Agglomération, la Seine-Maritime. **2 817 042 lignes,
      681 sources, 94 communes, 32 EPCI, 35 départements, 10 128 cumuls à trois
      échelons. 50/50 contrôles.**
      Le total voté BAISSE de 1,34 Md€ en gagnant 23 sources, et c'est une
      correction : **1,67 Md€ venaient d'une seule colonne servant à la fois de
      bénéficiaire et de montant**, qui faisait lire des SIREN et des RNA comme
      des euros. Ouvrir ces jeux a révélé trois autres défauts du même ordre —
      un en-tête lu sur une ligne de données, un donateur lu dans une colonne de
      code, un publieur qui est un service et non une collectivité.
      Le §1d qui commandait ce chantier était faux sur ses trois points :
      leçon rangée dans les pièges.

- [x] **Phase 12** — Rennes : le chantier n'était pas celui qui était écrit. Le
      §1d annonçait « une trentaine de jeux à rouvrir » ; les fichiers étaient
      déjà là, et **mal classés**. « CA 2014 » est un compte administratif que
      `measure_of` ne reconnaissait pas : le site comptait le budget primitif ET
      son exécution du même exercice comme deux subventions votées — **1 828
      lignes, 227,2 M€** sur tout le corpus. Et un compte de publication servait
      de donateur : **396 M€ versés par la Ville de Rennes étaient crédités à
      Rennes Métropole**, sans se dédupliquer avec la même donnée publiée sur le
      portail.
      **2 811 070 lignes, 698 sources, 95 communes, 31 EPCI, 35 départements,
      148,40 Md€ votés et 10,43 Md€ payés. 50/50 contrôles.**
      La couverture PERD un EPCI et c'est juste : Rennes Métropole n'a jamais
      rien publié en propre. Les cumuls à trois échelons tombent de 562 pour la
      même raison — comparaison exacte des deux index : 567 bénéficiaires
      passent sous trois échelons, dont **554 en perdant leur échelon EPCI**.
      Ces cumuls n'existaient pas.
      Quatre graphies de plus (`realise_de_l_annee`, `budget_de_l_annee`,
      `somme`, `libelle` strict) ouvrent les budgets primitifs de Rennes et,
      avec eux, les financements de la DRAC des Pays de la Loire (9 988 lignes,
      363,66 M€). Les comptes administratifs 2008-2010 de Rennes restent dehors,
      mesure à l'appui.

- [x] **Phase 13** — l'interface. Le site savait des choses qu'aucun autre ne
      sait, et les rendait difficiles à atteindre. **DuckDB-WASM est retiré** :
      la recherche téléchargeait 34,2 Mo de moteur puis 17,7 Mo de Parquet
      avant d'afficher un champ de saisie. Un index précalculé le remplace —
      **6,06 Mo, champ utilisable en ~0,3 s, recherche en 14–51 ms, fiche en
      16–20 ms**, et un lien partagé vers une association s'ouvre avec **une
      requête de 120 Ko**. Le dépôt suivi passe de 342 à 309 Mo.
      L'accueil s'ouvre sur **un champ unique** — association, commune,
      département, région — et la carte porte enfin son sens : un titre qui dit
      qu'elle situe les BÉNÉFICIAIRES, une légende avec ses bornes et son gris,
      une bascule total / par habitant, et le tactile. **`commune.html`** devient
      une page à part entière, avec autocomplétion sur les 34 936 communes et
      adresse partageable. **Tout est partageable** : `#dep`, `#annee`,
      `#niveau`, `#vue`, `#q`, `#a`, `#insee`, et le bouton Retour fonctionne.
      Un **lexique** définit « échelon », « voté », « payé », « mandaté »,
      « compte 6574 » là où ces mots s'affichent ; les raisons pour lesquelles
      un montant sort des totaux quittent les attributs `title` ; les sources,
      sélectionnées par la requête et jamais affichées, entrent dans le tableau.
      Trois bogues de `build_methode.py` corrigés, dont un total de
      « 80 002 255 770,2 Md€ ». Aucun chiffre n'est plus écrit en dur dans le
      HTML. **49/50 contrôles**, le compte normal hors assemblage complet.

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
python3 scripts/pipeline/build_index_navigateur.py # index servi au navigateur
python3 scripts/pipeline/fetch_scdl.py           # moissonneur générique data.gouv.fr
python3 scripts/pipeline/normalize_scdl.py       # famille scdl
python3 scripts/pipeline/build_couverture.py     # carte de couverture
python3 scripts/pipeline/build_methode.py        # page sources & méthode
python3 scripts/pipeline/fetch_ods.py            # moissonneur des portails Opendatasoft
python3 scripts/pipeline/normalize_ods.py        # famille portail

# Ce que le site NE VOIT PAS — hors table canonique, jamais sommé avec elle
python3 scripts/pipeline/fetch_balances.py       # compte 6574 des balances DGFiP
python3 scripts/pipeline/build_denominateur.py   # « le site connaît Y € sur X € »
python3 scripts/pipeline/build_fiches_communes.py # découpe le dénominateur par département
python3 scripts/pipeline/fetch_jo_comptes.py     # comptes annuels déposés au JO
python3 scripts/pipeline/build_angle_mort.py     # croisement avec l'index (après lui)
python3 scripts/pipeline/fetch_totaux_controle.py  # D751 des comptes nationaux
```

En pratique on ne les lance plus un par un : `bash
scripts/pipeline/tout_reconstruire.sh` rejoue toute la chaîne dans le bon
ordre, les moissonnages exceptés (ils ont leur propre cache). **`verify.py` y
vient EN DERNIER** : plusieurs de ses contrôles comparent l'index de recherche
à la table canonique et échouent tant que l'index n'est pas reconstruit.

`refresh_rapport.py` recalcule `quality-report.json` et `coverage.json` depuis
la table canonique quand les parties d'assemblage ne sont pas là — cf. le piège
correspondant.

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
