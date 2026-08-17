var fs = require('fs');
var path = require('path');

var csv = fs.readFileSync(path.join(__dirname, '..', 'data', 'tmp', 'ille-vilaine-2022.csv'), 'utf8');
var lines = csv.split('\n').filter(function(l) { return l.trim() !== ''; });
var header = lines[0].split(';').map(function(h) { return h.trim(); });
var out = [];
for (var i = 1; i < lines.length; i++) {
    var vals = lines[i].split(';');
    var item = {};
    for (var j = 0; j < header.length; j++) {
        item[header[j]] = (vals[j] || '').trim();
    }
    var nom = item['nomBeneficiaire'];
    var siret = item['IdBeneficiaire'];
    var montant = parseFloat(String(item['montant']).replace(',', '.')) || 0;
    var annee = parseInt(item['anneeVersement']) || 0;
    if (!nom || montant <= 0) continue;
    out.push({
        id: 'ille-vilaine-' + String(i).padStart(6, '0'),
        association: {
            name: nom.trim(),
            siret: siret,
            address: item['communeBeneficiaire'] || '',
            department: (item['CPBeneficiaire'] || '').substring(0, 2) || '35',
            object: ''
        },
        entity: {
            name: "Departement d'Ille-et-Vilaine",
            type: 'department',
            level: 'department'
        },
        amount: montant,
        year: annee,
        justification: '',
        convention: montant >= 23000,
        source: 'https://static.data.gouv.fr/resources/subventions-versees-aux-associations-par-le-departement-dille-et-vilaine/20230921-084751/fichieropendatasubasso.csv'
    });
}
var src = 'window.__DATA_SOURCES = window.__DATA_SOURCES || [];\n';
src += 'window.__DATA_SOURCES.push({\n';
src += '    id: "cd-ille-vilaine",\n';
src += '    label: "Ille-et-Vilaine — Subventions aux associations (2022)",\n';
src += '    data: ' + JSON.stringify(out) + '\n';
src += '});\n';
var outPath = path.join(__dirname, '..', 'data', 'sources', 'cd-ille-vilaine.js');
fs.writeFileSync(outPath, src, 'utf8');
console.log('Genere: ' + outPath + ' (' + out.length + ' lignes)');
