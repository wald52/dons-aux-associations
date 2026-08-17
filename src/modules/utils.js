// Shared utility functions used across modules
const Utils = (function() {
    /**
     * Format an amount as EUR currency
     * @param {number} amount - The amount to format
     * @returns {string} Formatted currency string
     */
    function formatAmount(amount) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR',
            maximumFractionDigits: 0
        }).format(amount);
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} html - The HTML string to escape
     * @returns {string} Escaped HTML string
     */
    function escapeHtml(html) {
        if (!html || typeof html !== 'string') return '';
        
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }

    /**
     * Debounce a function call
     * @param {Function} fn - The function to debounce
     * @param {number} delay - Delay in milliseconds
     * @returns {Function} Debounced function
     */
    function debounce(fn, delay) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    /**
     * Format a number with French locale
     * @param {number} num - The number to format
     * @returns {string} Formatted number string
     */
    function formatNumber(num) {
        return new Intl.NumberFormat('fr-FR').format(num);
    }

    /**
     * Truncate text to a maximum length
     * @param {string} text - The text to truncate
     * @param {number} maxLength - Maximum length
     * @param {string} suffix - Suffix to add if truncated (default: '…')
     * @returns {string} Truncated text
     */
    function truncate(text, maxLength, suffix = '…') {
        if (!text || typeof text !== 'string') return '';
        if (text.length <= maxLength) return text;
        return text.slice(0, maxLength - suffix.length) + suffix;
    }

    /**
     * Check if a value is defined and not empty
     * @param {*} value - The value to check
     * @returns {boolean} True if value is defined and not empty
     */
    function isDefined(value) {
        if (value === null || value === undefined) return false;
        if (typeof value === 'string') return value.trim().length > 0;
        if (Array.isArray(value)) return value.length > 0;
        return true;
    }

    /**
     * Safe JSON parse with fallback
     * @param {string} json - JSON string to parse
     * @param {*} fallback - Fallback value if parsing fails
     * @returns {*} Parsed object or fallback
     */
    function safeJsonParse(json, fallback = null) {
        try {
            return JSON.parse(json);
        } catch (e) {
            return fallback;
        }
    }

    /**
     * Generate a unique ID
     * @param {string} prefix - Prefix for the ID
     * @returns {string} Unique ID
     */
    function generateId(prefix = 'id') {
        return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Deep clone an object
     * @param {*} obj - Object to clone
     * @returns {*} Cloned object
     */
    function deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => deepClone(item));
        
        const clonedObj = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clonedObj[key] = deepClone(obj[key]);
            }
        }
        return clonedObj;
    }

    return {
        formatAmount,
        escapeHtml,
        debounce,
        formatNumber,
        truncate,
        isDefined,
        safeJsonParse,
        generateId,
        deepClone
    };
})();

export default Utils;
