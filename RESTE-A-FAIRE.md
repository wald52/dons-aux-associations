# Ce qui reste à faire

État arrêté au **20/08/2026**, après la phase 6b. Chiffres mesurés, pas estimés :
ils viennent de `data/canonical/quality-report.json`, `couverture.json` et des
manifestes de moissonnage.

À lire après `CLAUDE.md` (contexte et pièges) et `ROADMAP.md` (ce qui a été fait
et pourquoi).

---

## Où en est le site

Les phases 0 à 6b sont faites. Sur les quatre objectifs de départ — vitesse,
données justes et exhaustives, recherche croisée, lisibilité — **trois sont
atteints**. Le site charge en 0,07 s, la recherche croisée fonctionne sur
2,7 M de lignes sans backend, le design est unifié.

**L'exhaustivité est le seul objectif encore largement ouvert.**

| | valeur |
|---|---|
| Lignes servies | 2 690 242 |
| Total individuel | 157,68 Md€ |
| Sources | 630 |
| Bénéficiaires résolus | 406 280 |
| Dont cumulant 3 échelons ou plus | 6 739 |

---

## 1. L'exhaustivité — le vrai manque

Couverture face au référentiel INSEE. **C'est un MINIMUM** : l'appariement
échoue plutôt qu'il n'invente, donc l'erreur va toujours vers la
sous-estimation (cf. `CLAUDE.md`).

| Échelon | Couvert | Univers |
|---|---|---|
| Communes | **113** | 34 936 |
| EPCI | **40** | 1 335 |
| Départements | **37** | 101 |
| Régions | **6** | 18 |

10,3 % de la population française.

### 1a. Dépivoter les tableaux par année — *le plus sûr*

Environ **178 fichiers** publient une colonne par exercice
(`2018-Subventions Accordées`, `2019-…`) au lieu d'une ligne par versement.
Ils sont aujourd'hui écartés au moissonnage.

Le format est régulier, donc automatisable : une colonne dont le libellé
contient une année devient une ligne portant cette année. Aucun arbitrage
métier, gain mécanique.

Où : la reconnaissance de colonnes est dans `common.py`
(`ROLES_COLONNES`, `trouver_colonne`, `porte_des_subventions`) ; les fichiers
écartés sont listés dans `data/sources-manifest/scdl.json` et `ods.json`, avec
leurs colonnes réelles — de quoi mesurer le gain avant d'écrire une ligne de
code, comme cela a été fait en phase 6a.

### 1b. Re-tenter les liens morts

**371 échecs amont** : 236 réponses 404 et 135 échecs de connexion chez
`datacat.datalocale`. Rien à corriger chez nous — à relancer, les portails
bougent.

### 1c. Élargir la liste des portails Opendatasoft

Le moissonneur `fetch_ods.py` ne visite que **11 portails** (liste en tête du
fichier, constante `PORTAILS`). Beaucoup d'autres collectivités publient sur
la même API Explore v2.1 : les ajouter ne demande qu'une ligne chacune, le
reste du moissonneur ne bouge pas.

### 1d. `api.datasubvention.beta.gouv.fr` — *le plus gros gain, mais bloqué*

Ce serait **la** source de référence : elle agrège Chorus et les données des
collectivités. L'API vit mais renvoie **401** — réservée aux agents publics et
aux associations habilitées.

**C'est une démarche administrative, pas technique.** Une demande de compte est
le seul chemin. À faire hors du code.

### Ce qui manquera toujours

Les communes de moins de 3 500 habitants ne sont pas tenues de publier, et
parmi celles qui le sont, l'obligation est peu suivie. Aucun moissonnage ne
comblera cela : la lacune est légale. C'est ce que la page « Ce que ce site ne
sait pas » est là pour dire.

---

## 2. Les anomalies connues

Toutes signalées dans le rapport de qualité, aucune corrigée en douce.

### 2a. L'année 2011 — **12,54 Md€, soit 6,7 fois les années voisines**

Jamais élucidé. C'est **8 % du total affiché** : le plus gros point
d'interrogation qui subsiste. Le chiffre est conforme à ce que publie la
source ; c'est le périmètre de l'annexe cette année-là qui reste à vérifier.

Piste : le PLF Jaune change de structure tous les 3-4 ans, et le millésime qui
porte 2011 pourrait mêler deux périmètres. Comparer colonne à colonne avec
2010 et 2012.

### 2b. La quarantaine Lyon — **48 Md€ mis de côté**

`metropole-lyon` : 9 081 lignes totalisant 48 Md€ quand le budget de la
Métropole avoisine 3,8 Md€. Médiane à 1 584 200 €, minimum 100, et 85 % des
valeurs multiples de 100 : tout indique des **centimes lus comme des euros**.

On ne divise pas par cent de sa propre autorité. `data.grandlyon.com` renvoie
**401**, l'amont n'est donc pas vérifiable. Même blocage que 1d.

Idem, plus petit : deux lignes de `ville-boulogne-billancourt` à 750 M€ et
75 M€.

### 2c. Identifiants et champs manquants

| Défaut | Lignes |
|---|---|
| Sans RNA | 2 408 486 |
| Sans SIRET | 883 176 |
| Sans URL de source | 804 790 |
| Département inexploitable | 328 056 |
| Sans année | 169 105 |
| Montant nul | 77 139 |
| **SIRET détruits par un tableur** (`2,19301E+13`) | **29 159** |
| Montants invraisemblables, exclus des totaux | 9 139 |
| Doublons internes à une source, conservés et signalés | 96 890 |

Les SIRET en notation scientifique **ne sont pas réparables** : Excel n'a gardé
que six chiffres significatifs. Le vrai correctif est de re-moissonner l'amont.

### 2d. `cd-finistere` — 5 442 lignes au nom de donateur détruit

Les octets du fichier hérité sont `\xef\xbf\xbd` (U+FFFD) : « Conseil
D<?>partemental du Finist<?>re ». Irrécupérable depuis ce fichier. Ces lignes
ne se dédupliquent pas avec leurs jumelles bien encodées. À re-moissonner.

---

## 3. Dette mineure

- **Le banc de mesure n'a pas été rejoué depuis la phase 6a.** Les chiffres de
  vitesse dans `CLAUDE.md` sont ceux de 6a ; la 6b ne change que les données
  (en baisse), donc ils ne peuvent qu'être meilleurs — mais ce n'est pas
  mesuré. `node scripts/bench/measure.js --label phase6b`.
- **Le doublon Baule** : 182 lignes, 365 k€. `communes-pays-loire` étiquette
  « Commune de La Baule » ce qui est en réalité **Baule dans le Loiret**. On ne
  corrige pas le libellé : deviner qu'un « La Baule » veut dire « Baule »
  ailleurs fondrait deux communes réelles. Détail dans `CLAUDE.md`.

---

## Ordre recommandé

1. **Le dépivotage (1a)** — mécanique, sans arbitrage métier, et c'est ce qui
   devrait faire bouger la couverture communale plus que tout le reste.
   Mesurer le gain sur les manifestes AVANT de coder, comme en phase 6a.
2. **Les portails ODS (1c) et les liens morts (1b)** — quelques lignes, gain
   immédiat.
3. **L'anomalie 2011 (2a)** — un huitième du total repose dessus.
4. **Les habilitations (1d, 2b)** — à lancer en parallèle, le délai est
   administratif.

---

## Comment reprendre à froid

```bash
# Le pipeline entier, moissonnages exceptés (ils ont leur cache) :
bash scripts/pipeline/tout_reconstruire.sh

# Les moissonnages, quand on veut rafraîchir l'amont :
python3 scripts/pipeline/fetch_scdl.py     # data.gouv.fr
python3 scripts/pipeline/fetch_ods.py      # portails Opendatasoft
python3 scripts/pipeline/fetch_plf_jaune.py

# Le banc de mesure :
node scripts/bench/measure.js --label <phase>
```

`normalize_legacy.py` a besoin de `data/sources/*.js`, retirés du dépôt :
`git checkout 0b14348 -- data/sources` avant de le rejouer.

**`verify.py` vient EN DERNIER** (plusieurs contrôles comparent l'index de
recherche à la table canonique) et **doit rester vert** : 30/30 aujourd'hui.

Travailler sur `main`, et seulement `main`.
