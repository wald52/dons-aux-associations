# Ce qui reste à faire

État arrêté au **20/08/2026**, après la phase 7. Chiffres mesurés, pas estimés :
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
| Total individuel | 144,71 Md€ |
| Sources | 548 |
| Bénéficiaires résolus | 406 846 |
| Dont cumulant 3 échelons ou plus | 6 783 |
| Contrôles `verify.py` | 30/30 |

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

### 1b. `api.datasubvention.beta.gouv.fr` — *le seul gain d'un ordre de grandeur*

Ce serait **la** source de référence : elle agrège Chorus et les données des
collectivités. L'API vit mais renvoie **401** — réservée aux agents publics et
aux associations habilitées.

**C'est une démarche administrative, pas technique.** Une demande de compte est
le seul chemin, et c'est désormais le premier poste du reste-à-faire : aucun
travail de code ne remplacera cette habilitation.

### 1c. Ce qui manquera toujours

Les communes de moins de 3 500 habitants ne sont pas tenues de publier, et
parmi celles qui le sont, l'obligation est peu suivie. Aucun moissonnage ne
comblera cela : la lacune est légale. C'est ce que la page « Ce que ce site ne
sait pas » est là pour dire.

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
- **`measure_of` ne voit pas les libellés à tirets bas.** `fold` ne ramène pas
  `_` à l'espace, si bien que `subventions_fonctionnement_versees_...csv` n'est
  pas reconnu comme une exécution budgétaire. Grenoble entre donc en `attribue`
  alors qu'il publie du « versé ». Le corriger déplacerait des montants hors
  des totaux dans plusieurs sources à la fois : à mesurer avant de toucher.
- **Le fichier PLF 2024 est vide à la source** (« csv: fichier vide ou non
  tabulaire ») : l'exercice 2022 manque donc au corpus PLF Jaune.

---

## Ordre recommandé

1. **La demande d'habilitation `datasubvention` (1b)** — c'est le seul chantier
   qui change l'ordre de grandeur de la couverture, et son délai est
   administratif : à lancer d'abord, il avancera pendant qu'on code.
2. **La levée de la quarantaine 2011 (2a)** — 12,3 Md€ et un huitième de
   l'histoire du site en dépendent, et c'est la seule des deux quarantaines qui
   ne demande pas d'habilitation.
3. **`measure_of` et les tirets bas (dette mineure)** — un défaut de
   reconnaissance qui déplace des montants entre « voté » et « versé » ;
   mesurer l'ampleur avant de décider.
4. **Ne pas relancer le moissonnage pour la couverture.** Les deux canaux sont
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
