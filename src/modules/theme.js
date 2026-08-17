import State from '../state.js';
import Charts from './charts.js';

// Theme management module (dark/light mode)
const Theme = (function() {
    function initTheme() {
        const btn = document.getElementById('darkModeToggle');
        if (!btn) return;

        const saved = localStorage.getItem('theme');
        if (saved === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            btn.textContent = '☀️';
            btn.setAttribute('aria-label', 'Activer le mode clair');
            State.dispatch({
                type: 'SET_THEME',
                payload: 'dark'
            });
        }

        btn.addEventListener('click', toggleTheme);
    }

    function toggleTheme() {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const btn = document.getElementById('darkModeToggle');
        
        if (isDark) {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
            if (btn) {
                btn.textContent = '🌙';
                btn.setAttribute('aria-label', 'Activer le mode sombre');
            }
            State.dispatch({
                type: 'SET_THEME',
                payload: 'light'
            });
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            if (btn) {
                btn.textContent = '☀️';
                btn.setAttribute('aria-label', 'Activer le mode clair');
            }
            State.dispatch({
                type: 'SET_THEME',
                payload: 'dark'
            });
        }

        Charts.updateChartTheme();
    }

    function getTheme() {
        return State.getUI().theme;
    }

    return {
        initTheme,
        toggleTheme,
        getTheme
    };
})();

export default Theme;
