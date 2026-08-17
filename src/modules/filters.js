import State from '../state.js';
import Validation from './validation.js';

// Filter logic module
const Filters = (function() {
    const ENTITY_TYPE_LABELS = {
        state: 'État',
        region: 'Région',
        department: 'Département',
        commune: 'Commune',
        epci: 'EPCI'
    };

    function getEntityTypeLabel(type) {
        return ENTITY_TYPE_LABELS[type] || type;
    }

    function getFilteredData() {
        const state = State.getState();
        const { allSubventions } = state.data;
        const filter = state.filter;

        return allSubventions.filter(s => {
            // Department filter
            if (filter.department && s.association.department !== filter.department) {
                return false;
            }

            // Region filter
            if (filter.region) {
                const depInfo = typeof DEPARTMENTS !== 'undefined' ? DEPARTMENTS[s.association.department] : null;
                const regionName = typeof REGION_INFO !== 'undefined' ? REGION_INFO[filter.region]?.name : null;
                if (!depInfo || !regionName || depInfo.region !== regionName) {
                    return false;
                }
            }

            // Entity type filter
            if (filter.entityType !== 'all' && s.entity.type !== filter.entityType) {
                return false;
            }

            // Year filter
            if (filter.year !== 'all' && s.year !== parseInt(filter.year)) {
                return false;
            }

            // Amount range filter
            if (filter.amountRange !== 'all') {
                const [min, max] = filter.amountRange.split('-').map(v => 
                    v === '500000+' ? Infinity : parseInt(v)
                );
                if (s.amount < min || s.amount > max) {
                    return false;
                }
            }

            // Search filter
            if (filter.search) {
                const search = filter.search.toLowerCase();
                const matchAssoc = s.association.name.toLowerCase().includes(search) ||
                                 (s.association.object && s.association.object.toLowerCase().includes(search));
                const matchEntity = s.entity.name.toLowerCase().includes(search);
                if (!matchAssoc && !matchEntity) {
                    return false;
                }
            }

            return true;
        });
    }

    function applyFilters() {
        const filtered = getFilteredData();
        State.dispatch({
            type: 'SET_FILTERED_DATA',
            payload: filtered
        });
        return filtered;
    }

    function setFilter(key, value) {
        // Validate the filter value before setting it
        const currentFilter = State.getFilter();
        const tempFilters = { ...currentFilter, [key]: value };
        const validation = Validation.validateFilters(tempFilters);
        
        if (!validation.valid) {
            console.warn('Filter validation failed:', validation.errors);
            // Use sanitized values
            State.dispatch({
                type: 'SET_FILTER',
                payload: { [key]: validation.sanitized[key] }
            });
        } else {
            State.dispatch({
                type: 'SET_FILTER',
                payload: { [key]: value }
            });
        }
    }

    function resetFilters() {
        State.dispatch({ type: 'RESET_FILTERS' });
    }

    return {
        getFilteredData,
        applyFilters,
        setFilter,
        resetFilters,
        getEntityTypeLabel
    };
})();

export default Filters;
