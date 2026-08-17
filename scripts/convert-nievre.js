var fs = require('fs');
var path = require('path');

var years = ['2024', '2023', '2022', '2021', '2020', '2019', '2018'];
var all = [];

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

years.forEach(function(y) {
    var csv = fs.readFileSync(path.join(__dirname, '..', 'data', 'tmp', 'nievre-' + y + '.csv'), 'utf8');
    var lines = csv.split('\n').filter(function(l) { return l.trim(); });
    if (lines.length < 2) { console.log('Skipping Nievre ' + y + ': empty'); return; }
    var header = parseCSVLine(lines[0], ';');
    var count = 0;
    for (var i = 1; i < lines.length; i++) {
        var vals = parseCSVLine(lines[i], ';');
        if (vals.length < 2) continue;
        if (vals.length !== header.length) continue;
        var item = {};
        for (var j = 0; j < header.length; j++) {
            item[header[j]] = vals[j] || '';
        }
        item._sourceId = 'cd-nievre';
        item._entityType = 'department';
        item._entityLevel = 'department';
        item._entityName = "Département de la Nièvre";
        count++;
        item._id = 'cd-nievre-' + String(all.length + 1).padStart(6, '0');
        all.push(item);
    }
    console.log('Nievre ' + y + ': ' + count + ' lignes');
});

console.log('Total: ' + all.length + ' lignes');

var src = '(function() {\n';
src += '    var RAW_DATA = ' + JSON.stringify(all) + ';\n';
src += "    __registerDataSource('cd-nievre', RAW_DATA);\n";
src += "    console.log('Source \"cd-nievre\" : ' + RAW_DATA.length + ' lignes enregistrées');\n";
src += '})();\n';

var outPath = path.join(__dirname, '..', 'data', 'sources', 'cd-nievre.js');
fs.writeFileSync(outPath, src, 'utf8');
console.log('Genere: ' + outPath);
