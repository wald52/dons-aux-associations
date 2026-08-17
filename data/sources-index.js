// Index of all data sources for lazy loading
// This file defines metadata for each data source to enable selective loading

const DATA_SOURCES_INDEX = {
    // Sample/demo data (small, always loaded)
    sample: {
        id: 'sample-data',
        file: 'data/sample-data.js',
        size: 'small',
        priority: 'high',
        description: 'Jeu de démonstration',
        years: null,
        entityType: null,
        region: null,
        department: null
    },
    
    // PLF Jaune - État (by year)
    plfJaune: {
        id: 'plf-jaune',
        files: {
            2012: 'data/sources/plf-jaune-2012.js',
            2013: 'data/sources/plf-jaune-2013.js',
            2014: 'data/sources/plf-jaune-2014.js',
            2015: 'data/sources/plf-jaune-2015.js',
            2016: 'data/sources/plf-jaune-2016.js',
            2017: 'data/sources/plf-jaune-2017.js',
            2018: 'data/sources/plf-jaune-2018.js',
            2019: 'data/sources/plf-jaune-2019.js',
            2020: 'data/sources/plf-jaune-2020.js',
            2021: 'data/sources/plf-jaune-2021.js',
            2022: 'data/sources/plf-jaune-2022.js',
            2025: 'data/sources/plf-jaune-2025.js'
        },
        size: 'large',
        priority: 'medium',
        description: 'PLF Jaune - Subventions de l\'État',
        years: [2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
        entityType: 'state',
        region: null,
        department: null
    },
    
    // Paris
    paris: {
        id: 'paris',
        file: 'data/sources/paris.js',
        size: 'medium',
        priority: 'medium',
        description: 'Ville de Paris',
        years: [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
        entityType: 'commune',
        region: 'Île-de-France',
        department: '75'
    },
    
    // Départements
    departments: {
        mayenne: { id: 'cd-mayenne', file: 'data/sources/cd-mayenne.js', size: 'small', entityType: 'department', department: '53' },
        isere: { id: 'cd-isere', file: 'data/sources/cd-isere.js', size: 'small', entityType: 'department', department: '38' },
        loireAtlantique: { id: 'cd-loire-atlantique', file: 'data/sources/cd-loire-atlantique.js', size: 'medium', entityType: 'department', department: '44' },
        hautesPyrenees: { id: 'cd-hautes-pyrenees', file: 'data/sources/cd-hautes-pyrenees.js', size: 'small', entityType: 'department', department: '65' },
        maineLoireConventions: { id: 'cd-maine-loire-conventions', file: 'data/sources/cd-maine-loire-conventions.js', size: 'small', entityType: 'department', department: '49' },
        maineLoireConventions2025: { id: 'cd-maine-loire-conventions-2025', file: 'data/sources/cd-maine-loire-conventions-2025.js', size: 'small', entityType: 'department', department: '49' },
        illeVilaine: { id: 'cd-ille-vilaine', file: 'data/sources/cd-ille-vilaine.js', size: 'small', entityType: 'department', department: '35' },
        illeVilaine2021: { id: 'cd-ille-vilaine-2021', file: 'data/sources/cd-ille-vilaine-2021.js', size: 'small', entityType: 'department', department: '35' },
        illeVilaine2022: { id: 'cd-ille-vilaine-2022v2', file: 'data/sources/cd-ille-vilaine-2022v2.js', size: 'small', entityType: 'department', department: '35' },
        savoie: { id: 'cd-savoie', file: 'data/sources/cd-savoie.js', size: 'small', entityType: 'department', department: '73' },
        savoie2018: { id: 'cd-savoie-2018', file: 'data/sources/cd-savoie-2018.js', size: 'small', entityType: 'department', department: '73' },
        savoie2019: { id: 'cd-savoie-2019', file: 'data/sources/cd-savoie-2019.js', size: 'small', entityType: 'department', department: '73' },
        savoie2020: { id: 'cd-savoie-2020', file: 'data/sources/cd-savoie-2020.js', size: 'small', entityType: 'department', department: '73' },
        savoie2021: { id: 'cd-savoie-2021', file: 'data/sources/cd-savoie-2021.js', size: 'small', entityType: 'department', department: '73' },
        savoie2022: { id: 'cd-savoie-2022', file: 'data/sources/cd-savoie-2022.js', size: 'small', entityType: 'department', department: '73' },
        savoie2023: { id: 'cd-savoie-2023', file: 'data/sources/cd-savoie-2023.js', size: 'small', entityType: 'department', department: '73' },
        maineLoireSubventions: { id: 'cd-maine-loire-subventions', file: 'data/sources/cd-maine-loire-subventions.js', size: 'medium', entityType: 'department', department: '49' },
        finistere: { id: 'cd-finistere', file: 'data/sources/cd-finistere.js', size: 'medium', entityType: 'department', department: '29' },
        nievre: { id: 'cd-nievre', file: 'data/sources/cd-nievre.js', size: 'medium', entityType: 'department', department: '58' },
        dordogne: { id: 'cd-dordogne', file: 'data/sources/cd-dordogne.js', size: 'medium', entityType: 'department', department: '24' },
        loire: { id: 'cd-loire', file: 'data/sources/cd-loire.js', size: 'small', entityType: 'department', department: '42' },
        basRhin: { id: 'cd-bas-rhin', file: 'data/sources/cd-bas-rhin.js', size: 'medium', entityType: 'department', department: '67' },
        lot: { id: 'cd-lot', file: 'data/sources/cd-lot.js', size: 'small', entityType: 'department', department: '46' },
        cotesArmor: { id: 'cd-cotes-armor', file: 'data/sources/cd-cotes-armor.js', size: 'medium', entityType: 'department', department: '22' },
        cotesArmor2002: { id: 'cd-cotes-armor-2002', file: 'data/sources/cd-cotes-armor-2002.js', size: 'medium', entityType: 'department', department: '22' },
        seineSaintDenis: { id: 'dept-seine-saint-denis', file: 'data/sources/dept-seine-saint-denis.js', size: 'medium', entityType: 'department', department: '93' }
    },
    
    // Villes
    cities: {
        lyon: { id: 'ville-lyon', file: 'data/sources/ville-lyon.js', size: 'medium', entityType: 'commune', department: '69' },
        grenoble2015: { id: 'ville-grenoble-2015', file: 'data/sources/ville-grenoble-2015.js', size: 'small', entityType: 'commune', department: '38' },
        grenoble2016: { id: 'ville-grenoble-2016', file: 'data/sources/ville-grenoble-2016.js', size: 'small', entityType: 'commune', department: '38' },
        redon2017: { id: 'ville-redon-2017', file: 'data/sources/ville-redon-2017.js', size: 'small', entityType: 'commune', department: '35' },
        redon2018: { id: 'ville-redon-2018', file: 'data/sources/ville-redon-2018.js', size: 'small', entityType: 'commune', department: '35' },
        sailly: { id: 'ville-sailly', file: 'data/sources/ville-sailly.js', size: 'small', entityType: 'commune', department: '59' },
        longjumeau: { id: 'ville-longjumeau', file: 'data/sources/ville-longjumeau.js', size: 'small', entityType: 'commune', department: '91' },
        lisieux2018: { id: 'ville-lisieux-2018', file: 'data/sources/ville-lisieux-2018.js', size: 'small', entityType: 'commune', department: '14' },
        manosque2025: { id: 'ville-manosque-2025', file: 'data/sources/ville-manosque-2025.js', size: 'small', entityType: 'commune', department: '04' },
        carquefou2025: { id: 'ville-carquefou-2025', file: 'data/sources/ville-carquefou-2025.js', size: 'small', entityType: 'commune', department: '44' },
        roubaix: { id: 'ville-roubaix', file: 'data/sources/ville-roubaix.js', size: 'medium', entityType: 'commune', department: '59' },
        baugeAnjou: { id: 'ville-bauge-anjou', file: 'data/sources/ville-bauge-anjou.js', size: 'small', entityType: 'commune', department: '49' },
        arras2018: { id: 'ville-arras-2018', file: 'data/sources/ville-arras-2018.js', size: 'small', entityType: 'commune', department: '62' },
        arras2017: { id: 'ville-arras-2017', file: 'data/sources/ville-arras-2017.js', size: 'small', entityType: 'commune', department: '62' },
        nogent2012: { id: 'ville-nogent-2012', file: 'data/sources/ville-nogent-2012.js', size: 'small', entityType: 'commune', department: '94' },
        nogent2013: { id: 'ville-nogent-2013', file: 'data/sources/ville-nogent-2013.js', size: 'small', entityType: 'commune', department: '94' },
        nogent2014: { id: 'ville-nogent-2014', file: 'data/sources/ville-nogent-2014.js', size: 'small', entityType: 'commune', department: '94' },
        roscloff2017: { id: 'ville-roscloff-2017', file: 'data/sources/ville-roscloff-2017.js', size: 'small', entityType: 'commune', department: '29' },
        vitry2017: { id: 'ville-vitry-2017', file: 'data/sources/ville-vitry-2017.js', size: 'small', entityType: 'commune', department: '94' },
        villejuif: { id: 'ville-villejuif', file: 'data/sources/ville-villejuif.js', size: 'medium', entityType: 'commune', department: '94' },
        rennes: { id: 'ville-rennes', file: 'data/sources/ville-rennes.js', size: 'large', entityType: 'commune', department: '35' },
        marseille: { id: 'ville-marseille', file: 'data/sources/ville-marseille.js', size: 'large', entityType: 'commune', department: '13' },
        tours: { id: 'ville-tours', file: 'data/sources/ville-tours.js', size: 'medium', entityType: 'commune', department: '37' },
        nantes: { id: 'ville-nantes', file: 'data/sources/ville-nantes.js', size: 'large', entityType: 'commune', department: '44' },
        toulouse: { id: 'ville-toulouse', file: 'data/sources/ville-toulouse.js', size: 'large', entityType: 'commune', department: '31' },
        orvault: { id: 'ville-orvault', file: 'data/sources/ville-orvault.js', size: 'small', entityType: 'commune', department: '44' },
        boulogne: { id: 'ville-boulogne', file: 'data/sources/ville-boulogne.js', size: 'small', entityType: 'commune', department: '92' },
        anglet: { id: 'ville-anglet', file: 'data/sources/ville-anglet.js', size: 'small', entityType: 'commune', department: '64' },
        sarcelles2025: { id: 'ville-sarcelles-2025', file: 'data/sources/ville-sarcelles-2025.js', size: 'small', entityType: 'commune', department: '95' },
        villemomble: { id: 'ville-villemomble', file: 'data/sources/ville-villemomble.js', size: 'small', entityType: 'commune', department: '93' },
        issy: { id: 'ville-issy', file: 'data/sources/ville-issy.js', size: 'small', entityType: 'commune', department: '92' },
        asnieres: { id: 'ville-asnieres', file: 'data/sources/ville-asnieres.js', size: 'small', entityType: 'commune', department: '92' },
        meudon: { id: 'ville-meudon', file: 'data/sources/ville-meudon.js', size: 'small', entityType: 'commune', department: '92' }
    },
    
    // Communes
    communes: {
        soissons: { id: 'commune-soissons', file: 'data/sources/commune-soissons.js', size: 'small', entityType: 'commune', department: '02' },
        barLeDuc: { id: 'commune-bar-le-duc', file: 'data/sources/commune-bar-le-duc.js', size: 'small', entityType: 'commune', department: '55' },
        sarcelles: { id: 'commune-sarcelles', file: 'data/sources/commune-sarcelles.js', size: 'small', entityType: 'commune', department: '95' },
        meze: { id: 'commune-meze', file: 'data/sources/commune-meze.js', size: 'small', entityType: 'commune', department: '34' },
        iffendic: { id: 'commune-iffendic', file: 'data/sources/commune-iffendic.js', size: 'small', entityType: 'commune', department: '35' },
        pleumeleuc: { id: 'commune-pleumeleuc', file: 'data/sources/commune-pleumeleuc.js', size: 'small', entityType: 'commune', department: '35' },
        talensac: { id: 'commune-talensac', file: 'data/sources/commune-talensac.js', size: 'small', entityType: 'commune', department: '35' },
        breteil: { id: 'commune-breteil', file: 'data/sources/commune-breteil.js', size: 'small', entityType: 'commune', department: '35' },
        sixtSurAff: { id: 'commune-sixt-sur-aff', file: 'data/sources/commune-sixt-sur-aff.js', size: 'small', entityType: 'commune', department: '74' },
        saintGonlay: { id: 'commune-saint-gonlay', file: 'data/sources/commune-saint-gonlay.js', size: 'small', entityType: 'commune', department: '77' },
        laNouaye: { id: 'commune-la-nouaye', file: 'data/sources/commune-la-nouaye.js', size: 'small', entityType: 'commune', department: '35' }
    },
    
    // EPCI / Métropoles
    epci: {
        nevers: { id: 'agglo-nevers', file: 'data/sources/agglo-nevers.js', size: 'small', entityType: 'epci', department: '58' },
        metropoleLyon: { id: 'metropole-lyon', file: 'data/sources/metropole-lyon.js', size: 'large', entityType: 'epci', region: 'Auvergne-Rhône-Alpes' },
        metropoleNantes: { id: 'metropole-nantes', file: 'data/sources/metropole-nantes.js', size: 'medium', entityType: 'epci', region: 'Pays de la Loire' },
        metropoleToulouse: { id: 'metropole-toulouse', file: 'data/sources/metropole-toulouse.js', size: 'large', entityType: 'epci', region: 'Occitanie' },
        metropoleBordeaux: { id: 'metropole-bordeaux', file: 'data/sources/metropole-bordeaux.js', size: 'medium', entityType: 'epci', region: 'Nouvelle-Aquitaine' },
        paysBasque: { id: 'pays-basque-2023', file: 'data/sources/pays-basque-2023.js', size: 'small', entityType: 'epci', region: 'Nouvelle-Aquitaine' },
        cciRouen: { id: 'cci-rouen-2024', file: 'data/sources/cci-rouen-2024.js', size: 'small', entityType: 'epci', region: 'Normandie' },
        gpso: { id: 'epci-gpso', file: 'data/sources/epci-gpso.js', size: 'small', entityType: 'epci', region: 'Île-de-France' }
    },
    
    // Régions
    regions: {
        ileDeFrance: { id: 'region-idf', file: 'data/sources/region-idf.js', size: 'large', entityType: 'region', region: 'Île-de-France' },
        centre: { id: 'region-centre', file: 'data/sources/region-centre.js', size: 'medium', entityType: 'region', region: 'Centre-Val de Loire' }
    },
    
    // État / Ministères
    state: {
        dilcrah2024: { id: 'dilcrah-2024', file: 'data/sources/dilcrah-2024.js', size: 'small', entityType: 'state' },
        dilcrah2025: { id: 'dilcrah-2025', file: 'data/sources/dilcrah-2025.js', size: 'small', entityType: 'state' },
        agriculture: { id: 'ministere-agriculture', file: 'data/sources/ministere-agriculture.js', size: 'medium', entityType: 'state' },
        idfSante: { id: 'idf-sante', file: 'data/sources/idf-sante.js', size: 'small', entityType: 'state', region: 'Île-de-France' }
    },
    
    // Divers
    divers: {
        subvAssociations2024: { id: 'subv-associations-2024', file: 'data/sources/subv-associations-2024.js', size: 'small' },
        subvVotees23k: { id: 'subv-votees-23k', file: 'data/sources/subv-votees-23k.js', size: 'small' },
        subvCommunales: { id: 'subv-communales', file: 'data/sources/subv-communales.js', size: 'small' },
        subvSup23k2024: { id: 'subv-sup-23k-2024', file: 'data/sources/subv-sup-23k-2024.js', size: 'small' },
        donges: { id: 'donges', file: 'data/sources/donges.js', size: 'small', entityType: 'commune', department: '44' },
        saintJoachim: { id: 'saint-joachim', file: 'data/sources/saint-joachim.js', size: 'small', entityType: 'commune', department: '44' },
        laBaule: { id: 'la-baule', file: 'data/sources/la-baule.js', size: 'small', entityType: 'commune', department: '44' },
        argentonSurCreuse: { id: 'argenton-sur-creuse', file: 'data/sources/argenton-sur-creuse.js', size: 'small', entityType: 'commune', department: '36' },
        fleuryLesAubrais: { id: 'fleury-les-aubrais', file: 'data/sources/fleury-les-aubrais.js', size: 'small', entityType: 'commune', department: '45' },
        noyalChatillon: { id: 'noyal-chatillon-sur-seiche', file: 'data/sources/noyal-chatillon-sur-seiche.js', size: 'small', entityType: 'commune', department: '35' },
        communesPaysLoire: { id: 'communes-pays-loire', file: 'data/sources/communes-pays-loire.js', size: 'small', region: 'Pays de la Loire' },
        communesCentre: { id: 'communes-centre', file: 'data/sources/communes-centre.js', size: 'small', region: 'Centre-Val de Loire' }
    }
};

// Helper functions to find sources by criteria
function findSourcesByYear(year) {
    const results = [];
    
    // Check PLF Jaune
    if (DATA_SOURCES_INDEX.plfJaune.files[year]) {
        results.push(DATA_SOURCES_INDEX.plfJaune.files[year]);
    }
    
    // Check other sources
    Object.values(DATA_SOURCES_INDEX).forEach(category => {
        if (category.files) {
            Object.values(category).forEach(source => {
                if (source.years && source.years.includes(year)) {
                    results.push(source);
                }
            });
        } else if (Array.isArray(category)) {
            category.forEach(source => {
                if (source.years && source.years.includes(year)) {
                    results.push(source);
                }
            });
        }
    });
    
    return results;
}

function findSourcesByDepartment(deptCode) {
    const results = [];
    
    Object.values(DATA_SOURCES_INDEX).forEach(category => {
        if (Array.isArray(category)) {
            category.forEach(source => {
                if (source.department === deptCode) {
                    results.push(source);
                }
            });
        }
    });
    
    return results;
}

function findSourcesByRegion(regionName) {
    const results = [];
    
    Object.values(DATA_SOURCES_INDEX).forEach(category => {
        if (Array.isArray(category)) {
            category.forEach(source => {
                if (source.region === regionName) {
                    results.push(source);
                }
            });
        }
    });
    
    return results;
}

function findSourcesByEntityType(entityType) {
    const results = [];
    
    Object.values(DATA_SOURCES_INDEX).forEach(category => {
        if (Array.isArray(category)) {
            category.forEach(source => {
                if (source.entityType === entityType) {
                    results.push(source);
                }
            });
        }
    });
    
    return results;
}

function getAllSourceFiles() {
    const files = [];
    
    Object.values(DATA_SOURCES_INDEX).forEach(category => {
        if (category.file) {
            files.push(category.file);
        } else if (category.files) {
            Object.values(category.files).forEach(file => files.push(file));
        } else if (Array.isArray(category)) {
            category.forEach(source => {
                if (source.file) files.push(source.file);
            });
        }
    });
    
    return files;
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        DATA_SOURCES_INDEX,
        findSourcesByYear,
        findSourcesByDepartment,
        findSourcesByRegion,
        findSourcesByEntityType,
        getAllSourceFiles
    };
}
