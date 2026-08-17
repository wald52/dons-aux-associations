# Cartographie des Dons Publics aux Associations

Application web statique qui cartographie les subventions publiques versées aux associations en France par l'État, les régions, les départements, les communes et les EPCI.

## 🚀 Caractéristiques

- **Architecture modulaire** : Code organisé en modules ES6 pour une meilleure maintenabilité
- **Gestion d'état centralisée** : Pattern Redux-like pour la gestion de l'état de l'application
- **Performance** : Système de lazy loading des données et cache localStorage
- **Sécurité** : Validation des données, protection XSS et Content Security Policy
- **Accessibilité** : Support du mode sombre, navigation clavier, contraste amélioré
- **Fonctionnalités** :
  - Carte interactive de France (départements/régions)
  - Filtres dynamiques (type d'entité, année, montant, recherche)
  - Export CSV et JSON
  - Partage d'URL avec filtres
  - Pagination configurable
  - Graphiques de visualisation (Chart.js)

## 📋 Prérequis

- Un navigateur web moderne (Chrome, Firefox, Safari, Edge)
- Un serveur HTTP local (pour charger les modules ES6)

## 🛠️ Installation

### Option 1: Serveur HTTP Python

```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000
```

### Option 2: Serveur HTTP Node.js

```bash
# Installation globale de http-server
npm install -g http-server

# Lancement
http-server -p 8000
```

### Option 3: Extension VS Code

1. Installer l'extension "Live Server"
2. Ouvrir `index.html`
3. Clic droit → "Open with Live Server"

## 📁 Structure du projet

```
.
├── index.html                 # Page principale
├── src/
│   ├── app.js                # Point d'entrée de l'application
│   ├── state.js              # Gestion d'état centralisée
│   ├── styles.css            # Styles CSS
│   └── modules/
│       ├── filters.js        # Logique de filtrage
│       ├── sorting.js        # Logique de tri
│       ├── map.js            # Gestion de la carte
│       ├── charts.js         # Graphiques Chart.js
│       ├── ui.js             # Interactions UI
│       ├── export.js         # Export CSV/JSON
│       ├── search.js         # Recherche
│       ├── theme.js          # Thème sombre/clair
│       ├── data-loader.js    # Lazy loading des données
│       ├── cache-manager.js  # Cache localStorage
│       ├── validation.js     # Validation des données
│       ├── error-handler.js  # Gestion d'erreurs
│       └── url-manager.js    # Gestion d'URL pour partage
├── data/
│   ├── departments.js        # Données des départements
│   ├── loader.js             # Loader de données
│   ├── sources-index.js      # Index des sources de données
│   ├── sample-data.js        # Jeu de données de démonstration
│   ├── svg/                  # Cartes SVG
│   └── sources/              # Fichiers de données par source
└── README.md                 # Ce fichier
```

## 🎯 Utilisation

### Filtres

- **Type d'entité** : Filtrer par type de donateur (État, Région, Département, Commune, EPCI)
- **Plage de montants** : Filtrer par montant de subvention
- **Année** : Filtrer par année de subvention
- **Recherche** : Rechercher par nom d'association ou d'entité

### Carte interactive

- Cliquez sur un département ou une région pour filtrer les résultats
- Utilisez le sélecteur pour basculer entre vue département/région
- Les couleurs indiquent le montant total des subventions reçues

### Export

- **Export CSV** : Exporter les résultats filtrés au format CSV
- **Export JSON** : Exporter les résultats filtrés au format JSON avec métadonnées
- **Copier le lien** : Partager la vue actuelle via URL

### Thème

- Utilisez le bouton 🌙/☀️ pour basculer entre mode clair et mode sombre
- La préférence est sauvegardée dans localStorage

## 🔧 Développement

### Architecture modulaire

L'application utilise une architecture modulaire avec ES6 modules :

- **State** (`src/state.js`) : Gestion centralisée de l'état
- **Modules** (`src/modules/`) : Fonctionnalités séparées en modules indépendants
- **App** (`src/app.js`) : Orchestrateur qui initialise tous les modules

### Ajouter une nouvelle source de données

1. Ajouter le fichier de données dans `data/sources/`
2. Mettre à jour `data/sources-index.js` avec les métadonnées
3. Ajouter le script dans `index.html` si nécessaire

### Personnalisation

- **Styles** : Modifier `src/styles.css`
- **Couleurs** : Modifier les variables CSS dans `:root` et `[data-theme="dark"]`
- **Filtres** : Modifier `src/modules/filters.js`

## 🔒 Sécurité

- **Content Security Policy** : Protection contre XSS et injections
- **Validation des données** : Validation stricte des entrées utilisateur
- **Sanitization** : Échappement automatique des données affichées
- **HTTPS** : Utilisation recommandée pour la production

## ♿ Accessibilité

- **Navigation clavier** : Support complet de la navigation au clavier
- **ARIA labels** : Labels ARIA pour les éléments interactifs
- **Contraste** : Contraste amélioré en mode sombre
- **Skip link** : Lien pour sauter au contenu principal
- **Focus visible** : Indicateur de focus visible
- **Reduced motion** : Support des animations réduites

## 📊 Sources de données

Les données proviennent de sources officielles d'open data français :

- **PLF Jaune** : data.economie.gouv.fr
- **Ville de Paris** : opendata.paris.fr
- **Départements** : data.gouv.fr et portails open data régionaux
- **Régions** : Portails open data régionaux
- **EPCI** : Portails open data des métropoles

Voir `SOURCES.md` pour la liste complète des sources intégrées.

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Fork le projet
2. Créez une branche pour votre fonctionnalité
3. Commit vos changements
4. Push vers la branche
5. Ouvrez une Pull Request

## 📝 Licence

Ce projet est open source. Voir le fichier LICENSE pour plus de détails.

## 📞 Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une issue sur le dépôt du projet.

## 🙏 Remerciements

- À toutes les collectivités françaises pour leurs données ouvertes
- À la communauté open data française
- Aux contributeurs du projet
