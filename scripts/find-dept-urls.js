const https = require('https');

function fetch(url) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, { headers: { 'Accept': 'application/json' } }, (res) => {
            let data = '';
            if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                let redirect = res.headers.location;
                if (redirect.startsWith('/')) redirect = 'https://www.data.gouv.fr' + redirect;
                https.get(redirect, { headers: { 'Accept': 'application/json' } }, (res2) => {
                    res2.on('data', c => data += c);
                    res2.on('end', () => { try { resolve(JSON.parse(data)); } catch(e) { reject(e); } });
                });
                return;
            }
            res.on('data', c => data += c);
            res.on('end', () => { try { resolve(JSON.parse(data)); } catch(e) { reject(e); } });
        });
        req.on('error', reject);
    });
}

async function findDepartment(slug) {
    try {
        const data = await fetch('https://www.data.gouv.fr/api/1/datasets/' + slug + '/');
        console.log('=== ' + slug + ' ===');
        console.log('Title:', data.title);
        if (data.resources) {
            data.resources.forEach(r => console.log('  ' + (r.title || 'Resource') + ': ' + r.url));
        }
    } catch (e) {
        console.log('=== ' + slug + ' === ERR: ' + e.message.substring(0, 100));
    }
}

async function main() {
    const slugs = [
        'subventions-aux-associations-versees-par-le-departement-de-loire-atlantique-2',
        'detail-des-subventions-accordees-par-le-departement-de-la-gironde-1',
        'subventions-aux-associations-du-departement-de-maine-et-loire',
        'subventions-versees-aux-associations-par-le-departement-dille-et-vilaine',
        'subventions-aux-personnes-morales-2',
        'publication-des-subventions-aux-associations',
        'subventions-versees-par-le-departement-de-la-savoie-cd73-en-2017',
        'subventions-du-departement-des-hautes-pyrenees',
        'donnees-essentielles-des-conventions-subventions',
        'conventions-de-subventions-2017-2019-du-departement-de-maine-et-loire',
        'conventions-de-subventions-2025-du-departement-de-maine-et-loire',
        'donnees-essentielles-des-conventions-de-subvention-2021-departement-du-lot',
        'donnees-essentielles-des-conventions-de-subvention-2022-departement-du-lot',
        'subventions-de-plus-de-23000-euros-accordees-par-le-conseil-departemental-du-finistere',
        'subventions-versees-par-le-departement-de-la-manche-aux-collectivites-et-organismes',
        'finances-subventions-departementales-bas-rhin',
        'subventions-versees-aux-collectivites-et-organismes-1',
        'subventions-accordees-par-le-departement-de-lisere'
    ];

    for (const slug of slugs) {
        await findDepartment(slug);
        console.log('');
    }
}

main();
