import State from '../state.js';
import Filters from './filters.js';
import MapModule from './map.js';
import Validation from './validation.js';
import Utils from './utils.js';

// Search functionality module
const Search = (function() {
    function debounce(fn, delay) {
        return Utils.debounce(fn, delay);
    }

    function performSearch() {
        const query = document.getElementById('searchInput')?.value || '';
        const validatedQuery = Validation.validateSearchQuery(query);
        
        State.dispatch({
            type: 'SET_FILTER',
            payload: { 
                search: validatedQuery,
                department: null,
                region: null
            }
        });

        // Reset map selection
        document.getElementById('franceMap')?.querySelectorAll('path[data-code]').forEach(p => {
            p.style.stroke = '#fff';
            p.style.strokeWidth = '0.5';
        });

        // Trigger display update
        window.dispatchEvent(new CustomEvent('filterChanged'));
    }

    function initLiveSearch() {
        const input = document.getElementById('searchInput');
        if (!input) return;

        input.addEventListener('input', debounce((e) => {
            const query = Validation.validateSearchQuery(e.target.value);
            State.dispatch({
                type: 'SET_FILTER',
                payload: { 
                    search: query,
                    department: null,
                    region: null
                }
            });

            document.getElementById('franceMap')?.querySelectorAll('path[data-code]').forEach(p => {
                p.style.stroke = '#fff';
                p.style.strokeWidth = '0.5';
            });

            window.dispatchEvent(new CustomEvent('filterChanged'));
        }, 250));
    }

    function initSearchButton() {
        document.getElementById('searchBtn')?.addEventListener('click', performSearch);
    }

    function initAdvancedSearch() {
        // Advanced search fields (RNA, SIRET, custom amount range)
        const rnaInput = document.getElementById('rnaSearch');
        const siretInput = document.getElementById('siretSearch');
        const customMinInput = document.getElementById('customMinAmount');
        const customMaxInput = document.getElementById('customMaxAmount');

        if (rnaInput) {
            rnaInput.addEventListener('input', debounce((e) => {
                // RNA search logic would go here
                // For now, it's part of the general search
            }, 300));
        }

        if (siretInput) {
            siretInput.addEventListener('input', debounce((e) => {
                // SIRET search logic would go here
            }, 300));
        }

        if (customMinInput && customMaxInput) {
            const applyCustomRange = () => {
                const min = parseInt(customMinInput.value) || 0;
                const max = parseInt(customMaxInput.value) || Infinity;
                // Custom range logic would go here
            };
            
            customMinInput.addEventListener('change', applyCustomRange);
            customMaxInput.addEventListener('change', applyCustomRange);
        }
    }

    return {
        performSearch,
        initLiveSearch,
        initSearchButton,
        initAdvancedSearch
    };
})();

export default Search;
