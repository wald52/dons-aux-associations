const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// ============================================================
//  Configuration des millésimes PLF Jaune
// ============================================================

const MILLESIMES = [
    {
        year: 2012, label: 'PLF 2012 (subventions 2010)',
        datasetId: 'plf2012-jaune-donnees-associations-subventionnees',
        colProgram: null, colSiren: 'SIREN', colNic: null,
        colDenomination: 'ASSOCIATION', colMontant: null,
        colObjet: null, colRNA: null,
        colCOGCode: null, colCOGLibelle: null,
        colDepartement: null, colVille: null,
        convention: false, montantField: 'Total des subventions',
        objetField: 'Détail des subventions'
    },
    {
        year: 2013, label: 'PLF 2013 (subventions 2011)',
        datasetId: 'plf2013-jaune-donnees-associations-subventionnees',
        colProgram: 'Programme en 2011', colSiren: 'SIREN', colNic: null,
        colDenomination: 'Association', colMontant: null,
        colObjet: 'Objet de la subvention', colRNA: null,
        colCOGCode: null, colCOGLibelle: null,
        colDepartement: 'Département', colVille: 'Ville',
        convention: false, montantField: 'Subvention 2011 en euros',
        objetField: null
    },
    {
        year: 2014, label: 'PLF 2014 (subventions 2012)',
        datasetId: 'plf-2014-jaune-donnees-associations-subventionnees-2012',
        colProgram: 'PROGRAMME', colSiren: 'SIREN', colNic: null,
        colDenomination: 'ASSOCIATION', colMontant: null,
        colObjet: 'OBJET', colRNA: null,
        colCOGCode: null, colCOGLibelle: null,
        colDepartement: 'DEPARTEMENT', colVille: 'VILLE',
        convention: true, conventionField: 'Convention',
        montantField: 'Subvention 2012', objetField: null
    },
    {
        year: 2015, label: 'PLF 2015 (subventions 2013)',
        datasetId: 'plf-2015-jaune-effort-financier-de-letat-en-faveur-des-associations-',
        colProgram: 'PROGRAMME 2013', colSiren: 'SIREN', colNic: null,
        colDenomination: 'ASSOCIATION', colMontant: null,
        colObjet: 'OBJET', colRNA: null,
        colCOGCode: null, colCOGLibelle: null,
        colDepartement: 'DEPARTEMENT', colVille: 'VILLE',
        convention: true, conventionField: 'Convention',
        montantField: 'Subvention 2013', objetField: null
    },
    {
        year: 2016, label: 'PLF 2016 (subventions 2014)',
        datasetId: 'plf-2016-jaune-effort-financier-de-letat-en-faveur-des-associations-',
        colProgram: 'PROGRAMME', colSiren: 'SIREN', colNic: null,
        colDenomination: 'ASSOCIATION', colMontant: null,
        colObjet: 'OBJET', colRNA: null,
        colCOGCode: null, colCOGLibelle: null,
        colDepartement: 'DEPARTEMENT', colVille: 'VILLE',
        convention: true, conventionField: 'Convention',
        montantField: '2014', objetField: null
    },
    {
        year: 2017, label: 'PLF 2017 (subventions 2015)',
        datasetId: 'projet-de-loi-de-finances-pour-2017-plf-2017-jaune-effort-financier-de-letat-en-',
        colProgram: 'PROGRAMME', colSiren: 'SIREN', colNic: null,
        colDenomination: 'ASSOCIATION', colMontant: null,
        colObjet: null, colRNA: null,
        colCOGCode: null, colCOGLibelle: null,
        colDepartement: 'Département', colVille: 'Ville',
        convention: false, montantField: 'Subvention 2015',
        objetField: null
    },
    {
        year: 2018, label: 'PLF 2018 (subventions 2016)',
        datasetId: 'projet-de-loi-de-finances-pour-2018-plf-2018-donnees-de-lannexe-jaune-effort-fin',
        colProgram: 'Programme (2016)', colSiren: 'SIREN', colNic: 'NIC',
        colDenomination: 'Dénomination', colMontant: 'Montant',
        colObjet: 'Objet', colRNA: 'RNA',
        colCOGCode: 'COG : code département', colCOGLibelle: 'COG : ville ou pays',
        colDepartement: null, colVille: null,
        convention: true, conventionField: 'Convention 2016',
        montantField: null, objetField: null
    },
    {
        year: 2020, label: 'PLF 2020 (subventions 2018)',
        datasetId: 'projet-de-loi-de-finances-pour-2020-plf-2020-donnees-de-lannexe-jaune-effort-fin',
        colProgram: 'Programme', colSiren: 'SIREN', colNic: 'NIC',
        colDenomination: 'Dénomination', colMontant: 'Montant',
        colObjet: 'Objet', colRNA: null,
        colCOGCode: 'COG : code département ou pays', colCOGLibelle: 'COG : ville ou pays',
        colDepartement: null, colVille: null,
        convention: true, conventionField: 'Convention',
        montantField: null, objetField: null
    },
    {
        year: 2025, label: 'PLF 2025 (subventions 2023)',
        datasetId: 'plf25-donnees-de-l-annexe-jaune-effort-financier-de-l-etat-en-faveur-des-associations',
        colProgram: 'Programme', colSiren: 'SIREN', colNic: 'NIC',
        colDenomination: 'Dénomination', colMontant: 'Montant',
        colObjet: null, colRNA: null,
        colCOGCode: 'COG : code', colCOGLibelle: 'COG : libellé',
        colDepartement: null, colVille: null,
        convention: true, conventionField: 'Convention 2022',
        montantField: null, objetField: 'Objet 2023'
    }
];

// ============================================================
//  Helpers
// ============================================================

function parseCSVLine(line, delimiter) {
    delimiter = delimiter || ';';
    var result = [];
    var current = '';
    var inQuotes = false;
    for (var i = 0; i < line.length; i++) {
        var char = line[i];
        if (char === '"') { inQuotes = !inQuotes; }
        else if (char === delimiter && !inQuotes) { result.push(current.trim()); current = ''; }
        else { current += char; }
    }
    result.push(current.trim());
    return result;
}

function parseMontant(str) {
    if (!str) return 0;
    if (typeof str === 'number') return str;
    var cleaned = str.replace(/[^0-9,\-\.]/g, '').replace(',', '.');
    var val = parseFloat(cleaned);
    return val || 0;
}

function getDepartmentFromCOG(cogCode) {
    if (!cogCode || cogCode.length < 2) return null;
    var code = String(cogCode).padStart(5, '0');
    if (code.startsWith('75')) return '75';
    if (code.startsWith('69')) return '69';
    if (code.startsWith('13')) return '13';
    if (code.startsWith('97') || code.startsWith('98')) return code.substring(0, 3);
    return code.substring(0, 2);
}

function getProgramLabel(code) {
    var labels = {
        '101': 'Accès au droit et à la justice', '102': 'Accès et retour à l\'emploi',
        '103': 'Accompagnement des mutations économiques et développement de l\'emploi',
        '104': 'Intégration et accès à la nationalité française',
        '105': 'Action de la France en Europe et dans le monde',
        '107': 'Administration pénitentiaire', '109': 'Aide à l\'accès aux soins',
        '110': 'Aide à la vie associative',
        '111': 'Amélioration de la qualité de l\'emploi et des relations du travail',
        '112': 'Aménagement et service des transports terrestres',
        '113': 'Paysages, eau et biodiversité',
        '119': 'Coordination des moyens de secours et de sécurité',
        '122': 'Compétitivité et durabilité de l\'agriculture et de l\'agroalimentaire',
        '123': 'Conditions de vie outre-mer',
        '124': 'Conduite et soutien des politiques sanitaires et sociales',
        '129': 'Coordination du travail gouvernemental', '131': 'Création',
        '134': 'Développement des entreprises et régulations', '135': 'Développement des sports',
        '137': 'Égalité entre les femmes et les hommes', '138': 'Emploi outre-mer',
        '139': 'Enseignement privé du premier et du second degrés',
        '140': 'Enseignement scolaire public du premier degré',
        '141': 'Enseignement scolaire public du second degré',
        '142': 'Enseignement supérieur et recherche agricoles',
        '143': 'Enseignement technique agricole',
        '144': 'Environnement et prospective de la politique de défense',
        '146': 'Équipement des forces', '147': 'Politique de la ville',
        '148': 'Fonction de contrôle de l\'administration', '149': 'Forêt',
        '150': 'Formations supérieures et recherche universitaire',
        '151': 'Français à l\'étranger et affaires consulaires',
        '152': 'Gestion des finances publiques',
        '155': 'Conception et pilotage des politiques de l\'agriculture',
        '156': 'Gestion fiscale et financière de l\'État',
        '157': 'Handicap et dépendance',
        '159': 'Information géographique et cartographique',
        '161': 'Interventions économiques en faveur des entreprises',
        '162': 'Interventions territoriales de l\'État',
        '163': 'Jeunesse et vie associative', '164': 'Justice judiciaire',
        '165': 'Justice administrative', '166': 'Justice des mineurs',
        '167': 'Liens entre la Nation et son armée', '169': 'Mémoire',
        '172': 'Monnaie', '174': 'Métropole', '175': 'Patrimoines',
        '176': 'Police nationale',
        '177': 'Prévention de l\'exclusion et insertion des personnes vulnérables',
        '178': 'Préparation et emploi des forces', '180': 'Presse et médias',
        '181': 'Protection de l\'environnement', '182': 'Protection des droits et libertés',
        '185': 'Rayonnement culturel et scientifique',
        '186': 'Recherche en matière de développement durable',
        '190': 'Recherche dans les domaines de l\'énergie et du développement durable',
        '192': 'Recherche et enseignement supérieur en matière économique et industrielle',
        '198': 'Régimes sociaux et de retraite',
        '203': 'Infrastructures et services de transports',
        '204': 'Prévention des risques',
        '205': 'Sécurité et qualité sanitaires de l\'alimentation',
        '206': 'Sécurité et paix publiques', '207': 'Sécurité et éducation routières',
        '209': 'Solidarité à l\'égard des pays en développement',
        '212': 'Soutien aux politiques du ministère de la Culture',
        '214': 'Soutien aux politiques du ministère de l\'Intérieur',
        '215': 'Soutien aux politiques de l\'Éducation nationale',
        '216': 'Soutien aux politiques de l\'enseignement supérieur',
        '217': 'Soutien aux politiques de la Défense',
        '218': 'Soutien aux politiques de l\'Outre-mer',
        '219': 'Soutien aux politiques de la Jeunesse et des Sports',
        '220': 'Soutien aux politiques du ministère de la Transition écologique',
        '224': 'Soutien aux politiques du ministère de l\'Agriculture',
        '230': 'Vie politique et citoyenne', '231': 'Vie étudiante',
        '232': 'Climat et transitions écologiques',
        '302': 'Facilitation et sécurisation des échanges',
        '303': 'Conduite et pilotage des politiques sanitaires et sociales',
        '304': 'Inclusion sociale et protection des personnes',
        '305': 'Recherche et développement dans le domaine de l\'environnement',
        '308': 'Protection des droits des victimes et accès à la nationalité',
        '310': 'Conduite et animation des politiques de l\'immigration et de l\'asile',
        '334': 'Livres et industries culturelles',
        '335': 'Innovations et transitions industrielles',
        '348': 'Réhabilitation des centres urbains',
        '349': 'Transition démographique et petite enfance',
        '352': 'Réussite scolaire et éducation prioritaire',
        '354': 'Santé des adolescents et jeunes adultes',
        '357': 'Soutien à l\'économie sociale et solidaire',
        '612': 'Coordination des politiques publiques et administration territoriale',
        '613': 'Relations avec les collectivités territoriales',
        '614': 'Animation et coordination des politiques éducatives et sociales',
        '623': 'Conduite et soutien des politiques territoriales',
        '624': 'Pilotage et animation des politiques sociales',
        '723': 'Soutien aux Outre-mer', '751': 'Politiques en faveur de l\'égalité des chances',
        '764': 'Transition écologique et cohésion territoriale',
        '775': 'Conduite et pilotage de la politique de défense',
        '776': 'Développement des territoires ultramarins',
        '901': 'Administration territoriale de l\'État',
        '902': 'Action extérieure de l\'État',
        '907': 'Administration et soutien des politiques économiques',
        '912': 'Soutien aux politiques de l\'environnement'
    };
    return labels[String(code)] || ('Programme ' + code);
}

function download(url) {
    return new Promise(function(resolve, reject) {
        var client = url.startsWith('https') ? https : http;
        console.log('  Téléchargement: ' + url.substring(0, 120) + '...');
        client.get(url, function(res) {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                console.log('  Redirection vers: ' + res.headers.location.substring(0, 120) + '...');
                client.get(res.headers.location, function(res2) {
                    var data = [];
                    res2.on('data', function(chunk) { data.push(chunk); });
                    res2.on('end', function() { resolve(Buffer.concat(data).toString('utf-8')); });
                });
                return;
            }
            var data = [];
            res.on('data', function(chunk) { data.push(chunk); });
            res.on('end', function() { resolve(Buffer.concat(data).toString('utf-8')); });
        }).on('error', reject);
    });
}

// ============================================================
//  Main
// ============================================================

var args = process.argv.slice(2);
var onlyYear = args.length > 0 ? parseInt(args[0]) : null;

var millesimes = MILLESIMES.filter(function(m) {
    return !onlyYear || m.year === onlyYear;
});

async function processAll() {
    for (var mi = 0; mi < millesimes.length; mi++) {
        var m = millesimes[mi];
        console.log('\n========================================');
        console.log('Conversion ' + m.label + ' (dataset: ' + m.datasetId + ')');
        console.log('========================================');

        var csvUrl = 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/' + m.datasetId + '/exports/csv?use_labels=true';
        
        try {
            var content = await download(csvUrl);
            var lines = content.split('\n').filter(function(l) { return l.trim(); });
            
            if (lines.length < 2) {
                console.log('  Fichier vide ou invalide');
                continue;
            }

            var headers = parseCSVLine(lines[0]);
            // Remove BOM character if present
            if (headers[0] && headers[0].charCodeAt(0) === 0xFEFF) {
                headers[0] = headers[0].substring(1);
            }
            
            // Skip if we got the ODS internal format (recordid columns)
            if (headers[0] === 'recordid' || headers[0] === '_record_id') {
                console.log('  Format ODS interne non utilisable (recordid). Tentative sans labels...');
                var csvUrl2 = 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/' + m.datasetId + '/exports/csv?use_labels=false';
                content = await download(csvUrl2);
                lines = content.split('\n').filter(function(l) { return l.trim(); });
                if (lines.length < 2) {
                    console.log('  Toujours invalide');
                    continue;
                }
                headers = parseCSVLine(lines[0]);
                if (headers[0] && headers[0].charCodeAt(0) === 0xFEFF) {
                    headers[0] = headers[0].substring(1);
                }
            }

            // Detect which columns we actually have
            console.log('  Colonnes: ' + headers.join('; '));
            console.log('  Lignes de données: ' + (lines.length - 1));

            var buildColIndex = function(name, alt) {
                var idx = headers.indexOf(name);
                if (idx === -1 && alt) idx = headers.indexOf(alt);
                if (idx === -1) {
                    // Try case-insensitive
                    for (var hi = 0; hi < headers.length; hi++) {
                        if (headers[hi].toLowerCase() === name.toLowerCase() ||
                            (alt && headers[hi].toLowerCase() === alt.toLowerCase())) {
                            idx = hi;
                            break;
                        }
                    }
                }
                return idx;
            };

            var idxProgram = buildColIndex(m.colProgram || 'PROGRAMME');
            var idxSiren = buildColIndex(m.colSiren || 'SIREN');
            var idxNic = m.colNic ? buildColIndex(m.colNic) : -1;
            var idxDenom = buildColIndex(m.colDenomination || 'Dénomination');
            var idxMontant = buildColIndex(m.montantField || 'Montant');
            var idxObjet = buildColIndex(m.objetField || m.colObjet || 'Objet');
            var idxRNA = buildColIndex(m.colRNA || 'RNA');
            var idxCOGCode = buildColIndex(m.colCOGCode || 'COG : code');
            var idxCOGLibelle = buildColIndex(m.colCOGLibelle || 'COG : libellé');
            var idxDepartement = buildColIndex(m.colDepartement || 'DEPARTEMENT');
            var idxVille = buildColIndex(m.colVille || 'VILLE');
            var idxConvention = m.convention ? buildColIndex(m.conventionField || 'Convention') : -1;
            var idxMission = buildColIndex('Mission');
            var idxMinistere = buildColIndex('Ministère');

            // If COG columns exist, use them for dept; override departement if COG present
            var useCOG = idxCOGCode >= 0;

            // Determine the subvention data year from the file
            var dataYear = 0;
            if (m.year < 2018) {
                // For 2012-2017, try to detect from the montant column name
                var montantCol = m.montantField;
                if (montantCol) {
                    var mMatch = montantCol.match(/(\d{4})/);
                    if (mMatch) dataYear = parseInt(mMatch[1]);
                }
            } else {
                // For 2018+, try to detect from filename or labels
                // Check the "Objet 2023" pattern
                var objetCol = m.objetField || m.colObjet || 'Objet';
                var oMatch = objetCol.match(/Objet\s+(\d{4})/);
                if (oMatch && !dataYear) dataYear = parseInt(oMatch[1]);
                // Or convention column
                var convCol = m.conventionField || 'Convention';
                var cMatch = convCol.match(/(\d{4})/);
                if (cMatch && !dataYear) dataYear = parseInt(cMatch[1]);
                // Or from the millesime field in the data
            }

            if (!dataYear) {
                // Try to extract from the first few rows
                for (var ri = 1; ri < Math.min(5, lines.length); ri++) {
                    var vals = parseCSVLine(lines[ri]);
                    if (vals.length === headers.length) {
                        if (idxMontant >= 0 && vals[idxMontant]) {
                            // Check if montant column name has a year in the header
                            var hdrYear = headers[idxMontant].match(/(\d{4})/);
                            if (hdrYear) { dataYear = parseInt(hdrYear[1]); break; }
                        }
                    }
                }
            }

            // If year still unknown, infer from convention: PLF year reports N-2
            // PLF year convention: 2018 -> 2016, etc.
            if (!dataYear) {
                // Check millesime
                if (lines.length > 1) {
                    var firstVals = parseCSVLine(lines[1]);
                    if (firstVals[0]) {
                        var milMatch = firstVals[0].match(/(\d{4})/);
                        if (milMatch) dataYear = parseInt(milMatch[1]);
                    }
                }
            }
            
            var subventionYear = dataYear || (m.year - 2);
            console.log('  Année des données: ' + subventionYear);

            var subventions = [];
            var errorCount = 0;
            var rowsWithAmount = 0;
            var idCounter = 0;

            for (var li = 1; li < lines.length; li++) {
                var values = parseCSVLine(lines[li]);
                if (values.length !== headers.length && values.length < 3) continue;
                
                idCounter++;

                try {
                    var denomination = '';
                    if (idxDenom >= 0 && idxDenom < values.length) denomination = values[idxDenom] || '';

                    var siren = '';
                    if (idxSiren >= 0 && idxSiren < values.length) siren = values[idxSiren] || '';
                    var nic = '';
                    if (idxNic >= 0 && idxNic < values.length) nic = values[idxNic] || '';

                    var montant = 0;
                    if (idxMontant >= 0 && idxMontant < values.length) {
                        montant = parseMontant(values[idxMontant]);
                    }

                    if (montant <= 0) continue;
                    if (!denomination) continue;

                    rowsWithAmount++;

                    var rna = '';
                    if (idxRNA >= 0 && idxRNA < values.length) {
                        var rnaVal = values[idxRNA] || '';
                        if (rnaVal.startsWith('W')) rna = rnaVal;
                    }

                    var objet = '';
                    if (idxObjet >= 0 && idxObjet < values.length) objet = values[idxObjet] || '';

                    var cogCode = '';
                    if (useCOG && idxCOGCode >= 0 && idxCOGCode < values.length) {
                        cogCode = values[idxCOGCode] || '';
                    }

                    var ville = '';
                    if (idxVille >= 0 && idxVille < values.length) ville = values[idxVille] || '';
                    if (!ville && idxCOGLibelle >= 0 && idxCOGLibelle < values.length) {
                        ville = values[idxCOGLibelle] || '';
                    }

                    var departement = '';
                    if (idxDepartement >= 0 && idxDepartement < values.length) {
                        departement = values[idxDepartement] || '';
                    }
                    if (!departement && useCOG) {
                        departement = getDepartmentFromCOG(cogCode);
                    }

                    var programCode = '';
                    if (idxProgram >= 0 && idxProgram < values.length) {
                        var progVal = values[idxProgram] || '';
                        // Extract numeric code: "102 - Accès..." or "102" or "Programme 102"
                        var progMatch = progVal.match(/(\d{3})/);
                        if (progMatch) programCode = progMatch[1];
                    }

                    var convention = false;
                    if (idxConvention >= 0 && idxConvention < values.length) {
                        var convVal = (values[idxConvention] || '').toLowerCase();
                        convention = convVal === 'oui' || convVal === 'true' || convVal === '1' || convVal === 'x' || convVal === 'yes';
                    }

                    var ministere = '';
                    if (idxMinistere >= 0 && idxMinistere < values.length) ministere = values[idxMinistere] || '';

                    // Build entity name
                    var entityName = 'État';
                    if (programCode) {
                        entityName = 'État — ' + getProgramLabel(programCode);
                    } else if (ministere) {
                        entityName = 'État — ' + ministere;
                    }

                    subventions.push({
                        id: 'plf-' + m.year + '-' + String(idCounter).padStart(6, '0'),
                        association: {
                            name: denomination,
                            rna: rna,
                            siret: siren + nic,
                            address: ville,
                            department: departement || '00',
                            object: objet
                        },
                        entity: {
                            name: entityName,
                            type: 'state',
                            level: 'ministère',
                            program: programCode ? getProgramLabel(programCode) : ''
                        },
                        amount: montant,
                        year: subventionYear,
                        justification: objet,
                        convention: convention,
                        source: 'https://www.data.gouv.fr/datasets/' + m.datasetId
                    });

                } catch (e) {
                    errorCount++;
                }

                if (idCounter % 5000 === 0) {
                    console.log('  ... ' + idCounter + ' lignes traitées (' + subventions.length + ' valides)');
                }
            }

            console.log('  Résultat: ' + subventions.length + ' subventions valides sur ' + idCounter + ' lignes');
            if (errorCount > 0) console.log('  Erreurs: ' + errorCount);

            var totalAmount = subventions.reduce(function(sum, s) { return sum + s.amount; }, 0);
            console.log('  Montant total: ' + totalAmount.toLocaleString('fr-FR') + ' €');

            if (subventions.length === 0) {
                console.log('  Aucune subvention extraite, fichier ignoré');
                continue;
            }

            var programs = {};
            subventions.forEach(function(s) {
                var p = s.entity.program || 'Inconnu';
                programs[p] = (programs[p] || 0) + 1;
            });
            var programCount = Object.keys(programs).length;

            var outputFile = path.join(__dirname, '..', 'data', 'sources', 'plf-jaune-' + m.year + '.js');
            var sourceId = 'plf-jaune-' + m.year;

            var sourceContent = '(function() {\n';
            sourceContent += '    var RAW_DATA = ' + JSON.stringify(subventions) + ';\n';
            sourceContent += '    __registerDataSource(\'' + sourceId + '\', RAW_DATA);\n';
            sourceContent += '    console.log(\'Source "' + sourceId + '" : \' + RAW_DATA.length + \' lignes, ' + programCount + ' programmes, ' + totalAmount.toLocaleString('fr-FR') + ' €\');\n';
            sourceContent += '})();\n';

            fs.writeFileSync(outputFile, sourceContent, 'utf-8');
            console.log('  Fichier généré: ' + outputFile);

        } catch (err) {
            console.log('  Erreur: ' + err.message);
        }
    }
}

processAll().then(function() {
    console.log('\n========================================');
    console.log('Conversion terminée');
    console.log('========================================');
}).catch(function(err) {
    console.error('Erreur fatale:', err);
});
