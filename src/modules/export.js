import State from '../state.js';
import Filters from './filters.js';

// Export functionality module
const Export = (function() {
    function escapeCsvValue(value) {
        if (value === null || value === undefined) return '';
        const stringValue = String(value);
        return `"${stringValue.replace(/"/g, '""')}"`;
    }

    function exportCsv() {
        const state = State.getState();
        const sorted = state.data.sortedData;
        
        if (sorted.length === 0) return;

        const headers = ['Association', 'RNA', 'SIRET', 'Objet', 'Département', 'Entité donatrice', 'Type', 'Montant', 'Année', 'Programme', 'Convention', 'Justification', 'Source'];
        const rows = sorted.map(s => [
            s.association.name,
            s.association.rna || '',
            s.association.siret || '',
            s.association.object || '',
            s.association.department,
            s.entity.name,
            Filters.getEntityTypeLabel(s.entity.type),
            s.amount,
            s.year,
            s.program || '',
            s.convention ? 'Oui' : 'Non',
            s.justification || '',
            s.source
        ].map(escapeCsvValue).join(','));

        const csv = '\uFEFF' + headers.join(',') + '\n' + rows.join('\n');
        downloadFile(csv, `subventions-${new Date().toISOString().slice(0, 10)}.csv`, 'text/csv;charset=utf-8;');
    }

    function exportJson() {
        const state = State.getState();
        const sorted = state.data.sortedData;
        const filter = state.filter;
        
        if (sorted.length === 0) return;

        const exportData = {
            metadata: {
                exportDate: new Date().toISOString(),
                totalResults: sorted.length,
                filters: {
                    entityType: filter.entityType,
                    amountRange: filter.amountRange,
                    year: filter.year,
                    search: filter.search,
                    department: filter.department,
                    region: filter.region,
                    mapLevel: filter.mapLevel
                }
            },
            data: sorted.map(s => ({
                association: {
                    name: s.association.name,
                    rna: s.association.rna || null,
                    siret: s.association.siret || null,
                    object: s.association.object || null,
                    address: s.association.address || null,
                    department: s.association.department
                },
                entity: {
                    name: s.entity.name,
                    type: s.entity.type,
                    level: s.entity.level || null,
                    program: s.program || null
                },
                amount: s.amount,
                year: s.year,
                convention: s.convention,
                justification: s.justification || null,
                source: s.source
            }))
        };

        const json = JSON.stringify(exportData, null, 2);
        downloadFile(json, `subventions-${new Date().toISOString().slice(0, 10)}.json`, 'application/json');
    }

    function downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
        URL.revokeObjectURL(link.href);
    }

    function initExport() {
        document.getElementById('exportCsv')?.addEventListener('click', exportCsv);
        
        // Add JSON export button if it doesn't exist
        const exportBtn = document.getElementById('exportCsv');
        if (exportBtn && !document.getElementById('exportJson')) {
            const jsonBtn = document.createElement('button');
            jsonBtn.id = 'exportJson';
            jsonBtn.className = 'export-btn';
            jsonBtn.title = 'Exporter en JSON';
            jsonBtn.textContent = '📄 Export JSON';
            jsonBtn.style.marginLeft = '0.5rem';
            exportBtn.parentNode.insertBefore(jsonBtn, exportBtn.nextSibling);
            jsonBtn.addEventListener('click', exportJson);
        }
    }

    return {
        exportCsv,
        exportJson,
        initExport
    };
})();

export default Export;
