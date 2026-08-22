# Ce qui reste à faire

État arrêté au **22/08/2026**, après la phase 10. Chiffres mesurés, pas estimés :
ils viennent de `data/canonical/quality-report.json`, `couverture.json`, des
manifestes de moissonnage et du banc `bench/phase7.json`.

À lire après `CLAUDE.md` (contexte et pièges) et `ROADMAP.md` (ce qui a été fait
et pourquoi).

> **Avertissement de méthode.** La version précédente de ce fichier annonçait
> « ~178 fichiers » à dépivoter et « 371 liens morts » : les manifestes en
> portaient respectivement 37 et deux hôtes. Un chiffre écrit ici sans avoir été
> relu dans les manifestes envoie la session suivante sur le mauvais chantier.
> **Vérifier avant d'écrire, et dire d'où vient le chiffre.**

---

## Où en est le site

Les phases 0 à 7 sont faites. Sur les quatre objectifs de départ — vitesse,
données justes et exhaustives, recherche croisée, lisibilité — **trois sont
atteints**. Le site charge en 0,07 s, la recherche croisée fonctionne sur
2,7 M de lignes sans backend, le design est unifié.

**L'exhaustivité est le seul objectif encore largement ouvert, et la phase 7 a
montré qu'elle ne s'ouvrira plus par moissonnage.**

| | valeur |
|---|---|
| Lignes servies | 2 809 711 |
| **Dons votés** | **149,68 Md€** |
| **Dons payés** (à côté, jamais additionnés) | **10,02 Md€** |
| Ingéré mais pas un don (prestations, remboursements, nature) | 1,57 Md€ |
| Sources | 658 |
| Bénéficiaires résolus | 439 803 |
| Dont cumulant 3 échelons ou plus | 9 800 |
| Contrôles `verify.py` | **49 / 50** (le 50ᵉ demande `data/canonical/parts/`, non versionné) |
| **Ce que déclarent les communes à la DGFiP (6574, 2010-2025)** | **51,10 Md€**, dont le site connaît **14,9 %** |
| **Organismes déposant leurs comptes au JO** | **31 683**, dont **18 745 reconnus** |
| **D751 INSEE — versé aux ISBLSM en 2023** | **45,60 Md€**, dont le site retrouve **24,0 Md€** |

Le total baisse en gagnant 107 sources : la déduplication passe de 580 321 à
1 064 346 lignes retirées. Les jeux rouverts republient largement ce que le site
avait déjà, et la clé métier les rapproche.

---

## 1. L'exhaustivité — le vrai manque

Couverture face au référentiel INSEE. **C'est un MINIMUM** : l'appariement
échoue plutôt qu'il n'invente, donc l'erreur va toujours vers la
sous-estimation (cf. `CLAUDE.md`).

| Échelon | Avec données | Univers | phase 8 |
|---|---|---|---|
| Communes | **90** | 34 936 | 86 |
| EPCI | **31** | 1 335 | 29 |
| Départements | **34** | 101 | 31 |
| Régions | **6** | 18 | 5 |

10,9 % de la population française. (« Repérées » ajoute les collectivités qui
publient mais dont rien n'est encore exploité.)

**Six régions et non sept** : la phase 10 a retiré un faux positif. La
Nouvelle-Aquitaine était comptée couverte à cause du SIREN de la Région
Île-de-France, bâti sur son chef-lieu et non sur le code de la région.

**Et depuis la phase 10, cette lacune est CHIFFRÉE** : 34 829 communes
déclarent 51,10 Md€ au compte 6574 des balances DGFiP entre 2010 et 2025, le
site en connaît 7,60 Md€. Le détail par échelon, par exercice et par
département est sur la page « Ce qu'on ne sait pas ».

> **Une autre façon de poser la question, instruite le 22/08/2026 puis
> ENGAGÉE le même jour : `SOURCES-RECEPTION.md`.** Ses trois options sont
> faites (dénominateur DGFiP, angle mort du JO, totaux de contrôle INSEE) ;
> l'impasse des PDF scannés reste une impasse.
>
> Pour mémoire, l'inventaire d'origine : Au lieu de moissonner ce que les collectivités
> publient, regarder ce que les associations DÉCLARENT recevoir. Inventaire
> vérifié des sources, avec leurs volumes mesurés — dont les 227 586 comptes
> annuels déposés au Journal officiel (montants dans des PDF scannés : impasse),
> les 45,6 Md€ d'APU vers les ISBLSM des comptes nationaux, et le compte 6574
> des balances comptables DGFiP, qui couvre **31 797 communes** contre 90 ici.
> Rien n'est engagé : le document s'arrête à l'inventaire.

### 1a. Les deux canaux de moissonnage sont épuisés — *mesuré, pas supposé*

C'est le résultat le plus utile de la phase 7, et il est négatif.

- **Opendatasoft** : le moissonneur est passé de 11 à 41 portails, repérés en
  demandant au fédérateur le domaine d'origine de chacun de ses jeux. 98 jeux
  de plus ont été retenus (273 → 371) et **la couverture n'a pas bougé d'une
  seule collectivité** : le fédérateur republiait déjà tout. Ne pas relancer ce
  chantier en espérant de la couverture.
- **data.gouv.fr** : 666 jeux examinés sur six angles de découverte ; la
  recherche « subvention » en renvoie 685 aujourd'hui. Il n'y a plus de marge.

Il reste des portails Opendatasoft hors du fédérateur, mais rien n'indique
qu'ils soient nombreux — et cinq de ceux repérés sont déjà morts.

### 1b. `api.datasubvention.beta.gouv.fr` — **ABANDONNÉ (décision du 21/08/2026)**

Ce serait la source de référence : elle agrège Chorus et les données des
collectivités. L'API vit mais renvoie **401** — réservée aux agents publics et
aux associations habilitées.

**L'utilisateur a tranché : il n'y aura pas accès.** Ce chantier sort donc de la
liste. Ne pas le reproposer, et ne pas construire de plan qui en dépende : la
couverture du site devra se faire sans, ou ne pas se faire.

Conséquence à assumer : **le plafond de couverture est celui d'aujourd'hui, à
peu de chose près.** Ce qui reste (§1d) apporte de la profondeur — des exercices
en plus sur des collectivités déjà présentes — pas un changement d'échelle.

### 1b bis. Chercher hors des deux canaux — *fait le 21/08/2026, ET ÇA A DONNÉ*

La phase 7 concluait que les deux canaux étaient épuisés. C'était vrai **de la
manière dont on cherchait** : en partant des portails connus. En partant des
collectivités ABSENTES, on trouve autre chose.

Méthode : prendre les 30 plus grosses communes sans aucune donnée (Nice,
Montpellier, Strasbourg, Bordeaux, Lille, Toulon, Reims…), fabriquer les
adresses plausibles de leur portail, et interroger l'API Explore. 185 domaines
sondés.

**Six portails Opendatasoft inconnus du fédérateur ET du site :**

| Portail | Qui | Jeux « subvention » |
|---|---|---|
| `opendata.bordeaux-metropole.fr` | Bordeaux Métropole, Ville de Bordeaux, Pessac, Le Haillan | 4 |
| `opendata.hauts-de-seine.fr` | **Département des Hauts-de-Seine** | 6 |
| `opendata.aude.fr` | **Département de l'Aude** | 1 |
| `data.seineouest.fr` | Grand Paris Seine Ouest | 4 |
| `data.issy.com` | Ville d'Issy-les-Moulineaux | 9 |
| `data.bourgesplus.fr` | Bourges Plus | 5 |

Les quatre jeux de Bordeaux ont été vérifiés colonne à colonne : tous seraient
retenus. Bordeaux est la 9ᵉ ville de France.

**Et une découverte plus grosse encore : un filtre d'adresse perdait 333 jeux.**
`ressources_csv` exigeait qu'une adresse FINISSE par « .csv ». Les points
d'export d'API — `.../datasets/<jeu>/exports/csv`, `.../resource/493/download/` —
ne finissent pas ainsi et servent pourtant de vrais fichiers. Mesuré sur les six
angles de découverte : **333 jeux de 63 organisations** étaient écartés en
silence, sans aucune trace dans le manifeste. Huit ont été testés en
téléchargeant l'adresse réelle : **cinq servent un SCDL valide** (Bourges,
l'Aude, Grand Paris Seine Ouest, les Hauts-de-Seine, Boulogne-Billancourt).

**FAIT le 22/08/2026 — le pipeline a été entièrement rejoué.** Moissonnage des
trois familles, normalisation, assemblage, agrégats, index, contrôles. Résultat :

| | avant | après |
|---|---|---|
| Jeux retenus data.gouv.fr | 148 | **377** (504 fichiers) |
| Jeux retenus Opendatasoft | 371 | **407** |
| Sources dans la table | 548 | **655** |
| Communes couvertes | 86 | **90** |
| Départements | 31 | **34** |
| Régions | 5 | **7**, ramenées à **6** par la phase 10 (voir ci-dessous) |
| Associations à 3 échelons ou plus | 6 783 | **9 613** |
| Contrôles `verify.py` | 32/33 | **33/33** |

Bordeaux (469,0 M€), Bourges (117,7 M€), les Hauts-de-Seine (318,4 M€), l'Aude,
Issy-les-Moulineaux, Grand Paris Seine Ouest et Blois sont entrés.

*Le chiffre des régions est celui du jour, et il était faux d'une unité* : la
phase 10 a retiré la Nouvelle-Aquitaine, comptée couverte à cause du SIREN de la
Région Île-de-France, bâti sur son chef-lieu. **Six régions, pas sept** — c'est le
chiffre du §1 qui fait foi.

Un troisième blocage a été trouvé en route : **`openpyxl` n'était pas installé**,
ce qui écartait 110 fichiers XLSX sous un motif noyé dans la liste des raisons.
Installé, puis moissonnage relancé — le cache ne reprend que ce qui manque.

**Ce que Nice, Montpellier, Strasbourg, Lille et Toulon ne publient pas.**
Vérifié des deux côtés : ni portail (Strasbourg et Angers ont un portail ouvert
avec ZÉRO jeu de subventions), ni data.gouv.fr. Seule Lille publie — et son
adresse d'export répond du HTML. Leur absence du site n'est donc pas un défaut
de moissonnage : **c'est une absence de publication**, et c'est à ce titre
qu'elle doit être dite.

### 1c. Ce qui manquera toujours

Les communes de moins de 3 500 habitants ne sont pas tenues de publier, et
parmi celles qui le sont, l'obligation est peu suivie. Aucun moissonnage ne
comblera cela : la lacune est légale. C'est ce que la page « Ce que ce site ne
sait pas » est là pour dire.

### 1d. L'inventaire de ce qui a été téléchargé PUIS écarté — *mesuré le 21/08/2026*

Le seul gisement restant qui ne dépende de personne : les fichiers que les
moissonneurs ont déjà vus et rejetés. Relevé dans les `ecartes` des manifestes,
qui enregistrent les colonnes réelles de chaque fichier rejeté — la mesure se
fait donc hors ligne, sans re-télécharger.

**Portails Opendatasoft — 203 jeux écartés**, dont 28 sans colonnes enregistrées.

| Ce qui bloque | jeux | de qui |
|---|---|---|
| En-tête mal détecté (les « colonnes » sont une ligne de données) | 51 | Ville de Rennes, BP et CA |
| `libelle` porte le bénéficiaire, motif trop générique pour être pris | 18 | Ville de Rennes |
| `organismes` | 12 | Agglopolys (Blois) |
| `organisme_de_formation_libelle_et_code` | 8 | Région Île-de-France |
| `beneficiare` — faute de frappe du publieur | 4 | Ville de Rennes, CA |
| `attributaires`, `noms` | 4 | Ville de Blois |
| `liborgabenef` / `mtsubv` — colonnes abrégées | 2 | une région |
| **Reconnus en l'état — le manifeste date d'avant le correctif de phase 6a** | **4** | **communes de Fronton et Labarthe-sur-Lèze (31)** |
| Hors champ pour de bon (statistiques, Fédération Wallonie-Bruxelles, vélos) | ~70 | — |

**data.gouv.fr — 95 fichiers écartés dans 50 jeux** : 41 en-têtes non détectés
(dont le Département d'Ille-et-Vilaine), 19 échecs réseau sur
`datacat.datalocale.fr`, 8 fichiers au format OpenDocument que le lecteur ne
sait pas ouvrir, 3 liens morts chez Rennes Métropole, et une dizaine de cas
uniques (`Libellé tiers`, `BGT_NOM`, en-tête d'Antibes lu en une seule colonne).
**Aucun n'est récupérable sans toucher au code.**

Ce que cela vaut, honnêtement : **69 des 91 jeux récupérables sont la Ville de
Rennes**, déjà présente dans le corpus par sa source héritée. Le gain est en
PROFONDEUR (des exercices, des séries budgétaires), pas en couverture. Les
seules collectivités vraiment nouvelles au bout du compte sont Blois/Agglopolys
et deux communes de Haute-Garonne.

---

## 2. Les anomalies connues

Toutes signalées dans le rapport de qualité, aucune corrigée en douce.

### 2a. Deux quarantaines d'unité — **60,3 Md€ mis de côté**

Même doctrine dans les deux cas : montants dans `amount_rejected_eur`, lignes
conservées et consultables, drapeau `amount_unit_suspect`. La collectivité
montre son activité, aucun montant douteux n'entre dans un total.

**`plf-jaune-2013` (exercice 2011) — 12,30 Md€, 21 167 lignes. LE DOSSIER EST
COMPLET, LA DÉCISION APPARTIENT À L'UTILISATEUR.**

Preuve rejouable : `python3 scripts/analyse/verifier_unite_2011.py`. Cinq
faisceaux, tous mesurés sur la table canonique, agrégats exclus :

| Comparaison, association par association | associations | médiane | quartiles |
|---|---|---|---|
| **2011 / 2012** | 11 382 | **10,00** | 7,38 – 11,94 |
| **2011 / 2010** | 9 479 | **10,00** | 7,50 – 12,00 |
| 2010 / 2012 *(témoin)* | 10 614 | 1,00 | 0,72 – 1,26 |
| 2012 / 2013 *(témoin)* | 15 026 | 1,00 | 0,85 – 1,25 |
| 2013 / 2014 *(témoin)* | 14 741 | 1,00 | 0,88 – 1,33 |
| 2014 / 2015 *(témoin)* | 15 180 | 1,00 | 0,72 – 1,13 |

Deux comparaisons **indépendantes** rendent exactement 10,00 ; les quatre
témoins rendent exactement 1,00, ce qui prouve que la méthode lit 1 quand rien
ne cloche. S'ajoutent : **100,0 % des montants de 2011 sont multiples de 10**
(70 à 84 % les autres années — un décalage de virgule fabrique un zéro final sur
chaque ligne) ; le montant **moyen par ligne divisé par dix vaut 58 212 €, contre
58 251 € en 2012** — 0,07 % d'écart ; et le total divisé par dix (1,23 Md€) se
range entre 2010 (1,48) et 2012 (1,86), alors que tel qu'il est publié il pèse
plus que les six exercices suivants réunis.

Vérifié aussi : **le publieur n'a pas corrigé**. L'API `data.economie.gouv.fr`
sert toujours 71 070 € pour le poste Fonjep de CRESCENDO, dont l'unité est
d'environ 7 107 €.

**Ce que cela n'établit pas : notre droit de diviser.** « Pas de correction de
montant » est la doctrine du projet. Diviser par dix 21 167 lignes sur la foi de
notre propre analyse, c'est prendre sur nous de réécrire ce qu'un ministère a
publié. La quarantaine tient donc tant que l'utilisateur n'a pas tranché — et
le dossier est désormais complet pour qu'il puisse le faire.

**`metropole-lyon` — 48 Md€, 9 081 lignes.** Médiane à 1 584 200 €, minimum
100, 85 % de valeurs multiples de 100 : tout indique des centimes lus comme des
euros. `data.grandlyon.com` renvoie **401**, l'amont n'est pas vérifiable.
Bloqué au même endroit que 1b.

Idem, plus petit : deux lignes de `ville-boulogne-billancourt` à 750 M€ et
75 M€ (`PLAFOND_DOUTEUX`).

### 2b. Identifiants et champs manquants

| Défaut | Lignes |
|---|---|
| Sans RNA | 2 406 141 |
| Sans SIRET | 886 487 |
| Sans URL de source | 773 870 |
| Département inexploitable | 298 590 |
| **Année déduite du libellé** (`year_from_label`) | **120 796** |
| Sans année | 45 107 |
| Montant nul | 77 144 |
| **SIRET détruits par un tableur** (`2,19301E+13`) | **29 159** |
| Montants invraisemblables, exclus des totaux | 122 |
| Doublons internes à une source, conservés et signalés | 97 103 |

Les SIRET en notation scientifique **ne sont pas réparables** : Excel n'a gardé
que six chiffres significatifs. Le vrai correctif est de re-moissonner l'amont.

Les 120 796 lignes à année déduite ne sont pas un défaut mais une provenance :
`year_provenance = "inferred"`. Elles sont exactes tant que le publieur nomme
correctement ses fichiers, et le drapeau permet de les isoler si un doute naît.

### 2c. `cd-finistere` — 5 442 lignes au nom de donateur détruit

Les octets du fichier hérité sont `\xef\xbf\xbd` (U+FFFD) : « Conseil
D<?>partemental du Finist<?>re ». Irrécupérable depuis ce fichier. Ces lignes
ne se dédupliquent pas avec leurs jumelles bien encodées. À re-moissonner.

### 2d. Quatre donateurs que l'appariement rate

Visibles dans `couverture.json`, champ `donateurs_non_apparies` :

- `VILLE DE VINEUIL 41350` — le code postal collé au nom fait échouer
  l'appariement. Il *identifie* pourtant la commune (41269, contre Vineuil dans
  l'Indre) : le lire serait plus précis que le nom seul, pas moins.
- `DEPARTEMENTDESHAUTESPYRENEES` — libellé sans séparateurs à la source.
- `CONSEIL D PARTEMENTAL DU FINIST RE` — le U+FFFD de 2c.
- `DEPARTEMENT D ILLE ET VLAINE` — faute de frappe du publieur.

Aucun n'est corrigé : deviner ferait courir le risque d'apparier une
collectivité qu'on ne couvre pas. Les trois derniers coûtent zéro couverture
(ces collectivités sont déjà couvertes par d'autres libellés).

---

## 3. Dette mineure

- **Le doublon Baule** : 182 lignes, 365 k€. `communes-pays-loire` étiquette
  « Commune de La Baule » ce qui est en réalité **Baule dans le Loiret**. On ne
  corrige pas le libellé : deviner qu'un « La Baule » veut dire « Baule »
  ailleurs fondrait deux communes réelles. Détail dans `CLAUDE.md`.
- **`measure_of` et les tirets bas : MESURÉ le 21/08/2026, correctif NON
  appliqué — voir §4.** Le défaut est réel mais minuscule, et le corriger seul
  ferait perdre de l'argent réel plutôt que d'en dédoubler.
- **Le fichier PLF 2024 est vide à la source** (« csv: fichier vide ou non
  tabulaire ») : l'exercice 2022 manque donc au corpus PLF Jaune.

---

## 4. « Voté / versé » — mesuré puis tranché (21/08/2026)

Chantier n° 3 de l'ordre recommandé. **Mesuré d'abord, corrigé ensuite — mais
pas là où on croyait.** Mesure rejouable :
`python3 scripts/analyse/mesure_measure.py` (demande `duckdb`).

### 4a. Le défaut signalé est réel, et minuscule

`fold` ne ramène ni « _ » ni « - » à l'espace, alors que tous les motifs de
`_MOTS_VERSE` sont écrits avec des espaces. Ramener les séparateurs à l'espace
avant l'appariement fait basculer **2 sources, 8 lignes, 850 244 €** — les deux
fichiers `subventions-versees-aux-associations-{2019,2020}.xlsx` de la Ville de
Chatou.

Et cela ne règle pas le cas de Grenoble cité jusqu'ici : dans
`subventions_fonctionnement_versees_associations_2019.csv`, les séparateurs une
fois ramenés à l'espace, le libellé donne « subventions fonctionnement versees
associations », qui ne contient toujours pas la suite contiguë « subventions
versees ». **Le motif est un bigramme, pas un mot** : les séparateurs n'étaient
que la moitié du défaut.

### 4b. Une détection par mots attrape Grenoble — et coûte cher

Variante testée : reconnaître « versées », « mandatées », « paiements »… comme
des MOTS. Elle fait basculer 34 sources, 2 518 lignes, 54,41 M€. Mais en
regardant si la même collectivité a publié le **même exercice** en « attribué »
ailleurs :

| | lignes | montant |
|---|---|---|
| Vrai double compte (contrepartie « attribué », même exercice) | 678 | 6,36 M€ |
| **Sans contrepartie — sortiraient des totaux à perte** | **1 840** | **48,05 M€** |

Grenoble-Alpes Métropole en est l'exemple : ses exercices 2015, 2016, 2019,
2020, 2022 et 2023 sont déjà dédupliqués contre la source héritée
`metropole-grenoble` par la clé métier — la mesure n'y sert à rien. Mais 2017,
2018 et 2021 n'existent QUE par ces fichiers « versées ». Les basculer
effacerait trois exercices entiers d'un EPCI, 41,49 M€.

**Conclusion : ne pas appliquer le correctif seul.** Il déplace peu, et ce
qu'il déplace est presque entièrement de l'argent réel non dédoublé.

### 4c. Ce que la mesure a trouvé à la place — **TRANCHÉ, phase 8**

Le vrai défaut n'était pas dans la reconnaissance, il était dans la règle : elle
retirait 1,86 Md€ que rien ne dédoublait, dont la totalité du département de
Loire-Atlantique (778,3 M€, 28 573 subventions), qui ne publie que ses paiements
et n'apparaissait donc nulle part.

| Lignes classées « versé » | lignes | montant |
|---|---|---|
| Total exclu par la seule règle « versé » | 99 837 | 7,45 Md€ |
| · avec contrepartie « attribué », même donateur, même exercice | 53 635 | 5,59 Md€ |
| · **sans aucune contrepartie** | **46 202** | **1,86 Md€** |

**Arbitrage de l'utilisateur (21/08/2026) : afficher les deux valeurs.** Le site
montre désormais « dons votés » et « dons payés » côte à côte, et ne les somme
jamais. Personne n'est effacé, et aucun euro n'est compté deux fois.

### 4d. Les doublons que la clé métier ne voit pas — **signalés, non corrigés**

`ville-grenoble` et `ville-grenoble-2016` publient la même subvention sous
« SUBVENTION PROJET » d'un côté et « MUSIQUES » de l'autre : même bénéficiaire,
même donateur, même exercice, même montant, deux clés — parce que l'objet fait
partie de la clé métier.

**Chiffre corrigé le 21/08/2026 : 18 369 groupes, 22 867 lignes, 442,62 M€.**
Une première mesure annonçait 4 784 groupes et 144,84 M€ : elle appariait les
donateurs sur leur LIBELLÉ, quand la clé métier, elle, les apparie sur leur
IDENTITÉ (`identite_donateur`). Mesurer autrement que ne compte le code, c'est
sous-estimer — le bon chiffre est celui qui utilise la même clé.

Ils restent **dans les totaux**, et sont désormais signalés dans le rapport de
qualité (`doublons_probables_hors_cle`) et sur `methode.html`. Retirer l'objet
de la clé n'est PAS la solution : deux subventions réellement distinctes de même
montant à la même association la même année se fondraient — même asymétrie que
pour les homonymes, et du mauvais côté.

### 4e. Deux autres signalements ajoutés le 21/08/2026

- **`nom_de_beneficiaire_numerique`** — 7 121 lignes, 1,80 Md€. La source a
  recopié le SIREN ou le RNA dans la colonne du nom : le site affiche
  « 911671485 » comme bénéficiaire de 911,7 M€. Identifiable mais illisible, et
  ces lignes ne se rapprochent pas de celles du même organisme correctement
  nommé.
- **`nature_devinee_gros_montants`** — 166 430 lignes, 49,88 Md€ comptés comme
  « association » parce que la source ne dit pas le contraire. On y trouve SNCF
  Voyageurs, SNCF Réseau, l'Agence France-Presse, le Centre national du cinéma,
  l'Association internationale de développement (Banque mondiale). **Rien n'est
  retiré** — deviner une exclusion effacerait des associations réelles, et c'est
  la doctrine du projet — mais la liste des vingt plus gros est dans le rapport,
  et c'est un arbitrage métier à faire un jour.

---

## 5. Ce que la phase 10 ouvre, et qui n'est pas fait

Le dénominateur et l'angle mort sont construits ; le site n'en montre encore
qu'une partie. Ces quatre chantiers n'ont besoin d'aucune source nouvelle —
les données sont déjà dans le dépôt.

### 5a. La carte de couverture — **FAIT le 22/08/2026**

La carte a désormais deux vues, sous une bascule : « ce qui est publié » (les
trois états, inchangés) et « ce qui nous échappe » (la part connue des
subventions communales, par département).

Six paliers plutôt qu'un dégradé continu, parce que la distribution l'impose :
sur 101 départements, **59 sont à zéro**, 13 sous 1 %, et trois seulement
dépassent 50 %. Un dégradé linéaire aurait écrasé tout le reste dans la même
teinte pâle. Le zéro garde une couleur à lui, grise et récessive : « le site
n'en connaît rien » est une absence, pas le bas d'une échelle de bleus.

Le tableau bascule avec la carte — sans cela, la nouvelle échelle n'aurait pas
son équivalent écrit, et une couleur porterait seule l'information.

### 5b. La fiche d'une commune — **FAITE le 22/08/2026**

**Ce que ça a changé.** Jusqu'ici, un visiteur qui cherchait sa commune n'obtenait
rien : ou bien elle fait partie des 90 couvertes, ou bien le site est muet. Avec
le dénominateur, il n'y a plus AUCUNE commune sur laquelle le site n'ait rien à
dire — 34 829 des 34 936 déclarent un compte 6574. La fiche répond enfin, pour
n'importe laquelle : « votre commune a mandaté X € à des associations en 2023,
et le site n'en connaît aucune ligne » ou « … et le site en connaît Y € ».

C'est aussi la seule pièce de la phase 10 qui parle à quelqu'un qui ne s'occupe
pas de statistiques : un habitant, un élu, un journaliste local.

#### Les chiffres, mesurés le 22/08/2026

| | |
|---|---|
| Communes déclarantes dans `denominateur.json` | **34 829** |
| Dont le site connaît au moins un versement nominatif | **82** — 78 en voté, 10 en payé, 6 dans les deux |
| **Communes qui déclarent sans que le site en connaisse rien** | **34 751** |
| Exercices déclarés par commune | médiane **16** (2010-2025), minimum 1 |
| Communes dont le total déclaré est nul | **0** |

#### Le format à produire

Un fichier par département, comme `data/aggregates/departements/` déjà servi
au clic sur la carte d'accueil :

```
data/aggregates/denominateur-communes/<dep>.json.gz
  { "departement": "35",
    "communes": { "35238": { "n": "Rennes",
                             "d": {"2010": 32982947, "2011": 33977340, …},
                             "v": {"2011": 47915270, "2012": 74562260, …},
                             "p": {} } } }
```

`d` est le déclaré au compte 6574, `v` ce que le site connaît de voté, `p` de
payé. Les valeurs ci-dessus sont les vraies : Rennes déclare 594,1 M€ sur
2010-2025 et le site en connaît 728,5 M€ de voté, soit **122,6 %** — le cas
type qui oblige à expliquer un dépassement plutôt qu'à le cacher.

**Poids mesuré en simulant le découpage : 101 fichiers, médiane 21 Ko
gzippés, maximum 52 Ko (Pas-de-Calais, 886 communes), 2,15 Mo au total.**
Chargé à la demande, jamais au premier écran — le budget du premier écran
(113 Ko) n'est pas touché.

*Résultat négatif à ne pas refaire* : omettre les clés `v` et `p` quand elles
sont vides ne gagne que 27 Ko sur 2,15 Mo. Gzip compresse déjà ces répétitions ;
ça ne vaut pas la complication.

#### Où la mettre, et pourquoi pas ailleurs

Sur **`couverture.html`**, sous la carte. C'est là qu'on se demande « et ma
commune ? », et cela n'ajoute ni page ni entrée de menu.

**Pas sur la carte d'accueil, et c'est la vraie raison de ce paragraphe.**
`data/aggregates/departements/<dep>.json.gz` existe déjà, mais il décrit les
associations SITUÉES dans le département — des bénéficiaires. Le dénominateur,
lui, décrit la commune qui PAIE. Les afficher dans le même panneau ferait lire
« Rennes : 594 M€ » comme de l'argent reçu par des associations rennaises alors
que c'est de l'argent versé par la ville. **Ce sont deux géographies opposées
et elles ne doivent jamais partager un écran sans le dire.**

**Sélection en deux temps plutôt qu'une recherche par nom** : un choix de
département, puis la liste de ses communes, tirée du fichier qu'on vient de
charger. Un index nom → code des 34 936 communes pèserait **274 Ko gzippés**
(785 Ko bruts) : mesuré, et trop cher pour le confort qu'il apporte. À garder
comme raffinement ultérieur, pas comme point de départ.

#### Ce que la fiche doit dire, et taire

- Le **déclaré par exercice**, en toutes lettres, avec la mention du compte
  6574 et de ce qu'il recouvre (« et autres personnes de droit privé »).
- Ce que le site en connaît, **voté et payé séparés**, jamais additionnés.
- Quand le site ne connaît rien : le dire comme une lacune du site, pas comme
  une absence de subventions. La formule doit distinguer « cette commune ne
  verse rien » (faux, elle déclare) de « nous n'avons pas la donnée » (vrai).
- Les budgets annexes sont INCLUS dans le déclaré : « ECOLE MUSIQUE-LUDRES »
  est un budget de la commune de Ludres, rattaché par son SIREN. Une fiche qui
  n'en dirait rien laisserait croire à une erreur quand le montant dépasse le
  budget principal.
- Une part **au-dessus de 100 %** est normale et doit être expliquée sur place :
  Rennes est à 122,6 % parce que le site connaît des montants VOTÉS quand la
  balance porte des montants MANDATÉS.

#### Les pièges connus qui attendent ce chantier

1. **Les communes fusionnées.** 12 002 lignes de balance (232,6 M€) ne sont
   rattachées à aucune commune du référentiel actuel : codes INSEE historiques
   de communes absorbées depuis, et quelques budgets annexes dont le SIREN
   n'apparaît sur aucun budget principal. Une fiche de commune nouvelle ne
   montrera donc pas l'historique de ses composantes. **Ne pas le reconstituer
   au jugé** — dire que la série commence à la fusion.
2. **Le rattachement d'un versement à une commune passe par le libellé du
   donateur**, avec l'appariement de `build_couverture.py`, pas par une clé.
   Une commune peut donc déclarer et avoir des versements dans le site sans
   que les deux se rejoignent, si son libellé est inhabituel. La fiche montre
   alors « rien de connu » à tort — dans le sens de la sous-estimation, comme
   toujours, mais il faut le dire dans la page.
3. **Paris est à la fois commune et département.** Sa fiche communale
   (3,96 Md€ déclarés) ne doit pas être présentée à côté de la ligne
   départementale sans préciser qu'avant 2019 il y avait deux collectivités.

#### Contrôles à ajouter à `verify.py`

- la somme des fichiers servis = le détail de `denominateur.json` (aucune
  commune perdue au découpage) ;
- chaque commune est dans le fichier de SON département ;
- aucune commune servie n'est absente du référentiel INSEE.

#### Ce qui a été livré, et ce que la mise en œuvre a appris

`build_fiches_communes.py` écrit les 101 fichiers (médiane **21,8 Ko** gzippés,
maximum 53,1 Ko, **2,26 Mo** au total), `couverture.html` porte le sélecteur en
deux temps et la fiche, et `verify.py` gagne **quatre** contrôles — aucune
commune perdue au découpage, chacune dans son département, toutes au
référentiel, et la somme des fichiers servis égale le détail canonique.
**48 contrôles sur 49.**

Deux choses que la spécification n'avait pas vues :

- **Arrondir en millions affichait « 0 M€ » sur une fiche communale.** Rennes
  2016 vaut 10 k€ de subventions connues, 2017 en vaut 125 k€ : le site les
  montrait comme « 0 M€ », c'est-à-dire comme rien. Le formatage descend
  désormais au millier puis à l'euro — un village déclare 1 680 €, pas
  « 0 M€ ».
- **Une année absente n'est pas une fusion.** La rédaction prévue disait
  « la série commence en 2019, le plus souvent parce que la commune est née
  d'une fusion » : c'est une devinette, et le plus souvent fausse. La balance
  ne porte une ligne que si le compte a servi — la commune peut n'avoir rien
  versé, avoir imputé ailleurs, ou ne pas encore exister. La fiche énonce les
  trois causes au lieu d'en choisir une.

La fiche est partageable par son adresse : `couverture.html#commune=35238`.

### 5c. L'angle mort — **CLASSÉ le 22/08/2026, et la consigne a changé**

**Ce paragraphe demandait un travail impossible.** Il présentait les 3 220 gros
déposants non reconnus comme « une liste de travail » : 3 220 noms à examiner un
par un, ce que personne ne fera jamais. Une liste n'était pas le livrable — la
CAUSE de chaque absence l'est, et elle se calcule sans le moindre arbitrage
humain.

Les 12 938 organismes non reconnus sont désormais rangés sous six causes,
toutes lues dans une donnée existante :

| Cause | Organismes | Part |
|---|---|---|
| Reconnu par nom + département, sans identifiant commun | 157 | 1,2 % |
| **Fonds de dotation ou fondation — vit de dons privés** | **3 967** | **30,7 %** |
| Nom connu du site, mais dans un autre département | 531 | 4,1 % |
| Aucun financeur ne publie sur ce territoire | 755 | 5,8 % |
| **Territoire dont le site connaît moins de 1 % du 6574 communal** | **3 430** | **26,5 %** |
| **Aucune explication automatique** | **4 098** | **31,7 %** |

**68,3 % des absences s'expliquent donc toutes seules.** Le reste n'est pas une
liste à traiter : c'est la mesure de ce qu'on ignore, et la page le dit en ces
termes — *aucune donnée publique ne permet de savoir si un organisme donné
reçoit de l'argent public*.

#### Deux résultats négatifs, mesurés le 22/08/2026

- **L'appariement par identifiant n'était pas trop strict.** On pouvait croire
  le chiffre de 12 938 gonflé par des organismes que le site connaît sans
  identifiant. Testé en appariant sur NOM + DÉPARTEMENT, la règle d'identité
  que le site s'applique déjà à lui-même : **157 organismes récupérés, soit
  1,2 %**. L'angle mort est réel.
- **Les jeux `osop-*` du portail DILA ne disent pas l'origine des ressources.**
  `SOURCES-RECEPTION.md` les signalait comme « une typologie d'organisation »
  prometteuse. Vérifié : `osop-comptes-de-resultats` (68 477 lignes) ne couvre
  que les **syndicats de salariés et d'employeurs**, et son champ `ressources`
  est une TRANCHE (1 à 4), pas une origine. Rien à en tirer pour distinguer
  l'argent public de l'argent privé.

#### Ce qui reste possible, et qui ne demande toujours personne

Les **531 « nom connu ailleurs »** sont le seul gisement d'amélioration
technique : le Journal officiel donne le département du SIÈGE, le site celui de
l'adresse publiée par le financeur. Les rapprocher demanderait une règle
d'identité inter-registres, donc un risque de faux positif — à ne pas ouvrir
sans mesurer d'abord combien de ces 531 sont de vrais homonymes.

### 5d. Le dénominateur avant 2019, hors communes — *bloqué, mesuré*

Les jeux par nature ne remontent qu'à 2019 pour les départements, les régions
et les EPCI. La présentation croisée nature-fonction couvre 2012-2021 mais
**ne peut pas servir de substitut** : vérifié sur 2020, elle ne contient que
les collectivités au-dessus du seuil de la présentation fonctionnelle (communes
2 438 M€ contre 3 044, groupements 1 413 contre 2 255). Chercher ailleurs, ou
assumer la borne de 2019.

---

## Ordre recommandé

*Révisé le 22/08/2026, après la phase 10.*

1. ~~Colorer la carte de couverture par la part connue (5a)~~ — **fait le
   22/08/2026.** Ce que la carte montre maintenant, et qu'aucun tableau ne
   disait aussi vite : la Bretagne et l'Ille-et-Vilaine bien couvertes, tout
   un quart nord-est à zéro, et 59 départements sur 101 dont le site ne
   connaît rien des subventions communales.
2. ~~La fiche d'une commune (5b)~~ — **faite le 22/08/2026.** Il n'existe plus
   une seule commune sur laquelle le site n'ait rien à dire.
3. ~~Les 3 220 gros déposants non reconnus (5c)~~ — **classés le 22/08/2026,
   et la consigne était mauvaise.** Une liste de 3 220 noms n'est traitable par
   personne : ce sont les CAUSES qui sont le livrable, et 68,3 % des absences
   s'expliquent automatiquement. Leçon à retenir pour la suite : quand un
   chantier se formule « il faudra vérifier N éléments à la main » avec N au-delà
   de quelques dizaines, c'est le chantier qui est mal posé, pas le lecteur qui
   manque de courage.
4. **Décider ce que devient le site sans changement d'échelle.** Le plafond de
   couverture est atteint, et la valeur du site se déplace vers ce qu'il FAIT de
   ce qu'il a — croisements, séries, exports, lisibilité — plutôt que vers un
   corpus plus gros. La phase 10 en est un exemple : elle n'a pas ajouté une
   subvention, elle a rendu mesurable ce qui manque.
5. **Les jeux écartés à rouvrir (1d)** — le seul gisement qui ne dépende de
   personne. Trois correctifs de reconnaissance (en-tête mal détecté, `beneficiare`,
   `organismes`) rouvrent ~91 jeux, mais 69 sont la Ville de Rennes : gain en
   profondeur, pas en couverture. Demande un re-moissonnage complet.
6. **La levée de la quarantaine 2011 (2a)** — 12,3 Md€ et un huitième de
   l'histoire du site en dépendent.
7. ~~`measure_of` et les tirets bas~~ — **fait (§4, phase 8)**. Le correctif de
   séparateurs n'a PAS été appliqué (8 lignes, 850 k€, toutes à perte). À sa
   place, deux changements de doctrine tranchés par l'utilisateur : voté et payé
   s'affichent côte à côte, et seuls les DONS entrent dans les totaux.
8. **Ne pas relancer le moissonnage pour la couverture.** Les deux canaux sont
   mesurés épuisés (1a). Y revenir sans une source nouvelle serait du travail
   jetable.

---

## Comment reprendre à froid

```bash
# Le pipeline entier, moissonnages exceptés (ils ont leur cache) :
bash scripts/pipeline/tout_reconstruire.sh

# Les moissonnages, quand on veut rafraîchir l'amont :
python3 scripts/pipeline/fetch_scdl.py     # data.gouv.fr
python3 scripts/pipeline/fetch_ods.py      # 41 portails Opendatasoft
python3 scripts/pipeline/fetch_plf_jaune.py
python3 scripts/pipeline/fetch_balances.py        # compte 6574 DGFiP (phase 10)
python3 scripts/pipeline/fetch_jo_comptes.py      # comptes déposés au JO
python3 scripts/pipeline/fetch_totaux_controle.py # D751 des comptes nationaux

# Le banc de mesure (CHROMIUM_PATH si Playwright cherche une révision absente) :
node scripts/bench/measure.js --label <phase>
```

`normalize_legacy.py` a besoin de `data/sources/*.js`, retirés du dépôt :
`git checkout 0b14348 -- data/sources` avant de le rejouer — **et
`git rm -r --cached data/sources` avant de commiter**, sinon les 835 Mo
repartent dans l'historique.

**`verify.py` vient EN DERNIER** (plusieurs contrôles comparent l'index de
recherche à la table canonique) et **doit rester vert** : 49/50 aujourd'hui,
le seul échec étant « conservation des lignes », qui compare la table aux
parties d'assemblage — non versionnées, donc absentes tant que les
normaliseurs n'ont pas été rejoués.

Travailler sur `main`, et seulement `main`.
