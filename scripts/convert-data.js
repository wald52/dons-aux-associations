const fs = require('fs');
const path = require('path');

const dataDir = path.join(__dirname, '..', 'data');
const plfFile = path.join(dataDir, 'plf-jaune-2022.csv');
const parisFile = path.join(dataDir, 'paris-subventions.csv');

function parseCSVLine(line, delimiter = ';') {
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

function parseMontant(montantStr) {
    if (!montantStr) return 0;
    const cleaned = montantStr.replace(/[^0-9,]/g, '').replace(',', '.');
    return parseFloat(cleaned) || 0;
}

function getDepartmentFromCode(cogCode) {
    if (!cogCode || cogCode.length < 2) return null;
    const code = cogCode.padStart(5, '0');
    if (code.startsWith('75')) return '75';
    if (code.startsWith('69')) return '69';
    if (code.startsWith('13')) return '13';
    return code.substring(0, 2);
}

function convertPLFJaune() {
    console.log('Conversion PLF Jaune 2022...');
    const content = fs.readFileSync(plfFile, 'latin1');
    const lines = content.split('\n').filter(l => l.trim());
    
    if (lines.length < 2) {
        console.log('Fichier vide ou invalide');
        return [];
    }
    
    const headers = parseCSVLine(lines[0]);
    console.log('Colonnes PLF:', headers);
    
    const subventions = [];
    const maxRows = 1000;
    
    for (let i = 1; i < Math.min(lines.length, maxRows + 1); i++) {
        const values = parseCSVLine(lines[i]);
        if (values.length < 6) continue;
        
        const montant = parseMontant(values[4]);
        if (montant < 1000) continue;
        
        const rna = values[10] && values[10].startsWith('W') ? values[10] : '';
        const cogCode = values[12];
        const commune = values[13] || '';
        const department = getDepartmentFromCode(cogCode);
        
        subventions.push({
            id: `plf-${String(i).padStart(6, '0')}`,
            association: {
                name: values[3] || 'Association inconnue',
                rna: rna,
                siret: values[1] ? values[1] + (values[2] || '') : '',
                address: commune,
                department: department || '75',
                object: values[5] || 'Subvention de fonctionnement'
            },
            entity: {
                name: 'État - Ministère (PLF 2022)',
                type: 'state',
                level: 'ministère',
                program: `Programme ${values[0]}`
            },
            amount: montant,
            year: 2020,
            program: `Programme ${values[0]}`,
            justification: values[5] || 'Subvention de l\'État',
            convention: values[6] ? true : false,
            source: 'https://www.data.gouv.fr/datasets/projet-de-loi-de-finances-pour-2022-plf-2022-donnees-de-lannexe-jaune-effort-financier-de-letat-en-faveur-des-associations/'
        });
    }
    
    console.log(`PLF Jaune: ${subventions.length} subventions converties`);
    return subventions;
}

function convertParisData() {
    console.log('Conversion Paris Data...');
    const content = fs.readFileSync(parisFile, 'utf-8');
    const lines = content.split('\n').filter(l => l.trim());
    
    if (lines.length < 2) {
        console.log('Fichier vide ou invalide');
        return [];
    }
    
    const headers = parseCSVLine(lines[0]);
    console.log('Colonnes Paris:', headers);
    
    const subventions = [];
    const maxRows = 1000;
    
    for (let i = 1; i < Math.min(lines.length, maxRows + 1); i++) {
        const values = parseCSVLine(lines[i]);
        if (values.length < 7) continue;
        
        const montant = parseFloat(values[6]) || 0;
        if (montant < 500) continue;
        
        const annee = parseInt(values[1]) || 2024;
        const collectivite = values[2] === 'v' ? 'Ville de Paris' : 'Département de Paris';
        
        subventions.push({
            id: `paris-${String(i).padStart(6, '0')}`,
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
                type: 'commune',
                level: 'commune',
                direction: values[7] || ''
            },
            amount: montant,
            year: annee,
            program: values[7] ? `Direction ${values[7]}` : 'Subvention municipale',
            justification: values[5] || 'Subvention de la Ville de Paris',
            convention: montant > 23000,
            nature: values[8] || '',
            source: 'https://opendata.paris.fr/explore/dataset/subventions-associations-votees-/'
        });
    }
    
    console.log(`Paris Data: ${subventions.length} subventions converties`);
    return subventions;
}

const plfSubventions = convertPLFJaune();
const parisSubventions = convertParisData();

const allSubventions = [...plfSubventions, ...parisSubventions];

const outputContent = `const SUBVENTIONS_DATA = ${JSON.stringify(allSubventions, null, 2)};

__registerDataSource('plf-jaune', SUBVENTIONS_DATA);
`;

// Pour générer un fichier source autonome (au lieu d'écraser sample-data.js) :
//   node scripts/convert-data.js --source <nom-source>
// Cela crée data/sources/<nom-source>.js avec le nouveau format.
if (process.argv.includes('--source')) {
    const srcIdx = process.argv.indexOf('--source') + 1;
    const sourceName = srcIdx < process.argv.length ? process.argv[srcIdx] : 'nouvelle-source';
    const sourceContent = `(function() {
    var RAW_DATA = ${JSON.stringify(allSubventions, null, 2)};

    __registerDataSource('${sourceName}', RAW_DATA);
    console.log('Source "${sourceName}" : ' + RAW_DATA.length + ' lignes enregistr\u00e9es');
})();
`;
    const sourceFile = path.join(dataDir, 'sources', sourceName + '.js');
    fs.writeFileSync(sourceFile, sourceContent, 'utf-8');
    console.log(`\nSource autonome générée: ${sourceFile}`);
} else {
    fs.writeFileSync(path.join(dataDir, 'sample-data.js'), outputContent, 'utf-8');
    console.log(`\nTotal: ${allSubventions.length} subventions`);
    console.log(`Montant total: ${allSubventions.reduce((sum, s) => sum + s.amount, 0).toLocaleString('fr-FR')} €`);
    console.log(`Fichier généré: data/sample-data.js`);
}
