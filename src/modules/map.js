import State from '../state.js';
import Utils from './utils.js';

// Map management module
const MapModule = (function() {
    const SVG_PATHS = {
        departments: 'data/svg/departements-2024.svg',
        regions: 'data/svg/regions-2024.svg'
    };

    const REGION_INFO = {
        '84': { name: 'Auvergne-Rhône-Alpes' },
        '27': { name: 'Bourgogne-Franche-Comté' },
        '53': { name: 'Bretagne' },
        '24': { name: 'Centre-Val de Loire' },
        '94': { name: 'Corse' },
        '44': { name: 'Grand Est' },
        '32': { name: 'Hauts-de-France' },
        '11': { name: 'Île-de-France' },
        '28': { name: 'Normandie' },
        '75': { name: 'Nouvelle-Aquitaine' },
        '76': { name: 'Occitanie' },
        '52': { name: 'Pays de la Loire' },
        '93': { name: "Provence-Alpes-Côte d'Azur" }
    };

    const MAP_COLORS = ['#e8f5e9', '#c8e6c9', '#a5d6a7', '#66bb6a', '#388e3c', '#1b5e20'];
    let colorBins = [];

    async function loadMapSVG(level) {
        const svg = document.getElementById('franceMap');
        const container = svg?.parentElement;
        const loading = document.getElementById('mapLoading');
        
        if (loading) loading.style.display = 'block';

        try {
            const response = await fetch(SVG_PATHS[level]);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const text = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'image/svg+xml');
            let newSvg = doc.querySelector('svg');
            
            if (newSvg) {
                newSvg.removeAttribute('width');
                newSvg.removeAttribute('height');
                newSvg.id = 'franceMap';
                container.replaceChild(newSvg, svg);
                if (loading) loading.style.display = 'none';
                return newSvg;
            }
        } catch (e) {
            console.warn(`Failed to load ${level} SVG:`, e);
        }
        
        if (loading) loading.style.display = 'none';
        return document.getElementById('franceMap');
    }

    function initMapPaths(svg, level) {
        if (level === 'departments' && typeof DEPARTMENTS !== 'undefined') {
            Object.entries(DEPARTMENTS).forEach(([code, info]) => {
                const svgId = code === '2A' ? 'dep_2a' : code === '2B' ? 'dep_2b' : `dep_${code.padStart(2, '0')}`;
                const existingPath = svg.getElementById(svgId);
                if (existingPath) {
                    existingPath.dataset.code = code;
                    existingPath.dataset.name = info.name;
                    existingPath.dataset.region = info.region;
                    existingPath.addEventListener('mouseenter', (e) => showTooltip(e, code, info));
                    existingPath.addEventListener('mouseleave', hideTooltip);
                    existingPath.addEventListener('click', () => selectDepartment(code));
                }
            });
        } else if (level === 'regions') {
            const paths = svg.querySelectorAll('path[id^="reg_"]');
            paths.forEach(path => {
                const code = path.id.replace('reg_', '');
                path.dataset.code = code;
                const info = REGION_INFO[code];
                if (info) {
                    path.dataset.name = info.name;
                    path.addEventListener('mouseenter', (e) => showRegionTooltip(e, code, info));
                    path.addEventListener('mouseleave', hideTooltip);
                    path.addEventListener('click', () => selectRegion(code));
                }
            });
        }
    }

    function getDepartmentSubventions(code) {
        const state = State.getState();
        return state.data.filteredData.filter(s => s.association.department === code);
    }

    function getDepartmentTotal(code) {
        return getDepartmentSubventions(code).reduce((sum, s) => sum + s.amount, 0);
    }

    function getDepartmentCount(code) {
        return getDepartmentSubventions(code).length;
    }

    function getRegionDeps(code) {
        const regionName = REGION_INFO[code]?.name;
        if (!regionName || typeof DEPARTMENTS === 'undefined') return [];
        return Object.entries(DEPARTMENTS)
            .filter(([_, info]) => info.region === regionName)
            .map(([code]) => code);
    }

    function getRegionSubventions(code) {
        const deps = getRegionDeps(code);
        const state = State.getState();
        return state.data.filteredData.filter(s => deps.includes(s.association.department));
    }

    function getRegionTotal(code) {
        return getRegionSubventions(code).reduce((sum, s) => sum + s.amount, 0);
    }

    function getRegionCount(code) {
        return getRegionSubventions(code).length;
    }

    function computeColorBins() {
        const state = State.getState();
        const level = state.filter.mapLevel;
        const totals = [];

        if (level === 'departments' && typeof DEPARTMENTS !== 'undefined') {
            Object.keys(DEPARTMENTS).forEach(code => {
                totals.push(getDepartmentTotal(code));
            });
        } else {
            Object.keys(REGION_INFO).forEach(code => {
                totals.push(getRegionTotal(code));
            });
        }

        const nonZero = totals.filter(t => t > 0);
        if (nonZero.length === 0) {
            colorBins = [];
            return;
        }

        const min = Math.min(...nonZero);
        const max = Math.max(...nonZero);
        if (min === max) {
            colorBins = [min * 0.5, min, max * 1.5];
            return;
        }

        const logMin = Math.log10(Math.max(min, 1));
        const logMax = Math.log10(Math.max(max, 1));
        const step = (logMax - logMin) / 5;

        colorBins = [];
        for (let i = 0; i < 5; i++) {
            colorBins.push(Math.pow(10, logMin + i * step));
        }
    }

    function getColorForAmount(amount) {
        if (amount === 0) return '#8ad';
        if (colorBins.length === 0) return MAP_COLORS[0];

        for (let i = colorBins.length - 1; i >= 0; i--) {
            if (amount >= colorBins[i]) return MAP_COLORS[i];
        }
        return MAP_COLORS[0];
    }

    function colorMapBySubventions() {
        const state = State.getState();
        const level = state.filter.mapLevel;
        const svg = document.getElementById('franceMap');
        if (!svg) return;

        if (level === 'departments' && typeof DEPARTMENTS !== 'undefined') {
            Object.entries(DEPARTMENTS).forEach(([code]) => {
                const svgId = code === '2A' ? 'dep_2a' : code === '2B' ? 'dep_2b' : `dep_${code.padStart(2, '0')}`;
                const path = svg.getElementById(svgId);
                if (path) {
                    path.style.fill = getColorForAmount(getDepartmentTotal(code));
                }
            });
        } else if (level === 'regions') {
            Object.keys(REGION_INFO).forEach(code => {
                const path = svg.querySelector(`path[data-code="${code}"]`);
                if (path) {
                    path.style.fill = getColorForAmount(getRegionTotal(code));
                }
            });
        }
    }

    function updateLegend() {
        const legend = document.getElementById('mapLegend');
        if (!legend) return;
        
        let html = `<h3>Total des subventions reçues</h3>`;
        html += `<div class="legend-item"><span class="color-box" style="background:#8ad;"></span> Aucune donnée</div>`;

        if (colorBins.length > 0) {
            for (let i = 0; i < colorBins.length; i++) {
                const next = i < colorBins.length - 1 ? colorBins[i + 1] : null;
                if (i === 0) {
                    html += `<div class="legend-item"><span class="color-box" style="background:${MAP_COLORS[0]};"></span> < ${formatAmount(colorBins[1])}</div>`;
                } else if (next) {
                    html += `<div class="legend-item"><span class="color-box" style="background:${MAP_COLORS[i]};"></span> ${formatAmount(colorBins[i])} - ${formatAmount(next)}</div>`;
                } else {
                    html += `<div class="legend-item"><span class="color-box" style="background:${MAP_COLORS[Math.min(i, MAP_COLORS.length - 1)]};"></span> > ${formatAmount(colorBins[i])}</div>`;
                }
            }
        } else {
            html += `<div class="legend-item"><span class="color-box" style="background:#e8f5e9;"></span> Données disponibles</div>`;
        }

        legend.innerHTML = html;
    }

    function formatAmount(amount) {
        return Utils.formatAmount(amount);
    }

    function showTooltip(e, code, info) {
        const tooltip = document.getElementById('tooltip');
        if (!tooltip) return;
        
        const total = getDepartmentTotal(code);
        const count = getDepartmentCount(code);
        tooltip.innerHTML = `
            <strong>${code} - ${info.name}</strong><br>
            Région : ${info.region}<br>
            Subventions reçues : ${count}<br>
            Montant total : ${formatAmount(total)}
        `;
        tooltip.style.display = 'block';
        positionTooltip(e, tooltip);
    }

    function showRegionTooltip(e, code, info) {
        const tooltip = document.getElementById('tooltip');
        if (!tooltip) return;
        
        const total = getRegionTotal(code);
        const count = getRegionCount(code);
        tooltip.innerHTML = `
            <strong>${code} - ${info.name}</strong><br>
            Subventions reçues : ${count}<br>
            Montant total : ${formatAmount(total)}
        `;
        tooltip.style.display = 'block';
        positionTooltip(e, tooltip);
    }

    function positionTooltip(e, tooltip) {
        const rect = e.target.getBoundingClientRect();
        const wrapper = document.getElementById('mapWrapper')?.getBoundingClientRect();
        if (!wrapper) return;
        
        tooltip.style.left = (rect.left - wrapper.left + rect.width / 2) + 'px';
        tooltip.style.top = (rect.top - wrapper.top - 10) + 'px';
        tooltip.style.transform = 'translate(-50%, -100%)';
    }

    function hideTooltip() {
        const tooltip = document.getElementById('tooltip');
        if (tooltip) tooltip.style.display = 'none';
    }

    function selectDepartment(code) {
        State.dispatch({
            type: 'SET_FILTER',
            payload: { department: code, region: null }
        });
        
        const svg = document.getElementById('franceMap');
        if (!svg) return;
        
        svg.querySelectorAll('path').forEach(p => {
            if (p.dataset.code === code) {
                p.style.stroke = '#e74c3c';
                p.style.strokeWidth = '3';
            } else {
                p.style.stroke = '';
                p.style.strokeWidth = '';
            }
        });
    }

    function selectRegion(code) {
        State.dispatch({
            type: 'SET_FILTER',
            payload: { department: null, region: code }
        });
        
        const svg = document.getElementById('franceMap');
        if (!svg) return;
        
        svg.querySelectorAll('path').forEach(p => {
            if (p.dataset.code === code) {
                p.style.stroke = '#e74c3c';
                p.style.strokeWidth = '3';
            } else {
                p.style.stroke = '';
                p.style.strokeWidth = '';
            }
        });
    }

    async function switchMapLevel(level) {
        State.dispatch({
            type: 'SET_FILTER',
            payload: { mapLevel: level, department: null, region: null }
        });
        
        const svg = await loadMapSVG(level);
        if (svg) {
            initMapPaths(svg, level);
            computeColorBins();
            colorMapBySubventions();
            updateLegend();
        }
    }

    async function initMap() {
        const loading = document.getElementById('mapLoading');
        const svg = await loadMapSVG('departments');
        if (svg) {
            initMapPaths(svg, 'departments');
            computeColorBins();
            colorMapBySubventions();
            updateLegend();
        }
        if (loading) loading.style.display = 'none';
    }

    function refreshMap() {
        computeColorBins();
        colorMapBySubventions();
        updateLegend();
    }

    return {
        initMap,
        switchMapLevel,
        refreshMap,
        selectDepartment,
        selectRegion,
        getDepartmentTotal,
        getRegionTotal
    };
})();

export default MapModule;
