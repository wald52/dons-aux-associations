# Ce qui reste à faire

État arrêté au **21/08/2026**, après la phase 8. Chiffres mesurés, pas estimés :
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
| Lignes servies | 2 687 791 |
| **Dons votés** | **142,59 Md€** |
| **Dons payés** (à côté, jamais additionnés) | **7,45 Md€** |
| Ingéré mais pas un don (prestations, remboursements, nature) | 2,19 Md€ |
| Sources | 548 |
| Bénéficiaires résolus | 406 846 |
| Dont cumulant 3 échelons ou plus | 6 783 |
| Contrôles `verify.py` | 33 |

---

## 1. L'exhaustivité — le vrai manque

Couverture face au référentiel INSEE. **C'est un MINIMUM** : l'appariement
échoue plutôt qu'il n'invente, donc l'erreur va toujours vers la
sous-estimation (cf. `CLAUDE.md`).

| Échelon | Avec données | Repérées | Univers |
|---|---|---|---|
| Communes | **86** | 96 | 34 936 |
| EPCI | **29** | 38 | 1 335 |
| Départements | **31** | 36 | 101 |
| Régions | **5** | 7 | 18 |

10,3 % de la population française. (« Repérées » ajoute les collectivités qui
publient mais dont rien n'est encore exploité.)

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

Les deux correctifs sont dans le code. **Ils ne produisent rien tant que le
moissonnage n'est pas rejoué** — c'est le prochain geste, et il demande de
re-télécharger l'amont (`data/raw/` n'est pas versionné).

**Ce que Nice, Montpellier, Strasbourg, Lille et Toulon ne publient pas.**
Vérifié des deux côtés : ni portail (Strasbourg et Angers ont un portail ouvert
avec ZÉRO jeu de subventions), ni data.gouv.fr. Seule Lille publie — et son
adresse d'export répond du HTML. Leur absence du site n'est donc pas un défaut
de moissonnage : **c'est une absence de publication**, et c'est à ce titre
qu'elle doit être dite.

### 1c. Ce qui manquera toujours

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

**`plf-jaune-2013` (exercice 2011) — 12,30 Md€, 21 167 lignes.** Élucidé en
phase 7 : la source publie avec la virgule décalée d'un rang. 100,0 % de ses
montants sont multiples de 10 (75,9 % au millésime suivant) ; le rapport
2011/2012 par SIREN pique exactement à 10,0 ; l'Orchestre de Paris passe de
9 278 494 € en 2010 à 92 784 940 € en 2011 puis revient à 9 278 494 € en 2012 ;
un poste Fonjep (~7 107 €) y figure à 71 070 €. L'API amont stocke bien la
valeur gonflée : l'erreur est du publieur.
**Levée possible** — sans habilitation ni démarche : il suffit que le publieur
corrige son millésime, ou qu'une source tierce (les rapports annuels des
associations concernées) confirme le facteur dix association par association.
C'est la quarantaine la plus proche d'être levée.

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

## Ordre recommandé

*Révisé le 21/08/2026, `datasubvention` étant abandonné (1b).*

1. **Décider ce que devient le site sans changement d'échelle.** C'est la
   question à trancher avant de coder quoi que ce soit : le plafond de
   couverture est atteint, et la valeur du site se déplace vers ce qu'il FAIT de
   ce qu'il a — croisements, séries, exports, lisibilité — plutôt que vers un
   corpus plus gros.
2. **Les jeux écartés à rouvrir (1d)** — le seul gisement qui ne dépende de
   personne. Trois correctifs de reconnaissance (en-tête mal détecté, `beneficiare`,
   `organismes`) rouvrent ~91 jeux, mais 69 sont la Ville de Rennes : gain en
   profondeur, pas en couverture. Demande un re-moissonnage complet.
3. **La levée de la quarantaine 2011 (2a)** — 12,3 Md€ et un huitième de
   l'histoire du site en dépendent.
4. ~~`measure_of` et les tirets bas~~ — **fait (§4, phase 8)**. Le correctif de
   séparateurs n'a PAS été appliqué (8 lignes, 850 k€, toutes à perte). À sa
   place, deux changements de doctrine tranchés par l'utilisateur : voté et payé
   s'affichent côte à côte, et seuls les DONS entrent dans les totaux.
5. **Ne pas relancer le moissonnage pour la couverture.** Les deux canaux sont
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

# Le banc de mesure (CHROMIUM_PATH si Playwright cherche une révision absente) :
node scripts/bench/measure.js --label <phase>
```

`normalize_legacy.py` a besoin de `data/sources/*.js`, retirés du dépôt :
`git checkout 0b14348 -- data/sources` avant de le rejouer — **et
`git rm -r --cached data/sources` avant de commiter**, sinon les 835 Mo
repartent dans l'historique.

**`verify.py` vient EN DERNIER** (plusieurs contrôles comparent l'index de
recherche à la table canonique) et **doit rester vert** : 30/30 aujourd'hui.

Travailler sur `main`, et seulement `main`.
