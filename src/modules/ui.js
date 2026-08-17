import State from '../state.js';
import Filters from './filters.js';
import Sorting from './sorting.js';
import MapModule from './map.js';
import Charts from './charts.js';
import Validation from './validation.js';
import Utils from './utils.js';

// UI interactions module
const UI = (function() {
    function formatAmount(amount) {
        return Utils.formatAmount(amount);
    }

    function updateStats() {
        const state = State.getState();
        const filtered = state.data.filteredData;
        
        const totalAmount = filtered.reduce((sum, s) => sum + s.amount, 0);
        const uniqueAssociations = new Set(filtered.map(s => s.association.name)).size;
        const uniqueEntities = new Set(filtered.map(s => s.entity.name)).size;
        const totalSubventions = filtered.length;
        const uniqueYears = new Set(filtered.map(s => s.year)).size;

        const totalAmountEl = document.getElementById('totalAmount');
        const totalAssociationsEl = document.getElementById('totalAssociations');
        const totalEntitiesEl = document.getElementById('totalEntities');
        const totalSubventionsEl = document.getElementById('totalSubventions');
        const totalYearsEl = document.getElementById('totalYears');

        if (totalAmountEl) totalAmountEl.textContent = formatAmount(totalAmount);
        if (totalAssociationsEl) totalAssociationsEl.textContent = uniqueAssociations;
        if (totalEntitiesEl) totalEntitiesEl.textContent = uniqueEntities;
        if (totalSubventionsEl) totalSubventionsEl.textContent = totalSubventions.toLocaleString('fr-FR');
        if (totalYearsEl) totalYearsEl.textContent = uniqueYears;
    }

    function updateCoverage() {
        const state = State.getState();
        const allSubventions = state.data.allSubventions;
        
        const bar = document.getElementById('coverageBar');
        if (!bar) return;
        
        const types = {};
        const sources = new Set();
        const years = new Set();

        allSubventions.forEach(s => {
            types[s.entity.type] = (types[s.entity.type] || 0) + 1;
            sources.add(s.source);
            years.add(s.year);
        });

        const ENTITY_TYPE_LABELS = {
            state: 'État',
            region: 'Région',
            department: 'Département',
            commune: 'Commune',
            epci: 'EPCI'
        };

        const allTypes = ['state', 'region', 'department', 'commune', 'epci'];
        let html = '<span class="coverage-label">Couverture :</span>';

        allTypes.forEach(type => {
            const count = types[type] || 0;
            const available = count > 0;
            html += `<span class="coverage-badge ${available ? 'available' : 'unavailable'}">
                ${available ? '✓' : '✗'} ${ENTITY_TYPE_LABELS[type]}
                ${available ? `(${count})` : ''}
            </span>`;
        });

        html += `<span class="coverage-badge">📅 ${years.size} an${years.size > 1 ? 's' : ''}</span>`;
        html += `<span class="coverage-badge">📚 ${sources.size} source${sources.size > 1 ? 's' : ''}</span>`;
        html += `<span class="coverage-badge">📊 ${allSubventions.length} ligne${allSubventions.length > 1 ? 's' : ''}</span>`;

        bar.innerHTML = html;
    }

    function renderCurrentPage() {
        const state = State.getState();
        const sorted = state.data.sortedData;
        const pagination = state.pagination;
        
        const list = document.getElementById('resultsList');
        const paginationEl = document.getElementById('pagination');
        const totalPages = Math.ceil(sorted.length / pagination.pageSize) || 1;

        if (!list) return;

        if (sorted.length === 0) {
            list.innerHTML = '<p class="placeholder">Aucun résultat trouvé</p>';
            if (paginationEl) paginationEl.style.display = 'none';
            return;
        }

        if (sorted.length <= pagination.pageSize) {
            if (paginationEl) paginationEl.style.display = 'none';
        } else {
            if (paginationEl) paginationEl.style.display = 'flex';
            
            const prevBtn = document.getElementById('prevPage');
            const nextBtn = document.getElementById('nextPage');
            const pageInfo = document.getElementById('pageInfo');
            
            if (prevBtn) prevBtn.disabled = pagination.currentPage <= 1;
            if (nextBtn) nextBtn.disabled = pagination.currentPage >= totalPages;
            if (pageInfo) pageInfo.textContent = `Page ${pagination.currentPage} / ${totalPages} (${sorted.length} résultats)`;
        }

        const start = (pagination.currentPage - 1) * pagination.pageSize;
        const pageItems = sorted.slice(start, start + pagination.pageSize);

        list.innerHTML = pageItems.map(s => {
            const deptInfo = typeof DEPARTMENTS !== 'undefined' ? DEPARTMENTS[s.association.department] : null;
            const entityLabel = Filters.getEntityTypeLabel(s.entity.type);
            return `<div class="result-item" onclick="window.showDetail('${s.id}')" onkeydown="if(event.key==='Enter'||event.key===' ')event.preventDefault(),window.showDetail('${s.id}')" tabindex="0" role="button" aria-label="Détails de ${s.association.name}">
                <div class="result-header">
                    <span class="result-name">${escapeHtml(s.association.name)}</span>
                    <span class="result-amount">${formatAmount(s.amount)}</span>
                </div>
                <div class="result-meta">${escapeHtml(s.association.object || '')}</div>
                <div class="result-donors">
                    <span class="result-entity-label">Donateur :</span>
                    <span class="result-entity">${escapeHtml(s.entity.name)}</span>
                    <span class="result-entity-type">${entityLabel}</span>
                    <span class="result-entity">${s.year}</span>
                    <span class="result-entity">${s.association.department} - ${deptInfo ? deptInfo.name : ''}</span>
                </div>
            </div>`;
        }).join('');
    }

    function escapeHtml(text) {
        return Utils.escapeHtml(text);
    }

    function showDetail(id) {
        const state = State.getState();
        const subvention = state.data.allSubventions.find(s => s.id === id);
        if (!subvention) return;
        
        const modal = document.getElementById('detailModal');
        const body = document.getElementById('modalBody');
        if (!modal || !body) return;
        
        const deptInfo = typeof DEPARTMENTS !== 'undefined' ? DEPARTMENTS[subvention.association.department] : {};

        body.innerHTML = `
            <div class="detail-section">
                <h3>Bénéficiaire — Association</h3>
                <div class="detail-row"><span class="detail-label">Nom</span><span class="detail-value">${escapeHtml(subvention.association.name)}</span></div>
                <div class="detail-row"><span class="detail-label">RNA</span><span class="detail-value">${escapeHtml(subvention.association.rna || 'N/A')}</span></div>
                <div class="detail-row"><span class="detail-label">SIRET</span><span class="detail-value">${escapeHtml(subvention.association.siret || 'N/A')}</span></div>
                <div class="detail-row"><span class="detail-label">Objet</span><span class="detail-value">${escapeHtml(subvention.association.object || 'N/A')}</span></div>
                <div class="detail-row"><span class="detail-label">Localisation</span><span class="detail-value">${subvention.association.department} - ${deptInfo.name || 'N/A'} (${deptInfo.region || 'N/A'})</span></div>
            </div>
            <div class="detail-section">
                <h3>Donateur — Entité publique</h3>
                <div class="detail-row"><span class="detail-label">Nom</span><span class="detail-value">${escapeHtml(subvention.entity.name)}</span></div>
                <div class="detail-row"><span class="detail-label">Type</span><span class="detail-value">${escapeHtml(Filters.getEntityTypeLabel(subvention.entity.type))}</span></div>
                <div class="detail-row"><span class="detail-label">Niveau</span><span class="detail-value">${escapeHtml(subvention.entity.level || 'N/A')}</span></div>
            </div>
            <div class="detail-section">
                <h3>Détails de la subvention</h3>
                <div class="detail-row"><span class="detail-label">Montant</span><span class="detail-value amount">${formatAmount(subvention.amount)}</span></div>
                <div class="detail-row"><span class="detail-label">Année</span><span class="detail-value">${subvention.year}</span></div>
                <div class="detail-row"><span class="detail-label">Programme</span><span class="detail-value">${escapeHtml(subvention.program || 'N/A')}</span></div>
                <div class="detail-row"><span class="detail-label">Convention</span><span class="detail-value">${subvention.convention ? 'Oui (obligatoire > 23 000 €)' : 'Non'}</span></div>
                <div class="detail-row"><span class="detail-label">Justification</span><span class="detail-value">${escapeHtml(subvention.justification || 'N/A')}</span></div>
            </div>
            <div class="detail-section">
                <h3>Source officielle</h3>
                <a href="${escapeHtml(subvention.source)}" target="_blank" rel="noopener" class="source-link">Consulter la source →</a>
            </div>`;

        modal.classList.add('active');
        modal.focus();
        modal._cleanupFocus = focusTrapModal(modal);
    }

    function focusTrapModal(modal) {
        const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        function handler(e) {
            if (e.key !== 'Tab') return;
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }

        modal.addEventListener('keydown', handler);
        if (first) setTimeout(() => first.focus(), 50);
        return () => modal.removeEventListener('keydown', handler);
    }

    function closeModal() {
        const modal = document.getElementById('detailModal');
        if (!modal) return;
        
        modal.classList.remove('active');
        if (modal._cleanupFocus) {
            modal._cleanupFocus();
            modal._cleanupFocus = null;
        }
    }

    function updateResultsCount() {
        const state = State.getState();
        const countEl = document.getElementById('resultsCount');
        const subtitleEl = document.getElementById('resultsSubtitle');
        const filter = state.filter;
        
        if (countEl) countEl.textContent = state.data.sortedData.length;
        
        if (subtitleEl) {
            if (filter.department) {
                const dept = typeof DEPARTMENTS !== 'undefined' ? DEPARTMENTS[filter.department] : null;
                subtitleEl.textContent = `— ${dept ? dept.name : filter.department}`;
            } else if (filter.region) {
                const reg = typeof REGION_INFO !== 'undefined' ? REGION_INFO[filter.region] : null;
                subtitleEl.textContent = `— ${reg ? reg.name : filter.region}`;
            } else if (filter.search) {
                subtitleEl.textContent = `— Recherche : "${filter.search}"`;
            } else {
                subtitleEl.textContent = '';
            }
        }
    }

    function displayResults() {
        State.dispatch({ type: 'SET_PAGE', payload: 1 });
        
        Filters.applyFilters();
        Sorting.applySort();
        
        updateStats();
        Charts.refreshAllCharts();
        MapModule.refreshMap();
        updateResultsCount();
        renderCurrentPage();
    }

    function initPagination() {
        document.getElementById('prevPage')?.addEventListener('click', () => {
            const state = State.getState();
            const total = state.data.sortedData.length;
            if (state.pagination.currentPage > 1) {
                State.dispatch({
                    type: 'SET_PAGE',
                    payload: state.pagination.currentPage - 1
                });
                renderCurrentPage();
            }
        });

        document.getElementById('nextPage')?.addEventListener('click', () => {
            const state = State.getState();
            const total = state.data.sortedData.length;
            if (state.pagination.currentPage * state.pagination.pageSize < total) {
                State.dispatch({
                    type: 'SET_PAGE',
                    payload: state.pagination.currentPage + 1
                });
                renderCurrentPage();
            }
        });

        // Add page size selector if it doesn't exist
        const paginationEl = document.getElementById('pagination');
        if (paginationEl && !document.getElementById('pageSizeSelector')) {
            const selector = document.createElement('select');
            selector.id = 'pageSizeSelector';
            selector.className = 'page-size-selector';
            selector.title = 'Nombre de résultats par page';
            
            const pageSizes = [25, 50, 100, 200];
            pageSizes.forEach(size => {
                const option = document.createElement('option');
                option.value = size;
                option.textContent = `${size} par page`;
                if (size === 50) option.selected = true;
                selector.appendChild(option);
            });

            selector.addEventListener('change', (e) => {
                const pageSize = parseInt(e.target.value);
                State.dispatch({
                    type: 'SET_PAGE_SIZE',
                    payload: pageSize
                });
                
                // Save preference to localStorage
                localStorage.setItem('pageSize', pageSize);
                
                renderCurrentPage();
            });

            // Load saved preference
            const savedPageSize = localStorage.getItem('pageSize');
            if (savedPageSize) {
                selector.value = savedPageSize;
                State.dispatch({
                    type: 'SET_PAGE_SIZE',
                    payload: parseInt(savedPageSize)
                });
            }

            paginationEl.insertBefore(selector, paginationEl.firstChild);
        }
    }

    function initModal() {
        document.querySelector('.close-modal')?.addEventListener('click', closeModal);
        document.getElementById('detailModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'detailModal') closeModal();
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        });
    }

    // Expose showDetail globally for onclick handlers
    window.showDetail = showDetail;

    return {
        updateStats,
        updateCoverage,
        renderCurrentPage,
        showDetail,
        closeModal,
        displayResults,
        initPagination,
        initModal
    };
})();

export default UI;
