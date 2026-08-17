const fs = require('fs');
const path = require('path');

const CSV_FILE = path.join(__dirname, '..', 'data', 'paris-subventions.csv');
const OUTPUT_FILE = path.join(__dirname, '..', 'data', 'sources', 'paris.js');

const SOURCE_ID = 'paris';
const SOURCE_URL = 'https://opendata.paris.fr/explore/dataset/subventions-associations-votees-';

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

console.log('Conversion subventions Paris...');

var content = fs.readFileSync(CSV_FILE, 'utf-8');
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
    if (values.length < 7) continue;

    var montant = parseFloat(values[6]) || 0;
    if (montant <= 0) continue;

    var annee = parseInt(values[1]) || 2024;
    var collectivite = values[2] === 'v' ? 'Ville de Paris' : 'Département de Paris';
    var entityType = values[2] === 'v' ? 'commune' : 'department';
    var entityLevel = values[2] === 'v' ? 'commune' : 'department';

    subventions.push({
        id: 'paris-' + String(subventions.length + 1).padStart(6, '0'),
        association: {
            name: values[3] || 'Association inconnue',
            rna: '',
            siret: values[4] || '',
            address: 'Paris',
            department: '75',
            object: values[5] || 'Subvention de fonctionnement'
        },
        entity: {
            name: collectivite,
            type: entityType,
            level: entityLevel,
            direction: values[7] || ''
        },
        amount: montant,
        year: annee,
        program: values[7] ? 'Direction ' + values[7] : 'Subvention municipale',
        justification: values[5] || 'Subvention de la Ville de Paris',
        convention: montant > 23000,
        nature: values[8] || '',
        source: SOURCE_URL
    });

    if (subventions.length % 10000 === 0) {
        console.log('... ' + subventions.length + ' lignes converties');
    }
}

console.log('Total: ' + subventions.length + ' subventions converties');

var totalAmount = subventions.reduce(function(sum, s) { return sum + s.amount; }, 0);
console.log('Montant total: ' + totalAmount.toLocaleString('fr-FR') + ' €');

var years = {};
subventions.forEach(function(s) { years[s.year] = (years[s.year] || 0) + 1; });
console.log('Années couvertes:', Object.keys(years).sort().join(', '));

var sourceContent = '(function() {\n';
sourceContent += '    var RAW_DATA = ' + JSON.stringify(subventions) + ';\n';
sourceContent += '    __registerDataSource(\'' + SOURCE_ID + '\', RAW_DATA);\n';
sourceContent += '    console.log(\'Source "' + SOURCE_ID + '" : \' + RAW_DATA.length + \' lignes enregistrées, ' + totalAmount.toLocaleString('fr-FR') + ' €\');\n';
sourceContent += '})();\n';

fs.writeFileSync(OUTPUT_FILE, sourceContent, 'utf-8');
console.log('\nFichier généré: ' + OUTPUT_FILE);
