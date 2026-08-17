// ============================================================
//  TEMPLATE POUR AJOUTER UNE NOUVELLE SOURCE DE DONNÉES
// ============================================================
//
//  RÈGLE : TOUTES LES DONNÉES DOIVENT ÊTRE STOCKÉES LOCALEMENT.
//  Le site ne doit PAS appeler d'API externe au chargement.
//  Si la source est une API, utiliser un script Node.js (comme
//  scripts/convert-data.js) pour télécharger et convertir les
//  données en fichier JS statique. Cela évite toute restriction
//  d'accès future (CORS, quota, clé API, fermeture du service).
//
//  Étapes :
//    1. Copier ce fichier → data/sources/<nom-source>.js
//    2. Remplacer RAW_DATA par vos données (ou l'importer depuis un CSV)
//    3. Ajouter un normalizer dans data/loader.js (si le format diffère)
//    4. Ajouter <script src="data/sources/<nom-source>.js"></script>
//       dans index.html, AVANT data/loader.js
//
// ============================================================

(function() {
    // ---- VOS DONNÉES BRUTES ----
    // Remplacez par vos données, importées depuis un CSV, API, etc.
    var RAW_DATA = [
        // Exemple avec le format attendu (tous les champs obligatoires) :
        // {
        //     id: "ma-source-000001",
        //     association: {
        //         name: "NOM DE L'ASSOCIATION",
        //         rna: "W751123456",          // RNA (optionnel)
        //         siret: "12345678901234",     // SIRET (optionnel)
        //         address: "Paris",            // Commune (optionnel)
        //         department: "75",            // Code département 2 chiffres
        //         object: "Objet social"       // Optionnel
        //     },
        //     entity: {
        //         name: "Ministère - Programme X",  // Nom du donateur
        //         type: "state",                     // state|region|department|commune|epci
        //         level: "ministère",                // ministère|region|department|commune|epci
        //         program: "Programme 101"           // Optionnel
        //     },
        //     amount: 15000,                    // Montant en euros (nombre)
        //     year: 2024,                       // Année d'exercice
        //     program: "Programme 101",         // Optionnel
        //     justification: "Description",     // Optionnel
        //     convention: false,                // true/false
        //     source: "https://..."             // URL de la source
        // }
    ];

    // ---- ENREGISTREMENT ----
    // L'identifiant unique de la source. Utilisé aussi dans le normalizer.
    var SOURCE_ID = 'ma-source';

    __registerDataSource(SOURCE_ID, RAW_DATA);
    console.log('Source "' + SOURCE_ID + '" : ' + RAW_DATA.length + ' lignes enregistrées');
})();
