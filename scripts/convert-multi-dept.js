var fs = require('fs');
var path = require('path');

function convertFile(inputFile, sourceName, label, yearMapping, entityName, entityType, entityLevel) {
    var csv = fs.readFileSync(path.join(__dirname, '..', inputFile), 'utf8');
    var lines = csv.split('\n').filter(function(l) { return l.trim() !== ''; });
    var header = lines[0].split(';').map(function(h) { return h.replace(/^[\s\uFEFF\u00EF\u00BB\u00BF\?]+/, '').replace(/\r$/, '').trim(); });
    var out = [];
    for (var i = 1; i < lines.length; i++) {
        var vals = lines[i].split(';');
        var item = {};
        for (var j = 0; j < header.length; j++) {
            item[header[j]] = (vals[j] || '').trim();
        }
        var nom = (
            item['NOM_BENEFICIAIRE'] || item['nomBeneficiaire'] || 
            item['raison_sociale'] || item['Raison Sociale'] || ''
        ).replace(/^"|"$/g, '').trim();
        var siret = (
            item['ID_BENEFICIAIRE'] || item['IdBeneficiaire'] || 
            item['siret_ou_nir'] || item['SIRET ou NIR'] || ''
        ).replace(/^"|"$/g, '').trim();
        var montant = parseFloat(String(
            item['MONTANT'] || item['montant'] || item['mandate'] || item['Mandaté'] || '0'
        ).replace(',', '.')) || 0;
        var annee = parseInt(
            item['ANNEE_VERSEMENT'] || item['anneeVersement'] || 
            item['annee'] || item['Année'] || '0'
        ) || 0;
        var cp = (
            item['CODE_POSTAL_BENEFICIAIRE'] || item['CPBeneficiaire'] || 
            item['code_postal'] || item['Code postal'] || ''
        ).replace(/^"|"$/g, '').trim();
        var commune = (
            item['NOM_COM_BENEFICIAIRE'] || item['communeBeneficiaire'] || 
            item['commune'] || item['Commune'] || ''
        ).replace(/^"|"$/g, '').trim();
        var objet = (
            item['objet'] || item['Objet'] || ''
        ).replace(/^"|"$/g, '').trim();
        
        if (!nom || montant <= 0) continue;
        
        if (yearMapping && annee === 0) {
            annee = yearMapping;
        }
        
        var dept = cp.substring(0, 2) || '00';
        if (dept.match(/^9[78]/)) dept = cp.substring(0, 3);
        
        var entityNameVal = entityName || (item['SACollNom'] || '').replace(/^"|"$/g, '').trim() || "Collectivité";
        
        out.push({
            id: sourceName + '-' + String(i).padStart(6, '0'),
            association: {
                name: nom,
                siret: siret,
                address: commune || cp,
                department: dept,
                object: objet
            },
            entity: {
                name: entityNameVal,
                type: entityType || 'department',
                level: entityLevel || 'department'
            },
            amount: montant,
            year: annee,
            justification: objet,
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

// Ille-et-Vilaine 2021 (format NOM_BENEFICIAIRE;ID_BENEFICIAIRE;...)
convertFile('data\\tmp\\ille-vilaine-2021.csv', 'cd-ille-vilaine-2021', 'Ille-et-Vilaine — Subventions aux associations (2021)', null, "Département d'Ille-et-Vilaine");

// Ille-et-Vilaine 2022 v2 (format NOM_BENEFICIAIRE;ID_BENEFICIAIRE;...)
convertFile('data\\tmp\\ille-vilaine-2022v2.csv', 'cd-ille-vilaine-2022v2', 'Ille-et-Vilaine — Subventions aux associations (2022)', null, "Département d'Ille-et-Vilaine");

// Maine-et-Loire subventions (format annee;siret_ou_nir;raison_sociale;...)
convertFile('data\\tmp\\maine-loire-subventions.csv', 'cd-maine-loire-subventions', 'Maine-et-Loire — Subventions aux associations', null, "Département de Maine-et-Loire");
