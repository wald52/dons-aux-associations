import State from '../state.js';

// Dynamic data loader module for lazy loading
const DataLoader = (function() {
    const loadedSources = new Set();
    const loadingPromises = new Map();

    // Load a single JavaScript file dynamically
    function loadScript(src) {
        if (loadedSources.has(src)) {
            return Promise.resolve();
        }

        if (loadingPromises.has(src)) {
            return loadingPromises.get(src);
        }

        const promise = new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = () => {
                loadedSources.add(src);
                loadingPromises.delete(src);
                resolve();
            };
            script.onerror = () => {
                loadingPromises.delete(src);
                reject(new Error(`Failed to load script: ${src}`));
            };
            document.head.appendChild(script);
        });

        loadingPromises.set(src, promise);
        return promise;
    }

    // Load sources based on current filters
    async function loadSourcesForFilters() {
        const filter = State.getFilter();
        const sourcesToLoad = [];

        // Always load sample data first
        if (!loadedSources.has('data/sample-data.js')) {
            sourcesToLoad.push('data/sample-data.js');
        }

        // Load by year if specified
        if (filter.year !== 'all') {
            const year = parseInt(filter.year);
            // PLF Jaune files are named plf-jaune-{year+2}.js (e.g., 2012 data is in plf-jaune-2014.js)
            const plfYear = year + 2;
            const plfFile = `data/sources/plf-jaune-${plfYear}.js`;
            if (!loadedSources.has(plfFile)) {
                sourcesToLoad.push(plfFile);
            }
        }

        // Load by department if specified
        if (filter.department) {
            const deptSources = findDepartmentSources(filter.department);
            deptSources.forEach(src => {
                if (!loadedSources.has(src)) {
                    sourcesToLoad.push(src);
                }
            });
        }

        // Load by region if specified
        if (filter.region) {
            const regionSources = findRegionSources(filter.region);
            regionSources.forEach(src => {
                if (!loadedSources.has(src)) {
                    sourcesToLoad.push(src);
                }
            });
        }

        // Load by entity type if specified
        if (filter.entityType !== 'all') {
            const entityTypeSources = findEntityTypeSources(filter.entityType);
            entityTypeSources.forEach(src => {
                if (!loadedSources.has(src)) {
                    sourcesToLoad.push(src);
                }
            });
        }

        // Load sources in parallel
        if (sourcesToLoad.length > 0) {
            State.dispatch({ type: 'SET_LOADING', payload: true });
            try {
                await Promise.all(sourcesToLoad.map(src => loadScript(src)));
                // Merge data from newly loaded sources
                mergeLoadedData();
            } catch (error) {
                console.error('Error loading sources:', error);
                State.dispatch({ 
                    type: 'SET_ERROR', 
                    payload: `Erreur lors du chargement des données: ${error.message}` 
                });
            } finally {
                State.dispatch({ type: 'SET_LOADING', payload: false });
            }
        }
    }

    // Find sources for a specific department
    function findDepartmentSources(deptCode) {
        const sources = [];
        
        // Known department mappings
        const deptMappings = {
            '53': ['data/sources/cd-mayenne.js'],
            '38': ['data/sources/cd-isere.js'],
            '44': ['data/sources/cd-loire-atlantique.js', 'data/sources/cd-maine-loire-subventions.js'],
            '65': ['data/sources/cd-hautes-pyrenees.js'],
            '49': ['data/sources/cd-maine-loire-conventions.js', 'data/sources/cd-maine-loire-conventions-2025.js'],
            '35': ['data/sources/cd-ille-vilaine.js', 'data/sources/cd-ille-vilaine-2021.js', 'data/sources/cd-ille-vilaine-2022v2.js'],
            '73': ['data/sources/cd-savoie.js', 'data/sources/cd-savoie-2018.js', 'data/sources/cd-savoie-2019.js', 
                   'data/sources/cd-savoie-2020.js', 'data/sources/cd-savoie-2021.js', 'data/sources/cd-savoie-2022.js', 'data/sources/cd-savoie-2023.js'],
            '29': ['data/sources/cd-finistere.js'],
            '58': ['data/sources/cd-nievre.js'],
            '24': ['data/sources/cd-dordogne.js'],
            '42': ['data/sources/cd-loire.js'],
            '67': ['data/sources/cd-bas-rhin.js'],
            '46': ['data/sources/cd-lot.js'],
            '22': ['data/sources/cd-cotes-armor.js', 'data/sources/cd-cotes-armor-2002.js'],
            '93': ['data/sources/dept-seine-saint-denis.js']
        };

        return deptMappings[deptCode] || [];
    }

    // Find sources for a specific region
    function findRegionSources(regionCode) {
        const regionNameMap = {
            '84': 'Auvergne-Rhône-Alpes',
            '27': 'Bourgogne-Franche-Comté',
            '53': 'Bretagne',
            '24': 'Centre-Val de Loire',
            '94': 'Corse',
            '44': 'Grand Est',
            '32': 'Hauts-de-France',
            '11': 'Île-de-France',
            '28': 'Normandie',
            '75': 'Nouvelle-Aquitaine',
            '76': 'Occitanie',
            '52': 'Pays de la Loire',
            '93': "Provence-Alpes-Côte d'Azur"
        };

        const regionName = regionNameMap[regionCode];
        if (!regionName) return [];

        const regionMappings = {
            'Île-de-France': ['data/sources/region-idf.js', 'data/sources/idf-sante.js', 'data/sources/epci-gpso.js'],
            'Pays de la Loire': ['data/sources/region-centre.js', 'data/sources/metropole-nantes.js', 'data/sources/communes-pays-loire.js'],
            'Auvergne-Rhône-Alpes': ['data/sources/metropole-lyon.js'],
            'Occitanie': ['data/sources/metropole-toulouse.js'],
            'Nouvelle-Aquitaine': ['data/sources/metropole-bordeaux.js', 'data/sources/pays-basque-2023.js'],
            'Centre-Val de Loire': ['data/sources/region-centre.js', 'data/sources/communes-centre.js']
        };

        return regionMappings[regionName] || [];
    }

    // Find sources for a specific entity type
    function findEntityTypeSources(entityType) {
        const typeMappings = {
            'state': ['data/sources/dilcrah-2024.js', 'data/sources/dilcrah-2025.js', 'data/sources/ministere-agriculture.js'],
            'region': ['data/sources/region-idf.js', 'data/sources/region-centre.js'],
            'epci': ['data/sources/metropole-lyon.js', 'data/sources/metropole-nantes.js', 'data/sources/metropole-toulouse.js', 
                     'data/sources/metropole-bordeaux.js', 'data/sources/agglo-nevers.js', 'data/sources/pays-basque-2023.js',
                     'data/sources/cci-rouen-2024.js', 'data/sources/epci-gpso.js']
        };

        return typeMappings[entityType] || [];
    }

    // Merge data from newly loaded sources into state
    function mergeLoadedData() {
        // Check if new data has been registered via __registerDataSource
        if (typeof window.__DATA_SOURCES !== 'undefined') {
            const newSubventions = [];
            window.__DATA_SOURCES.forEach(source => {
                if (source.data && Array.isArray(source.data)) {
                    newSubventions.push(...source.data);
                }
            });

            if (newSubventions.length > 0) {
                const currentState = State.getState();
                const existingData = currentState.data.allSubventions;
                const mergedData = [...existingData, ...newSubventions];
                
                State.dispatch({
                    type: 'SET_DATA',
                    payload: { allSubventions: mergedData }
                });
            }
        }
    }

    // Load all sources (for initial load or when user wants all data)
    async function loadAllSources() {
        const allSources = [
            'data/sample-data.js',
            'data/sources/plf-jaune-2012.js',
            'data/sources/plf-jaune-2013.js',
            'data/sources/plf-jaune-2014.js',
            'data/sources/plf-jaune-2015.js',
            'data/sources/plf-jaune-2016.js',
            'data/sources/plf-jaune-2017.js',
            'data/sources/plf-jaune-2018.js',
            'data/sources/plf-jaune-2019.js',
            'data/sources/plf-jaune-2020.js',
            'data/sources/plf-jaune-2021.js',
            'data/sources/plf-jaune-2022.js',
            'data/sources/plf-jaune-2025.js',
            'data/sources/paris.js'
            // Add more sources as needed
        ];

        State.dispatch({ type: 'SET_LOADING', payload: true });
        
        try {
            // Load in batches to avoid overwhelming the browser
            const batchSize = 5;
            for (let i = 0; i < allSources.length; i += batchSize) {
                const batch = allSources.slice(i, i + batchSize);
                await Promise.all(batch.map(src => loadScript(src)));
                mergeLoadedData();
            }
        } catch (error) {
            console.error('Error loading all sources:', error);
            State.dispatch({ 
                type: 'SET_ERROR', 
                payload: `Erreur lors du chargement des données: ${error.message}` 
            });
        } finally {
            State.dispatch({ type: 'SET_LOADING', payload: false });
        }
    }

    // Get loading status
    function isLoading() {
        return State.getUI().loading;
    }

    // Get loaded sources count
    function getLoadedSourcesCount() {
        return loadedSources.size;
    }

    return {
        loadScript,
        loadSourcesForFilters,
        loadAllSources,
        isLoading,
        getLoadedSourcesCount,
        mergeLoadedData
    };
})();

export default DataLoader;
