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

### Aujourd'hui (phase 7, 20/08/2026)

| Mesure | v0 | aujourd'hui |
|---|---|---|
| Octets transférés | ~73,6 Mo | **0,14 Mo** |
| Premier affichage | 12,96 s | **0,07 s** |
| Données exploitables | 57,75 s | **0,58 s** |
| Mémoire JS | 1 965 Mo | **3 Mo** |
| Balises `<script>` | 170 | **1** |
| Lignes dans la table | 1 595 805 | **2 687 791** |

(Banc `bench/phase7.json`, rejoué le 20/08/2026.)

Données : **548 sources**, **142,59 Md€ de dons VOTÉS** et **7,45 Md€ de dons
PAYÉS** affichés côte à côte et jamais additionnés ; 2,19 Md€ ingérés mais hors
des totaux parce que ce ne sont pas des dons (prestations facturées,
remboursements, aides en nature), 10,24 Md€ à bénéficiaires déclarés hors du
champ associatif, 2,03 Md€ de lignes agrégées, et 60,3 Md€ en quarantaine
d'unité. 406 846 bénéficiaires résolus, dont 6 783 cumulent au moins trois
échelons.

Couverture face au référentiel INSEE, et c'est un MINIMUM : **86 communes**
avec données sur 34 936 (96 repérées), **29 EPCI** sur 1 335 (38 repérés),
**31 départements** sur 101 (36), **5 régions** sur 18 (7) — soit 10,3 % de la
population. Ces chiffres sont ceux de `couverture.json` ; les « 113 communes,
40 EPCI, 37 départements » qu'annonçait ce fichier jusqu'en phase 6b ne s'y
retrouvaient déjà pas.

Le double comptage de Paris est corrigé (phase 6b) : la série ne rompt plus à
la fusion de 2019, 271 M€ en 2018 puis 291 M€ en 2019. L'anomalie de 2011 est
élucidée et mise en quarantaine (phase 7) : la source y publiait avec la
virgule décalée d'un rang.

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

- **La couche HTTP de DuckDB-WASM se replie sur le téléchargement complet.**
  Malgré `registerFileURL(..., directIO=true)` et un serveur répondant
  correctement aux requêtes Range, la première fiche rapatriait les 25 Mo du
  fichier de versements. D'où le sharding en 64 fichiers par hachage du
  bénéficiaire (~400 Ko chacun), qui marche sur n'importe quel hébergeur
  statique. La fonction de répartition existe en double (Python
  `shard_of`, JS `shardDe`) et DOIT rester identique.

- **`duckdb-browser.mjs` n'est pas autonome** : il importe « apache-arrow » par
  son nom nu, insoluble pour un navigateur. `assets/vendor/duckdb/duckdb.mjs`
  est un bundle esbuild autosuffisant. L'extension Parquet est elle aussi
  versionnée (`assets/vendor/duckdb/extensions/…`) et chargée via
  `SET custom_extension_repository` — la CSP interdit le CDN duckdb.org.

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

- **Le gisement Opendatasoft est épuisé — mesuré.** Passer le moissonneur de 11
  à 41 portails a retenu 98 jeux de plus et n'a apporté **aucune collectivité
  nouvelle** : le fédérateur republiait déjà tout. Les communes de Grand Paris
  Sud, par exemple, ont bien leur portail, mais le donateur y est
  l'agglomération. Ne pas relancer ce chantier en espérant de la couverture.

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
python3 scripts/pipeline/build_search_index.py   # index de recherche croisée
python3 scripts/pipeline/fetch_scdl.py           # moissonneur générique data.gouv.fr
python3 scripts/pipeline/normalize_scdl.py       # famille scdl
python3 scripts/pipeline/build_couverture.py     # carte de couverture
python3 scripts/pipeline/build_methode.py        # page sources & méthode
python3 scripts/pipeline/fetch_ods.py            # moissonneur des portails Opendatasoft
python3 scripts/pipeline/normalize_ods.py        # famille portail
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
