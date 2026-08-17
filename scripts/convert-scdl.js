// ============================================================
//  convert-scdl.js — Télécharge un CSV SCDL depuis data.gouv.fr
//  et génère un fichier JS source.
//
//  Usage :
//    node scripts/convert-scdl.js <nom-source> <url-csv> [options]
//
//  Exemple :
//    node scripts/convert-scdl.js ville-bordeaux https://www.data.gouv.fr/api/1/datasets/r/xxxxx/csv
//
//  Options :
//    --id-field <champ>     Nom du champ à utiliser comme ID (défaut: auto)
//    --entity-type <type>   Forcer le type d'entité (state|region|department|commune|epci)
//    --entity-level <level> Forcer le niveau (ministère|region|department|commune|epci)
//    --entity-name <nom>    Forcer le nom du donateur
//    --year <année>         Forcer l'année si absente des données
//    --delimiter <char>     Délimiteur CSV (défaut: ,)
//    --encoding <enc>       Encodage (défaut: utf8)
// ============================================================

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

var args = process.argv.slice(2);
if (args.length < 2) {
    console.log('Usage: node scripts/convert-scdl.js <nom-source> <url-csv> [options]');
    console.log('Exemple:');
    console.log('  node scripts/convert-scdl.js ville-bordeaux https://www.data.gouv.fr/api/1/datasets/r/xxxxx/csv');
    process.exit(1);
}

var sourceName = args[0];
var csvUrl = args[1];
var forceEntityType = null;
var forceEntityLevel = null;
var forceEntityName = null;
var forceYear = null;
var idField = null;
var delimiter = ',';
var encoding = 'utf8';

for (var i = 2; i < args.length; i++) {
    switch (args[i]) {
        case '--entity-type': forceEntityType = args[++i]; break;
        case '--entity-level': forceEntityLevel = args[++i]; break;
        case '--entity-name': forceEntityName = args[++i]; break;
        case '--year': forceYear = parseInt(args[++i]); break;
        case '--id-field': idField = args[++i]; break;
        case '--delimiter': delimiter = args[++i]; break;
        case '--encoding': encoding = args[++i]; break;
    }
}

function parseCSVLine(line) {
    var result = [];
    var current = '';
    var inQuotes = false;

    for (var i = 0; i < line.length; i++) {
        var char = line[i];
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

function download(url) {
    return new Promise(function(resolve, reject) {
        var client = url.startsWith('https') ? https : http;
        console.log('Téléchargement:', url);
        client.get(url, function(res) {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                console.log('Redirection vers:', res.headers.location);
                client.get(res.headers.location, function(res2) {
                    var data = [];
                    res2.on('data', function(chunk) { data.push(chunk); });
                    res2.on('end', function() { resolve(Buffer.concat(data).toString(encoding)); });
                });
                return;
            }
            var data = [];
            res.on('data', function(chunk) { data.push(chunk); });
            res.on('end', function() { resolve(Buffer.concat(data).toString(encoding)); });
        }).on('error', reject);
    });
}

download(csvUrl).then(function(content) {
    console.log('Téléchargé: ' + (content.length / 1024).toFixed(0) + ' Ko');

    var lines = content.split('\n').filter(function(l) { return l.trim(); });
    if (lines.length < 2) {
        console.log('Fichier vide ou invalide');
        process.exit(1);
    }

    var headers = parseCSVLine(lines[0]);
    console.log('Colonnes:', JSON.stringify(headers));

    var records = [];
    var idCounter = 0;

    for (var i = 1; i < lines.length; i++) {
        var values = parseCSVLine(lines[i]);
        if (values.length < 2) continue;
        if (values.length !== headers.length) continue;

        var item = {};
        for (var j = 0; j < headers.length; j++) {
            item[headers[j]] = values[j] || '';
        }

        item._sourceId = sourceName;
        if (forceEntityType) item._entityType = forceEntityType;
        if (forceEntityLevel) item._entityLevel = forceEntityLevel;
        if (forceEntityName) item._entityName = forceEntityName;
        if (forceYear) item._year = forceYear;

        if (idField && item[idField]) {
            item._id = sourceName + '-' + item[idField];
        } else {
            idCounter++;
            item._id = sourceName + '-' + String(idCounter).padStart(6, '0');
        }

        records.push(item);
    }

    console.log('Lignes valides:', records.length);

    var outputContent = '(function() {\n';
    outputContent += '    var RAW_DATA = ' + JSON.stringify(records) + ';\n';
    outputContent += '    __registerDataSource(\'' + sourceName + '\', RAW_DATA);\n';
    outputContent += '    console.log(\'Source "' + sourceName + '" : \' + RAW_DATA.length + \' lignes enregistrées\');\n';
    outputContent += '})();\n';

    var outputFile = path.join(__dirname, '..', 'data', 'sources', sourceName + '.js');
    fs.writeFileSync(outputFile, outputContent, 'utf-8');
    console.log('\nFichier généré: ' + outputFile);
    console.log('Pour charger cette source, ajoutez dans index.html :');
    console.log('  <script src="data/sources/' + sourceName + '.js"></script>');
    console.log('Le normalizer SCDL (source ID: "' + sourceName + '") sera appliqué automatiquement.');
}).catch(function(err) {
    console.error('Erreur:', err.message);
    process.exit(1);
});
