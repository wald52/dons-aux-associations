// Main application entry point - orchestrates all modules
import State from './state.js';
import Filters from './modules/filters.js';
import Sorting from './modules/sorting.js';
import MapModule from './modules/map.js';
import Charts from './modules/charts.js';
import UI from './modules/ui.js';
import Export from './modules/export.js';
import Search from './modules/search.js';
import Theme from './modules/theme.js';
import URLManager from './modules/url-manager.js';
import ErrorHandler from './modules/error-handler.js';

// Initialize dynamic filters (entity types and years)
function initDynamicFilters() {
    const state = State.getState();
    const allSubventions = state.data.allSubventions;
    
    if (!allSubventions || allSubventions.length === 0) {
        console.warn('No data available for dynamic filters');
        return;
    }

    const typeCounts = {};
    const yearSet = new Set();
    
    allSubventions.forEach(s => {
        typeCounts[s.entity.type] = (typeCounts[s.entity.type] || 0) + 1;
        yearSet.add(s.year);
    });

    const entitySelect = document.getElementById('entityType');
    if (entitySelect) {
        const allOpt = entitySelect.querySelector('[value="all"]');
        if (allOpt) allOpt.textContent = `Tous les donateurs (${allSubventions.length})`;
        Array.from(entitySelect.options).forEach(o => { if (o.value !== 'all') o.remove(); });

        Object.entries(typeCounts).forEach(([type, count]) => {
            const opt = document.createElement('option');
            opt.value = type;
            opt.textContent = `${Filters.getEntityTypeLabel(type)} (${count})`;
            entitySelect.appendChild(opt);
        });
    }

    const yearSelect = document.getElementById('yearFilter');
    if (yearSelect) {
        const allYrOpt = yearSelect.querySelector('[value="all"]');
        if (allYrOpt) allYrOpt.textContent = `Toutes les années (${yearSet.size})`;
        Array.from(yearSelect.options).forEach(o => { if (o.value !== 'all') o.remove(); });

        [...yearSet].sort().forEach(year => {
            const opt = document.createElement('option');
            opt.value = String(year);
            opt.textContent = String(year);
            yearSelect.appendChild(opt);
        });
    }
}

// Initialize filter controls
function initControls() {
    document.getElementById('mapLevel')?.addEventListener('change', (e) => {
        MapModule.switchMapLevel(e.target.value);
    });
    
    document.getElementById('entityType')?.addEventListener('change', (e) => {
        Filters.setFilter('entityType', e.target.value);
        UI.displayResults();
    });
    
    document.getElementById('amountRange')?.addEventListener('change', (e) => {
        Filters.setFilter('amountRange', e.target.value);
        UI.displayResults();
    });
    
    document.getElementById('yearFilter')?.addEventListener('change', (e) => {
        Filters.setFilter('year', e.target.value);
        UI.displayResults();
    });
    
    // Sort buttons
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const field = btn.dataset.sort;
            Sorting.toggleSort(field);
            
            // Update UI
            document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const state = State.getState();
            btn.querySelector('.arrow').textContent = state.sort.order === 'asc' ? '↑' : '↓';
            
            UI.displayResults();
        });
    });
    
    // Reset button
    document.getElementById('resetFilters')?.addEventListener('click', () => {
        const wasRegion = State.getFilter().mapLevel === 'regions';
        Filters.resetFilters();
        
        // Reset UI elements
        document.getElementById('searchInput').value = '';
        document.getElementById('entityType').value = 'all';
        document.getElementById('amountRange').value = 'all';
        document.getElementById('yearFilter').value = 'all';
        document.getElementById('mapLevel').value = 'departments';
        
        document.getElementById('franceMap')?.querySelectorAll('path[data-code]').forEach(p => {
            p.style.stroke = '#fff';
            p.style.strokeWidth = '0.5';
        });
        
        if (wasRegion) {
            MapModule.switchMapLevel('departments');
        } else {
            UI.displayResults();
            MapModule.refreshMap();
        }
    });
}

// Listen for filter changes from search module
function setupEventListeners() {
    window.addEventListener('filterChanged', () => {
        UI.displayResults();
    });
}

// Main initialization
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize global error handler
    ErrorHandler.initGlobalErrorHandler();
    
    // Initialize state with global data
    State.initialize();
    
    // Initialize URL manager (may apply filters from URL)
    const hasURLFilters = URLManager.initURLManager();
    
    // Initialize all modules
    initDynamicFilters();
    Theme.initTheme();
    await MapModule.initMap();
    Charts.initCharts();
    Charts.initEvolutionChart();
    UI.initPagination();
    UI.initModal();
    Export.initExport();
    Search.initLiveSearch();
    Search.initSearchButton();
    initControls();
    setupEventListeners();
    
    // Initial data display
    UI.updateCoverage();
    
    // If URL filters were applied, display results after they're applied
    if (hasURLFilters) {
        UI.displayResults();
    } else {
        UI.displayResults();
    }
});
