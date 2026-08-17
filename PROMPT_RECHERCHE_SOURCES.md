# Prompt de recherche exhaustive des sources de subventions publiques aux associations

Tu trouveras ci-dessous un prompt prêt à copier-coller dans une session IA dédiée.

---

Tu es un expert en open data français et en données publiques. Ta mission est de réaliser un inventaire exhaustif de **toutes** les sources de données ouvertes concernant les subventions publiques aux associations en France.

## Contexte du projet

Un site statique HTML/CSS/JS (aucun backend) cartographie les subventions publiques aux associations sur une carte de France. Les données sont stockées en fichiers JS statiques locaux — **aucun appel API depuis le navigateur** (CORS, quota, fermeture de service).

Format standard attendu par l'UI :
```js
{
  id: "source-000001",
  association: {
    name: "NOM ASSOCIATION",
    rna: "W751123456",        // optionnel
    siret: "12345678901234",  // optionnel
    address: "Paris",
    department: "75",
    object: "objet social"    // optionnel
  },
  entity: {
    name: "Ministère - Programme X",
    type: "state",       // state|region|department|commune|epci
    level: "ministère",  // ministère|region|department|commune|epci
    program: "Programme 101"  // optionnel
  },
  amount: 15000,
  year: 2024,
  justification: "...",  // optionnel
  convention: false,
  source: "https://..."
}
```

## Le projet a déjà intégré

- **État PLF Jaune 2022** : 95 807 subventions, 105 programmes (data.economie.gouv.fr)
- **Ville de Paris** : 76 207 subventions, 2013-2026 (opendata.paris.fr)

Un fichier SOURCES.md existe déjà avec un inventaire partiel. L'objectif est de le **compléter et corriger**.

## Ta mission

Recherche de manière systématique et exhaustive **toutes les sources de données ouvertes** listant des subventions versées à des associations par des organismes publics français.

### Catégories à couvrir

1. **État** — PLF Jaune (toutes années disponibles sur budget.gouv.fr et data.economie.gouv.fr)
2. **Ministères et opérateurs** — Chorus, Data.Subvention, FONJEP...
3. **Régions** — Chaque région : son portail open data, ses datasets sur data.gouv.fr
4. **Départements** — Chaque département : datasets sur data.gouv.fr, portails dédiés
5. **Métropoles et EPCI** — Données au format SCDL (schéma.data.gouv.fr/scdl/subventions)
6. **Communes** — Villes publiant leurs subventions (>3500 habitants, obligation légale)
7. **Autres** — OFGL, INJEP, associations.gouv.fr, Comptes annuels des associations...

### Pour chaque source trouvée, collecte :

- **URL précise** du dataset ou du portail
- **Producteur** (ministère, collectivité, organisme)
- **Format des données** (CSV, JSON, XLSX, API)
- **Colonnes disponibles** (si possible)
- **Volume approximatif** (nombre de lignes, période couverte)
- **Licence** (Licence Ouverte, ODbL, etc.)
- **Mise à jour** (fréquence, dernière mise à jour)
- **Qualité** (contient-il SIRET ? RNA ? département ? montant précis ?)
- **Contraintes d'accès** (API avec auth ? téléchargement direct ?)

### Méthodologie de recherche

1. **data.gouv.fr** — Chercher "subventions aux associations", "subventions associations", filtrer par organisation, explorer la page https://www.data.gouv.fr/pages/donnees_associations
2. **Portails open data régionaux** — data.iledefrance.fr, data.laregion.fr, etc.
3. **Portails open data des métropoles** — data.grandlyon.com, opendata.marseille.fr, data.toulouse-metropole.fr, opendata.bordeaux.fr, opendata.lillemetropole.fr, data.strasbourg.eu, data.nantesmetropole.fr...
4. **Portails open data départementaux** — datarmor.cotesdarmor.fr, data.loire-atlantique.fr, etc.
5. **data.economie.gouv.fr** — Datasets budgétaires
6. **OFGL** — data.ofgl.fr
7. **Data.Subvention** — beta.gouv.fr, documentation API, liste des collectivités intégrées
8. **budget.gouv.fr** — Annexes jaunes PLF

### Livrable attendu

Produis un inventaire structuré en tableau Markdown, organisé par catégorie (État, Régions, Départements, EPCI, Communes, Autres), avec pour chaque source : nom, URL, volume estimé, format, statut (👉 à intégrer / ⚠️ à vérifier / ❌ inaccessible), et toute note utile.

L'inventaire doit être le plus exhaustif possible. Privilégie la quantité à la qualité du détail — il vaut mieux 50 sources avec peu de détail que 5 sources très détaillées.

Format attendu :

```markdown
## [Catégorie]

| Source | URL | Producteur | Volume | Format | Période | Statut |
|--------|-----|-----------|--------|--------|---------|--------|
| ... | ... | ... | ... | ... | ... | ... |
```

N'oublie pas les Outre-mer (Guadeloupe, Martinique, Guyane, La Réunion, Mayotte, Nouvelle-Calédonie, Polynésie).
