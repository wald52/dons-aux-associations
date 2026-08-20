# Suivi des sources — Subventions publiques aux associations

## Architecture

```
index.html → registre inline → departments.js → [sources/*.js] → data/loader.js → src/app.js
```

Scripts de conversion : `scripts/convert-<source>.js`
Données générées : `data/sources/<source>.js`

---

## 1. ÉTAT — PLF Jaune (Projet de Loi de Finances)

**Source :** data.economie.gouv.fr (CSV) + budget.gouv.fr (XLSX annexe)
**Contenu :** Subventions de l'État aux associations, par ministère et programme
**Licence :** Licence Ouverte 2.0
**Volume total intégré :** **654 000+ lignes, ~47 Md€**

| Données (année) | PLF | Lignes | Montant | Source ID |
|-----------------|-----|--------|---------|-----------|
| 2010 | PLF 2012 | 17 459 | 1,48 Md€ | `plf-jaune-2012` |
| 2011 | PLF 2013 | 21 125 | 12,30 Md€ | `plf-jaune-2013` |
| 2012 | PLF 2014 | 31 843 | 1,85 Md€ | `plf-jaune-2014` |
| 2013 | PLF 2015 | 28 144 | 2,14 Md€ | `plf-jaune-2015` |
| 2014 | PLF 2016 | 29 670 | 2,11 Md€ | `plf-jaune-2016` |
| 2015 | PLF 2017 | 32 982 | 2,05 Md€ | `plf-jaune-2017` |
| 2016 | PLF 2018 | 56 497 | 4,69 Md€ | `plf-jaune-2018` |
| 2017 | PLF 2019 | 70 063 | 5,32 Md€ | `plf-jaune-2019` |
| 2018 | PLF 2020 | 92 107 | 7,24 Md€ | `plf-jaune-2020` |
| 2019 | PLF 2021 | 96 737 | 7,73 Md€ | `plf-jaune-2021` |
| 2020 | PLF 2022 | 95 807 | ~9,0 Md€ | `plf-jaune-2022` |
| 2023 | PLF 2025 | 81 448 | 7,77 Md€ | `plf-jaune-2025` |
| **Total** | | **654 000** | **~47 Md€** | |

**Lacunes :**
- **2021** (PLF 2023) — Non trouvé sur data.economie.gouv.fr
- **2022** (PLF 2024) — Uniquement données agrégées (111 lignes, par programme)

**URLs des datasets data.gouv.fr :**
- Tous les millésimes : https://www.data.gouv.fr/datasets/plf-jaune-associations-subventionnees/
- PLF 2025 : https://www.data.gouv.fr/datasets/plf-2025-donnees-de-lannexe-jaune-effort-financier-de-letat-en-faveur-des-associations-1/
- PLF 2024 (agrégé) : https://www.data.gouv.fr/datasets/plf24-donnees-de-lannexe-jaune-effort-financier-de-letat-en-faveur-des-associations
- PLF 2021-2015 : https://www.data.gouv.fr/fr/datasets/?q=PLF+Jaune+effort+financier+associations

---

## 1 bis. PORTAILS OPENDATASOFT — moissonnage automatique (phase 6a)

Les collectivités qui publient le plus ne passent pas par data.gouv.fr : elles
ont leur propre portail. Ces portails partagent la même API (Explore v2.1),
donc **un seul moissonneur les couvre tous** — `scripts/pipeline/fetch_ods.py`.

Relevé complet et à jour : `data/sources-manifest/ods.json`.
463 jeux examinés, **273 retenus**, 1 202 009 lignes annoncées.

| Portail | Jeux | Lignes |
|---|---|---|
| `data.opendatasoft.com` (fédérateur) | 166 | 720 060 |
| `opendata.paris.fr` | 4 | 202 347 |
| `data.bretagne.bzh` | 1 | 101 128 |
| `data.laregion.fr` (Occitanie) | 1 | 64 541 |
| `data.iledefrance.fr` | 8 | 40 625 |
| `data.toulouse-metropole.fr` | 46 | 23 120 |
| `data.rennesmetropole.fr` | 6 | 19 685 |
| `data.nantesmetropole.fr` | 20 | 15 116 |
| `data.centrevaldeloire.fr` | 11 | 7 772 |
| `data.ampmetropole.fr` | 6 | 7 288 |
| `opendata.clermontmetropole.eu` | 4 | 327 |

**Deux pièges propres à ce moissonnage**, documentés dans `CLAUDE.md` :

- Le **fédérateur republie** les jeux des portails territoriaux. Chaque jeu
  arrive donc deux fois ; la déduplication par clé métier les rattrape.
- Le fédérateur est **international** : les jeux belges, suisses et canadiens
  sont écartés au moissonnage (`PUBLIEURS_HORS_FRANCE`), pas plus loin, pour
  ne pas les traîner dans toute la chaîne.

---

## 2. VILLE DE PARIS

| Dataset | URL | Période | Format | Statut |
|---------|-----|---------|--------|--------|
| Subventions votées | https://opendata.paris.fr/explore/dataset/subventions-associations-votees- | 2013-2026 | CSV | **✅ 107 693 lignes, 3,41 Md€** |
| Subventions versées (CA) 2018+ | https://opendata.paris.fr/explore/dataset/subventions-versees-annexe-compte-administratif-a-partir-de-2018/ | 2018+ | CSV | **✅ ingéré, `measure = verse`, hors totaux** |
| Subventions versées (CA) 2013-2017 | idem, millésimes antérieurs | 2013-2017 | CSV | **✅ ingéré, `measure = verse`, hors totaux** |

**Paris publie le même argent deux fois** : ce qu'il a voté, et ce qu'il a
versé au compte administratif. Les additionner double la ville. Seules les
« votées » entrent dans les totaux — elles portent en outre l'année, le SIRET
et l'objet, que le compte administratif n'a pas.

Et le compte administratif ne concerne pas que des associations : 5,5 Md€ y
vont à des établissements publics, 2,1 Md€ à des entreprises, 38 878 lignes à
des personnes physiques. La nature juridique y étant DÉCLARÉE, elle fait foi.

⚠️ **Paris reste compté environ deux fois** tant que la clé métier compare des
libellés de donateur : la source héritée `paris` (« Département de Paris ») ne
se déduplique pas avec le jeu Opendatasoft (« Ville de Paris »). Phase 6b.

---

## 3. DATA.SUBVENTION (beta.gouv.fr)

**Site :** https://datasubvention.beta.gouv.fr/
**API :** Réservée aux agents publics (habilitation DataPass)
**Alternative :** Sources individuelles des collectivités sur data.gouv.fr

---

## 4. CATALOGUE API data.gouv.fr (556 datasets)

L'API `https://www.data.gouv.fr/api/1/datasets/?q=subventions&page_size=100` retourne **556 datasets**.
Inventaire complet organisé par type d'entité.

### 4.1 Départements (30+ datasets identifiés)

| Département | Datasets disponibles | Période |
|-------------|---------------------|---------|
| Seine-Maritime (76) | Carte subventions CD76 2008a2023, Subventions CD76 2008a2022, 2008-2023, 20191231, 2022 | 2008-2023 |
| Morbihan (56) | Subventions aux personnes morales | ? |
| Nièvre (58) | Subventions | ? |
| Vaucluse (84) | Publication des subventions aux associations | ? |
| Pyrénées-Orientales (66) | Données essentielles des conventions subventions | 2019+ |
| Hautes-Pyrénées (65) | Subventions du Département | ? |
| Hauts-de-Seine (92) | Subventions versées aux collectivités/organismes, CLS, CUCS, rénovation urbaine | ? |
| Bas-Rhin (67) | FINANCES : Subventions départementales | ? |
| Dordogne (24) | Subventions 2017, 2018, 2019 | 2017-2019 |
| Isère (38) | Subventions accordées par le département | ? |
| Loire-Atlantique (44) | Subventions versées par le Département | ? |
| Maine-et-Loire (49) | Subventions aux associations, Conventions 2017-2019, 2025 | 2017-2025 |
| Ille-et-Vilaine (35) | Subventions versées aux associations | ? |
| Finistère (29) | Subventions de plus de 23000€ | ? |
| Eure-et-Loir (28) | Subventions >23000€ (2024, 2025) | 2024-2025 |
| Savoie (73) | Subventions versées 2017-2023 | 2017-2023 |
| Loire (42) | Données essentielles conventions subventions 2018 | 2018 |
| Manche (50) | Subventions versées aux collectivités et organismes | ? |
| Lot (46) | Données essentielles conventions subventions 2021, 2022 | 2021-2022 |
| Alpes de Haute-Provence (04) | Subventions >23000€ | ? |
| Côtes d'Armor (22) | Subventions aux associations 2002-2015 et depuis 2015 | 2002-2025 |
| Mayenne (53) | Convention subventions depuis 2017 | 2017+ |
| Haute-Garonne (31) | Multiples directions (Éducation, Prévention, Transformation) | ? |
| Gironde (33) | Détail des subventions accordées | 2013-2016 |

### 4.2 Régions

| Région | Datasets disponibles | Période |
|--------|---------------------|---------|
| Normandie | Subventions 2018, 2019, 2020, 2022, 2023 | 2018-2023 |
| Bretagne | Les subventions attribuées depuis 2014 | 2014+ |
| Île-de-France | Subventions aux associations, aux formations sanitaires/sociales, clubs formateurs, DIM recherche, lycées, équipements SESAME | 2010-2017 |
| Hauts-de-France | FEDER, ERBM rénovations thermiques | ? |
| Grand Est | Liste des subventions votées 2012-2014 | 2012-2014 |
| Centre-Val de Loire | Conventions subventions 2018-2024 | 2018-2024 |

### 4.3 Métropoles et grandes intercommunalités

| Collectivité | Datasets disponibles | Période |
|-------------|---------------------|---------|
| Toulouse Métropole | Subventions versées aux organismes 2012-2024 + Ville de Toulouse 2023-2024 + Blagnac + Aérosporia | 2011-2024 |
| Nantes Métropole | Subventions versées aux associations 2017-2024 | 2017-2024 |
| Métropole de Lyon | Subventions de la Métropole de Lyon | ? |
| Métropole d'Aix-Marseille-Provence | Subventions attribuées 2018-2022 | 2018-2022 |
| Bordeaux Métropole | Subventions de Bordeaux Métropole | ? |
| Grenoble-Alpes Métropole | Subventions accordées aux associations | ? |
| Grand Paris Seine Ouest | Subventions aux associations + Conservatoires DRAC + Vélo | ? |
| Grand Paris Sud | Subventions GPS 2020, 2021 | 2020-2021 |
| Grand Poitiers | Subventions directes/indirectes | ? |
| Le Havre Seine Métropole | Conventions de subventions CODAH | ? |
| Grand Chambéry | Subventions attribuées | ? |
| Grand Besançon | Subventions aux associations | ? |
| GrandSoissons Agglomération | Subventions | ? |
| Rennes Métropole | Subventions d'équipement aux associations 2013 | 2013 |
| Quimper Bretagne Occidentale | Subventions | ? |
| Saint-Nazaire agglo - CARENE | Subventions numéraires aux associations, Subventions Donges | ? |
| Estérel Côte d'Azur Agglomération | Subventions attribuées | ? |
| Saint-Louis Agglomération | Subventions allouées 2020-2025 | 2020-2025 |
| Saintes Grandes Rives, l'Agglo | Subventions attribuées | ? |
| Agglopolys (CA de Blois) | Subventions 2018-2023 + Blois + Vineuil | 2018-2023 |
| Bourges Plus | Subventions 2020-2023 | 2020-2023 |
| Val de Fensch | Liste subventions attribuées + >23000€ | 2020+ |
| CAP Atlantique | La Baule-Escoublac, Férel, Guérande | ? |
| Lorient Agglomération | Subventions depuis 2014 | 2014+ |
| Clermont Auvergne Métropole | Subventions >23000€ 2020-2024 | 2020-2024 |
| Grand Belfort | Subventions publiques Ville + Agglo | ? |
| Pays Basque | Subventions versées aux organismes 2021, 2023 | 2021-2023 |
| Nevers | Subventions aux associations 2017 | 2017 |
| CA Bar-le-Duc Sud Meuse | Subventions >23000€ | ? |
| Pays de Mormal | Subventions Covid 2020 | 2020 |

### 4.4 Villes (50+ datasets)

| Ville | Datasets | Période |
|-------|----------|---------|
| Paris | ✅ Subventions votées + versées | 2013-2026 |
| Nantes | Subventions versées asso 2017-2024 (8 datasets) | 2017-2024 |
| Rennes | Subventions asso 2008-2024 (ordinaires, exceptionnelles, équipement) | 2008-2024 |
| Marseille | Subventions 2017-2022 (via datasud.fr) | 2017-2022 |
| Toulouse | Subventions versées aux organismes (ville) 2015-2024 | 2015-2024 |
| Lyon | Subventions de la Ville de Lyon (SCDL) | ? |
| Lille | Données essentielles conventions subventions (via Mairie de Lille) | ? |
| Grenoble | Subventions et avantages en nature | ? |
| Issy-les-Moulineaux | Paramunicipales, non paramunicipales, par adhérent 2017-2020 | 2017-2020 |
| Montbéliard | Subventions 2018-2021 | 2018-2021 |
| Nantes | Subventions versées 2017-2024 | 2017-2024 |
| Chelles | Subventions attribuées | ? |
| Meudon | BP 2026 - Subventions aux associations | 2026 |
| Dreux | Subventions >23000€ | ? |
| Digne-les-Bains | Subventions aux associations | ? |
| Villemomble | Liste subventions versées aux associations | ? |
| Longjumeau | Subventions aux associations 2018 | 2018 |
| Redon | Subventions aux associations 2018 | 2018 |
| Cannes | Subventions aux associations | ? |
| Boë | Subventions aux associations | ? |
| Mazingarbe | Subventions versées aux associations | ? |
| Torcy | Subventions attribuées | ? |
| Autun | Subventions 2017 | 2017 |
| Agen | Subventions 2014, 2023 | 2014, 2023 |
| Vaulx-en-Velin | Subventions | ? |
| Lisieux | Subventions aux associations 2018 | 2018 |
| Martigues | Subventions versées aux associations | ? |
| Roissy-en-Brie | Subventions 2018 | 2018 |
| Saint-Claude | Subventions +23000€ 2018-2022 | 2018-2022 |
| Nogent-sur-Marne | Subventions municipales 2012-2014 | 2012-2014 |
| Boulogne Billancourt | Conventions subventions 2025 | 2025 |
| Soissons | Subventions de fonctionnement (hors Amicale) | ? |
| Sarcelles | Subventions fonctionnement >23000€ | ? |
| Noyal-Châtillon-sur-Seiche | Subventions 2017 | 2017 |
| Saint-Nazaire | Subventions numéraires | ? |
| Plérin | Subventions versées 2015 | 2015 |
| Tours | Compte administratif - Subventions | ? |
| Anglet | Subventions >23000€ | ? |
| Mèze | Subventions >23000€ 2018 | 2018 |
| Villejuif | Subventions associations | ? |
| La Possession (La Réunion) | Subventions associations | ? |
| Fleury-sur-Orne | Subventions aux associations | ? |
| Les Lilas | Annexe budgétaire subventions | ? |
| Charleville-Mézières | Subventions aux associations | ? |
| Comines | Subventions 2016-2025 | 2016-2025 |
| Lannion | Subventions | ? |
| Orvault | Subventions attribuées | ? |
| + 20+ petites communes | Divers datasets SCDL individuels | |

### 4.5 Autres entités

| Entité | Datasets |
|--------|----------|
| Ministère de l'Intérieur | Réserve parlementaire, Réserve ministérielle |
| Premier ministre | DILCRAH subventions 2017-2024, Cabinet PM 2022, 2024 |
| Caisse des Dépôts | Subventions depuis 01/01/2018 |
| CNSA | Subventions de la CNSA |
| EFS (Établissement Français du Sang) | Tableaux subventions AURA, CPDL, Nouvelle-Aquitaine, OCPM, Siège (10+ datasets) |
| ANCT | Subventions politique de la ville P147 2016-2025 (266 975 lignes) ✅ |
| Île-de-France Mobilités | Subventions IDF Mobilités, stats vélo |
| SNCF Réseau | Subventions investissements CCO depuis 2015 |
| CCI Seine-Mer Normandie | Contributions et subventions 2017, 2018, 2020 |
| CCI Rouen Métropole | Subventions et contributions 2024 (38 lignes) |
| Ministère de l'agriculture | Subventions >23000€ |
| CNDS | Subventions équipements sportifs 2015 |
| Proparco | Subventions avec participation UE |
| SDIS Gironde | Subventions de fonctionnement aux associations |
| GIP Les entreprises s'engagent | Subventions |
| Ecole des beaux-arts Nantes Saint-Nazaire | Subventions |

---

## 5. OUTRE-MER

**Datasets trouvés :**
- La Possession (La Réunion) — Subventions attribuées aux associations par la ville
- PLF Jaune couvre programmes Outre-mer (programmes 123, 138, 218, 723, 776)

**À vérifier :**
- Portail région Réunion : https://data.regionreunion.com/
- Nouvelle-Calédonie : https://data.gouv.nc/
- Pas de dataset dédié "subventions aux associations" trouvé

---

## 6. AUTRES SOURCES

### 6.1 Comptes annuels des associations
- **URL :** https://www.data.gouv.fr/datasets/comptes-associations/
- **Contenu :** Comptes annuels des associations > 153k€ de subventions/dons
- **Statut :** ⏳

### 6.2 RNA — Répertoire National des Associations
- **URL :** https://www.data.gouv.fr/datasets/repertoire-national-des-associations/
- **Statut :** ⏳ (enrichissement référentiel)

### 6.3 ARUP
- **URL :** https://www.data.gouv.fr/datasets/associations-reconnues-d-utilite-publique/
- **Statut :** ⏳ (enrichissement)

### 6.4 Minefi consolidation 2011-2015
- Dataset : Subventions publiques des associations - consolidation Minefi 2011-2015
- **Statut :** ⏳

---

## SYNTHÈSE FINALE

### Sources intégrées (✅)

| # | Source | Lignes | Période | Montant |
|--:|--------|-------:|---------|--------:|
| 1 | PLF Jaune (12 années) | 654 000 | 2010-2023 | ~47 Md€ |
| 2 | Paris | 76 207 | 2013-2026 | ~3,9 Md€ |
| 3 | Côtes d'Armor (SCDL) | 14 289 | 2016+ | ? |
| 4 | Côtes d'Armor (custom) | 15 319 | 2002-2015 | ? |
| 5 | Mayenne (SCDL) | 585 | ? | ? |
| 6 | Isère (SCDL) | 208 | ? | ? |
| 7 | Loire-Atlantique (SCDL) | 28 679 | ? | ? |
| 8 | Hautes-Pyrénées (SCDL) | 245 | ? | ? |
| 9 | Maine-et-Loire conventions 2017-2019 (SCDL) | 91 | 2017-2019 | ? |
| 10 | Maine-et-Loire conventions 2025 (SCDL) | 42 | 2025 | ? |
| 11 | Ille-et-Vilaine (custom) | 972 | 2020-2022 | ? |
| 12 | Ille-et-Vilaine 2021 (custom) | 928 | 2021 | ? |
| 13 | Ille-et-Vilaine 2022 (custom) | 954 | 2022 | ? |
| 14 | Savoie 2017 (custom) | 111 | 2017 | ? |
| 15 | Savoie 2018 (custom) | 108 | 2018 | ? |
| 16 | Savoie 2019 (custom) | 111 | 2019 | ? |
| 17 | Savoie 2020 (custom) | 172 | 2020 | ? |
| 18 | Savoie 2021 (custom) | 128 | 2021 | ? |
| 19 | Savoie 2022 (custom) | 148 | 2022 | ? |
| 20 | Savoie 2023 (custom) | 178 | 2023 | ? |
| | _Savoie total (7 ans)_ | _956_ | _2017-2023_ | |
| 19 | Maine-et-Loire subventions (custom) | 15 684 | 2004-2016 | ? |
| 20 | Finistère (SCDL) | 5 442 | ? | ? |
| 21 | Nièvre (SCDL) | 5 183 | 2018-2024 | ? |
| 22 | Dordogne (SCDL) | 6 953 | 2017-2019 | ? |
| 23 | Loire (SCDL) | 153 | 2018 | ? |
| 24 | Bas-Rhin (custom XLSX) | 3 345 | 2017-2018 | ? |
| | **Total** | **~831 000** | | **~51 Md€+** |
| 25 | Lot (custom CSV) | 144 | 2021-2023 | ? |
| 25 | Ville de Lyon (SCDL) | 4 356 | 2006-2024 | ? |
| 26 | Ville de Grenoble (custom) 2015 | 995 | 2015 | ? |
| 27 | Ville de Grenoble (custom) 2016 | 917 | 2016 | ? |
| | **Total Cities** | **~6 268** | | |
| 28 | Soissons (02) custom | 1 401 | 2018-2019 | ? |
| 29 | Bar-le-Duc (55) XLSX | 55 | 2017-2023 | ? |
| 30 | Sarcelles (95) SCDL | 23 | 2024 | ? |
| 31 | Mèze (34) SCDL | 2 | 2018 | ? |
| 32 | Iffendic (35) custom | 375 | 2018 | ? |
| 33 | Pleumeleuc (35) custom | 147 | 2017 | ? |
| 34 | Talensac (35) custom | 110 | 2018 | ? |
| 35 | Breteil (35) custom | 141 | 2018 | ? |
| 36 | Sixt-sur-Aff (35) XLSX+CSV | 69 | 2017-2018 | ? |
| 37 | Saint-Gonlay (35) XLSX | 9 | 2017 | ? |
| 38 | La Nouaye (35) XLSX | 39 | 2018 | ? |
| | **Total Communes** | **~2 371** | | |
| 39 | Redon (35) 2017 | 113 | 2017 | ? |
| 40 | Redon (35) 2018 | 110 | 2018 | ? |
| 41 | Sailly-Lez-Lannoy (59) SCDL | 71 | 2018 | ? |
| 42 | Longjumeau (91) custom | 5 | 2018 | ? |
| 43 | Lisieux (14) SCDL | 119 | 2018 | ? |
| 44 | Manosque (04) SCDL | 13 | 2025 | ? |
| 45 | Carquefou (44) custom | 14 | 2025 | ? |
| 46 | Roubaix (59) custom >23k | 585 | 2017+ | ? |
| 47 | Subventions 2024 (divers) | 32 | 2024 | ? |
| 48 | Subventions communales SCDL | 137 | ? | ? |
| 49 | Subventions >23k 2024 SCDL | 16 | 2024 | ? |
| | **Total Villes** | **~1 215** | | |
| 50 | Baugé-en-Anjou (49) | 281 | 2018-2020 | ? |
| 51 | Arras (62) 2018 | 72 | 2018 | ? |
| 52 | Arras (62) 2017 | 168 | 2017 | ? |
| 53 | Nogent-sur-Marne (94) 2012 | 129 | 2012 | ? |
| 54 | Nogent-sur-Marne (94) 2013 | 215 | 2013 | ? |
| 55 | Nogent-sur-Marne (94) 2014 | 213 | 2014 | ? |
| 56 | Roscoff (29) SCDL | 46 | 2017 | ? |
| 57 | Vitry-sur-Seine (94) | 214 | 2017 | ? |
| 58 | Nevers Agglomération (58) SCDL | 16 | 2017 | ? |
| 59 | Métropole de Lyon SCDL | 9 081 | 2015+ | ? |
| | **Total Batch 2** | **~10 435** | | |
| 60 | Nantes Métropole (44) custom | 2 874 | 2017-2024 | data.gouv.fr |
| 61 | Ville de Villejuif (94) custom | 571 | 2020-2025 | data.gouv.fr |
| 62 | Département Seine-Saint-Denis (93) custom | 508 | ? | data.seinesaintdenis.fr |
| 63 | Communauté d'Agglomération Pays Basque (64) | 79 | 2023 | data.gouv.fr |
| 64 | Toulouse Métropole (31) SCDL | 3 521 | 2012-2024 | data.gouv.fr |
| 65 | Bordeaux Métropole (33) SCDL | 1 177 | 2018+ | datahub.bordeaux-metropole.fr |
| 66 | Ville de Rennes (35) custom | 17 298 | 2016-2024 | data.gouv.fr |
| 67 | Ville de Marseille (13) CSV | 11 164 | 2017-2022 | data.gouv.fr |
| 68 | Ville de Tours (37) SCDL | 2 484 | 2020+ | data.gouv.fr |
| 69 | Région Île-de-France (3 fichiers) | 33 071 | 2012-2024 | data.iledefrance.fr |
| 70 | Donges (44) SCDL | 130 | 2018+ | data.agglo-carene.fr |
| 71 | Saint-Joachim (44) SCDL | 270 | 2018+ | data.agglo-carene.fr |
| 72 | La Baule (44) custom | 385 | 2015+ | data.centrevaldeloire.fr |
| 73 | Argenton-sur-Creuse (36) custom | 608 | 2014+ | data.centrevaldeloire.fr |
| 74 | Région Centre-Val de Loire (5 fichiers) | 3 303 | 2018-2024 | data.centrevaldeloire.fr |
| 75 | Ville de Nantes (44) custom | 10 327 | 2017-2024 | data.gouv.fr |
| 76 | Orvault (44) SCDL | 79 | 2025 | data.gouv.fr |
| 77 | DILCRAH 2024 | 188 | 2024 | data.gouv.fr |
| 78 | Fleury-les-Aubrais (45) custom | 107 | 2019 | data.gouv.fr |
| 79 | Noyal-Châtillon-sur-Seiche (35) custom | 56 | 2018 | data.gouv.fr |
| 80 | Ville de Toulouse (31) SCDL | 10 637 | 2015-2024 | data.gouv.fr |
| 81 | PLF 2023 (État) | 102 615 | 2021 | data.economie.gouv.fr |
| 82 | DILCRAH 2025 (État) | 218 | 2025 | data.gouv.fr |
| 83 | Boulogne-Billancourt (92) | 49 | 2025 | data.gouv.fr |
| 84 | Anglet (64) | 85 | 2018-2025 | data.gouv.fr |
| 85 | Sarcelles (95) 2025 | 23 | 2025 | data.gouv.fr |
| 86 | Villemomble (93) | 107 | 2011-2012 | data.gouv.fr |
| 87 | Ministère Agriculture (>23K€) | 1 840 | 2018-2026 | data.gouv.fr |
| 88 | Issy-les-Moulineaux (92) | 23 | 2024-2026 | data.issy.com |
| 89 | Grand Paris Seine Ouest (92) | 116 | 2017-2024 | data.gouv.fr |
| 90 | Île-de-France Santé | 509 | 2010-2011 | data.iledefrance.fr |
| 91 | Ville de Meudon (92) BP 2026 | 103 | 2026 | data.gouv.fr |
| 92 | Ville d'Asnières-sur-Seine (92) | 22 | 2020 | data.gouv.fr |
| 93 | CCI Rouen Métropole | 38 | 2024 | data.gouv.fr |
| 94 | ANCT Politique de la ville P147 (10 fichiers) | 266 975 | 2016-2025 | data.gouv.fr |
| 95 | Pyrénées-Orientales (66) (15 fichiers) | 6 870 | 2020-2024 | data.gouv.fr |
| 96 | Ville de Quimper (29) | 76 | 2024-2025 | data.gouv.fr |
| 97 | Quimper Bretagne Occidentale (29) | 90 | 2024-2025 | data.gouv.fr |
| 98 | Communay (69) | 3 | 2023-2024 | data.gouv.fr |
| 99 | Saintes Grandes Rives (17) | 183 | 2023-2024 | data.gouv.fr |
| 100 | Rillieux-la-Pape (69) | 25 | ? | data.grandlyon.com |
| 101 | Sautron (44) | 6 | 2024-2025 | data.gouv.fr |
| 102 | Val de Fensch (57) (8 fichiers) | 148 | 2016-2019 | data.gouv.fr |
| 103 | Pays de l'Or (34) | 9 | ? | data.gouv.fr |
| 104 | Gironde (33) 2013-2016 | 14 734 | 2013-2016 | data.gouv.fr via archive.org |
| 105 | Réserve ministérielle (État, 7 fichiers) | 3 243 | 2011-2017 | data.gouv.fr |
| 106 | Nièvre (58) (7 fichiers) | 5 183 | 2018-2024 | data.gouv.fr |
| 107 | Ville de Dreux (28) | 43 | 2018-2020 | data.gouv.fr |
| 108 | Vaulx-en-Velin (69) | 655 | 2021-2023 | data.grandlyon.com |
| 109 | Grand Chambéry (73) (4 fichiers) | 507 | 2018-2021 | data.gouv.fr |
| 110 | EFS CPDL (4 fichiers) | 8 | 2020-2023 | data.gouv.fr |
| 111 | Mairie de Bouaye (44) (8 fichiers) | 331 | 2015-2024 | data.gouv.fr |
| 112 | Charleville-Mézières (08) (2 fichiers) | 39 | 2023-2024 | data.gouv.fr |
| 113 | Grenoble-Alpes Métropole (9 fichiers) | 2 631 | 2015-2023 | data.gouv.fr via archive.org |
| 114 | Somme (80) (10 fichiers) | 1 765 | 2017-2026 | data.gouv.fr |
| 115 | Ville de Nancy (54) (3 fichiers) | 217 | 2017-2019 | data.gouv.fr |
| 116 | Ville de Bayonne (64) (3 fichiers) | 111 | 2018-2020 | data.gouv.fr |
| 117 | Villejuif (94) (6 fichiers) | 339 | 2020-2025 | data.gouv.fr |
| 118 | EFS AURA (5 fichiers) | 10 | 2020-2024 | data.gouv.fr |
| 119 | Saint-Laurent-de-Mure (69) (5 fichiers) | 8 | 2017-2021 | data.gouv.fr |
| 120 | DITP (État) (3 fichiers) | 7 | 2023-2025 | data.gouv.fr |
| 121 | Lorient Agglomération (56) (10 fichiers) | 374 | 2014-2019 | data.gouv.fr |
| 122 | CNSA (État, associations) (7 fichiers) | 361 | 2017-2022 | data.gouv.fr |
| 123 | FEDER Hauts-de-France (1 fichier) | 1 075 | 2014-2019 | opendata.hautsdefrance.fr |
| 124 | École des beaux-arts de Nantes (2 fichiers) | 9 | 2021-2025 | data.gouv.fr |
| 125 | Sautron >23K€ (44) (2 fichiers) | 6 | 2024-2025 | data.gouv.fr |
| 126 | Ville de Grenoble (4 fichiers) | 3 211 | 2013-2016 | data.gouv.fr via archive.org |
| | **Total Batch 14** | **~5 043** | | |
| 127 | Eure-et-Loir (28) (1 fichier) | 25 | 2025 | data.eurelien.fr |
| 128 | Pays des Écrins (05) (4 fichiers) | 83 | 2018-2021 | datasud.fr |
| 129 | SDIS Gironde (33) (1 fichier) | 3 | 2017-2019 | data.gouv.fr |
| 130 | CNDS 2015 (État) (2 fichiers) | 52 182 | 2015 | data.gouv.fr |
| 131 | ARS Pays de la Loire FIR (1 fichier) | 1 903 | 2025 | data.gouv.fr |
| 132 | Clermont Auvergne Métropole (63) (5 fichiers) | 327 | 2020-2024 | opendata.clermontmetropole.eu |
| 133 | Ville de Bar-le-Duc (55) (5 fichiers) | 33 | 2017-2023 | data.gouv.fr |
| 134 | Haute-Garonne DTII+DPLCE (31) (2 fichiers) | 28 | 2025 | data.haute-garonne.fr |
| 135 | Boulogne-Billancourt (92) (1 fichier) | 62 | 2021-2025 | data.gouv.fr |
| 136 | Ville de Soissons (02) (1 fichier) | 610 | 2018-2021 | data.gouv.fr |
| 137 | Mulhouse Alsace Agglo (68) (1 fichier) | 216 | 2017 | data.mulhouse-alsace.fr |
| | **Total Batch 15** | **~55 472** | | |
| 138 | DILCRAH (État) (6 fichiers) | 557 | 2017-2023 | data.gouv.fr |
| 139 | Cabinet Premier ministre (1 fichier) | 51 | 2022 | data.gouv.fr |
| 140 | BOP 177 DRDJSCS PDL (1 fichier) | 289 | 2018 | data.gouv.fr |
| 141 | Charente-Maritime (17) (1 fichier) | 1 989 | 2019-2025 | data.gouv.fr |
| 142 | Cher (18) (1 fichier) | 5 | 2025 | data.gouv.fr |
| 143 | Dordogne (24) (3 fichiers) | 6 922 | 2017-2019 | data.gouv.fr |
| 144 | Hautes-Pyrénées (65) (1 fichier) | 255 | 2019-2026 | opendata.ha-py.fr |
| 145 | Hauts-de-Seine (92) (1 fichier) | 1 193 | 2020-2025 | opendata.hauts-de-seine.fr |
| 146 | Isère (38) (1 fichier) | 208 | 2025-2026 | opendata.isere.fr |
| 147 | Mayenne (53) (1 fichier complet) | 623 | 2017-2025 | data.lamayenne.fr |
| 148 | Aube (10) (2 fichiers) | 37 | 2017-2021 | data.gouv.fr |
| 149 | Ville de Lyon (69) (1 fichier) | 4 356 | 2006-2024 | data.grandlyon.com |
| 150 | Vaulx-en-Velin (69) (1 fichier) | 655 | 2021-2025 | data.grandlyon.com |
| 151 | Orvault (44) (1 fichier) | 79 | 2010-2026 | data.nantesmetropole.fr |
| 152 | Asnières-sur-Seine (92) (1 fichier) | 22 | 2020 | data.gouv.fr |
| 153 | Sailly-Lez-Lannoy (59) (1 fichier) | 71 | 2016-2022 | data.gouv.fr |
| 154 | Lisieux (14) (1 fichier) | 119 | 2018 | data.gouv.fr |
| 155 | Redon (35) (1 fichier) | 110 | 2018 | data.gouv.fr |
| 156 | Iffendic (35) (1 fichier) | 375 | 2015-2019 | data.gouv.fr |
| 157 | Talensac (35) (1 fichier) | 110 | 2015-2018 | data.gouv.fr |
| 158 | Le Poinçonnet (36) (2 fichiers) | 20 | 2021-2026 | data.centrevaldeloire.fr |
| 159 | Lannion (22) (1 fichier) | 179 | 2012-2014 | data.gouv.fr |
| 160 | EFS Siège (1 fichier) | 12 | 2020-2021 | data.gouv.fr |
| 161 | EFS OCPM (1 fichier) | 8 | 2015-2019 | data.gouv.fr |
| 162 | CC Quercy Vert-Aveyron (82) (2 fichiers) | 20 | 2018-2020 | data.gouv.fr |
| | **Total Batch 16** | **~16 234** | | |
| 163 | Ministère de la Culture (1 fichier) | 223 064 | 2019-2025 | data.gouv.fr |
| | **Total Batch 17** | **~223 064** | | |
| | **Grand Total** | **~1 642 042** (1 594 905 après dédup) | | **~72 Md€+** |

### État d'avancement

> **Correctif critique (17/08/2026)** : les convertisseurs batch 10-16 écrivaient `var NAME = [...]` sans
> enregistrer les données dans `__DATA_SOURCES`. L'app ne chargeait que 67 sources (832 346 lignes).
> Les 97 fichiers concernés ont été corrigés (ajout de `__registerDataSource`) → **162 sources chargées,
> 1 371 841 lignes après déduplication**. Fichiers écrasés restaurés : Lyon (4 356 lignes, 2006-2024),
> Dordogne (6 922 lignes, 2017-2019), Mayenne (623 lignes, 2017-2025), Orvault, Asnières (2020), Sailly.
> Doublon Vaulx-en-Velin supprimé (ville-vaulx.js conservé, année 2021 correcte).

| Catégorie | Disponibles | Intégrés | Estimation lignes restantes |
|-----------|-------------|----------|----------------------------|
| État — PLF Jaune | 13 datasets | **13** ✅ | — |
| Ville de Paris | 2 datasets | **1** ✅ | 76K (versées) |
| Départements | 30+ datasets | **30** ✅ | 200K-500K |
| Villes | 50+ datasets | **54** ✅ | 100K-300K |
| Métropoles/EPCI | 25+ datasets | **16** ✅ | 50K-200K |
| Régions | 6 datasets | **3** ✅ | 10K-50K |
| Autres (État, opérateurs) | 20+ datasets | **15** ✅ | 10K-50K |
| **Total** | **~150 datasets** | **117+** | **~500K-1M** |

### Plan d'action

**Phase 1 — PLF Jaune** ✅ **TERMINÉE**

**Phase 2 — Départements SCDL** (partiel)
- ✅ Loire-Atlantique (44, SCDL, 28 679)
- ✅ Hautes-Pyrénées (65, SCDL, 245)
- ✅ Maine-et-Loire conventions 2017-2019 (49, SCDL, 91)
- ✅ Maine-et-Loire conventions 2025 (49, SCDL, 42)
- ✅ Loire-Atlantique (44, SCDL, 28 679)
- ✅ Hautes-Pyrénées (65, SCDL, 245)
- ✅ Maine-et-Loire conventions 2017-2019 (49, SCDL, 91)
- ✅ Maine-et-Loire conventions 2025 (49, SCDL, 42)
- ✅ Maine-et-Loire subventions (49, custom, 15 684)
- ✅ Finistère (29, SCDL, 5 442)
- ✅ Nièvre (58, SCDL, 5 183)
- ✅ Dordogne (24, SCDL, 6 953)
- ✅ Loire (42, SCDL, 153)
- ✅ Ille-et-Vilaine (35, custom, 2 854 cumulé)
- ✅ Savoie (73, custom, 717 cumulé 2017-2023)
- ✅ Mayenne (53, SCDL, 585)
- ✅ Isère (38, SCDL, 208)
- ✅ Côtes d'Armor 2016+ (22, SCDL, 14 289)
- ✅ Bas-Rhin (67, XLSX, 3 345)
- ✅ Côtes d'Armor 2002-2015 (22, custom, 15 319)
- ⏳ Gironde (33, DNS bloqué), Seine-Maritime (76, opendata76.fr bloqué), Morbihan (56, DNS bloqué), Vaucluse (84, DNS bloqué), etc.

**Phase 3 — Grandes villes**
1. ✅ Lyon (13K lignes, SCDL)
2. ✅ Nantes (8 datasets, 2017-2024, 2 874 lignes Métropole + 10 327 Ville)
3. ✅ Rennes (9 datasets, 2016-2024, 17 298 lignes)
4. ✅ Marseille (5 datasets, 2017-2022, 11 164 lignes)
5. ✅ Toulouse (10 datasets Métropole + 10 Ville, 2012-2024, 3 521 + 10 637 lignes)
6. ✅ Bordeaux (2018+, 1 177 lignes)
7. ✅ Tours (2020+, 2 484 lignes)
8. ✅ Villejuif (6 datasets, 2020-2025, 571 lignes)
9. ✅ Orvault (79 lignes)
10. Strasbourg (DNS bloqué), Lille (308 redirect), Dijon (PDF), Besançon (PDF), Nice, Montpellier, etc.

**Phase 4 — Métropoles et EPCI**
1. ✅ Nantes Métropole (2017-2024, 2 874 lignes)
2. ✅ Métropole de Lyon (9 081 lignes)
3. ✅ Nevers Agglomération (16 lignes)
4. ✅ Communauté d'Agglomération Pays Basque (79 lignes)
5. ✅ Toulouse Métropole (2012-2024, 3 521 lignes)
6. ✅ Bordeaux Métropole (2018+, 1 177 lignes)
7. Grenoble-Alpes Métropole (DNS bloqué)
8. Métropole Aix-Marseille (2018-2022)

**Phase 5 — Reste**
1. ✅ Régions (2 intégrées: Île-de-France 33K + Centre-Val de Loire 3.3K)
2. ✅ DILCRAH (1 intégrée: 2024, 188 lignes)
3. Réserve parlementaire/ministérielle
4. Caisse des Dépôts
5. CNSA
6. EFS (10+ datasets)
7. Comptes annuels (enrichissement)
8. RNA (enrichissement)

### Notes techniques

- **Poids total des fichiers JS :** ~539 MB (104 fichiers sources)
- **Ralentissement possible au chargement** dans le navigateur (tous les fichiers sont chargés via `<script>` tags)
- **Optimisation future possible :** Chargement lazy par année sélectionnée, ou format compressé
- **Normalizer :** Les fichiers PLF sont déjà au format standard (normalizer identity). Les nouveaux fichiers SCDL utiliseront le normalizer 'scdl' existant.
