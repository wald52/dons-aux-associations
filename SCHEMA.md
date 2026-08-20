# Schéma canonique

Décidé en phase 0, avant toute écriture du pipeline. Une ligne = une attribution
de subvention **telle que publiée par sa source**.

Format de stockage : **Parquet** (`data/canonical/subventions.parquet`), colonnes
plates — pas d'objets imbriqués. C'est ce qui rend possible la lecture par plages
d'octets en phase 2 et les croisements SQL en phase 3.

## Doctrine

Reprise de `carte-finances-locales` : **fidélité maximale à la source**. On ne
corrige pas un montant, on ne devine pas un bénéficiaire. Tout enrichissement
(département déduit d'un SIRET, année extraite d'un libellé) est **marqué comme
tel** dans `quality_flags`, jamais fondu dans la donnée d'origine.
Si une information manque, elle reste nulle et la carte l'assume.

## Ce que l'échantillonnage des sources a révélé

Quatre constats relevés sur des enregistrements réels, qui justifient des
colonnes qu'on n'aurait pas mises spontanément :

1. **Toutes les lignes ne sont pas des subventions individuelles.**
   `ville-rennes` publie des **lignes de budget** :
   `"Subv. fonct. aux associat.et autres personnes droit privé"`, 357 638,62 €,
   objet `"6574.00"` (un compte M14). C'est un agrégat, pas une attribution.
   Le sommer avec des attributions individuelles compte deux fois et gonfle le
   nombre d'« associations ». → colonne **`granularity`**.

**Ce qui entre dans les totaux** est décidé par `compte_dans_les_totaux()`
dans `common.py`, et par elle seule — comme le schéma et la clé métier. Trois
exclusions, trois raisons distinctes : un agrégat déjà somme d'autres lignes
(`granularity`), une exécution budgétaire déjà comptée au vote (`measure`),
un bénéficiaire que la source déclare hors du champ associatif
(`beneficiary_kind` + `beneficiary_kind_provenance`). Rien n'est jeté : ces
lignes restent dans la table et restent consultables. Ne jamais recopier
cette règle ailleurs.

2. **Tous les bénéficiaires ne sont pas des associations.**
   `anct-politique-ville` verse à `"POLE EMPLOI"` (SIRET 130005481…), un
   établissement public. → colonne **`beneficiary_kind`**.

3. **Certains donateurs sont inconnus, pas étatiques.**
   Des lignes portent `"Source data.gouv.fr"`, `"Collectivité"` ou `"Commune"`
   comme attribuant, avec `type = "state"` : l'attribuant n'a pas été récupéré.
   → valeur **`inconnu`** dans `donor_level`, jamais un rattachement par défaut.
   *Mesuré après coup : 191 lignes seulement, et non un gonflement massif de
   l'État comme le laissait craindre le premier échantillon.*

4. **Le champ `source` mélange URL et texte libre.**
   Tantôt une URL, tantôt `"Ville de Rennes 2016"` ou `"CNDS 2015 part
   nationale"`. Non exploitable pour un lien cliquable.
   → **`source_url`** et **`source_label`** séparés.

Autres défauts constatés, traités par le pipeline : `justification` contenant
une date (`region-idf`), `convention` tantôt booléen tantôt `""`, département
absent codé tantôt `"00"` tantôt `""`, `program` tantôt à la racine tantôt dans
`entity`.

## Colonnes

### Identité

| Colonne | Type | Note |
|---|---|---|
| `row_id` | string | Hash déterministe de `source_id` + `source_row_ref`. Stable entre deux builds. |
| `business_key` | string | Clé de déduplication, cf. plus bas. |

### Bénéficiaire

| Colonne | Type | Note |
|---|---|---|
| `beneficiary_name_raw` | string | Verbatim de la source, jamais retouché. |
| `beneficiary_name_norm` | string | Accents pliés, majuscules, forme juridique retirée. **Sert au rapprochement** quand SIRET et RNA manquent (73 % des lignes). |
| `beneficiary_siret` | string(14) | Nul si invalide (contrôle de Luhn). |
| `beneficiary_siren` | string(9) | Dérivé du SIRET. |
| `beneficiary_rna` | string(10) | Format `W` + 9 chiffres, sinon nul. |
| `beneficiary_kind` | enum | `association`, `public_body`, `company`, `individual`, `inconnu` |
| `beneficiary_commune_insee` | string(5) | Référentiel INSEE. |
| `beneficiary_dep_code` | string(2-3) | Corse `2A`/`2B`, outre-mer sur 3. Nul si inconnu — **jamais `"00"`**. |
| `beneficiary_reg_code` | string(2) | |
| `beneficiary_address_raw` | string | |

### Donateur

| Colonne | Type | Note |
|---|---|---|
| `donor_name_raw` | string | |
| `donor_name_norm` | string | |
| `donor_siren` | string(9) | **Joignable avec `carte-finances-locales`** : c'est ce qui permettra de rapporter les subventions versées aux finances de la collectivité. |
| `donor_level` | enum | Taxonomie unifiée, cf. plus bas. |
| `donor_commune_insee` | string(5) | |
| `donor_dep_code` | string(2-3) | |
| `donor_reg_code` | string(2) | |
| `donor_program` | string | Programme budgétaire, direction, dispositif. |

### Montant et temps

| Colonne | Type | Note |
|---|---|---|
| `amount_eur` | float64 | Montant en euros. **Nul si la valeur publiée n'est pas un montant** (cf. `amount_implausible`), de sorte qu'une somme sur cette colonne soit juste sans filtre à ne pas oublier. |
| `amount_rejected_eur` | float64 | La valeur publiée, conservée verbatim, quand elle a été écartée de `amount_eur`. Nulle partout ailleurs. Rien n'est perdu. |
| `year` | int32, nullable | Exercice. **Nul si inconnu — jamais `0`.** |
| `year_provenance` | enum | `published`, `inferred`, `unknown` |
| `date_convention` | date, nullable | |

### Objet

| Colonne | Type | Note |
|---|---|---|
| `purpose_raw` | string | |
| `purpose_norm` | string | Sert à la clé métier. |

### Nature et fiabilité

| Colonne | Type | Note |
|---|---|---|
| `granularity` | enum | `individual` ou `aggregate`. **Ne jamais sommer les deux ensemble** : c'est la règle qui évite le double comptage. Par défaut l'interface ne montre que `individual`. |
| `measure` | enum | `attribue` ou `verse`. Une collectivité publie souvent le même argent deux fois : ce qu'elle a **voté**, et ce qu'elle a **versé** (annexe au compte administratif). **Seul `attribue` entre dans les totaux.** `verse` est ingéré et consultable, jamais sommé. Lu au titre du jeu par `measure_of`. |
| `beneficiary_kind_provenance` | enum | `declared` si la source publie la nature juridique du bénéficiaire, `guessed` si nous l'avons déduite du nom. Une nature **déclarée** hors du champ associatif sort la ligne des totaux ; une nature **devinée** ne suffit pas. L'asymétrie est voulue : exclure à tort efface une association réelle, inclure à tort laisse une ligne visible et corrigeable. |
| `is_convention` | bool, nullable | Vrai booléen, plus de `""`. |
| `quality_flags` | list\<string\> | Voir la liste ci-dessous. |
| `confidence` | enum | `high`, `medium`, `low` |

**Drapeaux qualité** — ce qui a été constaté, jamais corrigé en silence :

| Drapeau | Sens |
|---|---|
| `no_siret`, `no_rna` | Identifiant absent de la source. |
| `siret_invalid` | Présent mais refusé par la clé de Luhn. |
| `siret_scientific_notation` | **Le SIRET est passé par un tableur qui l'a traité comme un nombre** : `2,19301E+13`. Au-delà de six chiffres significatifs, tout est perdu. Irrécupérable — 29 214 lignes. |
| `dep_unknown` | Aucun département exploitable. |
| `dep_from_name` | Département déduit d'un libellé (« Seine-Saint-Denis », « Préfecture du Nord ») et non d'un code. Enrichissement, donc tracé. |
| `dep_only` | Département connu, mais pas la commune. |
| `year_missing`, `year_invalid` | Année absente, ou hors bornes plausibles. |
| `donor_unattributed` | Attribuant non récupéré de la source. |
| `beneficiary_not_association` | Le bénéficiaire est un établissement public. |
| `amount_zero`, `amount_negative` | Montant nul ou négatif publié tel quel. |
| `amount_implausible` | **Au-delà de dix milliards d'euros pour une attribution unique : ce n'est pas un montant.** Cas constaté : un SIRET recopié dans la colonne montant. Ligne conservée, mais exclue de tous les totaux. |

### Provenance

Toute ligne affichée doit pouvoir remonter à sa source. C'est non négociable
sur un sujet d'argent public.

| Colonne | Type | Note |
|---|---|---|
| `source_id` | string | Identifiant du jeu de données. |
| `source_label` | string | Libellé lisible. |
| `source_url` | string | URL du dataset. **Une URL, pas du texte.** |
| `source_row_ref` | string | Référence de la ligne dans le fichier d'origine. |
| `source_family` | enum | `scdl`, `plf_jaune`, `portail`, `manuel` |
| `source_published_at` | date, nullable | |
| `license` | string | |
| `ingested_at` | timestamp | |

## Taxonomie des donateurs — `donor_level`

Sept valeurs, closes. Le diagnostic initial en annonçait cinq ; **l'examen des
données en impose deux de plus**, et il vaut mieux le dire :

| Valeur | Périmètre |
|---|---|
| `etat` | Budget de l'État, ministères, services déconcentrés (DRAC, DILCRAH…). |
| `operateur` | Opérateurs de l'État à budget propre : CNDS, ANCT, CNSA, ARS, EFS. **54 497 lignes aujourd'hui.** Les fondre dans `etat` reviendrait à compter deux fois : ce sont des budgets distincts. |
| `region` | Conseils régionaux. |
| `departement` | Conseils départementaux. |
| `epci` | Intercommunalités, métropoles, communautés. |
| `commune` | Communes et villes. |
| `inconnu` | Attribuant non récupéré de la source. **Jamais rattaché d'office à un échelon** (cf. constat 3). |

Remplace les dix valeurs actuelles, dont les doublons `state`/`ministere`,
`department`/`departement`, `commune`/`city`, `epci`/`metropole`.

## Clé métier et déduplication

La déduplication actuelle compare les identifiants techniques, préfixés par
source : deux sources décrivant la même subvention ne se croisent jamais.

**Nouvelle clé :**

```
business_key = sha1(
      beneficiary_siret  ou  beneficiary_name_norm
  ||  donor_siren        ou  donor_name_norm
  ||  year
  ||  round(amount_eur, 2)
  ||  purpose_norm[:120]
)
```

**Arbitrage entre doublons**, dans l'ordre :

1. `confidence` la plus élevée ;
2. `source_family` la plus proche du terrain — le portail de la collectivité
   (`portail`) prime sur l'agrégat national (`scdl`) ;
3. la ligne portant un SIRET prime sur celle qui n'en a pas.

La ligne écartée n'est pas perdue : ses `source_id` sont conservés dans
`duplicate_of_sources` (list\<string\>), pour que l'utilisateur voie que deux
administrations publient la même subvention.

**Important** — cette déduplication va **faire baisser les totaux affichés**.
C'est le résultat attendu : les totaux actuels sont surévalués d'un montant
inconnu. La baisse devra être chiffrée source par source dans le rapport de
qualité, jamais subie en silence.

## Tables dérivées

Produites par le même pipeline, à partir de la table canonique.

| Fichier | Contenu |
|---|---|
| `data/canonical/subventions/year=AAAA/*.parquet` | La table ci-dessus, source de vérité, **partitionnée par année**. GitHub refuse tout fichier de plus de 100 Mo et la table entière en fait 110 ; le partitionnement lève cette contrainte et permet à DuckDB d'élaguer les années inutiles. |
| `data/canonical/quality-report.json` | Par source : lignes lues, retenues, écartées, taux de remplissage par colonne, drapeaux levés. **Fait foi pour juger toute évolution des données.** |
| `data/canonical/coverage.json` | Par collectivité du référentiel INSEE : donnée présente / absente / publiée mais non ingérée. Alimente la carte de couverture de la phase 4. |
| `data/aggregates/*.json.gz` | Agrégats précalculés du premier écran (phase 2). |

## Règles qui engagent tout le reste

1. **Nul plutôt que faux.** Pas de `"00"`, pas de `year: 0`, pas de `""` en guise d'absence.
2. **Tout enrichissement est tracé** dans `quality_flags`.
3. **Jamais de somme entre `individual` et `aggregate`.**
4. **`inconnu` n'est pas `etat`.**
5. **Toute ligne remonte à sa source** par `source_url` + `source_row_ref`.
