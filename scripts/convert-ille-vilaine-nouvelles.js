var fs = require('fs');
var path = require('path');

function convertFile(inputFile, sourceName, label) {
    var csv = fs.readFileSync(path.join(__dirname, '..', inputFile), 'utf8');
    var lines = csv.split('\n').filter(function(l) { return l.trim() !== ''; });
    var header = lines[0].split(';').map(function(h) { return h.trim().replace(/^\?+/, '').replace(/\r$/, ''); });
    var out = [];
    for (var i = 1; i < lines.length; i++) {
        var vals = lines[i].split(';');
        var item = {};
        for (var j = 0; j < header.length; j++) {
            item[header[j]] = (vals[j] || '').trim();
        }
        var nom = item['NOM_BENEFICIAIRE'] || item['nomBeneficiaire'] || '';
        var siret = item['ID_BENEFICIAIRE'] || item['IdBeneficiaire'] || '';
        var montant = parseFloat(String(item['MONTANT'] || item['montant'] || '0').replace(',', '.')) || 0;
        var annee = parseInt(item['ANNEE_VERSEMENT'] || item['anneeVersement']) || 0;
        var cp = item['CODE_POSTAL_BENEFICIAIRE'] || item['CPBeneficiaire'] || '';
        var commune = item['NOM_COM_BENEFICIAIRE'] || item['communeBeneficiaire'] || '';
        if (!nom || montant <= 0) continue;
        out.push({
            id: sourceName + '-' + String(i).padStart(6, '0'),
            association: {
                name: nom.trim(),
                siret: siret,
                address: commune,
                department: cp.substring(0, 2) || '35',
                object: ''
            },
            entity: {
                name: (item['SACollNom'] || "Departement d'Ille-et-Vilaine").trim(),
                type: 'department',
                level: 'department'
            },
            amount: montant,
            year: annee,
            justification: '',
            convention: montant >= 23000,
            source: ''
        });
    }
    var src = 'window.__DATA_SOURCES = window.__DATA_SOURCES || [];\n';
    src += 'window.__DATA_SOURCES.push({\n';
    src += '    id: "' + sourceName + '",\n';
    src += '    label: "' + label + '",\n';
    src += '    data: ' + JSON.stringify(out) + '\n';
    src += '});\n';
    var outPath = path.join(__dirname, '..', 'data', 'sources', sourceName + '.js');
    fs.writeFileSync(outPath, src, 'utf8');
    console.log('Genere: ' + outPath + ' (' + out.length + ' lignes)');
    return out;
}

// Convert 2021 file
convertFile('data\\tmp\\ille-vilaine-2021.csv', 'cd-ille-vilaine-2021', 'Ille-et-Vilaine — Subventions aux associations (2021)');

// Convert 2022 file
convertFile('data\\tmp\\ille-vilaine-2022v2.csv', 'cd-ille-vilaine-2022', 'Ille-et-Vilaine — Subventions aux associations (2022)');
