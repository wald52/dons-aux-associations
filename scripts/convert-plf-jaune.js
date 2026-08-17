const fs = require('fs');
const path = require('path');

const CSV_FILE = path.join(__dirname, '..', 'data', 'plf-jaune-2022.csv');
const OUTPUT_FILE = path.join(__dirname, '..', 'data', 'sources', 'plf-jaune.js');

const SOURCE_ID = 'plf-jaune';
const SOURCE_URL = 'https://data.economie.gouv.fr/explore/dataset/plf-jaune-associations-subventionnees/';

function parseCSVLine(line, delimiter) {
    delimiter = delimiter || ';';
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
            inQuotes = !inQuotes;
        } else if (char === delimiter && !inQuotes) {
            result.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }
    result.push(current.trim());
    return result;
}

function parseMontant(str) {
    if (!str) return 0;
    var cleaned = str.replace(/[^0-9,\-]/g, '').replace(',', '.');
    return parseFloat(cleaned) || 0;
}

function getDepartmentFromCode(cogCode) {
    if (!cogCode || cogCode.length < 2) return null;
    var code = cogCode.padStart(5, '0');
    if (code.startsWith('75')) return '75';
    if (code.startsWith('69')) return '69';
    if (code.startsWith('13')) return '13';
    if (code.startsWith('97')) return code.substring(0, 3);
    if (code.startsWith('98')) return code.substring(0, 3);
    return code.substring(0, 2);
}

function getProgramLabel(programCode) {
    var labels = {
        '101': 'Accès au droit et à la justice',
        '102': 'Accès et retour à l\'emploi',
        '103': 'Accompagnement des mutations économiques et développement de l\'emploi',
        '104': 'Intégration et accès à la nationalité française',
        '105': 'Action de la France en Europe et dans le monde',
        '107': 'Administration pénitentiaire',
        '109': 'Aide à l\'accès aux soins',
        '110': 'Aide à la vie associative',
        '111': 'Amélioration de la qualité de l\'emploi et des relations du travail',
        '112': 'Aménagement et service des transports terrestres',
        '113': 'Paysages, eau et biodiversité',
        '119': 'Coordination des moyens de secours et de sécurité',
        '122': 'Compétitivité et durabilité de l\'agriculture et de l\'agroalimentaire',
        '123': 'Conditions de vie outre-mer',
        '124': 'Conduite et soutien des politiques sanitaires et sociales',
        '129': 'Coordination du travail gouvernemental',
        '131': 'Création',
        '134': 'Développement des entreprises et régulations',
        '135': 'Développement des sports',
        '137': 'Égalité entre les femmes et les hommes',
        '138': 'Emploi outre-mer',
        '139': 'Enseignement privé du premier et du second degrés',
        '140': 'Enseignement scolaire public du premier degré',
        '141': 'Enseignement scolaire public du second degré',
        '142': 'Enseignement supérieur et recherche agricoles',
        '143': 'Enseignement technique agricole',
        '144': 'Environnement et prospective de la politique de défense',
        '146': 'Équipement des forces',
        '147': 'Politique de la ville',
        '148': 'Fonction de contrôle de l\'administration',
        '149': 'Forêt',
        '150': 'Formations supérieures et recherche universitaire',
        '151': 'Français à l\'étranger et affaires consulaires',
        '152': 'Gestion des finances publiques',
        '155': 'Conception et pilotage des politiques de l\'agriculture',
        '156': 'Gestion fiscale et financière de l\'État',
        '157': 'Handicap et dépendance',
        '159': 'Information géographique et cartographique',
        '161': 'Interventions économiques en faveur des entreprises',
        '162': 'Interventions territoriales de l\'État',
        '163': 'Jeunesse et vie associative',
        '164': 'Justice judiciaire',
        '165': 'Justice administrative',
        '166': 'Justice des mineurs',
        '167': 'Liens entre la Nation et son armée',
        '169': 'Mémoire',
        '172': 'Monnaie',
        '174': 'Métropole',
        '175': 'Patrimoines',
        '176': 'Police nationale',
        '177': 'Prévention de l\'exclusion et insertion des personnes vulnérables',
        '178': 'Préparation et emploi des forces',
        '180': 'Presse et médias',
        '181': 'Protection de l\'environnement',
        '182': 'Protection des droits et libertés',
        '185': 'Rayonnement culturel et scientifique',
        '186': 'Recherche en matière de développement durable',
        '190': 'Recherche dans les domaines de l\'énergie et du développement durable',
        '192': 'Recherche et enseignement supérieur en matière économique et industrielle',
        '198': 'Régimes sociaux et de retraite',
        '203': 'Infrastructures et services de transports',
        '204': 'Prévention des risques',
        '205': 'Sécurité et qualité sanitaires de l\'alimentation',
        '206': 'Sécurité et paix publiques',
        '207': 'Sécurité et éducation routières',
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
        '230': 'Vie politique et citoyenne',
        '231': 'Vie étudiante',
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
        '723': 'Soutien aux Outre-mer',
        '751': 'Politiques en faveur de l\'égalité des chances',
        '764': 'Transition écologique et cohésion territoriale',
        '775': 'Conduite et pilotage de la politique de défense',
        '776': 'Développement des territoires ultramarins',
        '901': 'Administration territoriale de l\'État',
        '902': 'Action extérieure de l\'État',
        '907': 'Administration et soutien des politiques économiques',
        '912': 'Soutien aux politiques de l\'environnement'
    };
    return labels[programCode] || ('Programme ' + programCode);
}

console.log('Conversion PLF Jaune 2022...');

var content = fs.readFileSync(CSV_FILE, 'latin1');
var lines = content.split('\n').filter(function(l) { return l.trim(); });

if (lines.length < 2) {
    console.log('Fichier vide ou invalide');
    process.exit(1);
}

var headers = parseCSVLine(lines[0]);
console.log('Colonnes:', JSON.stringify(headers));
console.log('Total lignes (hors en-tête):', lines.length - 1);

var subventions = [];

for (var i = 1; i < lines.length; i++) {
    var values = parseCSVLine(lines[i]);
    if (values.length < 6) continue;

    var programCode = values[0];
    var montant = parseMontant(values[4]);
    if (montant <= 0) continue;

    var rna = (values[10] && values[10].startsWith('W')) ? values[10] : '';
    var cogCode = values[12];
    var commune = values[13] || '';
    var department = getDepartmentFromCode(cogCode);
    var denomination = values[3] || 'Association inconnue';
    var objet = values[5] || 'Subvention de fonctionnement';

    var siret = '';
    if (values[1]) {
        siret = values[1];
        if (values[2]) siret += values[2];
    }

    subventions.push({
        id: 'plf-2022-' + String(subventions.length + 1).padStart(6, '0'),
        association: {
            name: denomination,
            rna: rna,
            siret: siret,
            address: commune,
            department: department || '75',
            object: objet
        },
        entity: {
            name: 'État — ' + getProgramLabel(programCode),
            type: 'state',
            level: 'ministère',
            program: getProgramLabel(programCode)
        },
        amount: montant,
        year: 2022,
        program: getProgramLabel(programCode),
        justification: objet,
        convention: values[6] ? true : false,
        source: SOURCE_URL
    });

    if (subventions.length % 10000 === 0) {
        console.log('... ' + subventions.length + ' lignes converties');
    }
}

console.log('Total: ' + subventions.length + ' subventions converties');

var totalAmount = subventions.reduce(function(sum, s) { return sum + s.amount; }, 0);
console.log('Montant total: ' + totalAmount.toLocaleString('fr-FR') + ' €');

var programs = {};
subventions.forEach(function(s) {
    var p = s.program;
    programs[p] = (programs[p] || 0) + 1;
});
var programCount = Object.keys(programs).length;
console.log('Nombre de programmes: ' + programCount);

var sourceContent = '(function() {\n';
sourceContent += '    var RAW_DATA = ' + JSON.stringify(subventions) + ';\n';
sourceContent += '    __registerDataSource(\'' + SOURCE_ID + '\', RAW_DATA);\n';
sourceContent += '    console.log(\'Source "' + SOURCE_ID + '" : \' + RAW_DATA.length + \' lignes enregistrées, ' + programCount + ' programmes, ' + totalAmount.toLocaleString('fr-FR') + ' €\');\n';
sourceContent += '})();\n';

fs.writeFileSync(OUTPUT_FILE, sourceContent, 'utf-8');
console.log('\nFichier généré: ' + OUTPUT_FILE);
