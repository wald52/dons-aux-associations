const XLSX = require('xlsx');
const fs = require('fs');
const path = require('path');
const https = require('https');

function download(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                https.get(res.headers.location, (res2) => {
                    var data = []; res2.on('data', c => data.push(c));
                    res2.on('end', () => resolve(Buffer.concat(data)));
                });
                return;
            }
            var data = []; res.on('data', c => data.push(c));
            res.on('end', () => resolve(Buffer.concat(data)));
        });
    });
}

function parseMontant(str) {
    if (!str) return 0;
    if (typeof str === 'number') return str;
    var cleaned = String(str).replace(/[^0-9,\-\.]/g, '').replace(',', '.');
    return parseFloat(cleaned) || 0;
}

function getDepartmentFromCOG(cogCode) {
    if (!cogCode) return null;
    var code = String(cogCode).padStart(5, '0');
    if (code.startsWith('75')) return '75';
    if (code.startsWith('69')) return '69';
    if (code.startsWith('13')) return '13';
    if (code.startsWith('97') || code.startsWith('98')) return code.substring(0, 3);
    return code.substring(0, 2);
}

var progLabels = {
    '101': 'Accès au droit et à la justice', '102': 'Accès et retour à l\'emploi',
    '103': 'Accompagnement des mutations économiques et développement de l\'emploi',
    '104': 'Intégration et accès à la nationalité française',
    '105': 'Action de la France en Europe et dans le monde',
    '107': 'Administration pénitentiaire', '109': 'Aide à l\'accès aux soins',
    '110': 'Aide à la vie associative',
    '111': 'Amélioration de la qualité de l\'emploi et des relations du travail',
    '112': 'Aménagement et service des transports terrestres',
    '113': 'Paysages, eau et biodiversité',
    '119': 'Coordination des moyens de secours et de sécurité',
    '122': 'Compétitivité et durabilité de l\'agriculture et de l\'agroalimentaire',
    '123': 'Conditions de vie outre-mer',
    '124': 'Conduite et soutien des politiques sanitaires et sociales',
    '129': 'Coordination du travail gouvernemental', '131': 'Création',
    '134': 'Développement des entreprises et régulations', '135': 'Développement des sports',
    '137': 'Égalité entre les femmes et les hommes', '138': 'Emploi outre-mer',
    '139': 'Enseignement privé du premier et du second degrés',
    '140': 'Enseignement scolaire public du premier degré',
    '141': 'Enseignement scolaire public du second degré',
    '142': 'Enseignement supérieur et recherche agricoles',
    '143': 'Enseignement technique agricole',
    '144': 'Environnement et prospective de la politique de défense',
    '146': 'Équipement des forces', '147': 'Politique de la ville',
    '148': 'Fonction de contrôle de l\'administration', '149': 'Forêt',
    '150': 'Formations supérieures et recherche universitaire',
    '151': 'Français à l\'étranger et affaires consulaires',
    '152': 'Gestion des finances publiques',
    '155': 'Conception et pilotage des politiques de l\'agriculture',
    '156': 'Gestion fiscale et financière de l\'État',
    '157': 'Handicap et dépendance',
    '159': 'Information géographique et cartographique',
    '161': 'Interventions économiques en faveur des entreprises',
    '162': 'Interventions territoriales de l\'État',
    '163': 'Jeunesse et vie associative', '164': 'Justice judiciaire',
    '165': 'Justice administrative', '166': 'Justice des mineurs',
    '167': 'Liens entre la Nation et son armée', '169': 'Mémoire',
    '172': 'Monnaie', '174': 'Métropole', '175': 'Patrimoines',
    '176': 'Police nationale',
    '177': 'Prévention de l\'exclusion et insertion des personnes vulnérables',
    '178': 'Préparation et emploi des forces', '180': 'Presse et médias',
    '181': 'Protection de l\'environnement', '182': 'Protection des droits et libertés',
    '185': 'Rayonnement culturel et scientifique',
    '186': 'Recherche en matière de développement durable',
    '190': 'Recherche dans les domaines de l\'énergie et du développement durable',
    '192': 'Recherche et enseignement supérieur en matière économique et industrielle',
    '198': 'Régimes sociaux et de retraite',
    '203': 'Infrastructures et services de transports',
    '204': 'Prévention des risques',
    '205': 'Sécurité et qualité sanitaires de l\'alimentation',
    '206': 'Sécurité et paix publiques', '207': 'Sécurité et éducation routières',
    '209': 'Solidarité à l\'égard des pays en développement',
    '212': 'Soutien aux politiques du ministère de la Culture',
    '214': 'Soutien aux politiques du ministère de l\'Intérieur',
    '215': 'Soutien aux politiques de l\'Éducation nationale',
    '216': 'Soutien aux politiques de l\'enseignement supérieur',
    '217': 'Soutien aux politiques de la Défense',
    '218': 'Soutien aux politiques de l\'Outre-mer',
    '219': 'Soutien aux politiques de la Jeunesse et des Sports',
    '220': 'Soutien aux politiques du ministère de la Transition écologique',
    '224': 'Soutien aux politiques du ministère de l\'Agriculture',
    '230': 'Vie politique et citoyenne', '231': 'Vie étudiante',
    '232': 'Climat et transitions écologiques',
    '302': 'Facilitation et sécurisation des échanges',
    '303': 'Conduite et pilotage des politiques sanitaires et sociales',
    '304': 'Inclusion sociale et protection des personnes',
    '305': 'Recherche et développement dans le domaine de l\'environnement',
    '308': 'Protection des droits des victimes et accès à la nationalité',
    '310': 'Conduite et animation des politiques de l\'immigration et de l\'asile',
    '334': 'Livres et industries culturelles', '335': 'Innovations et transitions industrielles',
    '348': 'Réhabilitation des centres urbains', '349': 'Transition démographique et petite enfance',
    '352': 'Réussite scolaire et éducation prioritaire', '354': 'Santé des adolescents et jeunes adultes',
    '357': 'Soutien à l\'économie sociale et solidaire',
    '612': 'Coordination des politiques publiques et administration territoriale',
    '613': 'Relations avec les collectivités territoriales',
    '614': 'Animation et coordination des politiques éducatives et sociales',
    '623': 'Conduite et soutien des politiques territoriales',
    '624': 'Pilotage et animation des politiques sociales',
    '723': 'Soutien aux Outre-mer', '751': 'Politiques en faveur de l\'égalité des chances',
    '764': 'Transition écologique et cohésion territoriale',
    '775': 'Conduite et pilotage de la politique de défense',
    '776': 'Développement des territoires ultramarins',
    '901': 'Administration territoriale de l\'État', '902': 'Action extérieure de l\'État',
    '907': 'Administration et soutien des politiques économiques',
    '912': 'Soutien aux politiques de l\'environnement'
};

async function convertXLSX(year, url, sheetName, dataYear) {
    console.log('\n=== Converting PLF ' + year + ' ===');
    var buf = await download(url);
    var wb = XLSX.read(buf);
    var ws = wb.Sheets[sheetName];
    var rows = XLSX.utils.sheet_to_json(ws, {header: 1, defval: ''});

    var startRow = 0;
    for (var i = 0; i < rows.length; i++) {
        if (rows[i][0] === 'Programme' || rows[i][0] === 'Programme (2017)') {
            startRow = i; break;
        }
    }

    var headers = rows[startRow];
    console.log('Headers: ' + headers.join('; '));
    console.log('Data rows: ' + (rows.length - startRow - 1));

    function colIdx(name) {
        for (var i = 0; i < headers.length; i++) {
            if (headers[i] && (headers[i] === name || headers[i].trim() === name)) return i;
        }
        return -1;
    }

    var idxProgram = colIdx('Programme') >= 0 ? colIdx('Programme') : colIdx('Programme (2017)');
    var idxSiren = colIdx('SIREN');
    var idxNic = colIdx('NIC');
    var idxDenom = colIdx('Dénomination');
    var idxMontant = colIdx('Montant');
    var idxObjet = colIdx('Objet 2017') >= 0 ? colIdx('Objet 2017') : colIdx('Objet 2019');
    var idxRNA = colIdx('Répertoire national des associations');
    var idxCOGCode = colIdx('COG : code');
    var idxCOGLibelle = colIdx('COG : libellé');
    var idxConvention = colIdx('Convention 2017') >= 0 ? colIdx('Convention 2017') : colIdx('Convention 2019');

    var subventions = [];
    var idCounter = 0;

    for (var r = startRow + 1; r < rows.length; r++) {
        var row = rows[r];
        idCounter++;

        var denomination = idxDenom >= 0 && idxDenom < row.length ? String(row[idxDenom] || '') : '';
        var siren = idxSiren >= 0 && idxSiren < row.length ? String(row[idxSiren] || '') : '';
        var nic = idxNic >= 0 && idxNic < row.length ? String(row[idxNic] || '') : '';
        var montant = parseMontant(idxMontant >= 0 && idxMontant < row.length ? row[idxMontant] : 0);
        var programVal = idxProgram >= 0 && idxProgram < row.length ? String(row[idxProgram] || '') : '';

        if (montant <= 0 || !denomination) continue;

        var rna = '';
        if (idxRNA >= 0 && idxRNA < row.length) {
            var rnaVal = String(row[idxRNA] || '');
            if (rnaVal.startsWith('W')) rna = rnaVal;
        }

        var objet = idxObjet >= 0 && idxObjet < row.length ? String(row[idxObjet] || '') : '';
        var cogCode = idxCOGCode >= 0 && idxCOGCode < row.length ? String(row[idxCOGCode] || '') : '';
        var ville = idxCOGLibelle >= 0 && idxCOGLibelle < row.length ? String(row[idxCOGLibelle] || '') : '';

        var dept = getDepartmentFromCOG(cogCode) || '00';

        var progMatch = programVal.match(/(\d{3})/);
        var progCode = progMatch ? progMatch[1] : '';
        var progLabel = progLabels[progCode] || ('Programme ' + progCode);

        var convention = false;
        if (idxConvention >= 0 && idxConvention < row.length) {
            var cv = String(row[idxConvention] || '');
            convention = cv.toLowerCase() === 'oui' || cv === 'true' || cv === '1';
        }

        subventions.push({
            id: 'plf-' + year + '-' + String(idCounter).padStart(6, '0'),
            association: {
                name: denomination,
                rna: rna,
                siret: siren + nic,
                address: ville,
                department: dept,
                object: objet
            },
            entity: {
                name: 'État \u2014 ' + progLabel,
                type: 'state',
                level: 'ministère',
                program: progLabel
            },
            amount: montant,
            year: dataYear,
            justification: objet,
            convention: convention,
            source: 'https://www.data.gouv.fr/datasets/plf-jaune-associations-subventionnees'
        });

        if (idCounter % 10000 === 0) console.log('  ... ' + idCounter + ' (' + subventions.length + ' valides)');
    }

    var totalAmt = subventions.reduce(function(s, i) { return s + i.amount; }, 0);
    console.log('Result: ' + subventions.length + ' subventions, ' + totalAmt.toLocaleString('fr-FR') + ' \u20AC');

    var programs = {};
    subventions.forEach(function(s) { programs[s.entity.program] = 1; });
    var pCount = Object.keys(programs).length;

    var content = '(function() {\n';
    content += '    var RAW_DATA = ' + JSON.stringify(subventions) + ';\n';
    content += '    __registerDataSource(\'plf-jaune-' + year + '\', RAW_DATA);\n';
    content += '    console.log(\'Source "plf-jaune-' + year + '" : \' + RAW_DATA.length + \' lignes, ' + pCount + ' programmes, ' + totalAmt.toLocaleString('fr-FR') + ' \u20AC\');\n';
    content += '})();\n';

    var outFile = path.join(__dirname, '..', 'data', 'sources', 'plf-jaune-' + year + '.js');
    fs.writeFileSync(outFile, content);
    console.log('File: ' + outFile);
}

(async () => {
    await convertXLSX(
        2019,
        'https://data.economie.gouv.fr/api/v2/catalog/datasets/projet-de-loi-de-finances-pour-2019-plf-2019-donnees-de-lannexe-jaune-effort-fin/attachments/plf2019_jaune_asso_liste_associations2017_xlsx',
        'subvention2017_final', 2017
    );
    await convertXLSX(
        2021,
        'https://data.economie.gouv.fr/api/v2/catalog/datasets/projet-de-loi-de-finances-pour-2021-plf-2021-donnees-de-lannexe-jaune-effort-fin/attachments/plf_2021_credits_attribues_au_monde_associatif_2019_xlsx',
        'versements2019', 2019
    );
})();
