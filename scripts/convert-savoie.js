var fs = require('fs');
var path = require('path');

var csv = fs.readFileSync(path.join(__dirname, '..', 'data', 'tmp', 'savoie-2017.csv'), 'utf8');
var lines = csv.split('\n').filter(function(l) { return l.trim() !== ''; });
var header = lines[0].split(';').map(function(h) { return h.trim().replace(/\r$/, ''); });
var out = [];
for (var i = 1; i < lines.length; i++) {
    var vals = lines[i].split(';');
    var item = {};
    for (var j = 0; j < header.length; j++) {
        item[header[j]] = (vals[j] || '').trim();
    }
    var nom = item['ATTRIB_NOM'];
    var siret = item['ATTRIB_SIRET'];
    var montant = 0;
    for (var k in item) { if (k.indexOf('Montant') >= 0) { montant = parseFloat(String(item[k]).replace(',', '.')) || 0; break; } }
    var dateStr = item['CONV_DAT'] || '';
    var annee = parseInt(dateStr.split('/')[2]) || 0;
    var objet = item['SUB_OBJET'] || '';
    if (!nom || montant <= 0) continue;
    out.push({
        id: 'savoie-' + String(i).padStart(6, '0'),
        association: {
            name: nom.trim(),
            siret: siret || '',
            department: '73',
            object: objet
        },
        entity: {
            name: (item['COLL_NOM'] || 'Departement de la Savoie').trim(),
            type: 'department',
            level: 'department'
        },
        amount: montant,
        year: annee,
        justification: objet,
        convention: montant >= 23000,
        source: 'https://static.data.gouv.fr/resources/liste-des-subventions-allouees-par-le-departement-en-2017-1/20180517-105132/OPEN_DATA_Liste_des_subventions_allouees_par_le_Departement_2017.csv'
    });
}
var src = 'window.__DATA_SOURCES = window.__DATA_SOURCES || [];\n';
src += 'window.__DATA_SOURCES.push({\n';
src += '    id: "cd-savoie",\n';
src += '    label: "Savoie — Subventions aux associations (2017)",\n';
src += '    data: ' + JSON.stringify(out) + '\n';
src += '});\n';
var outPath = path.join(__dirname, '..', 'data', 'sources', 'cd-savoie.js');
fs.writeFileSync(outPath, src, 'utf8');
console.log('Genere: ' + outPath + ' (' + out.length + ' lignes)');
