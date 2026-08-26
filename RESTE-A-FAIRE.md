# Ce qui reste à faire

État arrêté au **23/08/2026**, après la phase 12. Chiffres mesurés, pas estimés :
ils viennent de `data/canonical/quality-report.json`, `couverture.json`, des
manifestes de moissonnage et du banc `bench/phase7.json`.

À lire après `CLAUDE.md` (contexte et pièges) et `ROADMAP.md` (ce qui a été fait
et pourquoi).

> **Avertissement de méthode.** La version précédente de ce fichier annonçait
> « ~178 fichiers » à dépivoter et « 371 liens morts » : les manifestes en
> portaient respectivement 37 et deux hôtes. Un chiffre écrit ici sans avoir été
> relu dans les manifestes envoie la session suivante sur le mauvais chantier.
> **Vérifier avant d'écrire, et dire d'où vient le chiffre.**
>
> *Et cet avertissement ne suffit pas.* Le §1d a été écrit en le respectant, puis
> a vieilli en une journée : deux de ses trois correctifs ont été appliqués par
> la phase 9 sans qu'il soit relu, et son inventaire décrivait un moissonnage
> périmé. **Un chantier daté doit être re-mesuré avant d'être ouvert, pas
> seulement avant d'être écrit.**

---

## Où en est le site

Les phases 0 à 13 sont faites. Sur les quatre objectifs de départ — vitesse,
données justes et exhaustives, recherche croisée, lisibilité — **trois sont
atteints**. L'accueil charge en 0,06 s, la recherche croisée répond en
quelques millisecondes sur 2,8 M de lignes sans backend, et depuis la phase 13
elle n'attend plus rien : le champ de saisie est utilisable en 0,3 s au lieu de
4,5 s, et tout ce que le site montre a une adresse partageable.

**L'exhaustivité est le seul objectif encore largement ouvert, et la phase 7 a
montré qu'elle ne s'ouvrira plus par moissonnage.**

| | valeur |
|---|---|
| Lignes servies | 2 811 070 |
| **Dons votés** | **148,40 Md€** |
| **Dons payés** (à côté, jamais additionnés) | **10,43 Md€** |
| Ingéré mais pas un don (prestations, remboursements, nature) | 1,57 Md€ |
| Sources | 698 |
| Bénéficiaires résolus | 427 451 |
| Dont cumulant 3 échelons ou plus | 9 566 *(10 128 en phase 11 : 554 de ces cumuls étaient un échelon EPCI fantôme, cf. §1e)* |
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

| Échelon | Avec données | Univers | phase 11 |
|---|---|---|---|
| Communes | **95** | 34 936 | 94 |
| EPCI | **31** | 1 335 | 32 |
| Départements | **35** | 101 | 35 |
| Régions | **6** | 18 | 6 |

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

### 1d. Les jeux écartés — **FAIT le 23/08/2026, et le §1d précédent était faux**

Ce paragraphe annonçait « trois correctifs de reconnaissance, ~91 jeux, dont 69
sont la Ville de Rennes ». **Deux des trois correctifs étaient déjà appliqués**
depuis la phase 9 (`beneficiare`, `organismes`), et son inventaire datait du
21/08, avant le re-moissonnage. Ses « deux communes de Haute-Garonne vraiment
nouvelles », Fronton et Labarthe-sur-Lèze, publient **zéro ligne** : le jeu est
vide à la source.

Re-mesuré sur les manifestes du jour, puis **vérifié sur la donnée téléchargée**
et non sur le seul libellé. Sept graphies ajoutées :

| Graphie | Rôle | Ce qu'elle rouvre |
|---|---|---|
| `liborgabenef` + `mtsubv` | bénéficiaire, montant | Région Île-de-France, 22 958 versements |
| `mandate` | montant, **en dernier** | Maine-et-Loire, GrandSoissons, Grand Paris Sud |
| `organisation` | bénéficiaire | Ville de Montreuil |
| `destinataire`, `destinataires` | bénéficiaire | Saint-Maur-des-Fossés |
| `associations` | bénéficiaire | Fleury-sur-Orne, Issy, Noyal-Châtillon |

**Le résultat, mesuré :**

| | phase 10 | maintenant |
|---|---|---|
| Communes | 90 | **94** |
| EPCI | 31 | **32** |
| Départements | 34 | **35** |
| Sources | 658 | **681** |
| Lignes | 2 809 711 | **2 817 042** |
| Cumuls ≥ 3 échelons | 9 800 | **10 128** |

Nouvelles : Aix-en-Provence (12,66 M€), Saint-Maur-des-Fossés (3,71 M€),
Fleury-sur-Orne, Moissy-Cramayel, GrandSoissons Agglomération (2,18 M€) et le
**département de la Seine-Maritime** (973 lignes, 33,74 M€).

#### Ce que l'ouverture a cassé, et qu'il a fallu réparer

Rouvrir des jeux fait entrer des fichiers que le reste de la chaîne n'avait
jamais eu à lire. Quatre s'y sont cassés :

- **La première ligne, quand elle est déjà un en-tête valide, gagne.**
  `organisation;montant;thematique;type` (Montreuil) ne porte qu'un mot-repère,
  quand chacune de ses lignes de données en porte deux : le détecteur prenait la
  ligne 7 et les 270 lignes étaient écartées pour « montant illisible ».
  `read_rows` reçoit un prédicat facultatif, que les quatre lecteurs de
  subventions lui passent — moissonneur et normaliseur ne peuvent plus lire deux
  en-têtes différents. Mesuré sur les 935 fichiers bruts : 4 changent, tous des
  corrections, aucune régression.
- **« code » disqualifie l'attribuant** : GrandSoissons publie un `Code
  Collectivité` qui ne contient que « 1 ». Corrige au passage la Ville de
  Soissons, déjà présente, dont le donateur se lisait dans `Code INSEE
  collectivité`.
- **Le repli du donateur ODS remonte au publieur PUIS à l'éditeur du portail** :
  Saint-Maur publie sous « Direction des sports », un service qui ne se rattache
  à aucune collectivité.
- **Les séparateurs sont ramenés à l'espace dans `measure_of`**, et là seulement :
  Fleury-sur-Orne était « voté » côté portail (`subventions_versees`) et « payé »
  côté data.gouv.fr (« Subventions versées »), pour la même donnée.

#### Et un faux à 1,67 Md€, trouvé en chemin

**Une même colonne ne peut pas être à la fois le bénéficiaire et le montant.**
Six fichiers déjà RETENUS l'étaient ainsi — le titre du rapport lu comme un
en-tête. La Chambre de Commerce Seine Mer Normandie publiait un bénéficiaire
« 911671485 » pour 911 671 485 €, « W761003097 » pour 761 003 097 € : un SIREN
et un RNA lus comme des euros. **C'est l'origine du cas que le rapport de
qualité signalait sans en connaître la cause** — `nom_de_beneficiaire_numerique`
tombe de 1 798 M€ à 125 M€. Le total voté baisse donc de 1,34 Md€ **en gagnant
23 sources** : c'est une correction, pas une perte.

#### Deux correctifs écartés, avec leur raison mesurée

- **`total` nu** ferait entrer Blois 2020-2022, dont la colonne de noms s'appelle
  littéralement `empty` et dont la colonne `associations` ne porte que le code
  « P1 ». Blois 2019 et 2023, eux, ont un vrai `denomination` / `noms`.
- **`somme` nu** n'ouvre que des comptes administratifs de la Ville de Rennes,
  déjà largement présente, que `measure_of` étiquetterait « voté » alors qu'un CA
  est de l'exécution budgétaire.

#### Ce qui reste écarté, et pourquoi ça n'en vaut pas la peine

**172 jeux ODS et 197 fichiers data.gouv.fr.** Sur les jeux ODS dont les colonnes
sont enregistrées, **8 passeraient les règles actuelles et tous portent ZÉRO
ligne** : le gisement de reconnaissance est épuisé.

Ce qui reste tient en trois familles, aucune récupérable sans deviner :
la **Ville de Rennes** (une trentaine de jeux, ~20 000 lignes) dont les comptes
administratifs nomment leur montant `total_des_mandats_emis`, `provisions_par_tiers`
ou `bp_2013` et leur bénéficiaire `libelle` ; des **statistiques** qui ne nomment
personne (vélos subventionnés en Île-de-France, aménagements cyclables) ; et
19 échecs réseau chez `datacat.datalocale.fr`.

#### Ce que le Département de Maine-et-Loire ne publie plus

Son fichier de 17 756 mandatements se déduplique **entièrement** contre la source
héritée qui les portait déjà : aucun gain. Ses trois exercices récents, eux,
échappent pour une autre raison — **il a cessé de publier le nom du bénéficiaire
à partir de 2017**. 1 781 lignes, 22,1 M€, dont **96,9 % ont un SIRET** et aucune
raison sociale. Le pipeline écarte les lignes sans nom. Les récupérer sur le seul
SIRET est un **arbitrage de doctrine** — un bénéficiaire identifié mais sans nom
affichable —, pas un correctif de reconnaissance. À trancher par l'utilisateur.

### 1e. Rennes — **FAIT le 23/08/2026, et le chantier n'était pas celui qui était écrit**

Le §1d refermé annonçait « une trentaine de jeux de la Ville de Rennes à
rouvrir, ~20 000 lignes, gain en profondeur ». Les fichiers étaient **déjà dans
le site**, et mal classés.

**« CA 2014 » est un compte administratif.** `measure_of` ne reconnaissait
« compte administratif » qu'en toutes lettres, et Rennes ne l'écrit jamais
autrement. Le site comptait donc le budget primitif ET son exécution du même
exercice comme deux subventions VOTÉES : Rennes 2012 pesait 74,56 M€ pour un
budget associatif d'environ 54 M€. Mesuré sur tout le corpus : **1 828 lignes,
227,2 M€**, chez Rennes, Lorient Agglomération et la CC du Val d'Essonne.

**Un compte de publication servait de donateur.** Les fichiers budgétaires de la
Ville de Rennes sont déposés sur data.gouv.fr par « Rennes Métropole en accès
libre ». Faute de colonne d'attribuant, le site créditait **l'EPCI de 396 M€
versés par la COMMUNE**, et ces lignes ne se dédupliquaient pas avec la même
donnée publiée sur le portail.

| | phase 11 | maintenant |
|---|---|---|
| Lignes | 2 817 042 | **2 811 070** |
| Sources | 681 | **698** |
| Communes | 94 | **95** |
| EPCI | 32 | **31** |
| Dons votés | 148,34 Md€ | **148,40 Md€** |
| Dons payés | 10,04 Md€ | **10,43 Md€** |
| Cumuls ≥ 3 échelons | 10 128 | **9 566** |

**La couverture PERD un EPCI, et c'est juste.** Rennes Métropole n'a jamais rien
publié en propre : elle repasse de « données présentes » à « publie mais non
exploité ». Le site affirmait couvrir la métropole quand il ne couvrait que sa
ville-centre. Les cumuls à trois échelons tombent pour la même raison —
comparaison **exacte** des deux index de recherche : 567 bénéficiaires passent
sous trois échelons, dont **554 (97,7 %) en perdant précisément leur échelon
EPCI**, motifs dominants « commune,epci,inconnu » (328) et « commune,epci,etat »
(177). Ces cumuls n'existaient pas.

La série rennaise est enfin lisible, voté et payé côte à côte :

| exercice | voté (BP) | payé (CA) |
|---|---|---|
| 2012 | 53,78 M€ | 20,78 M€ |
| 2013 | 55,32 M€ | 14,69 M€ |
| 2014 | 56,24 M€ | 13,62 M€ |
| 2017 | 63,91 M€ | 47,86 M€ |
| 2019 | — | 50,94 M€ |

2019 n'a pas de voté parce que le site n'a pas le budget primitif 2019. C'est
une lacune vraie, pas un artefact.

**Deux effets de bord, tous deux des corrections.** Besançon entre dans la
couverture (4 050 lignes, 148,59 M€), rendu à sa commune au lieu de rester chez
« Open Data Bourgogne ». Et 421,54 M€ de la **DRAC des Pays de la Loire**
repassent de « région » à « État » : le repli par nom cherchait « region » en
sous-chaîne, et « Direction **région**ale des affaires culturelles » l'attrapait.

**Un invité imprévu, gardé.** Le motif `libelle`, nécessaire aux budgets
primitifs de Rennes, ouvre aussi les financements de la DRAC des Pays de la
Loire : 9 988 lignes, 363,66 M€ d'État. Son bénéficiaire est **concaténé avec
l'objet** (« O CAPITAINE MON CAPITAINE - Aide au projet Arts de la Rue pour… »),
donc inutilisable pour le rapprochement. Gardé quand même : l'erreur va vers la
fragmentation d'une association en plusieurs — une lacune — et non vers la
fusion de deux organismes, qui serait un mensonge.

**Ce qui reste dehors, mesuré.** Les comptes administratifs 2008-2010 de Rennes,
~13 000 lignes. **Deux millésimes du même publieur donnent aux mêmes noms de
colonnes des sens opposés** : en 2009, `provisions_par_tiers` porte le détail et
`total_des_mandats_emis` l'agrégat, proprement séparés ; en 2010, 414 des 461
lignes de `total_des_mandats_emis` sont des versements individuels, pour 125 M€
sur 1 920 lignes. Aucun choix de colonne unique n'est défendable.

---

### 1f. Le vocabulaire de la découverte — **MESURÉ le 26/08/2026, et ça change l'échelle**

Le §1a concluait que les deux canaux de moissonnage étaient épuisés, et le §1b
en tirait que « le plafond de couverture est celui d'aujourd'hui ». **Les deux
étaient faux, pour une raison qui n'est ni la source ni le format : le
vocabulaire des angles de découverte.**

Les six angles data.gouv.fr et les trois recherches Opendatasoft portaient tous
le mot « subvention », **et tous au pluriel**. Or :

| Mesure (26/08/2026) | Valeur |
|---|---|
| `q=subvention` sur data.gouv.fr | **684** jeux |
| `q=subventions` — l'angle utilisé | 545 |
| `q=données essentielles subvention` | **74** |
| `q=données essentielles subventions` — l'angle utilisé | 32 |
| Union des 6 angles d'origine | 665 jeux |
| Union des 15 angles élargis | **1 279** |
| Jeux jamais vus par le moissonneur | **699** |
| … retenus par `porte_des_subventions` | **115**, de 47 organisations |
| Opendatasoft : jeux appariés, 46 portails joignables | 602 → **1 311** |
| … jeux inédits / retenus | **708** / **87** (279 837 lignes annoncées) |

> **AVERTISSEMENT AJOUTÉ APRÈS COUP — le tableau ci-dessous compte des lignes
> DE FORME SUBVENTIONNELLE, pas des dons à des associations.** La distinction
> est tout le sujet du site, et elle a été mesurée au §1h : sur ces jeux
> inédits, **6,0 % du montant seulement va à une association**. Le « 17,34 Md€ »
> qui suit ne doit jamais être cité comme un apport de dons associatifs — il
> vaut **878 M€** une fois la nature juridique des bénéficiaires vérifiée.

**Apport brut, une fois les garde-fous posés et les doublons connus déduits :**

| | jeux | lignes | montant |
|---|---|---|---|
| **Apport brut** (forme subventionnelle, nature non vérifiée) | **105** | **151 520** | **17,34 Md€** |
| Catalogues de dispositifs — rejetés | 2 | 2 936 | 183,67 Md€ |
| PLF Jaune — déjà ingéré par `fetch_plf_jaune` | 2 | 187 935 | 16,24 Md€ |
| Investissements industriels, pas des subventions | 1 | 102 | 11,30 Md€ |
| AFD — aide internationale | 2 | 9 030 | 7,42 Md€ |
| Montant moyen > 5 M€/ligne — à instruire | 1 | 164 | 29,40 Md€ |

Le montant net est **avant déduplication**, qui en retirera une part inconnue :
le fédérateur Opendatasoft republie une partie de ce que data.gouv.fr sert
déjà.

**Ce que ça ouvre en couverture.** Absents de la table canonique, vérifié par
requête sur `donor_name_raw` : la **Commune de Saint-Claude** (5 exercices),
**Tourcoing**, **Fougères**, **Saint-Loubès**, **Comines**, le **Conseil
départemental d'Eure-et-Loir**, **Le Grand Charolais**, la **CC du Golfe de
Saint-Tropez**, **CALITOM**, l'**ADEME** et l'**ASP**. Et deux régions qui n'ont
aujourd'hui aucune donnée : la **Bourgogne-Franche-Comté** (6 127 lignes,
732,7 M€, SCDL parfait, aucun tag) et la **Réunion** (3 jeux côté
Opendatasoft).

**Fait dans cette phase** : les angles sont élargis dans `fetch_scdl.py`
(6 → 15) et `fetch_ods.py` (3 → 7), et deux garde-fous sont posés dans
`common.py`. **Reste à faire** : rejouer les moissonnages et toute la chaîne,
ce qui n'a pas été tenté ici — c'est un assemblage complet, et il déplacera les
totaux affichés.

**Trois arbitrages métier avant de rejouer**, qui ne sont pas les nôtres — et
que le §1h rend beaucoup plus tranchants qu'ils ne le paraissaient ici :

1. **L'ADEME** — 39 434 lignes, 11,21 Md€, 2021-2026, 99,3 % avec un
   identifiant valide. Mais l'ADEME finance surtout des entreprises et des
   collectivités, et sa source ne DÉCLARE pas la nature juridique : le défaut
   « association » de `beneficiary_kind` s'appliquerait, et le piège des
   « 49,88 Md€ comptés association sur une devinette » s'aggraverait d'autant.
   L'entrée est propre, la lecture ne l'est pas.
2. **Le Département de l'Indre** — 29,40 Md€ sur 164 lignes, soit 179 M€ par
   ligne. Même signature que Lyon et Boulogne-Billancourt. À instruire avant
   d'ingérer, et sans doute à mettre en quarantaine d'unité.
3. **Les aides aux entreprises** (Région Île-de-France, plan de relance) sont
   de vrais versements, mais pas à des associations. Les ingérer suppose de
   décider si le site les affiche hors totaux, comme les prestations facturées,
   ou pas du tout.

### 1g. Ce qui reste ouvert après cette mesure

- **La Région Normandie publie 8 millésimes que rien ne lit.** Ses jeux
  data.gouv.fr pointent vers `opendata.normandie.fr` en tant que **ArcGIS
  Hub** ; le portail a depuis migré vers Drupal / data4citizen et toutes les
  adresses enregistrées rendent du HTML. C'est le piège de l'« adresse
  périmée » (§ Grenoble), sur une famille de portails que le pipeline ne sait
  pas lire. Une région entière est derrière.
- **ArcGIS Hub et les portails CKAN / OneGeo ne sont balayés par personne.**
  `datasud.fr` (PACA), `datacat.datalocale.fr` (Nouvelle-Aquitaine),
  `opendata.lillemetropole.fr` (dataMEL) répondent, mais avec des API que ni
  `fetch_scdl.py` ni `fetch_ods.py` ne parlent. PACA et la Nouvelle-Aquitaine
  sont deux des douze régions sans données.
- **Les opérateurs de l'État n'ont jamais été cherchés en tant que tels.** Une
  seule agence de l'eau sur six est dans la table — Artois-Picardie, 9 171
  lignes, 1,02 Md€ — alors que les six versent aux associations
  environnementales. L'ADEME, mesurée ci-dessus, n'y était pas du tout.
  Chercher par ÉCHELON manquant, comme la phase 9 a cherché par collectivité
  manquante.
  *Contre-exemple à retenir, vérifié le 26/08/2026* : le sport n'est PAS un
  gisement. Le CNDS n'est dans la table que pour **le seul exercice 2015**
  (52 182 lignes), qui est aussi le seul qu'il ait publié ; et l'**Agence
  nationale du sport**, qui lui a succédé en 2019, n'a **aucune organisation ni
  aucun jeu sur data.gouv.fr** (`q="agence nationale du sport"` → 0,
  `q="projet sportif fédéral"` → 0). C'est une absence de publication, comme
  Nice ou Montpellier, et c'est à ce titre qu'elle doit être dite — pas un
  défaut de moissonnage à corriger.

### 1h. La nature du bénéficiaire — **FAIT (phase 15, 26/08/2026)**

> **CE CHANTIER EST FAIT.** Tout ce qui suit est le dossier qui l'a instruit ;
> il reste ici parce que les mesures et les réserves valent d'être relues, mais
> le correctif est en place : `fetch_nature_beneficiaires.py`,
> `enrich_nature.py`, quatre colonnes canoniques, la famille affichée sur la
> fiche, un sixième montant à l'export et trois contrôles dans `verify.py`.
> **Le total voté est passé de 148,40 à 110,71 Md€.** Ce qui reste ouvert est
> au §1g (Normandie, portails CKAN, agences de l'eau).

Mesuré le 26/08/2026, après une remise en cause de l'utilisateur : « je cherche
les dons aux associations et uniquement cela ». Le §1f n'avait pas vérifié la
nature juridique des bénéficiaires. Une fois vérifiée, il change de sens, et
l'audit trouve bien plus grave que ce qu'il cherchait.

**Méthode.** `recherche-entreprises.api.gouv.fr` rend la **catégorie juridique
INSEE** d'un SIREN. `92xx` = association, `93xx` = fondation, `7xxx` = personne
morale de droit public, le reste = privé lucratif. On interroge, par jeu, les
SIREN qui portent le plus d'argent — ce sont eux qui décident du total — et on
somme par catégorie. Rien n'est deviné : c'est l'INSEE qui déclare.

#### a. Les jeux inédits du §1f rapportent 878 M€, pas 17,34 Md€

| | montant | part associative |
|---|---|---|
| 37 jeux instruits (les autres n'ont aucun SIREN) | 14,69 Md€ | **6,0 %**, soit **878 M€** |
| … dont « Les aides financières de l'ADEME » | 11,21 Md€ | **1,1 %** — 71,2 % entreprises, 27,5 % droit public |
| … dont « Aides financières de la Région Î-d-F aux entreprises » | 1,24 Md€ | **0,1 %** |
| Les mêmes jeux, ADEME et aides aux entreprises retirées | 2,24 Md€ | **37,5 %**, soit **838 M€** |

**L'ADEME est donc à écarter**, et c'est un résultat, pas un échec : elle entre
proprement au validateur, elle publie un SCDL exemplaire, et elle ne finance
pas des associations. L'y faire entrer aurait ajouté **11,1 Md€ d'argent non
associatif** à un site qui en affiche 148,40 en tout.

Ce qui reste vaut d'être pris, et se lit par jeu :

| part associative | montant du jeu | source |
|---|---|---|
| **96,4 %** | 185,5 M€ | Ministère de la Culture — aides déconcentrées au spectacle vivant |
| **86,9 %** | 15,5 M€ | Département de la Savoie |
| **81,3 %** | 47,6 M€ | Ville de Toulouse (Toulouse Métropole) |
| **68,7 %** | 23,2 M€ | Ville de Grenoble |
| **65,9 %** | 8,2 M€ | Grand Paris Sud |
| 95 % et plus | ~2 M€ pièce | Montbéliard, Fougères, Saint-Claude, aides nationales à la création |
| 17,0 % | 732,7 M€ | Région Bourgogne-Franche-Comté — **78,7 M€ associatifs, et une région de plus** |

#### b. Et le site compte déjà ~17 Md€ qui ne sont pas des dons aux associations

C'est la trouvaille de cet audit, et elle ne porte pas sur de nouvelles sources.

`CLAUDE.md` note depuis la phase 6 que **49,88 Md€ sont comptés « association »
sur une devinette**, et que la liste des vingt plus gros contient SNCF
Voyageurs, l'AFP et le CNC — en concluant « c'est un arbitrage métier, pas un
correctif ». C'est resté non chiffré. Ça ne l'est plus :

| | |
|---|---|
| Lignes « association DEVINÉE » portant un SIREN exploitable | **740 835** |
| Montant | **40,89 Md€** |
| SIREN distincts | **103 879** |
| Échantillon interrogé (les 2 500 SIREN les plus gros) | **29,69 Md€ = 72,6 %** |
| **Réellement associatif** | **42,7 %** |
| **NON associatif** | **57,2 %**, soit **~17,0 Md€** |

Le détail du non-associatif : **28,6 % d'entreprises** — SNCF Voyageurs
1 419,6 M€, SNCF Mobilités 904,5 M€, Pass Culture 781,3 M€, l'AFP 697,3 M€,
SNCF Réseau 566,7 M€, le Centre national de la musique 375,0 M€ — et **28,2 %
de personnes morales de droit public** : l'ASP 591,6 M€, le CNC 428,0 M€,
Mégalis Bretagne 405,4 M€, France Travail 259,8 M€, le CNOUS 206,7 M€.

*Réserve de méthode, à ne pas escamoter* : l'échantillon prend les SIREN par
montant décroissant. Les très gros bénéficiaires sont justement ceux qui ont le
plus de chances de ne pas être des associations. Les **11,2 Md€ non interrogés**
(la traîne) sont donc vraisemblablement plus associatifs que 42,7 %. Le chiffre
de 17,0 Md€ vaut pour la portion mesurée ; il n'est pas extrapolable tel quel à
l'ensemble.

#### c. Le correctif existe, il est ouvert, et il ne devine rien

**SIRENE — `StockUniteLegale`, format Parquet, 705 Mo, Licence Ouverte 2.0**,
sur data.gouv.fr, millésime du 1ᵉʳ août 2026. Vérifié en le lisant :
**29 922 486 unités légales, dont 1 513 037 associations** (9220 déclarée,
9260 droit local d'Alsace-Moselle, 9223 groupement d'employeurs, 9230 reconnue
d'utilité publique…). Colonnes utiles : `siren`, `denominationUniteLegale`,
`categorieJuridiqueUniteLegale`. **DuckDB le lit en HTTP Range sans le
télécharger**, donc le dépôt n'a pas à grossir.

C'est exactement le geste que le projet s'autorise : la nature juridique
cesserait d'être DEVINÉE pour devenir DÉCLARÉE — par l'INSEE. La règle
d'asymétrie de `beneficiary_kind_provenance` (« exclure à tort efface une
association réelle ») a été écrite parce qu'on n'avait que le nom pour deviner.
Avec le SIREN et l'INSEE, on ne devine plus, et l'asymétrie n'a plus lieu
d'être sur les 740 835 lignes concernées.

*Le RNA ne convient PAS pour cela, et c'est mesuré* : le
`rna_import_20260801` du ministère de l'Intérieur ne remplit **jamais** sa
colonne `siret` (0 sur 3 312 dans l'Allier). Il ne peut pas servir de pont
SIREN → association. C'est SIRENE ou rien.

#### d. Ce que ça implique, et qui décide

Brancher SIRENE ferait **baisser le total voté du site**, peut-être de plus de
10 %. C'est une correction, pas une perte — le même mouvement que la phase 11,
qui a fait baisser le total de 1,34 Md€ en gagnant 23 sources. Mais l'ampleur
et le choix de la frontière (les fondations comptent-elles ? les fondations
d'entreprise ? les groupements d'employeurs ? les associations syndicales ?)
sont **des arbitrages métier, pas des correctifs**, et ils reviennent à
l'utilisateur.

#### e. La frontière est TRANCHÉE (utilisateur, 26/08/2026)

**Comptent comme dons aux associations** : les associations (INSEE `92xx`, ce
qui inclut les **groupements d'employeurs** `9223`, les associations reconnues
d'utilité publique `9230`, les associations de droit local d'Alsace-Moselle
`9260`, les entreprises d'insertion `9221` et les associations intermédiaires
`9222`), **plus les fondations** (`9300`, qui couvre aussi les **fondations
d'entreprise** et les **fonds de dotation**).

**Consigne qui accompagne la décision, et qui n'est pas négociable** : ces
familles doivent être **différenciées à l'affichage**, « pour ne pas que le
public se sente trompé ». Un total unique qui mélangerait une association de
quartier et un fonds de dotation d'entreprise serait exact et malhonnête.

Effet mesuré de cette frontière sur l'échantillon des 2 500 plus gros SIREN
devinés (29,69 Md€) : **42,7 % dedans, 57,3 % dehors**.

*Les codes limitrophes ne changent rien, c'est mesuré* — et c'est ce qui rend
la frontière sûre : congrégations `9240` 5,0 M€, entreprises d'insertion
`9221` 23,5 M€, associations intermédiaires `9222` 15,1 M€. Hors périmètre et
tout aussi légers : groupements de coopération sociale `9970` 13,8 M€, autre
personne morale de droit privé `9900` 3,9 M€, comités d'entreprise `8310`
3,1 M€, mutuelles `8210` 2,2 M€, syndicats professionnels `84xx` ~25 M€.
Les associations d'avocats `9224` — qui sont des cabinets — ne portent **aucun
euro** dans le corpus. Aucun de ces codes ne mérite un débat.

#### f. Différencier : ce que l'INSEE sait faire, et ce qu'il ne sait pas

**Il ne sait pas séparer fondation, fondation d'entreprise et fonds de
dotation.** Vérifié dans SIRENE : les 5 621 unités du code `9300` se
répartissent, *au libellé seulement*, en 2 946 « FONDS DE DOTATION », 675
« FONDATION », 300 « FONDATION D'ENTREPRISE » et 1 700 autres libellés. La
catégorie juridique les confond ; seul le nom les distingue, et mal.

**Le Journal officiel, lui, sait** — et le site l'a déjà moissonné
(`angle-mort.json`) : il déclare `Associations loi du 1er juillet 1901`
(26 843), `Fonds de dotation` (3 669), `Fondations-Fondations d'entreprise`
(720), `Fondations partenariales` (20). Mais il ne couvre que les organismes
au-dessus de 153 000 €, soit 31 683 en tout.

**Et SIRENE porte le RNA** : la colonne `identifiantAssociationUniteLegale` est
remplie pour **1 100 411 des 1 513 037 associations `92xx` (72,7 %)**. C'est le
pont SIREN → RNA que le fichier RNA du ministère de l'Intérieur ne fournit pas.
Il remplirait au passage la colonne `beneficiary_rna` du site, vide à 73,3 %.

#### g. LA MESURE EXACTE — SIRENE joint à la table, plus aucun échantillon

Fait le 26/08/2026 une fois la frontière tranchée. Les colonnes `siren`,
`categorieJuridiqueUniteLegale`, `identifiantAssociationUniteLegale` et
`denominationUniteLegale` de SIRENE sont extraites en 43 secondes vers un
Parquet local de 387 Mo, puis jointes à la table canonique. La règle des totaux
appliquée est celle du pipeline — `compte_dans_les_totaux` de `common.py`, pas
une réécriture — et elle retrouve **148,40 Md€**, ce qui valide la méthode.

| Sur les 148,40 Md€ votés | lignes | montant | part |
|---|---|---|---|
| **Association ou fondation** — le périmètre retenu | 1 407 639 | **85,11 Md€** | 57,4 % |
| **Vérifié NON associatif** — à sortir | 425 776 | **37,68 Md€** | **25,4 %** |
| Sans identifiant — invérifiable | 609 570 | 25,48 Md€ | 17,2 % |
| SIREN absent de SIRENE | 2 266 | 0,13 Md€ | 0,1 % |

**Le total voté passerait de 148,40 à 110,71 Md€.**

> *Correction d'un chiffre annoncé plus haut* : le §1h.b estimait « ~17,0 Md€ »
> par échantillon. Ce n'était pas faux, c'était PARTIEL — il ne portait que sur
> les lignes « association DEVINÉE portant un SIREN ». La mesure exacte porte
> sur **toutes** les lignes qui entrent dans les totaux, et le chiffre est
> **37,68 Md€**. Le §1h.b est conservé tel quel, avec sa réserve de méthode :
> c'est la trace de la façon dont on y est arrivé.

**D'où viennent ces 37,68 Md€** — et la troisième ligne est une surprise :

| provenance de la nature | lignes | montant | exemples |
|---|---|---|---|
| devinée « association » | 232 147 | **21,14 Md€** | ASP, France Travail, ministère de l'Écologie |
| devinée « inconnu » | 93 679 | **11,85 Md€** | Recette des finances de Toulouse, ASP |
| **devinée « public_body »** | 99 217 | **4,59 Md€** | musée du Louvre, CCAS de Toulouse |
| déclarée « association », contredite par l'INSEE | 733 | 0,10 Md€ | caisses de retraite (cj 8520) |

**Le site devine déjà « établissement public » pour 4,59 Md€ — et les compte
quand même.** Ce n'est pas un bogue : `est_un_don` n'écarte que si la nature est
DÉCLARÉE non associative. L'asymétrie était juste tant qu'on ne savait pas ; on
sait, maintenant.

**Et la contradiction source/INSEE est négligeable : 733 lignes, 0,10 Md€.** La
décision « l'INSEE prime » est donc sûre et sans effet de bord — elle ne
renverse presque rien de ce que les publieurs déclarent.

#### h. Composition du périmètre retenu — la différenciation à afficher

Les 85,11 Md€ qui restent, par famille juridique. C'est exactement le découpage
que la consigne « bien les différencier » demande de montrer :

| famille | lignes | montant | part |
|---|---|---|---|
| Association déclarée (92xx courants) | 1 341 335 | 79,27 Md€ | **93,1 %** |
| Association reconnue d'utilité publique (9230) | 19 393 | 3,01 Md€ | 3,5 % |
| Association de droit local d'Alsace-Moselle (9260) | 37 920 | 2,06 Md€ | 2,4 % |
| **Fondation / fonds de dotation (9300)** | 6 765 | **0,71 Md€** | 0,8 % |
| **Groupement d'employeurs (9223)** | 2 226 | **0,06 Md€** | 0,1 % |

**Les deux familles que vous avez explicitement fait entrer pèsent 0,77 Md€,
soit 0,9 % du total.** Leur inclusion ne déplace donc presque rien — et c'est ce
qui rend la consigne de différenciation facile à tenir : montrer ces lignes à
part ne coûte rien au total et retire tout soupçon.

#### i. Les quatre décisions (utilisateur, 26/08/2026)

1. **Les 37,68 Md€ vérifiés non associatifs sortent des totaux, avec leur
   motif** — exactement comme les prestations facturées : la ligne reste
   ingérée, consultable, exportable, et son montant s'affiche grisé avec la
   raison. Aucun mécanisme nouveau, la doctrine existante suffit.
2. **Les 25,48 Md€ sans identifiant restent comptés, mais marqués « nature non
   vérifiée »** en fiche et en export. La doctrine « l'erreur va vers la
   sous-estimation » tient : exclure à tort effacerait des milliers de petites
   associations communales qui n'ont jamais eu de SIRET publié.
3. **Quand l'INSEE contredit la source, l'INSEE prime.** Une colonne de tableur
   vaut moins que le registre national des personnes morales. Portée mesurée :
   733 lignes, 0,10 Md€.
4. **Différencier en croisant le Journal officiel**, déjà moissonné, qui
   distingue associations loi 1901, fonds de dotation, fondations et fondations
   d'entreprise, fondations partenariales — pour les 31 683 organismes
   au-dessus de 153 000 €, les autres restant « type non précisé ».

#### j. Le Journal officiel peut-il nommer les fondations ? — **OUI, à 94,6 %**

C'était le dernier point non mesuré. Fait le 26/08/2026 : l'export `dca` du JO
(227 738 dépôts) est joint à la table par SIREN **et par RNA**, ce dernier venant
de `identifiantAssociationUniteLegale` de SIRENE. Le JO type **31 686 SIREN et
18 964 RNA**.

**Portée générale, bien meilleure qu'attendu** : le JO type **76,2 % du montant**
du périmètre associatif (64,89 Md€ sur 85,11), pour 38,1 % des lignes. Ce n'est
donc pas un outil réservé aux fondations : il confirme « association loi 1901 »
sur les trois quarts de l'argent associatif du site.

**Les fondations et fonds de dotation** — 6 765 lignes, 705,6 M€,
357 organismes :

| type déclaré | lignes | montant | part |
|---|---|---|---|
| Fondations-Fondations d'entreprise | 4 955 | 511,9 M€ | **72,5 %** |
| Associations loi du 1er juillet 1901 *(le JO contredit l'INSEE)* | 970 | 148,9 M€ | 21,1 % |
| *(non déposé)* libellé « fondation » | 539 | 32,7 M€ | 4,6 % |
| Fonds de dotation | 73 | 4,0 M€ | 0,6 % |
| Fondations partenariales | 111 | 2,7 M€ | 0,4 % |
| **TYPE NON PRÉCISÉ** | 97 | **4,7 M€** | **0,7 %** |

- **94,6 % du montant est nommé précisément** par une déclaration du JO ;
- 4,7 % ne le serait que par le libellé du nom, donc par devinette ;
- **0,7 % — 4,7 M€ — resterait « type non précisé »**.

La consigne « bien les différencier » est donc tenable presque partout, et le
trou résiduel est assez petit pour être dit sans gêne.

*Résultat secondaire notable* : les **fonds de dotation ne pèsent que 4,0 M€**
dans le site, alors qu'ils sont 3 669 à déposer leurs comptes. C'est cohérent
avec la réserve déjà écrite au §5c — le seuil de 153 000 € mélange dons privés
et argent public, et les fonds de dotation vivent surtout de dons privés.

#### k. Quand le JO et l'INSEE se contredisent — 0,3 % du périmètre

Les deux registres divergent, dans les deux sens, et sur peu :

| | organismes | montant |
|---|---|---|
| INSEE dit fondation (9300), le JO dit association loi 1901 | 45 | 148,9 M€ |
| INSEE dit association (92xx), le JO dit fondation ou fonds | 47 | 91,3 M€ |
| **Total de la divergence** | **92** | **240,2 M€ = 0,3 %** |

Les noms disent pourquoi : « FONDATION DE NICE PATRONAGE SAINT-PIERRE ACTES »,
« FONDATION FALRET », « FONDATION ARALIS », « Institut du monde arabe »,
« Mémorial de la Shoah ». **Des organismes qui s'appellent « fondation » sans
en avoir la forme juridique, et l'inverse.** Aucun des deux registres ne ment :
l'INSEE enregistre la FORME JURIDIQUE, le JO le TYPE DÉCLARÉ au dépôt.

Proposition, à valider — elle ne bloque rien tant qu'on ne code pas : la
**frontière** (dedans / dehors) reste à l'INSEE, comme décidé ; le **libellé de
famille affiché** vient du JO quand il existe, puisque c'est l'organisme
lui-même qui l'a déclaré en déposant ses comptes ; et les 92 cas divergents
portent la mention des deux, plutôt qu'un arbitrage silencieux. 240 M€ sur
85,11 Md€ ne justifient pas de trancher à la place des registres.

#### l. Ce qui reste à trancher

Trois options, à trancher avant tout code :

1. **Exclure des totaux** ce que l'INSEE déclare non associatif, comme le site
   le fait déjà quand la SOURCE déclare la nature. Cohérent avec la doctrine
   existante ; fait baisser le total d'environ 17 Md€ sur la portion mesurée.
2. **Afficher à part**, comme le payé à côté du voté : « dons aux associations »
   et « autres bénéficiaires publics de subventions », jamais additionnés.
   Ne perd aucune donnée et rend l'écart lisible.
3. **Ne rien changer aux totaux, mais marquer chaque ligne** de sa catégorie
   juridique INSEE et le dire dans la fiche et l'export. Le moins engageant,
   et déjà bien plus honnête qu'aujourd'hui.

**Rien n'est engagé** : la mesure est faite, le correctif est identifié, la
décision n'est pas la nôtre.

### 1i. Quand deux registres se contredisent — **analysé le 26/08/2026**

La phase 15 fait cohabiter trois sources d'identité : ce que la source publie,
ce que SIRENE enregistre, ce que le Journal officiel déclare. Elles ne disent
pas toujours la même chose. Les deux divergences sont **mesurées, leurs causes
nommées, et rien n'est corrigé** — comme partout ici, on signale.

#### a. Le RNA — 384 organismes, 3 680 lignes, 694,5 M€

Le numéro publié par la source et celui que SIRENE attache au même SIREN
diffèrent. **97,4 % viennent du PLF Jaune** : c'est un défaut d'une source, pas
un phénomène général.

| Cause | Organismes | Montant |
|---|---|---|
| **A. Le numéro publié n'existe dans aucun registre** | **266 (69,3 %)** | 502,9 M€ |
| … dont format valide, inconnu de SIRENE *et* du JO | 249 | 479,5 M€ |
| … dont connu du JO, absent de SIRENE | 17 | 23,4 M€ |
| **C. Le numéro désigne une AUTRE personne morale** | **118 (30,7 %)** | 191,5 M€ |
| … antenne locale ou structure affiliée (≥ 2 mots communs) | 56 | 53,9 M€ |
| … parenté probable (1 mot commun) | 31 | 39,9 M€ |
| … aucun mot commun | 31 | 97,8 M€ |

**Le cas anodin n'existe pas.** L'hypothèse la plus rassurante — deux numéros
successifs pour un même organisme, après renumérotation — a été testée : **zéro
cas**. Les deux causes sont de vrais défauts du numéro publié.

Le cas C se lit tout seul : la source donne le RNA d'une antenne locale quand le
SIREN est celui du siège. « SECOURS POPULAIRE FRANCAIS » porte le RNA du Secours
populaire de Morsang-sur-Orge ; « FEDER OEUVRES LAIQUES NIEVRE » celui de
l'UFOLEP Nièvre ; les CEMEA nationaux celui de leur union régionale
Nord-Pas-de-Calais. **Le RNA et le SIREN d'une même ligne ne désignent pas la
même personne morale.**

*Réserve de méthode* : le tri « aucun mot commun » sur-compte. Il classe ainsi
« OFFICE CENTRAL COOPERATION ECOLE » face à « UNION REGIONALE OCCE LANGUEDOC
ROUSSILLON », qui sont manifestement parents — le sigle ne partage aucun mot
avec le nom développé. Les 97,8 M€ de cette ligne sont donc un MAJORANT du
« sans lien apparent ».

**Ce que le site en fait** : il garde le numéro de la source, affiche celui de
l'INSEE à part, et signale la divergence dans le rapport de qualité
(`rna_contredit_par_sirene`). Réécrire un identifiant publié par un ministère
n'est pas son rôle.

**Ce qui reste à trancher, et qui n'est pas notre arbitrage** : la fiche montre
aujourd'hui le numéro de la SOURCE quand les deux divergent. L'analyse plaide
pour l'inverse — dans 69,3 % des cas le numéro publié ne désigne rien, et celui
de l'INSEE est rattaché au SIREN qui sert déjà à identifier le bénéficiaire,
donc cohérent par construction. Changer l'ordre d'affichage est une entorse à
« fidélité maximale à la source » : à l'utilisateur de dire.

#### b. La forme juridique — 104 organismes, 485,9 M€

L'INSEE et le Journal officiel ne rangent pas ces organismes dans la même
famille. **Et c'est marginal : les deux registres concordent sur 99,4 % des
18 419 organismes que tous deux typent** (18 316).

Les divergences sont symétriques — 52 organismes que l'INSEE dit association et
le JO fondation (110,2 M€), 51 l'inverse (375,7 M€) — et **le nom ne tranche
pas** : 68 des 104 portent un nom qui ne dit rien de leur forme.

Mais les plus gros tranchent, eux :

| Montant | INSEE | JO | Organisme |
|---|---|---|---|
| 67,6 M€ | fondation | association 1901 | Institut du monde arabe |
| 66,4 M€ | fondation | association 1901 | Cité internationale universitaire de Paris |
| 52,9 M€ | fondation | association 1901 | Fondation Patronage Saint-Pierre-Actes |
| 28,6 M€ | fondation | association 1901 | Mémorial de la Shoah |
| 15,6 M€ | fondation | association 1901 | Fondation Charles de Gaulle |

**Ce sont des fondations, et l'INSEE a raison.** Le champ du JO n'est pas la
forme juridique : c'est **la case sous laquelle les comptes ont été déposés**,
et le dépôt d'une fondation se range couramment dans le bac « associations » du
JOAFE. C'est ce qui justifie après coup la règle posée en phase 15 : **la forme
vient de l'INSEE, le JO n'affine qu'à l'intérieur des fondations, il ne
renverse jamais.** Sans elle, ces 375,7 M€ auraient été réétiquetés
« association loi 1901 » sur la foi d'un champ qui ne dit pas ce qu'on croyait.

Signalé dans le rapport sous `forme_juridique_contredite_par_le_jo`.

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
| Valeurs écartées, hors des totaux (quarantaines d'unité comprises) | 30 255 |
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

- **Ce que la phase 13 laisse ouvert, côté interface.** Aucun de ces points
  n'est bloquant, et chacun se mesure avant d'être ouvert :
  - la page `couverture.html` reste très longue (dix sections, sept tableaux) ;
    elle a maintenant un sommaire, mais mériterait d'être coupée en deux ;
  - aucune vue par DONATEUR n'existe : « tout ce que la Région Bretagne a
    financé » demanderait un index shardé par donateur, symétrique de celui des
    bénéficiaires — le calcul est le même, le fichier serait du même ordre ;
  - `top.json.gz` n'a pas de dimension annuelle : « les plus gros bénéficiaires
    en 2023 » n'est pas répondable sans un nouvel agrégat ;
  - ~~aucun export~~ — **fait le 25/08/2026**, quatre exports CSV.

- **Le doublon Baule** : 182 lignes, 365 k€. `communes-pays-loire` étiquette
  « Commune de La Baule » ce qui est en réalité **Baule dans le Loiret**. On ne
  corrige pas le libellé : deviner qu'un « La Baule » veut dire « Baule »
  ailleurs fondrait deux communes réelles. Détail dans `CLAUDE.md`.
- **`measure_of` et les tirets bas : appliqué le 23/08/2026 — voir §1d et §4.**
  Non pour les 8 lignes de Chatou que mesurait le §4a, mais pour lever une
  contradiction : le même fichier était lu « voté » d'un côté et « payé » de
  l'autre selon le portail qui le sert. Les séparateurs sont ramenés à l'espace
  dans `measure_of`, et là seulement — `fold`, dont dépend toute la
  reconnaissance de colonnes, n'est pas touché.
- **Le fichier PLF 2024 est vide à la source** (« csv: fichier vide ou non
  tabulaire ») : l'exercice 2022 manque donc au corpus PLF Jaune.

---

### 3b. Le donateur « v » de la Ville de Paris — **722,4 M€ comptés deux fois**

*Trouvé le 25/08/2026 en relisant une fiche à l'écran, mesuré aussitôt. Non
corrigé : le correctif déplace un total de tête, c'est un arbitrage de
l'utilisateur.*

Le jeu `scdl-65ea8f56-e87042eb` — « Subventions aux associations votées »,
publié par la Ville de Paris sur data.gouv.fr et servi par
`opendata.paris.fr` — porte **`Collectivité = "v"`** sur ses 15 099 lignes.
Vérifié à la source, l'en-tête et trois lignes :

```
Numéro de dossier;Année budgétaire;Collectivité;Nom Bénéficiaire;...
2026_01700;2026;v;A.S PARIS 17;...
```

**Le défaut est du publieur, pas du pipeline** : le site lit fidèlement ce qui
est écrit, comme la doctrine l'exige. Mais la conséquence est un double compte,
et elle est entière :

| Mesure | Valeur |
|---|---|
| Lignes concernées | **15 099** (2024-2026) |
| Montant | **722,4 M€** |
| Lignes ayant une jumelle EXACTE ailleurs (même bénéficiaire, année, montant, objet) | **15 099, soit 100 %** |
| Donateur déclaré | `v`, échelon `inconnu` |

La déduplication ne peut pas les voir : `identite_donateur` fait partie de la
clé métier, et « v » ne se rapproche d'aucun libellé. C'est **exactement le
schéma de Rennes Métropole en phase 12** — un donateur faux qui empêche deux
publications du même argent de se rencontrer.

Trois issues possibles, à trancher :

1. **Traiter « v » comme un libellé qui ne nomme personne**, au même titre que
   « collectivite », « - » ou vide (`_DONOR_PLACEHOLDER` dans `common.py`), et
   laisser le donateur NON ATTRIBUÉ. Les lignes restent, se dédupliquent avec
   leurs jumelles, et 722,4 M€ sortent du total. C'est la solution la plus
   conforme à ce que la phase 12 a décidé pour Rennes.
2. **Remonter au publieur du portail** (`opendata.paris.fr` → Ville de Paris),
   comme pour Saint-Maur-des-Fossés. Attribue correctement, mais devine.
3. **Ne rien faire et le dire**, en l'ajoutant aux anomalies signalées du
   rapport de qualité.

Attention si l'on retient (1) ou (2) : le total voté du site **baisse de
722,4 M€**, et c'est une correction, pas une perte — exactement comme les
1,67 Md€ de la phase 11 et les 227,2 M€ de la phase 12. Il faudra le dire dans
`CLAUDE.md`, `methode.html` et le commit.

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

*Révisé le 23/08/2026, après la phase 12.*

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
4. ~~**Décider ce que devient le site sans changement d'échelle.**~~ — **fait
   le 23/08/2026, phase 13.** Réponse : il devient utilisable. Le corpus n'a pas
   bougé d'une ligne ; ce qui a changé, c'est qu'on peut l'atteindre. La
   recherche ne fait plus attendre 50 Mo derrière une phrase grise, la carte dit
   ce qu'elle montre, « ma commune » a sa page, et tout est partageable par son
   adresse. Trois résultats négatifs mesurés au passage sont dans les pièges de
   `CLAUDE.md` : un préchargement « en tâche de fond » se paie quand même, un
   index en chaînes JavaScript coûte deux fois sa taille en mémoire, et un
   balayage partiel trie ce qu'il a trouvé plutôt que ce qu'il fallait trouver.
5. ~~Les jeux écartés à rouvrir (1d)~~ — **fait le 23/08/2026, et l'énoncé
   était faux sur les trois points.** Deux des trois correctifs étaient déjà
   appliqués, l'inventaire datait d'avant le re-moissonnage, et les collectivités
   nouvelles n'étaient pas celles annoncées : +4 communes, +1 EPCI et **un
   département entier** (Seine-Maritime), pas seulement de la profondeur. Le
   gisement de reconnaissance est maintenant épuisé — les 8 jeux écartés que les
   règles actuelles retiendraient portent tous zéro ligne. Leçon : un inventaire
   qui n'est pas relu dans les manifestes du jour envoie sur le mauvais chantier,
   exactement ce que l'avertissement en tête de ce fichier dit d'éviter.
6. ~~La Ville de Rennes (1e)~~ — **faite le 23/08/2026**, et là encore l'énoncé
   était faux : les fichiers étaient déjà dans le site, mal classés. Un compte
   administratif comptait comme du budget voté (227,2 M€ sur tout le corpus) et
   un compte de publication servait de donateur (396 M€ de la commune crédités à
   l'EPCI). La couverture y perd Rennes Métropole, qui n'a jamais rien publié en
   propre, et y gagne Besançon.
7. **La levée de la quarantaine 2011 (2a)** — 12,3 Md€ et un huitième de
   l'histoire du site en dépendent.
8. ~~`measure_of` et les tirets bas~~ — **fait**, en deux temps. Phase 8 :
   deux changements de doctrine tranchés par l'utilisateur — voté et payé
   s'affichent côte à côte, et seuls les DONS entrent dans les totaux. Le
   23/08/2026, les séparateurs ont finalement été ramenés à l'espace **dans
   `measure_of` seulement**, non pour les 8 lignes de Chatou du §4a mais parce
   que le même fichier de Fleury-sur-Orne était « voté » côté portail
   (`subventions_versees`) et « payé » côté data.gouv.fr (« Subventions
   versées »). Ce que le §4b disait coûteux ne l'est plus depuis la phase 8 :
   « payé » s'affiche à côté du voté au lieu de disparaître.
9. **Ne pas relancer le moissonnage pour la couverture.** Les deux canaux sont
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
