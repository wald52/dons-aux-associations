import State from '../state.js';
import Validation from './validation.js';

// URL manager for sharing filtered views via URL parameters
const URLManager = (function() {
    const PARAM_KEYS = {
        ENTITY_TYPE: 'entityType',
        AMOUNT_RANGE: 'amountRange',
        YEAR: 'year',
        SEARCH: 'search',
        DEPARTMENT: 'dept',
        REGION: 'region',
        MAP_LEVEL: 'mapLevel',
        PAGE: 'page',
        PAGE_SIZE: 'pageSize',
        SORT_FIELD: 'sortField',
        SORT_ORDER: 'sortOrder'
    };

    // Encode filters to URL parameters
    function encodeFiltersToURL() {
        const filter = State.getFilter();
        const pagination = State.getPagination();
        const sort = State.getSort();
        
        const params = new URLSearchParams();
        
        // Add filter parameters
        if (filter.entityType !== 'all') {
            params.set(PARAM_KEYS.ENTITY_TYPE, filter.entityType);
        }
        if (filter.amountRange !== 'all') {
            params.set(PARAM_KEYS.AMOUNT_RANGE, filter.amountRange);
        }
        if (filter.year !== 'all') {
            params.set(PARAM_KEYS.YEAR, filter.year);
        }
        if (filter.search) {
            params.set(PARAM_KEYS.SEARCH, filter.search);
        }
        if (filter.department) {
            params.set(PARAM_KEYS.DEPARTMENT, filter.department);
        }
        if (filter.region) {
            params.set(PARAM_KEYS.REGION, filter.region);
        }
        if (filter.mapLevel !== 'departments') {
            params.set(PARAM_KEYS.MAP_LEVEL, filter.mapLevel);
        }
        
        // Add pagination parameters
        if (pagination.currentPage > 1) {
            params.set(PARAM_KEYS.PAGE, pagination.currentPage);
        }
        if (pagination.pageSize !== 50) {
            params.set(PARAM_KEYS.PAGE_SIZE, pagination.pageSize);
        }
        
        // Add sort parameters
        if (sort.field !== 'amount') {
            params.set(PARAM_KEYS.SORT_FIELD, sort.field);
        }
        if (sort.order !== 'desc') {
            params.set(PARAM_KEYS.SORT_ORDER, sort.order);
        }
        
        const queryString = params.toString();
        return queryString ? `?${queryString}` : '';
    }

    // Decode URL parameters to filters
    function decodeURLToFilters() {
        const params = new URLSearchParams(window.location.search);
        const filters = {};
        
        // Decode filter parameters
        const entityType = params.get(PARAM_KEYS.ENTITY_TYPE);
        if (entityType && Validation.isValidEntityType(entityType)) {
            filters.entityType = entityType;
        }
        
        const amountRange = params.get(PARAM_KEYS.AMOUNT_RANGE);
        if (amountRange) {
            filters.amountRange = amountRange;
        }
        
        const year = params.get(PARAM_KEYS.YEAR);
        if (year) {
            const yearNum = parseInt(year);
            if (!isNaN(yearNum) && yearNum >= 1900 && yearNum <= 2100) {
                filters.year = year;
            }
        }
        
        const search = params.get(PARAM_KEYS.SEARCH);
        if (search) {
            filters.search = Validation.validateSearchQuery(search);
        }
        
        const department = params.get(PARAM_KEYS.DEPARTMENT);
        if (department && Validation.isValidDepartmentCode(department)) {
            filters.department = department;
        }
        
        const region = params.get(PARAM_KEYS.REGION);
        if (region) {
            const validRegions = ['84', '27', '53', '24', '94', '44', '32', '11', '28', '75', '76', '52', '93'];
            if (validRegions.includes(region)) {
                filters.region = region;
            }
        }
        
        const mapLevel = params.get(PARAM_KEYS.MAP_LEVEL);
        if (mapLevel === 'regions' || mapLevel === 'departments') {
            filters.mapLevel = mapLevel;
        }
        
        // Decode pagination parameters
        const page = params.get(PARAM_KEYS.PAGE);
        const pageSize = params.get(PARAM_KEYS.PAGE_SIZE);
        
        // Decode sort parameters
        const sortField = params.get(PARAM_KEYS.SORT_FIELD);
        const sortOrder = params.get(PARAM_KEYS.SORT_ORDER);
        
        return {
            filters,
            pagination: {
                page: page ? parseInt(page) : 1,
                pageSize: pageSize ? parseInt(pageSize) : 50
            },
            sort: {
                field: sortField || 'amount',
                order: sortOrder || 'desc'
            }
        };
    }

    // Update URL without reloading the page
    function updateURL() {
        const queryString = encodeFiltersToURL();
        const newURL = `${window.location.pathname}${queryString}`;
        window.history.replaceState(null, '', newURL);
    }

    // Apply filters from URL on page load
    function applyURLFilters() {
        const { filters, pagination, sort } = decodeURLToFilters();
        
        if (Object.keys(filters).length > 0) {
            State.dispatch({
                type: 'SET_FILTER',
                payload: filters
            });
        }
        
        if (pagination.page > 1) {
            State.dispatch({
                type: 'SET_PAGE',
                payload: pagination.page
            });
        }
        
        if (pagination.pageSize !== 50) {
            State.dispatch({
                type: 'SET_PAGE_SIZE',
                payload: pagination.pageSize
            });
        }
        
        if (sort.field !== 'amount' || sort.order !== 'desc') {
            State.dispatch({
                type: 'SET_SORT',
                payload: sort
            });
        }
        
        return Object.keys(filters).length > 0;
    }

    // Copy current view URL to clipboard
    function copyCurrentURL() {
        const url = window.location.href;
        
        navigator.clipboard.writeText(url).then(() => {
            showCopySuccess();
        }).catch(err => {
            console.error('Failed to copy URL:', err);
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                showCopySuccess();
            } catch (e) {
                console.error('Fallback copy failed:', e);
            }
            document.body.removeChild(textArea);
        });
    }

    // Show success message for URL copy
    function showCopySuccess() {
        // Remove existing toast
        const existing = document.querySelector('.copy-toast');
        if (existing) existing.remove();
        
        const toast = document.createElement('div');
        toast.className = 'copy-toast';
        toast.textContent = '✓ Lien copié dans le presse-papier';
        
        // Add styles if not present
        if (!document.querySelector('#copy-toast-styles')) {
            const style = document.createElement('style');
            style.id = 'copy-toast-styles';
            style.textContent = `
                .copy-toast {
                    position: fixed;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #66bb6a;
                    color: white;
                    padding: 0.75rem 1.5rem;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    z-index: 10000;
                    animation: fadeIn 0.3s ease;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateX(-50%) translateY(20px); }
                    to { opacity: 1; transform: translateX(-50%) translateY(0); }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }

    // Initialize URL manager
    function initURLManager() {
        // Apply URL filters on load
        const hasURLFilters = applyURLFilters();
        
        // Listen for state changes to update URL
        State.subscribe((state) => {
            updateURL();
        });
        
        // Add copy URL button if it doesn't exist
        const exportBtn = document.getElementById('exportCsv');
        if (exportBtn && !document.getElementById('copyUrlBtn')) {
            const copyBtn = document.createElement('button');
            copyBtn.id = 'copyUrlBtn';
            copyBtn.className = 'export-btn';
            copyBtn.title = 'Copier le lien de cette vue';
            copyBtn.textContent = '🔗 Copier le lien';
            copyBtn.style.marginLeft = '0.5rem';
            copyBtn.addEventListener('click', copyCurrentURL);
            exportBtn.parentNode.insertBefore(copyBtn, exportBtn.nextSibling);
        }
        
        return hasURLFilters;
    }

    return {
        PARAM_KEYS,
        encodeFiltersToURL,
        decodeURLToFilters,
        updateURL,
        applyURLFilters,
        copyCurrentURL,
        initURLManager
    };
})();

export default URLManager;
