// ============================================================
//  DATA LOADER — Agrège, normalise et déduplique toutes les sources
// ============================================================
//
//  Ajouter une nouvelle source :
//    1. Créer data/sources/<source>.js (voir _template.js)
//    2. Ajouter un normalizer ci-dessous si le format diffère
//    3. Ajouter <script src="data/sources/<source>.js"> dans index.html
//
// ============================================================

(function() {
    var raw = window.__DATA_SOURCES || [];
    var seen = new Set();
    var merged = [];
    var COUNTER = {};

    // ---- HELPERS ----
    function pick(obj, keys) {
        for (var i = 0; i < keys.length; i++) {
            if (obj[keys[i]] !== undefined && obj[keys[i]] !== null && obj[keys[i]] !== '')
                return obj[keys[i]];
        }
        return '';
    }

    function parseYear(val) {
        if (!val) return 0;
        var n = parseInt(val);
        if (n > 1000 && n < 2100) return n;
        return 0;
    }

    function parseAmount(val) {
        if (!val) return 0;
        if (typeof val === 'number') return val;
        var cleaned = String(val).replace(/[^0-9,\-]/g, '').replace(',', '.');
        return parseFloat(cleaned) || 0;
    }

    function extractDepartment(codePostal, commune, cogCode) {
        if (codePostal) {
            var cp = String(codePostal);
            if (cp.length >= 2) {
                if (cp.startsWith('97') || cp.startsWith('98')) return cp.substring(0, 3);
                if (cp.startsWith('20')) return '2A';
                return cp.substring(0, 2);
            }
        }
        if (cogCode) {
            var cc = String(cogCode).padStart(5, '0');
            if (cc.startsWith('75')) return '75';
            if (cc.startsWith('69')) return '69';
            if (cc.startsWith('13')) return '13';
            if (cc.startsWith('97') || cc.startsWith('98')) return cc.substring(0, 3);
            return cc.substring(0, 2);
        }
        return '00';
    }

    function guessEntityTypeAndLevel(name, id) {
        name = (name || '').toLowerCase();
        id = (id || '').toLowerCase();

        if (name.indexOf('minist') !== -1 || name.indexOf('état') !== -1 || name.indexOf('direction ') !== -1 || id.indexOf('1100') === 0 || id.indexOf('1200') === 0 || id.indexOf('1300') === 0) {
            return { type: 'state', level: 'ministère' };
        }
        if (name.indexOf('région') !== -1 || name.indexOf('region') !== -1 || name.indexOf('conseil régional') !== -1 || name.indexOf('conseil regional') !== -1) {
            return { type: 'region', level: 'region' };
        }
        if (name.indexOf('département') !== -1 || name.indexOf('departement') !== -1 || name.indexOf('conseil départemental') !== -1 || name.indexOf('conseil departemental') !== -1 || name.indexOf('conseil général') !== -1) {
            return { type: 'department', level: 'department' };
        }
        if (name.indexOf('métropole') !== -1 || name.indexOf('metropole') !== -1 || name.indexOf('communauté') !== -1 || name.indexOf('communaut') !== -1 || name.indexOf('epci') !== -1 || name.indexOf('syndicat') !== -1) {
            return { type: 'epci', level: 'epci' };
        }
        if (name.indexOf('mairie') !== -1 || name.indexOf('ville de') !== -1 || name.indexOf('commune de') !== -1 || name.indexOf('village') !== -1) {
            return { type: 'commune', level: 'commune' };
        }
        return { type: 'commune', level: 'commune' };
    }

    function nextId(prefix) {
        COUNTER[prefix] = (COUNTER[prefix] || 0) + 1;
        return prefix + '-' + String(COUNTER[prefix]).padStart(6, '0');
    }

    // ---- NORMALIZERS ----
    // Chaque source peut avoir son propre format. Le normalizer
    // le transforme vers le format standard attendu par l'UI.
    //
    // Format standard :
    //   { id, association: { name, department, ... },
    //     entity: { type, name, ... },
    //     amount, year, source }
    //
    var NORMALIZERS = {

        // PLF Jaune — déjà au format standard
        'plf-jaune': function(item) { return item; },

        // Paris — déjà au format standard
        'paris': function(item) { return item; },

        // Ille-et-Vilaine — déjà au format standard (convertisseur dédié)
        'cd-ille-vilaine': function(item) { return item; },
        'cd-ille-vilaine-2021': function(item) { return item; },
        'cd-ille-vilaine-2022v2': function(item) { return item; },

        // Savoie — déjà au format standard (convertisseur dédié)
        'cd-savoie': function(item) { return item; },
        'cd-savoie-2018': function(item) { return item; },
        'cd-savoie-2020': function(item) { return item; },
        'cd-savoie-2019': function(item) { return item; },
        'cd-savoie-2021': function(item) { return item; },
        'cd-savoie-2022': function(item) { return item; },
        'cd-savoie-2023': function(item) { return item; },

        // Maine-et-Loire subventions — déjà au format standard (convertisseur dédié)
        'cd-maine-loire-subventions': function(item) { return item; },

        // Lot — déjà au format standard (convertisseur dédié)
        'cd-lot': function(item) { return item; },

        // Bas-Rhin — déjà au format standard (convertisseur XLSX dédié)
        'cd-bas-rhin': function(item) { return item; },

        // Villes — déjà au format standard (convertisseurs dédiés)
        'ville-lyon': function(item) { return item; },
        'ville-grenoble-2015': function(item) { return item; },
        'ville-grenoble-2016': function(item) { return item; },

        // Communes — déjà au format standard (convertisseurs dédiés)
        'commune-soissons': function(item) { return item; },
        'commune-bar-le-duc': function(item) { return item; },
        'commune-sarcelles': function(item) { return item; },
        'commune-meze': function(item) { return item; },
        'commune-iffendic': function(item) { return item; },
        'commune-pleumeleuc': function(item) { return item; },
        'commune-talensac': function(item) { return item; },
        'commune-breteil': function(item) { return item; },
        'commune-sixt-sur-aff': function(item) { return item; },
        'commune-saint-gonlay': function(item) { return item; },
        'commune-la-nouaye': function(item) { return item; },

        // Villes supplémentaires — déjà au format standard
        'ville-redon-2017': function(item) { return item; },
        'ville-redon-2018': function(item) { return item; },
        'ville-sailly': function(item) { return item; },
        'ville-longjumeau': function(item) { return item; },
        'ville-lisieux-2018': function(item) { return item; },
        'ville-manosque-2025': function(item) { return item; },
        'ville-carquefou-2025': function(item) { return item; },
        'ville-roubaix': function(item) { return item; },

        // Subventions diverses — déjà au format standard
        'subv-associations-2024': function(item) { return item; },
        'subv-votees-23k': function(item) { return item; },
        'subv-communales': function(item) { return item; },
        'subv-sup-23k-2024': function(item) { return item; },

        // Villes supplémentaires batch 2
        'ville-bauge-anjou': function(item) { return item; },
        'ville-arras-2018': function(item) { return item; },
        'ville-arras-2017': function(item) { return item; },
        'ville-nogent-2012': function(item) { return item; },
        'ville-nogent-2013': function(item) { return item; },
        'ville-nogent-2014': function(item) { return item; },
        'ville-roscloff-2017': function(item) { return item; },
        'ville-vitry-2017': function(item) { return item; },

        // EPCI
        'agglo-nevers': function(item) { return item; },
        'metropole-lyon': function(item) { return item; },
        'metropole-nantes': function(item) { return item; },
        'metropole-toulouse': function(item) { return item; },
        'metropole-bordeaux': function(item) { return item; },
        'pays-basque-2023': function(item) { return item; },
        'cci-rouen-2024': function(item) { return item; },

        // Nouvelles sources batch 9 (convertisseurs dédiés)
        'anct-politique-ville': function(item) { return item; },
        'cd-pyrenees-orientales': function(item) { return item; },
        'ville-quimper': function(item) { return item; },
        'agglo-quimper-bretagne-occidentale': function(item) { return item; },
        'commune-communay': function(item) { return item; },
        'agglo-saintes-grandes-rives': function(item) { return item; },
        'commune-rillieux-la-pape': function(item) { return item; },
        'commune-sautron': function(item) { return item; },
        'agglo-val-de-fensch': function(item) { return item; },
        'agglo-pays-de-l-or': function(item) { return item; },
        'cd-gironde': function(item) { return item; },
        'reserve-ministerielle': function(item) { return item; },
        'cd-nievre': function(item) { return item; },
        'ville-dreux': function(item) { return item; },
        'agglo-grand-chambery': function(item) { return item; },
        'efs-cpdl': function(item) { return item; },
        'commune-bouaye': function(item) { return item; },
        'ville-charleville-mezieres': function(item) { return item; },
        'metropole-grenoble': function(item) { return item; },
        'cd-somme': function(item) { return item; },
        'ville-nancy': function(item) { return item; },
        'ville-bayonne': function(item) { return item; },
        'ville-villejuif': function(item) { return item; },
        'efs-aura': function(item) { return item; },
        'commune-saint-laurent-de-mure': function(item) { return item; },
        'ditp': function(item) { return item; },
        'agglo-lorient': function(item) { return item; },
        'cnsa': function(item) { return item; },
        'feder-hauts-de-france': function(item) { return item; },
        'ecole-beaux-arts-nantes': function(item) { return item; },
        'commune-sautron-23k': function(item) { return item; },
        'ville-grenoble': function(item) { return item; },

        // Batch 15
        'cd-eure-et-loir': function(item) { return item; },
        'cc-pays-des-ecrins': function(item) { return item; },
        'sdis-gironde': function(item) { return item; },
        'cnds-2015': function(item) { return item; },
        'ars-pays-de-la-loire': function(item) { return item; },
        'metropole-clermont': function(item) { return item; },
        'ville-bar-le-duc': function(item) { return item; },
        'cd-haute-garonne': function(item) { return item; },
        'ville-boulogne-billancourt': function(item) { return item; },
        'ville-soissons-2018-2021': function(item) { return item; },
        'agglo-mulhouse': function(item) { return item; },

        // Batch 16
        'etat-dilcrah': function(item) { return item; },
        'etat-cabinet-pm': function(item) { return item; },
        'etat-bop177': function(item) { return item; },
        'cd-charente-maritime': function(item) { return item; },
        'cd-cher': function(item) { return item; },
        'cd-dordogne': function(item) { return item; },
        'cd-hautes-pyrenees': function(item) { return item; },
        'cd-hauts-de-seine': function(item) { return item; },
        'cd-isere': function(item) { return item; },
        'cd-mayenne': function(item) { return item; },
        'cd-aube': function(item) { return item; },
        'ville-vaulx': function(item) { return item; },
        'ville-lisieux': function(item) { return item; },
        'ville-redon': function(item) { return item; },
        'ville-iffendic': function(item) { return item; },
        'ville-talensac': function(item) { return item; },
        'ville-poinconnet': function(item) { return item; },
        'ville-lannion': function(item) { return item; },
        'efs-siege': function(item) { return item; },
        'efs-ocpm': function(item) { return item; },
        'cc-quercy-vert': function(item) { return item; },

        // Départements batch 3
        'dept-seine-saint-denis': function(item) { return item; },

        // Villes batch 3
        'ville-rennes': function(item) { return item; },
        'ville-marseille': function(item) { return item; },
        'ville-tours': function(item) { return item; },

        // Régions
        'region-idf': function(item) { return item; },
        'region-centre': function(item) { return item; },

        // Villes batch 3 supplement
        'ville-nantes': function(item) { return item; },
        'ville-toulouse': function(item) { return item; },

        // État/DILCRAH
        'dilcrah-2024': function(item) { return item; },
        'dilcrah-2025': function(item) { return item; },
        'plf-jaune-2023': function(item) { return item; },
        'ministere-agriculture': function(item) { return item; },
        'culture': function(item) { return item; },
        'ville-boulogne': function(item) { return item; },
        'ville-anglet': function(item) { return item; },
        'ville-sarcelles-2025': function(item) { return item; },
        'ville-villemomble': function(item) { return item; },
        'ville-issy': function(item) { return item; },
        'epci-gpso': function(item) { return item; },
        'idf-sante': function(item) { return item; },
        'ville-meudon': function(item) { return item; },
        'ville-asnieres': function(item) { return item; },

        // Communes batch 2
        'communes-pays-loire': function(item) { return item; },
        'communes-centre': function(item) { return item; },

        // Côtes d'Armor 2002-2015 (format custom: EXERCICE;LBASSOCIATION;SUBVF;SUBVI)
        'cd-cotes-armor-2002': function(item) {
            var nomAsso = item.LBASSOCIATION || '';
            var exercice = parseInt(item.EXERCICE) || 0;
            var montantFonct = parseAmount(item.SUBVF);
            var montantInvest = parseAmount(item.SUBVI);
            var montant = montantFonct + montantInvest;
            if (!nomAsso || montant <= 0) return null;
            return {
                id: item._id || nextId('cd22'),
                association: { name: nomAsso, department: '22' },
                entity: { name: 'Département des Côtes d\'Armor', type: 'department', level: 'department' },
                amount: montant,
                year: exercice,
                source: 'https://datarmor.cotesdarmor.fr/datasets/subventions-versees-par-le-conseil-departemental-des-cotes-darmor-aux-associations-de-2002-a-2015'
            };
        },

        // ---- Normalizer SCDL (Socle Commun des Données Locales) ----
        // Format utilisé par les collectivités sur data.gouv.fr.
        // Colonnes standard :
        //   nomAttribuant, idAttribuant, dateConvention, referenceDecision,
        //   nomBeneficiaire, idBeneficiaire, objet, montant, nature,
        //   conditionsVersement, datesPeriodeVersement, idRAE,
        //   notificationUE, pourcentageSubvention
        // Variantes courantes : annee, siret, rna, code_postal, ville,
        //   departement, libelle_commune, libelle_attribuant
        //
        'scdl': function(item) {
            var nomAsso = pick(item, ['nomBeneficiaire', 'nom_beneficiaire', 'nombeneficiaire', 'nomBenecifiaire', 'nom_du_beneficiaire', 'nom_association', 'denomination', 'association_nom', 'recipient_name', 'nom_declarant', 'nom_benef']);
            var idBenef = pick(item, ['idBeneficiaire', 'id_beneficiaire', 'idbeneficiaire', 'siret_attributaire', 'siret', 'numero_siret', 'num_siret']);
            var rna = pick(item, ['rna', 'num_rna', 'numero_rna']);
            var codePostal = pick(item, ['code_postal', 'cp', 'codepostal', 'code_insee']);
            var nomCommune = pick(item, ['libelle_commune', 'ville', 'commune', 'adresse', 'address', 'libcom']);
            var departement = pick(item, ['departement', 'code_departement', 'num_departement', 'department']);
            var objet = pick(item, ['objet', 'objet_du_dossier', 'objet_de_la_subvention', 'l_objet_de_la_subvention', 'object', 'objet_subvention', 'description', 'justification', 'projet']);
            var annee = parseYear(pick(item, ['annee', 'annee_budgetaire', 'anneebudgetaire', 'year', 'exercice', 'dateconvention', 'date_convention', 'date_de_la_convention', 'datedecision', 'dateDecision', 'date_decision']));
            var montant = parseAmount(pick(item, ['montant', 'montant_total', 'montant_vote', 'montant_subvention', 'amount', 'montant_aide', 'montant_attribue', 'subvention']));

            var nomAttrib = pick(item, ['nomAttribuant', 'nom_attribuant', 'nomattribuant', 'nom_de_l_attribuant', 'libelle_attribuant', 'attribuant', 'collectivite', 'donateur', 'entity_name', 'financeur']);
            var idAttrib = pick(item, ['idAttribuant', 'id_attribuant', 'idattribuant', 'identification_del_attribuant', 'siret_attribuant']);

            var entityInfo = guessEntityTypeAndLevel(nomAttrib, idAttrib);

            var source = item.source || item.url_source || item.source_url || '';
            var justification = objet;

            if (!nomAsso) return null;

            var id = item.id || nextId('scdl');

            return {
                id: id,
                association: {
                    name: nomAsso,
                    rna: rna || '',
                    siret: idBenef || '',
                    address: nomCommune,
                    department: departement || extractDepartment(codePostal, nomCommune, ''),
                    object: objet
                },
                entity: {
                    name: nomAttrib || 'Collectivité',
                    type: entityInfo.type,
                    level: entityInfo.level
                },
                amount: montant,
                year: annee || 0,
                justification: justification,
                convention: montant >= 23000,
                source: source
            };
        }

    };

    function detectSCDL(item) {
        if (!item || typeof item !== 'object') return false;
        var keys = Object.keys(item);
        return keys.some(function(k) {
            return /^nomattribuant|^montant|^nombeneficiaire|^objet|^dateconvention/i.test(k);
        });
    }

    raw.forEach(function(src) {
        var norm = NORMALIZERS[src.id];
        if (!norm && src.data && src.data.length > 0 && detectSCDL(src.data[0])) {
            norm = NORMALIZERS['scdl'];
        }
        if (!norm) norm = function(x) { return x; };
        (src.data || []).forEach(function(item) {
            try {
                var n = norm(item);
                if (n && n.id && !seen.has(n.id)) {
                    seen.add(n.id);
                    merged.push(n);
                }
            } catch(e) {
                console.warn('Loader: error normalizing item from', src.id, e);
            }
        });
    });

    window.ALL_SUBVENTIONS = merged;
})();
