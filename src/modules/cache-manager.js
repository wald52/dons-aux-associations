// LocalStorage cache manager for data and user preferences
const CacheManager = (function() {
    const CACHE_PREFIX = 'subventions_';
    const CACHE_VERSION = 'v1';
    const CACHE_KEYS = {
        DATA: 'data',
        FILTERS: 'filters',
        PREFERENCES: 'preferences',
        LOADED_SOURCES: 'loaded_sources'
    };

    // Get full cache key with prefix and version
    function getCacheKey(key) {
        return `${CACHE_PREFIX}${CACHE_VERSION}_${key}`;
    }

    // Save data to cache
    function saveData(key, data, ttl = 24 * 60 * 60 * 1000) {
        try {
            const cacheItem = {
                data: data,
                timestamp: Date.now(),
                ttl: ttl
            };
            localStorage.setItem(getCacheKey(key), JSON.stringify(cacheItem));
            return true;
        } catch (error) {
            console.warn('Failed to save to cache:', error);
            return false;
        }
    }

    // Load data from cache
    function loadData(key) {
        try {
            const cached = localStorage.getItem(getCacheKey(key));
            if (!cached) return null;

            const cacheItem = JSON.parse(cached);
            
            // Check if cache is expired
            if (Date.now() - cacheItem.timestamp > cacheItem.ttl) {
                removeData(key);
                return null;
            }

            return cacheItem.data;
        } catch (error) {
            console.warn('Failed to load from cache:', error);
            return null;
        }
    }

    // Remove data from cache
    function removeData(key) {
        try {
            localStorage.removeItem(getCacheKey(key));
            return true;
        } catch (error) {
            console.warn('Failed to remove from cache:', error);
            return false;
        }
    }

    // Clear all cache
    function clearCache() {
        try {
            Object.keys(localStorage).forEach(key => {
                if (key.startsWith(CACHE_PREFIX)) {
                    localStorage.removeItem(key);
                }
            });
            return true;
        } catch (error) {
            console.warn('Failed to clear cache:', error);
            return false;
        }
    }

    // Save current filters to cache
    function saveFilters(filters) {
        return saveData(CACHE_KEYS.FILTERS, filters, 7 * 24 * 60 * 60 * 1000); // 7 days TTL
    }

    // Load filters from cache
    function loadFilters() {
        return loadData(CACHE_KEYS.FILTERS);
    }

    // Save user preferences
    function savePreferences(preferences) {
        return saveData(CACHE_KEYS.PREFERENCES, preferences, 30 * 24 * 60 * 60 * 1000); // 30 days TTL
    }

    // Load user preferences
    function loadPreferences() {
        return loadData(CACHE_KEYS.PREFERENCES);
    }

    // Save list of loaded sources
    function saveLoadedSources(sources) {
        return saveData(CACHE_KEYS.LOADED_SOURCES, sources, 24 * 60 * 60 * 1000); // 24 hours TTL
    }

    // Load list of loaded sources
    function loadLoadedSources() {
        return loadData(CACHE_KEYS.LOADED_SOURCES);
    }

    // Cache filtered data results
    function cacheFilteredResult(cacheKey, filteredData) {
        return saveData(`filtered_${cacheKey}`, filteredData, 5 * 60 * 1000); // 5 minutes TTL
    }

    // Get cached filtered data
    function getCachedFilteredResult(cacheKey) {
        return loadData(`filtered_${cacheKey}`);
    }

    // Get cache size in bytes
    function getCacheSize() {
        let size = 0;
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith(CACHE_PREFIX)) {
                size += localStorage.getItem(key).length * 2; // UTF-16 uses 2 bytes per character
            }
        });
        return size;
    }

    // Get cache size in human-readable format
    function getCacheSizeFormatted() {
        const bytes = getCacheSize();
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    }

    // Check if cache is available
    function isCacheAvailable() {
        try {
            const testKey = '__cache_test__';
            localStorage.setItem(testKey, 'test');
            localStorage.removeItem(testKey);
            return true;
        } catch (error) {
            return false;
        }
    }

    return {
        CACHE_KEYS,
        saveData,
        loadData,
        removeData,
        clearCache,
        saveFilters,
        loadFilters,
        savePreferences,
        loadPreferences,
        saveLoadedSources,
        loadLoadedSources,
        cacheFilteredResult,
        getCachedFilteredResult,
        getCacheSize,
        getCacheSizeFormatted,
        isCacheAvailable
    };
})();

export default CacheManager;
