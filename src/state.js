// Centralized state management (Redux-like pattern)
const State = (function() {
    // Initial state
    const initialState = {
        filter: {
            entityType: 'all',
            amountRange: 'all',
            year: 'all',
            search: '',
            department: null,
            region: null,
            mapLevel: 'departments'
        },
        sort: {
            field: 'amount',
            order: 'desc'
        },
        pagination: {
            currentPage: 1,
            pageSize: 50
        },
        ui: {
            theme: localStorage.getItem('theme') || 'light',
            loading: false,
            error: null
        },
        data: {
            allSubventions: [],
            filteredData: [],
            sortedData: []
        }
    };

    let currentState = { ...initialState };
    const listeners = [];

    // Actions
    const actions = {
        SET_FILTER: (state, payload) => ({
            ...state,
            filter: { ...state.filter, ...payload },
            pagination: { ...state.pagination, currentPage: 1 }
        }),
        RESET_FILTERS: (state) => ({
            ...state,
            filter: { ...initialState.filter },
            pagination: { ...state.pagination, currentPage: 1 }
        }),
        SET_SORT: (state, payload) => ({
            ...state,
            sort: { ...state.sort, ...payload }
        }),
        SET_PAGE: (state, payload) => ({
            ...state,
            pagination: { ...state.pagination, currentPage: payload }
        }),
        SET_PAGE_SIZE: (state, payload) => ({
            ...state,
            pagination: { ...state.pagination, pageSize: payload, currentPage: 1 }
        }),
        SET_THEME: (state, payload) => ({
            ...state,
            ui: { ...state.ui, theme: payload }
        }),
        SET_LOADING: (state, payload) => ({
            ...state,
            ui: { ...state.ui, loading: payload }
        }),
        SET_ERROR: (state, payload) => ({
            ...state,
            ui: { ...state.ui, error: payload }
        }),
        SET_DATA: (state, payload) => ({
            ...state,
            data: { ...state.data, ...payload }
        }),
        SET_FILTERED_DATA: (state, payload) => ({
            ...state,
            data: { ...state.data, filteredData: payload }
        }),
        SET_SORTED_DATA: (state, payload) => ({
            ...state,
            data: { ...state.data, sortedData: payload }
        })
    };

    // Reducer
    function reducer(state, action) {
        const handler = actions[action.type];
        if (!handler) {
            console.warn(`Unknown action type: ${action.type}`);
            return state;
        }
        return handler(state, action.payload);
    }

    // Dispatch
    function dispatch(action) {
        currentState = reducer(currentState, action);
        listeners.forEach(listener => listener(currentState));
    }

    // Subscribe
    function subscribe(listener) {
        listeners.push(listener);
        return () => {
            const index = listeners.indexOf(listener);
            if (index > -1) listeners.splice(index, 1);
        };
    }

    // Get current state
    function getState() {
        return currentState;
    }

    // Get specific state slice
    function getFilter() {
        return currentState.filter;
    }

    function getSort() {
        return currentState.sort;
    }

    function getPagination() {
        return currentState.pagination;
    }

    function getUI() {
        return currentState.ui;
    }

    function getData() {
        return currentState.data;
    }

    // Initialize with global data if available
    function initialize() {
        if (typeof ALL_SUBVENTIONS !== 'undefined') {
            dispatch({
                type: 'SET_DATA',
                payload: { allSubventions: ALL_SUBVENTIONS }
            });
        }
    }

    return {
        dispatch,
        subscribe,
        getState,
        getFilter,
        getSort,
        getPagination,
        getUI,
        getData,
        initialize,
        actions
    };
})();

export default State;
