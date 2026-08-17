import State from '../state.js';
import Filters from './filters.js';

// Sorting logic module
const Sorting = (function() {
    function sortData(data) {
        const state = State.getState();
        const { field, order } = state.sort;
        const sorted = [...data];
        
        sorted.sort((a, b) => {
            let valA, valB;
            switch (field) {
                case 'amount':
                    valA = a.amount;
                    valB = b.amount;
                    break;
                case 'name':
                    valA = a.association.name.toLowerCase();
                    valB = b.association.name.toLowerCase();
                    break;
                case 'year':
                    valA = a.year;
                    valB = b.year;
                    break;
                case 'department':
                    valA = parseInt(a.association.department) || 0;
                    valB = parseInt(b.association.department) || 0;
                    break;
                case 'entityType':
                    valA = Filters.getEntityTypeLabel(a.entity.type);
                    valB = Filters.getEntityTypeLabel(b.entity.type);
                    break;
                default:
                    valA = a.amount;
                    valB = b.amount;
            }
            const cmp = valA < valB ? -1 : valA > valB ? 1 : 0;
            return order === 'asc' ? cmp : -cmp;
        });
        
        return sorted;
    }

    function setSort(field, order) {
        State.dispatch({
            type: 'SET_SORT',
            payload: { field, order }
        });
    }

    function toggleSort(field) {
        const state = State.getState();
        const currentField = state.sort.field;
        
        if (currentField === field) {
            // Toggle order if same field
            const newOrder = state.sort.order === 'asc' ? 'desc' : 'asc';
            setSort(field, newOrder);
        } else {
            // Set new field with default order
            const defaultOrder = field === 'amount' ? 'desc' : 'asc';
            setSort(field, defaultOrder);
        }
    }

    function applySort(data = null) {
        const dataToSort = data || State.getState().data.filteredData;
        const sorted = sortData(dataToSort);
        State.dispatch({
            type: 'SET_SORTED_DATA',
            payload: sorted
        });
        return sorted;
    }

    return {
        sortData,
        setSort,
        toggleSort,
        applySort
    };
})();

export default Sorting;
