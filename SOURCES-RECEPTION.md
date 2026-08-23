# Ce que les associations REÇOIVENT — inventaire des sources

Établi le **22/08/2026**. Tous les chiffres de ce document ont été mesurés en
appelant les API citées, pas repris d'un article. Les commandes qui les
reproduisent sont en fin de fichier.

À lire après `CLAUDE.md` (contexte et pièges) et `SOURCES.md` (l'inventaire du
côté payeur, celui que le site exploite aujourd'hui).

**ENGAGÉ le 22/08/2026 — phase 10.** Ce document s'arrêtait à l'inventaire.
Ses trois options (§6) ont depuis été mises en œuvre : le compte 6574 des
balances DGFiP est moissonné et sert de dénominateur, les 227 586 dépôts de
comptes du Journal officiel sont croisés avec l'index des bénéficiaires, et le
D751 des comptes nationaux donne l'échelle. **Aucune de ces sources n'entre dans
la table canonique** : aucune ne nomme de bénéficiaire, et les sommer avec les
versements nominatifs compterait deux fois le même argent.

L'impasse, elle, reste une impasse : les montants des comptes déposés sont dans
des PDF scannés (§2b), et rien ne les en sortira sans OCR.

Ce qui a été mesuré une fois engagé, et qui n'était pas dans l'inventaire :

| | mesuré le 22/08/2026 |
|---|---|
| Communes déclarant un compte 6574 (2010-2025) | **34 829** sur 34 936 |
| Ce qu'elles déclarent | **51,10 Md€**, dont le site connaît **14,9 %** |
| Organismes ayant déposé leurs comptes | **31 683** (par SIREN distinct) |
| Reconnus dans l'index du site | **18 745** — 59,2 % |
| Associations loi 1901 reconnues | **67,9 %** |
| Fonds de dotation reconnus | **3,5 %** — la preuve que le seuil mélange dons privés et argent public |

---

## 1. Pourquoi la distinction compte

Depuis la phase 1, le site est bâti **du côté du payeur** : on moissonne ce que
l'État, les régions, les départements, les communes et les EPCI *publient* de ce
qu'ils versent. `RESTE-A-FAIRE.md` §1a établit que ce canal est épuisé — **90
communes sur 34 936**, 10,9 % de la population — et que le plafond de couverture
est atteint.

Le côté receveur pose la même question par l'autre bout. Une association
enregistre dans ses comptes **tout** ce qu'elle encaisse, quel que soit le nombre
de guichets publics d'où l'argent vient et quelle que soit la politique d'open
data du guichet. Un chiffre côté receveur est donc **exhaustif par
construction**, là où le côté payeur dépend du bon vouloir de 36 000 publieurs.

Le prix de cette exhaustivité : le côté receveur est soit **agrégé** (des totaux
nationaux, sans association nommée), soit **enfermé dans des PDF scannés**. Il
n'existe aucune base ouverte donnant, association par association, le montant
public reçu. C'est le résultat central de cette recherche, et il est négatif.

---

## 2. Par association — une seule source existe

### 2a. Les comptes annuels déposés au Journal officiel (DILA)

Toute association ou fondation recevant plus de **153 000 €** de dons et/ou de
subventions publiques doit déposer ses comptes annuels et les faire publier
(art. L612-4 et D612-5 du code de commerce). Même obligation pour **tous** les
fonds de dotation, et au-delà de 230 000 € pour les associations
professionnelles militaires.

| | mesuré le 22/08/2026 |
|---|---|
| Dépôts recensés (`source="dca"`) | **227 586** |
| Exercices couverts | clôtures **2006 → 2026** |
| Volume par exercice récent | 11 000 à 14 700 |
| Métadonnées par dépôt | SIREN, RNA, titre, département, région, code EPCI, date de clôture, date de parution, rang de rectificatif |
| Licence | Licence Ouverte 2.0, **sans clé** |

**Les métadonnées, gratuites et immédiates.** Jeu `jo_associations` sur
`https://journal-officiel-datadila.opendatasoft.com/api/explore/v2.1` — un
portail **Opendatasoft**, donc interrogeable avec exactement le code que
`fetch_ods.py` sait déjà écrire. Le champ `source` vaut `joafe` (5 417 532
annonces de création, modification, dissolution) ou `dca` (227 586 dépôts de
comptes). Deux jeux complémentaires sur le même portail :
`osop-comptes-de-resultats` (68 476) et `osop-entites` (13 761), qui ajoutent une
typologie d'organisation et un département / région déjà normalisés. Attention :
leur champ `ressources` est un **code** (`1`, `2`…), pas un montant.

**Le PDF se télécharge un par un**, ce qui évite le vrac :

```
https://www.journal-officiel.gouv.fr/telechargements/ASSOCIATIONS/DCA/PDF/<aaaa>/<jjmm>/<id>.pdf
```

où `id` est le champ `id` du jeu, de la forme `<siren>_<jjmmaaaa>`. Vérifié :
HTTP 200, `application/pdf`, 240 Ko pour `775744725_31122023`.

**Le vrac, lui, est hors de portée.** `https://echanges.dila.gouv.fr/OPENDATA/COMPTES_DES_ASSOCIATIONS/`
publie **25 à 46 Go par exercice** (FLUX_HISTORIQUE 2015 → 2025) ; le flux de
l'année courante compte 5 651 archives pour ~30 Go. Et le XML qui accompagne
chaque PDF **ne porte aucun montant** : la DTD `Compte_Assoc.dtd` se limite à
`fichier, siren, titreLong, codePostal, dateDepot, dateCloture, dateValidation,
type, formeJuridique, url, numRNA`.

### 2b. Les montants sont dans des scans — mesuré, résultat négatif

24 PDF ont été tirés au hasard sur les exercices 2012, 2016, 2020 et 2023, puis
téléchargés et analysés octet par octet.

| Ce qu'on trouve | sur 24 |
|---|---|
| Images seules (`DCTDecode` / `CCITTFaxDecode`, aucune police embarquée) | la majorité |
| Texte réellement extractible | 4 à 6 |
| Contenant le mot « subvention » en clair | **2** |

Sans OCR, le taux de récupération est faible. Avec OCR, on afficherait un montant
**deviné par une machine sur une image** — ce que la doctrine « fidélité maximale
à la source » interdit. Ce n'est donc pas un chantier à ouvrir : c'est un
résultat à retenir, comme l'épuisement des deux canaux de moissonnage.

### 2c. Ce que la source vaut sans lire un seul montant

La liste **exhaustive et datée des associations qui franchissent 153 000 €**.
Croisée avec les 417 639 bénéficiaires résolus du site, elle mesure directement
l'angle mort : combien d'associations déposent des comptes sans apparaître dans
aucune de nos 681 sources. Ce serait la première mesure honnête de ce que le site
ne voit pas — et elle ne coûte que des appels d'API.

**Réserve à ne pas oublier** : le seuil de 153 000 € mélange **dons privés et
subventions publiques**. Franchir le seuil ne prouve pas un financement public.

### 2d. Et rien d'autre

Vérifié sur l'API data.gouv.fr le 22/08/2026 :

| Recherche | Jeux trouvés |
|---|---|
| « comptes associations » | 2 — tous deux la base DILA, dont un reformaté arrêté à 2013 |
| « reçus fiscaux » | **0** |
| « générosité » | **0** |
| « dons associations » | **0** |
| « financement associations » | **0** |
| « bilan associations » | **0** |

La déclaration des dons et des reçus fiscaux (art. 222 bis du CGI, obligatoire
depuis 2021 : montant total des dons et nombre de reçus délivrés) est collectée
par la DGFiP et **n'est pas publiée**.

---

## 3. Les totaux de contrôle — combien, en tout

Ces sources ne nomment aucune association. Elles disent **combien**, et c'est
précisément ce qui manque au site : un dénominateur.

### 3a. Comptes nationaux de l'INSEE — le chiffre officiel

Base 2020, séries **1949 → 2023**, tableaux xlsx libres.

| Poste | 2013 | 2023 |
|---|---|---|
| **D751 « Transferts courants aux ISBLSM » versé par les APU (S13)** — tableau 7.301 | | **45,603 Md€** |
| D751 reçu par les ISBLSM (S15) — tableau 7.501 | 46,036 Md€ | **63,788 Md€** |
| D92R aides à l'investissement à recevoir (S15) | 0,870 Md€ | 0,918 Md€ |
| D9R transferts en capital à recevoir (S15) | 2,517 Md€ | 3,318 Md€ |

- `https://www.insee.fr/fr/statistiques/fichier/8068612/T_7301.xlsx`
- `https://www.insee.fr/fr/statistiques/fichier/8068616/T_7501.xlsx`

**45,6 Md€ en 2023 : c'est ce que toutes les administrations publiques versent
aux associations en un an**, dans la comptabilité nationale. L'écart avec les
63,8 Md€ reçus est ce que versent les ménages et les entreprises.

**Réserve obligatoire** : le secteur S15 **exclut** les associations reclassées
en administrations publiques (S13) ou en sociétés (S11). C'est un périmètre plus
étroit que « les associations » au sens courant, et il ne faut pas présenter ces
45,6 Md€ comme le total du secteur associatif.

### 3b. Enquête « Situation des associations en 2024 » (INSEE)

Troisième édition (2014 sur l'exercice 2013, 2018 sur 2017, 2024). Collecte du
**18/09/2025 au 31/01/2026**, premiers résultats publiés le **28/07/2026**.
Questionnaire public. Elle ventile les ressources par origine : ventes aux
usagers, commande publique, subventions, cotisations, dons — c'est la source des
ordres de grandeur qui circulent (budget cumulé de l'ordre de 113 Md€ en 2017,
dont ~44 % de financement public).

- Série : `https://www.insee.fr/fr/metadonnees/source/serie/s1326`
- Édition 2024 : `https://www.insee.fr/fr/metadonnees/source/operation/s2229/presentation`

### 3c. Revue de dépenses IGF / IGÉSR, mai 2025

« Les dépenses publiques en direction des associations » : **53 Md€** de
financement public en 2023, dont 49 Md€ de dépenses budgétaires de l'État et des
collectivités, pour **314 000 associations** bénéficiaires. C'est la borne haute
officielle, plus large que le périmètre INSEE (elle inclut la commande publique
et les dépenses fiscales).

**Non vérifié à la source dans cette session** : `igf.finances.gouv.fr` a répondu
503 puis échoué en TLS. Le rapport est relayé par `education.gouv.fr`. Chiffres à
re-vérifier dans le PDF avant de les afficher sur le site.

### 3d. INJEP — chiffres clés de la vie associative

Fiches régionales 2025 (23ᵉ édition, avec Recherches & Solidarités) et collection
« Chiffres clés de la vie associative » : `https://injep.fr/vie-associative/`.
Déclinaison par région, PDF et données. Utile pour une lecture territoriale, pas
pour un chiffre par association.

---

## 4. La découverte adjacente — les balances comptables DGFiP

Ce n'est **pas** le côté receveur : c'est le côté payeur, mais mesuré dans la
**comptabilité officielle** au lieu de l'open data volontaire. Donc exhaustif. Ça
a sa place ici parce que ça répond à la même question — combien les associations
touchent-elles vraiment — et parce que c'est, de loin, le gisement le plus gros
trouvé ce jour.

`data.economie.gouv.fr`, API Explore, Licence Ouverte. Un jeu par exercice et par
catégorie : **communes 2010 → 2025** (~7 M lignes par an), départements, régions,
groupements à fiscalité propre, syndicats, établissements publics locaux. Le
compte **6574** « subventions de fonctionnement aux associations et autres
personnes de droit privé » y figure pour chaque collectivité, avec son montant.

| Mesuré par l'API le 22/08/2026 | budgets | montant |
|---|---|---|
| **Communes, exercice 2020, compte 6574** | **31 797** | **2,63 Md€** |
| Communes, exercice 2019, compte 6574 | 33 298 | 2,85 Md€ |
| EPCI à fiscalité propre, 2023, compte 6574 | 815 | 1,20 Md€ |
| Départements, 2023, compte 6574 | 58 | 992,2 M€ |
| Départements, 2023, compte 65748 | 66 | 765,4 M€ |
| Régions, 2023, compte 6574 | 6 | 768,5 M€ |
| Régions, 2023, compte 65748 | 13 | 1 353,0 M€ |

**31 797 communes, contre les 90 que le site couvre.** C'est le dénominateur qui
manque depuis le début : « cette commune a versé X € à des associations en 2020,
le site en connaît Y ». Aucun bénéficiaire n'est nommé, mais la carte de
couverture cesserait d'être binaire.

**Réserves à écrire si on s'en sert** :
- le compte dit « et autres personnes de droit privé » : il **n'est pas purement
  associatif** ;
- une subvention peut être imputée ailleurs — 6568, 657362 vers un CCAS,
  subventions d'investissement en compte 204 — donc 6574 seul **sous-estime** ;
- les départements et les régions éclatent leurs versements sur toute la famille
  6573x / 6574x selon la nomenclature (M52, M71), il faut choisir les comptes
  avec soin plutôt que de sommer aveuglément.

Pour mémoire, `balances_des_comptes_etat` existe aussi mais est ventilé par
mission et programme, **sans bénéficiaire** : sans intérêt ici, le Jaune fait
mieux.

---

## 5. Ce qui n'existe pas — à dire explicitement

- **Les concours publics qui ne sont pas des subventions**, et qui pèsent lourd
  dans ce que reçoivent les associations : prestations de service de la CNAF,
  tarification ARS / CNSA des établissements médico-sociaux, aides à l'emploi
  (France Travail, ASP). **Aucun n'est publié par bénéficiaire.** C'est
  probablement le plus gros angle mort de tout le sujet.
- **Les reçus fiscaux** de l'article 222 bis du CGI : collectés, non publiés.
- **`api.datasubvention.beta.gouv.fr`** : abandonné (décision de l'utilisateur du
  21/08/2026). Rappelé ici pour qu'aucune session ne le repropose.

---

## 6. Ce que ça a donné — les trois options, faites

Classées par coût croissant lorsqu'elles n'étaient que des options. Les trois
ont été retenues par l'utilisateur le 22/08/2026 et mises en œuvre le jour
même (phase 10, cf. `ROADMAP.md`).

1. **FAIT — Mesurer l'angle mort.** Croiser les 227 586 dépôts de comptes avec l'index
   de bénéficiaires du site. API seule, aucun PDF, aucun montant à extraire.
   C'est le meilleur rapport valeur / coût de la liste.
2. **FAIT — Donner un dénominateur territorial.** Le compte 6574 par collectivité et par
   exercice : la carte de couverture passerait de « publie / ne publie pas » à
   « le site connaît Y € sur X € versés ».
3. **FAIT — Afficher les totaux de contrôle** sur `methode.html` : 45,6 Md€ d'APU vers
   les ISBLSM en 2023 face au total du site pour le même exercice.
   **Attention** : les 149,68 Md€ affichés sont un **cumul 2001-2027**, pas un
   flux annuel. La comparaison n'a de sens qu'exercice par exercice — c'est
   ainsi qu'elle est faite : sur l'exercice 2023, le site retrouve 24,0 Md€ des
   45,6 Md€ de la comptabilité nationale.

Les scripts correspondants : `fetch_balances.py` + `build_denominateur.py`,
`fetch_jo_comptes.py` + `build_angle_mort.py`, `fetch_totaux_controle.py`.

---

## 7. Reproduire les chiffres de ce document

```bash
# 227 586 dépôts de comptes annuels
curl -s "https://journal-officiel-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/jo_associations/records?where=source%3D%22dca%22&limit=1" \
  | head -c 200

# un PDF de comptes déposés, par son id <siren>_<jjmmaaaa>
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' \
  "https://www.journal-officiel.gouv.fr/telechargements/ASSOCIATIONS/DCA/PDF/2023/3112/775744725_31122023.pdf"

# le compte 6574 de toutes les communes, exercice 2020
curl -s -G "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/balances-comptables-des-communes-en-2020/records" \
  --data-urlencode "where=compte='6574'" \
  --data-urlencode "select=count(*) as n, sum(sd) as total"

# les deux tableaux INSEE (D751 versé par les APU, D751 reçu par les ISBLSM)
curl -sI "https://www.insee.fr/fr/statistiques/fichier/8068612/T_7301.xlsx" | head -1
curl -sI "https://www.insee.fr/fr/statistiques/fichier/8068616/T_7501.xlsx" | head -1
```
