var XLSX = require('xlsx');
var fs = require('fs');
var path = require('path');

var wb = XLSX.readFile(path.join(__dirname, '..', 'data', 'tmp', 'bas-rhin.xlsx'));
var ws = wb.Sheets['Rapport 1'];
var data = XLSX.utils.sheet_to_json(ws, { header: 1 });

// Find header row (row 3)
var header = data[3];
var colMap = {};
for (var i = 0; i < header.length; i++) {
    var h = (header[i] || '').toString().trim();
    if (h.indexOf('Attributaire') >= 0 && h.indexOf('Nom') < 0) colMap.nom = i;
    else if (h.indexOf('SIRET') >= 0 && h.indexOf('organisme') < 0 && h.indexOf('attributaire') < 0) colMap.siret = i;
    else if (h.indexOf('SIRET') >= 0 && h.indexOf('attributaire') >= 0) colMap.siretAttrib = i;
    else if (h.indexOf('Montant') >= 0) colMap.montant = i;
    else if (h.indexOf('Objet') >= 0) colMap.objet = i;
    else if (h.indexOf('organisme') >= 0) colMap.entity = i;
    else if (h.indexOf('Date') >= 0) colMap.date = i;
}

function excelDateToYear(serial) {
    if (typeof serial === 'number' && serial > 40000) {
        var d = new Date((serial - 25569) * 86400 * 1000);
        return d.getFullYear();
    }
    return 0;
}

var out = [];
for (var i = 4; i < data.length; i++) {
    var row = data[i];
    if (!row || row.length < 5) continue;
    var nom = (row[colMap.nom] || '').toString().trim();
    var siret = (row[colMap.siret] || row[colMap.siretAttrib] || '').toString().trim();
    var montant = parseFloat(String(row[colMap.montant] || '0').replace(/,/g, '.')) || 0;
    var objet = (row[colMap.objet] || '').toString().trim();
    var annee = 0;
    if (colMap.date !== undefined) {
        annee = excelDateToYear(row[colMap.date]);
    }
    if (!annee) {
        var match = objet.match(/exercice\s*(\d{4})/);
        if (match) annee = parseInt(match[1]);
    }
    var entityName = (row[colMap.entity] || 'Département du Bas-Rhin').toString().trim();
    if (!nom || montant <= 0) continue;
    out.push({
        id: 'cd-bas-rhin-' + String(i).padStart(6, '0'),
        association: { name: nom, siret: siret, department: '67', object: objet },
        entity: { name: "Département du Bas-Rhin", type: 'department', level: 'department' },
        amount: montant, year: annee || 0, justification: objet, convention: montant >= 23000, source: ''
    });
}

var src = 'window.__DATA_SOURCES = window.__DATA_SOURCES || [];\n';
src += 'window.__DATA_SOURCES.push({\n';
src += '    id: "cd-bas-rhin",\n';
src += '    label: "Bas-Rhin — Subventions aux associations (2017-2018)",\n';
src += '    data: ' + JSON.stringify(out) + '\n';
src += '});\n';

var outPath = path.join(__dirname, '..', 'data', 'sources', 'cd-bas-rhin.js');
fs.writeFileSync(outPath, src, 'utf8');
console.log('Genere: ' + outPath + ' (' + out.length + ' lignes)');
