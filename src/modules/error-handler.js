// Error handling module for robust error management
const ErrorHandler = (function() {
    const errorLog = [];
    const MAX_ERROR_LOG_SIZE = 100;

    // Error types
    const ErrorTypes = {
        DATA_LOAD: 'DATA_LOAD',
        VALIDATION: 'VALIDATION',
        NETWORK: 'NETWORK',
        RENDER: 'RENDER',
        USER_INPUT: 'USER_INPUT',
        UNKNOWN: 'UNKNOWN'
    };

    // Log an error
    function logError(error, type = ErrorTypes.UNKNOWN, context = {}) {
        const errorEntry = {
            timestamp: new Date().toISOString(),
            type: type,
            message: error.message || String(error),
            stack: error.stack,
            context: context,
            userAgent: navigator.userAgent,
            url: window.location.href
        };

        errorLog.push(errorEntry);

        // Keep log size manageable
        if (errorLog.length > MAX_ERROR_LOG_SIZE) {
            errorLog.shift();
        }

        // Log to console
        console.error(`[${type}]`, error, context);

        // Dispatch error event for other modules to handle
        window.dispatchEvent(new CustomEvent('appError', {
            detail: errorEntry
        }));

        return errorEntry;
    }

    // Get error log
    function getErrorLog() {
        return [...errorLog];
    }

    // Clear error log
    function clearErrorLog() {
        errorLog.length = 0;
    }

    // Get recent errors
    function getRecentErrors(count = 10) {
        return errorLog.slice(-count);
    }

    // Handle data loading errors
    function handleDataLoadError(error, source) {
        const errorEntry = logError(error, ErrorTypes.DATA_LOAD, { source });
        
        // Show user-friendly message
        showErrorMessage(
            'Erreur de chargement des données',
            `Impossible de charger les données depuis ${source || 'la source'}. Veuillez réessayer ou contacter l'administrateur.`
        );

        return errorEntry;
    }

    // Handle validation errors
    function handleValidationError(errors, context) {
        const error = new Error(`Validation failed: ${errors.join(', ')}`);
        const errorEntry = logError(error, ErrorTypes.VALIDATION, { errors, context });

        // Show user-friendly message for critical validation errors
        if (errors.length > 5) {
            showErrorMessage(
                'Erreur de validation',
                'Certaines données ne sont pas valides. Elles ont été ignorées.'
            );
        }

        return errorEntry;
    }

    // Handle network errors
    function handleNetworkError(error, url) {
        const errorEntry = logError(error, ErrorTypes.NETWORK, { url });

        showErrorMessage(
            'Erreur réseau',
            'Impossible de contacter le serveur. Vérifiez votre connexion internet.'
        );

        return errorEntry;
    }

    // Handle render errors
    function handleRenderError(error, component) {
        const errorEntry = logError(error, ErrorTypes.RENDER, { component });

        console.warn(`Render error in ${component}:`, error);

        return errorEntry;
    }

    // Handle user input errors
    function handleUserInputError(error, input) {
        const errorEntry = logError(error, ErrorTypes.USER_INPUT, { input });

        // Don't show error message for minor input errors, just log them
        return errorEntry;
    }

    // Show error message to user
    function showErrorMessage(title, message) {
        // Remove existing error messages
        const existing = document.querySelector('.error-toast');
        if (existing) existing.remove();

        // Create error toast
        const toast = document.createElement('div');
        toast.className = 'error-toast';
        toast.innerHTML = `
            <div class="error-toast-content">
                <strong>${escapeHtml(title)}</strong>
                <p>${escapeHtml(message)}</p>
                <button class="error-toast-close">&times;</button>
            </div>
        `;

        // Add styles if not present
        if (!document.querySelector('#error-toast-styles')) {
            const style = document.createElement('style');
            style.id = 'error-toast-styles';
            style.textContent = `
                .error-toast {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #e74c3c;
                    color: white;
                    padding: 1rem;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    z-index: 10000;
                    max-width: 400px;
                    animation: slideIn 0.3s ease;
                }
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                .error-toast-content {
                    position: relative;
                }
                .error-toast strong {
                    display: block;
                    margin-bottom: 0.5rem;
                }
                .error-toast p {
                    margin: 0 0 0.5rem 0;
                    font-size: 0.9rem;
                }
                .error-toast-close {
                    position: absolute;
                    top: 0;
                    right: 0;
                    background: none;
                    border: none;
                    color: white;
                    font-size: 1.2rem;
                    cursor: pointer;
                    padding: 0 0.5rem;
                }
                .error-toast-close:hover {
                    opacity: 0.8;
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, 5000);

        // Close button
        toast.querySelector('.error-toast-close').addEventListener('click', () => {
            toast.remove();
        });
    }

    // Escape HTML to prevent XSS in error messages
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Wrap async functions with error handling
    function withErrorHandling(fn, errorType = ErrorTypes.UNKNOWN, context = {}) {
        return async (...args) => {
            try {
                return await fn(...args);
            } catch (error) {
                logError(error, errorType, context);
                
                // Handle specific error types
                switch (errorType) {
                    case ErrorTypes.DATA_LOAD:
                        handleDataLoadError(error, context.source);
                        break;
                    case ErrorTypes.NETWORK:
                        handleNetworkError(error, context.url);
                        break;
                    case ErrorTypes.VALIDATION:
                        handleValidationError([error.message], context);
                        break;
                    default:
                        showErrorMessage(
                            'Une erreur est survenue',
                            'Veuillez réessayer ou contacter l\'administrateur si le problème persiste.'
                        );
                }
                
                throw error;
            }
        };
    }

    // Wrap synchronous functions with error handling
    function withSyncErrorHandling(fn, errorType = ErrorTypes.UNKNOWN, context = {}) {
        return (...args) => {
            try {
                return fn(...args);
            } catch (error) {
                logError(error, errorType, context);
                
                switch (errorType) {
                    case ErrorTypes.RENDER:
                        handleRenderError(error, context.component);
                        break;
                    case ErrorTypes.USER_INPUT:
                        handleUserInputError(error, context.input);
                        break;
                    default:
                        console.error('Error:', error);
                }
                
                throw error;
            }
        };
    }

    // Initialize global error handler
    function initGlobalErrorHandler() {
        window.addEventListener('error', (event) => {
            logError(event.error, ErrorTypes.UNKNOWN, {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });

        window.addEventListener('unhandledrejection', (event) => {
            logError(event.reason, ErrorTypes.UNKNOWN, {
                promise: 'Unhandled Promise Rejection'
            });
        });
    }

    // Export error log for debugging
    function exportErrorLog() {
        const log = getErrorLog();
        const blob = new Blob([JSON.stringify(log, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `error-log-${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    return {
        ErrorTypes,
        logError,
        getErrorLog,
        clearErrorLog,
        getRecentErrors,
        handleDataLoadError,
        handleValidationError,
        handleNetworkError,
        handleRenderError,
        handleUserInputError,
        withErrorHandling,
        withSyncErrorHandling,
        initGlobalErrorHandler,
        exportErrorLog
    };
})();

export default ErrorHandler;
