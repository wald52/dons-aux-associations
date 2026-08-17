import State from '../state.js';
import Filters from './filters.js';
import Utils from './utils.js';

// Charts management module using Chart.js
const Charts = (function() {
    let charts = {};

    function formatAmount(amount) {
        return Utils.formatAmount(amount);
    }

    function getChartColors() {
        const isDark = State.getUI().theme === 'dark';
        return {
            textColor: isDark ? '#a0a0b0' : '#6c757d',
            gridColor: isDark ? '#2a2a3e' : '#e1e5e9',
            borderColor: isDark ? '#1a1a2e' : '#fff'
        };
    }

    function initCharts() {
        const ctx1 = document.getElementById('topAssociationsChart');
        const ctx2 = document.getElementById('entityTypeChart');
        const colors = getChartColors();

        if (ctx1) {
            charts.top = new Chart(ctx1, {
                type: 'bar',
                data: { 
                    labels: [], 
                    datasets: [{ 
                        label: 'Montant total', 
                        data: [], 
                        backgroundColor: '#4fc3f7', 
                        borderRadius: 6 
                    }] 
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { 
                            ticks: { 
                                color: colors.textColor, 
                                callback: v => (v / 1000).toFixed(0) + 'k' 
                            }, 
                            grid: { color: colors.gridColor } 
                        },
                        x: { 
                            ticks: { 
                                color: colors.textColor, 
                                maxRotation: 45, 
                                font: { size: 9 } 
                            }, 
                            grid: { display: false } 
                        }
                    }
                }
            });
        }

        if (ctx2) {
            charts.entity = new Chart(ctx2, {
                type: 'doughnut',
                data: { 
                    labels: [], 
                    datasets: [{ 
                        data: [], 
                        backgroundColor: ['#4fc3f7', '#66bb6a', '#ffa726', '#ef5350', '#ab47bc', '#26a69a'], 
                        borderWidth: 2, 
                        borderColor: colors.borderColor 
                    }] 
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: colors.textColor, font: { size: 10 }, padding: 8 }
                        }
                    }
                }
            });
        }
    }

    function initEvolutionChart() {
        const ctx = document.getElementById('evolutionChart');
        if (!ctx) return;
        
        const colors = getChartColors();

        charts.evolution = new Chart(ctx, {
            type: 'bar',
            data: { 
                labels: [], 
                datasets: [{ 
                    label: 'Montant total par année', 
                    data: [], 
                    backgroundColor: '#66bb6a', 
                    borderRadius: 4 
                }] 
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { 
                        ticks: { 
                            color: colors.textColor, 
                            callback: v => (v / 1000000).toFixed(1) + 'M' 
                        }, 
                        grid: { color: colors.gridColor } 
                    },
                    x: { 
                        ticks: { color: colors.textColor }, 
                        grid: { display: false } 
                    }
                }
            }
        });
    }

    function updateCharts() {
        const state = State.getState();
        const filtered = state.data.filteredData;
        
        if (!charts.top || !charts.entity) return;

        if (filtered.length === 0) {
            charts.top.data.labels = [];
            charts.top.data.datasets[0].data = [];
            charts.top.update();
            charts.entity.data.labels = [];
            charts.entity.data.datasets[0].data = [];
            charts.entity.update();
            return;
        }

        // Top 10 associations
        const byName = {};
        filtered.forEach(s => {
            const name = s.association.name;
            if (!byName[name]) byName[name] = 0;
            byName[name] += s.amount;
        });

        const top10 = Object.entries(byName)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);

        charts.top.data.labels = top10.map(([name]) => 
            name.length > 20 ? name.slice(0, 18) + '…' : name
        );
        charts.top.data.datasets[0].data = top10.map(([, total]) => total);
        charts.top.update();

        // By entity type
        const byType = {};
        filtered.forEach(s => {
            const type = Filters.getEntityTypeLabel(s.entity.type);
            if (!byType[type]) byType[type] = 0;
            byType[type] += s.amount;
        });

        charts.entity.data.labels = Object.keys(byType);
        charts.entity.data.datasets[0].data = Object.values(byType);
        charts.entity.update();
    }

    function updateEvolutionChart() {
        const state = State.getState();
        const filtered = state.data.filteredData;
        
        if (!charts.evolution) return;

        if (filtered.length === 0) {
            charts.evolution.data.labels = [];
            charts.evolution.data.datasets[0].data = [];
            charts.evolution.update();
            return;
        }

        const byYear = {};
        filtered.forEach(s => {
            if (!byYear[s.year]) byYear[s.year] = 0;
            byYear[s.year] += s.amount;
        });

        const years = Object.keys(byYear).sort();
        charts.evolution.data.labels = years;
        charts.evolution.data.datasets[0].data = years.map(y => byYear[y]);
        charts.evolution.update();
    }

    function updateChartTheme() {
        const colors = getChartColors();

        [charts.top, charts.entity, charts.evolution].forEach(chart => {
            if (!chart) return;
            const opts = chart.options;
            if (opts.scales) {
                Object.values(opts.scales).forEach(scale => {
                    if (scale.ticks) scale.ticks.color = colors.textColor;
                    if (scale.grid) scale.grid.color = colors.gridColor;
                });
            }
            if (opts.plugins?.legend?.labels) {
                opts.plugins.legend.labels.color = colors.textColor;
            }
            if (chart.data.datasets[0]) {
                chart.data.datasets[0].borderColor = colors.borderColor;
            }
            chart.update();
        });
    }

    function refreshAllCharts() {
        updateCharts();
        updateEvolutionChart();
    }

    return {
        initCharts,
        initEvolutionChart,
        updateCharts,
        updateEvolutionChart,
        updateChartTheme,
        refreshAllCharts
    };
})();

export default Charts;
