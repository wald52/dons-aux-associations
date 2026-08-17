var fs = require('fs');
var path = require('path');

function parseCSVLine(line, delimiter) {
    var result = [], current = '', inQuotes = false;
    for (var i = 0; i < line.length; i++) {
        var c = line[i];
        if (c === '"') { inQuotes = !inQuotes; }
        else if (c === delimiter && !inQuotes) { result.push(current.trim()); current = ''; }
        else { current += c; }
    }
    result.push(current.trim());
    return result;
}

function convertFile(inputFile, sourceName, label, entityName, colMap) {
    var csv = fs.readFileSync(path.join(__dirname, '..', inputFile), 'utf8');
    var lines = csv.split('\n').filter(function(l) { return l.trim(); });
    if (lines.length < 2) { console.log('Empty: ' + inputFile); return []; }

    // Auto-detect delimiter: if first line has "," sequences, use comma
    var firstLine = lines[0];
    var delimiter = ';';
    if (firstLine.indexOf('","') >= 0) delimiter = ',';

    var header = parseCSVLine(lines[0], delimiter);
    // Clean BOM from first column
    header[0] = header[0].replace(/^[\s\uFEFF\u00EF\u00BB\u00BF\?]+/, '');

    var out = [];
    for (var i = 1; i < lines.length; i++) {
        var vals = parseCSVLine(lines[i], delimiter);
        if (vals.length < 3 || vals.length !== header.length) continue;

        var item = {};
        for (var j = 0; j < header.length; j++) {
            item[header[j]] = vals[j] || '';
        }

        var nom = '';
        var siret = '';
        var montant = 0;
        var annee = 0;
        var cp = '';
        var commune = '';
        var objet = '';

        if (colMap) {
            nom = (item[colMap.nom] || '').replace(/^"|"$/g, '').trim();
            siret = (item[colMap.siret] || '').replace(/^"|"$/g, '').trim();
            montant = parseFloat(String(item[colMap.montant] || '0').replace(/[^0-9,\-]/g, '').replace(',', '.')) || 0;
            var yearVal = item[colMap.annee] || '';
            if (yearVal.match(/^\d{4}$/)) {
                annee = parseInt(yearVal);
            } else {
                annee = parseInt(yearVal.split('/')[2]) || parseInt(yearVal.split('-')[0]) || 0;
            }
            objet = (item[colMap.objet] || '').replace(/^"|"$/g, '').trim();
            cp = (item[colMap.cp] || '').replace(/^"|"$/g, '').trim();
            commune = (item[colMap.commune] || '').replace(/^"|"$/g, '').trim();
        } else {
            // SCDL auto-detect
            var nomAttempts = ['nomBeneficiaire', 'nom_beneficiaire', 'nombeneficiaire', 'nomBenecifiaire', 'nom_du_beneficiaire'];
            for (var k = 0; k < nomAttempts.length; k++) { nom = item[nomAttempts[k]] || ''; if (nom) break; }
            nom = nom.replace(/^"|"$/g, '').trim();

            var montFields = ['montant', 'montant_total', 'montant_vote', 'amount', 'montant_aide'];
            for (var k = 0; k < montFields.length; k++) { var v = item[montFields[k]]; if (v) { montant = parseFloat(String(v).replace(/[^0-9,\-]/g, '').replace(',', '.')) || 0; break; } }

            var yearFields = ['annee', 'annee_budgetaire', 'exercice', 'dateconvention', 'dateDecision', 'anneeDecision'];
            for (var k = 0; k < yearFields.length; k++) { var v = item[yearFields[k]]; if (v) { var y = parseInt(v.replace(/^"|"$/g, '').split('-')[0] || v); annee = (y > 1000 && y < 2100) ? y : 0; if (annee) break; } }

            var siretFields = ['idBeneficiaire', 'id_beneficiaire', 'idbeneficiaire', 'siret_attributaire', 'siret'];
            for (var k = 0; k < siretFields.length; k++) { siret = item[siretFields[k]] || ''; if (siret) break; }
            siret = siret.replace(/^"|"$/g, '').trim();

            objet = (item['objet'] || '').replace(/^"|"$/g, '').trim();
            cp = (item['code_postal'] || '').replace(/^"|"$/g, '').trim();
            commune = (item['commune'] || '').replace(/^"|"$/g, '').trim();
        }

        if (!nom || montant <= 0) continue;
        var dept = cp.substring(0, 2) || '00';

        out.push({
            id: sourceName + '-' + String(i).padStart(6, '0'),
            association: { name: nom, siret: siret, address: commune || cp, department: dept, object: objet },
            entity: { name: entityName, type: 'department', level: 'department' },
            amount: montant, year: annee, justification: objet, convention: montant >= 23000, source: ''
        });
    }
    return out;
}

function writeSource(sourceName, label, data) {
    var src = 'window.__DATA_SOURCES = window.__DATA_SOURCES || [];\n';
    src += 'window.__DATA_SOURCES.push({\n';
    src += '    id: "' + sourceName + '",\n';
    src += '    label: "' + label + '",\n';
    src += '    data: ' + JSON.stringify(data) + '\n';
    src += '});\n';
    var outPath = path.join(__dirname, '..', 'data', 'sources', sourceName + '.js');
    fs.writeFileSync(outPath, src, 'utf8');
    console.log('Genere: ' + outPath + ' (' + data.length + ' lignes)');
}

// --- Dordogne (24): 3 years, near-SCDL with nomBenecifiaire ---
var dordogneData = [];
['2017', '2018', '2019'].forEach(function(y) {
    var data = convertFile('data\\tmp\\dordogne-' + y + '.csv', 'cd-dordogne-' + y, '', "Département de la Dordogne", null);
    dordogneData = dordogneData.concat(data);
    console.log('Dordogne ' + y + ': ' + data.length + ' lignes');
});
writeSource('cd-dordogne', 'Dordogne — Subventions aux associations (2017-2019)', dordogneData);

// --- Loire (42): 2018 data ---
var loireData = convertFile('data\\tmp\\loire-2018.csv', 'cd-loire', '', "Département de la Loire", null);
writeSource('cd-loire', 'Loire — Conventions de subventions (2018)', loireData);

// Helper: find amount column by partial key match
function findMontantCol(item) {
    for (var k in item) { if (k.indexOf('Montant') >= 0 || k.indexOf('montant') >= 0 || k.indexOf('MONTANT') >= 0) return k; }
    return null;
}

// --- Savoie (73): additional years ---
// Savoie 2018 and 2020 use format: COLL_NOM;COLL_SIRET;...;ATTRIB_NOM;...;Montant décidé mouvement
var savoieData2018 = convertFile('data\\tmp\\savoie-2018.csv', 'cd-savoie-2018', '', "Département de la Savoie", null);
// The SCDL auto-detect won't work here. Override montant lookup
savoieData2018 = [];
var csv2018 = fs.readFileSync(path.join(__dirname, '..', 'data', 'tmp', 'savoie-2018.csv'), 'utf8');
var lines2018 = csv2018.split('\n').filter(function(l) { return l.trim(); });
var h2018 = parseCSVLine(lines2018[0], ';');
h2018[0] = h2018[0].replace(/^[\s\uFEFF]+/, '');
var montantCol2018 = '';
for (var j = 0; j < h2018.length; j++) { if (h2018[j].indexOf('Montant') >= 0) { montantCol2018 = h2018[j]; break; } }
for (var i = 1; i < lines2018.length; i++) {
    var vals = parseCSVLine(lines2018[i], ';');
    if (vals.length < 2 || vals.length !== h2018.length) continue;
    var item = {};
    for (var j = 0; j < h2018.length; j++) { item[h2018[j]] = vals[j] || ''; }
    var nom = (item['ATTRIB_NOM'] || '').replace(/^"|"$/g, '').trim();
    var montant = parseFloat(String(item[montantCol2018] || '0').replace(/[^0-9,\-]/g, '').replace(',', '.')) || 0;
    var dateStr = item['CONV_DAT'] || '';
    var annee = parseInt(dateStr.split('/')[2]) || 0;
    var objet = (item['SUB_OBJET'] || '').replace(/^"|"$/g, '').trim();
    if (!nom || montant <= 0) continue;
    savoieData2018.push({
        id: 'cd-savoie-2018-' + String(i).padStart(6, '0'),
        association: { name: nom, siret: (item['ATTRIB_SIRET'] || '').replace(/^"|"$/g, '').trim(), department: '73', object: objet },
        entity: { name: "Département de la Savoie", type: 'department', level: 'department' },
        amount: montant, year: annee, justification: objet, convention: montant >= 23000, source: ''
    });
}
console.log('Savoie 2018: ' + savoieData2018.length + ' lignes');

var savoieData2020 = [];
var csv2020 = fs.readFileSync(path.join(__dirname, '..', 'data', 'tmp', 'savoie-2020.csv'), 'utf8');
var lines2020 = csv2020.split('\n').filter(function(l) { return l.trim(); });
var h2020 = parseCSVLine(lines2020[0], ';');
h2020[0] = h2020[0].replace(/^[\s\uFEFF]+/, '');
var montantCol2020 = '';
for (var j = 0; j < h2020.length; j++) { if (h2020[j].indexOf('Montant') >= 0) { montantCol2020 = h2020[j]; break; } }
for (var i = 1; i < lines2020.length; i++) {
    var vals = parseCSVLine(lines2020[i], ';');
    if (vals.length < 2 || vals.length !== h2020.length) continue;
    var item = {};
    for (var j = 0; j < h2020.length; j++) { item[h2020[j]] = vals[j] || ''; }
    var nom = (item['ATTRIB_NOM'] || '').replace(/^"|"$/g, '').trim();
    var montant = parseFloat(String(item[montantCol2020] || '0').replace(/[^0-9,\-]/g, '').replace(',', '.')) || 0;
    var dateStr = item['CONV_DAT'] || '';
    var annee = parseInt(dateStr.split('/')[2]) || 0;
    var objet = (item['SUB_OBJET'] || '').replace(/^"|"$/g, '').trim();
    if (!nom || montant <= 0) continue;
    savoieData2020.push({
        id: 'cd-savoie-2020-' + String(i).padStart(6, '0'),
        association: { name: nom, siret: (item['ATTRIB_SIRET'] || '').replace(/^"|"$/g, '').trim(), department: '73', object: objet },
        entity: { name: "Département de la Savoie", type: 'department', level: 'department' },
        amount: montant, year: annee, justification: objet, convention: montant >= 23000, source: ''
    });
}
console.log('Savoie 2020: ' + savoieData2020.length + ' lignes');
console.log('Savoie 2020: ' + savoieData2020.length + ' lignes');

// Savoie 2022 and 2023 use new format with exercice
var savoieData2022 = convertFile('data\\tmp\\savoie-2022.csv', 'cd-savoie-2022', '', "Département de la Savoie", {
    nom: 'nomBeneficiaire', siret: 'idBeneficiaire', montant: 'montant', annee: 'exercice',
    objet: 'objet', cp: '', commune: ''
});
console.log('Savoie 2022: ' + savoieData2022.length + ' lignes');

var savoieData2023 = convertFile('data\\tmp\\savoie-2023.csv', 'cd-savoie-2023', '', "Département de la Savoie", {
    nom: 'nomBeneficiaire', siret: 'idBeneficiaire', montant: 'montant', annee: 'exercice',
    objet: 'objet', cp: '', commune: ''
});
console.log('Savoie 2023: ' + savoieData2023.length + ' lignes');

// Save individual Savoie years
writeSource('cd-savoie-2018', 'Savoie — Subventions aux associations (2018)', savoieData2018);
writeSource('cd-savoie-2020', 'Savoie — Subventions aux associations (2020)', savoieData2020);
writeSource('cd-savoie-2022', 'Savoie — Subventions aux associations (2022)', savoieData2022);
writeSource('cd-savoie-2023', 'Savoie — Subventions aux associations (2023)', savoieData2023);
