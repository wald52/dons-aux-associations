// Data validation module for security and data integrity
const Validation = (function() {
    // Validate subvention data structure
    function validateSubvention(subvention) {
        const errors = [];
        
        if (!subvention || typeof subvention !== 'object') {
            errors.push('Subvention must be an object');
            return { valid: false, errors };
        }

        // Validate ID
        if (!subvention.id || typeof subvention.id !== 'string') {
            errors.push('Invalid or missing id');
        }

        // Validate association
        if (!subvention.association || typeof subvention.association !== 'object') {
            errors.push('Invalid or missing association object');
        } else {
            if (!subvention.association.name || typeof subvention.association.name !== 'string') {
                errors.push('Invalid or missing association name');
            }
            if (subvention.association.department && !isValidDepartmentCode(subvention.association.department)) {
                errors.push(`Invalid department code: ${subvention.association.department}`);
            }
            if (subvention.association.rna && !isValidRNA(subvention.association.rna)) {
                errors.push(`Invalid RNA format: ${subvention.association.rna}`);
            }
            if (subvention.association.siret && !isValidSIRET(subvention.association.siret)) {
                errors.push(`Invalid SIRET format: ${subvention.association.siret}`);
            }
        }

        // Validate entity
        if (!subvention.entity || typeof subvention.entity !== 'object') {
            errors.push('Invalid or missing entity object');
        } else {
            if (!subvention.entity.name || typeof subvention.entity.name !== 'string') {
                errors.push('Invalid or missing entity name');
            }
            if (!isValidEntityType(subvention.entity.type)) {
                errors.push(`Invalid entity type: ${subvention.entity.type}`);
            }
        }

        // Validate amount
        if (typeof subvention.amount !== 'number' || subvention.amount < 0) {
            errors.push(`Invalid amount: ${subvention.amount}`);
        }

        // Validate year
        if (!subvention.year || typeof subvention.year !== 'number' || subvention.year < 1900 || subvention.year > 2100) {
            errors.push(`Invalid year: ${subvention.year}`);
        }

        // Validate convention
        if (subvention.convention !== undefined && typeof subvention.convention !== 'boolean') {
            errors.push(`Invalid convention value: ${subvention.convention}`);
        }

        // Validate source URL
        if (!subvention.source || !isValidURL(subvention.source)) {
            errors.push(`Invalid source URL: ${subvention.source}`);
        }

        return {
            valid: errors.length === 0,
            errors
        };
    }

    // Validate department code (01-95, 2A, 2B, 97X, 98X)
    function isValidDepartmentCode(code) {
        if (!code) return false;
        
        // Metropolitan departments (01-95)
        const metroDept = /^(0[1-9]|[1-8][0-9]|9[0-5])$/.test(code);
        if (metroDept) return true;

        // Corsica (2A, 2B)
        if (code === '2A' || code === '2B') return true;

        // Overseas departments (971-979)
        const overseasDept = /^97[1-9]$/.test(code);
        if (overseasDept) return true;

        // Overseas territories (98X)
        const overseasTerr = /^98[0-9]$/.test(code);
        if (overseasTerr) return true;

        return false;
    }

    // Validate RNA format (WXXXXXXXXX - 10 characters starting with W)
    function isValidRNA(rna) {
        if (!rna || typeof rna !== 'string') return false;
        return /^W\d{9}$/.test(rna);
    }

    // Validate SIRET format (14 digits)
    function isValidSIRET(siret) {
        if (!siret || typeof siret !== 'string') return false;
        if (!/^\d{14}$/.test(siret)) return false;
        
        // Luhn algorithm for SIRET validation
        let sum = 0;
        let parity = siret.length % 2;
        for (let i = 0; i < siret.length; i++) {
            let digit = parseInt(siret[i]);
            if (i % 2 === parity) {
                digit *= 2;
                if (digit > 9) digit -= 9;
            }
            sum += digit;
        }
        return sum % 10 === 0;
    }

    // Validate entity type
    function isValidEntityType(type) {
        const validTypes = ['state', 'region', 'department', 'commune', 'epci'];
        return validTypes.includes(type);
    }

    // Validate URL
    function isValidURL(url) {
        if (!url || typeof url !== 'string') return false;
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    // Sanitize user input to prevent XSS
    function sanitizeInput(input) {
        if (input === null || input === undefined) return '';
        
        if (typeof input !== 'string') {
            input = String(input);
        }

        // Remove potentially dangerous characters
        return input
            .replace(/[<>]/g, '') // Remove < and >
            .replace(/javascript:/gi, '') // Remove javascript: protocol
            .replace(/on\w+=/gi, '') // Remove event handlers like onclick=
            .trim();
    }

    // Sanitize HTML content
    function sanitizeHTML(html) {
        if (!html || typeof html !== 'string') return '';
        
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }

    // Validate and sanitize search query
    function validateSearchQuery(query) {
        if (!query) return '';
        
        const sanitized = sanitizeInput(query);
        
        // Limit search query length
        if (sanitized.length > 200) {
            return sanitized.substring(0, 200);
        }
        
        return sanitized;
    }

    // Validate filter values
    function validateFilters(filters) {
        const errors = [];
        const sanitized = { ...filters };

        // Validate entityType
        if (filters.entityType && filters.entityType !== 'all' && !isValidEntityType(filters.entityType)) {
            errors.push(`Invalid entityType: ${filters.entityType}`);
            sanitized.entityType = 'all';
        }

        // Validate year
        if (filters.year && filters.year !== 'all') {
            const year = parseInt(filters.year);
            if (isNaN(year) || year < 1900 || year > 2100) {
                errors.push(`Invalid year: ${filters.year}`);
                sanitized.year = 'all';
            }
        }

        // Validate amountRange
        if (filters.amountRange && filters.amountRange !== 'all') {
            const validRanges = ['0-10000', '10000-50000', '50000-100000', '100000-500000', '500000+'];
            if (!validRanges.includes(filters.amountRange)) {
                errors.push(`Invalid amountRange: ${filters.amountRange}`);
                sanitized.amountRange = 'all';
            }
        }

        // Validate department
        if (filters.department && !isValidDepartmentCode(filters.department)) {
            errors.push(`Invalid department: ${filters.department}`);
            sanitized.department = null;
        }

        // Validate region
        if (filters.region) {
            const validRegions = ['84', '27', '53', '24', '94', '44', '32', '11', '28', '75', '76', '52', '93'];
            if (!validRegions.includes(filters.region)) {
                errors.push(`Invalid region: ${filters.region}`);
                sanitized.region = null;
            }
        }

        // Sanitize search
        if (filters.search) {
            sanitized.search = validateSearchQuery(filters.search);
        }

        return {
            valid: errors.length === 0,
            errors,
            sanitized
        };
    }

    // Validate pagination parameters
    function validatePagination(page, pageSize) {
        const errors = {};
        const sanitized = {};

        // Validate page
        if (page !== undefined) {
            const pageNum = parseInt(page);
            if (isNaN(pageNum) || pageNum < 1) {
                errors.page = 'Page must be a positive integer';
                sanitized.page = 1;
            } else {
                sanitized.page = pageNum;
            }
        }

        // Validate pageSize
        if (pageSize !== undefined) {
            const size = parseInt(pageSize);
            const validSizes = [25, 50, 100, 200];
            if (isNaN(size) || !validSizes.includes(size)) {
                errors.pageSize = `Page size must be one of: ${validSizes.join(', ')}`;
                sanitized.pageSize = 50;
            } else {
                sanitized.pageSize = size;
            }
        }

        return {
            valid: Object.keys(errors).length === 0,
            errors,
            sanitized
        };
    }

    // Validate data array
    function validateDataArray(data) {
        if (!Array.isArray(data)) {
            return { valid: false, errors: ['Data must be an array'], validCount: 0, invalidCount: 0 };
        }

        let validCount = 0;
        let invalidCount = 0;
        const allErrors = [];

        data.forEach((item, index) => {
            const validation = validateSubvention(item);
            if (validation.valid) {
                validCount++;
            } else {
                invalidCount++;
                allErrors.push(`Item ${index}: ${validation.errors.join(', ')}`);
            }
        });

        return {
            valid: invalidCount === 0,
            errors: allErrors,
            validCount,
            invalidCount
        };
    }

    // Check for potential SQL injection patterns
    function containsSQLInjection(input) {
        if (!input || typeof input !== 'string') return false;
        
        const sqlPatterns = [
            /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|ALTER|CREATE|TRUNCATE)\b)/i,
            /(--|;|\/\*|\*\/)/,
            /(\bOR\b|\bAND\b).*=.*=/i,
            /(\b1\s*=\s*1\b)/i
        ];

        return sqlPatterns.some(pattern => pattern.test(input));
    }

    // Check for XSS patterns
    function containsXSS(input) {
        if (!input || typeof input !== 'string') return false;
        
        const xssPatterns = [
            /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
            /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi,
            /javascript:/gi,
            /on\w+\s*=/gi,
            /<img[^>]+src[^>]*>/gi,
            /<embed[^>]*>/gi,
            /<object[^>]*>/gi
        ];

        return xssPatterns.some(pattern => pattern.test(input));
    }

    return {
        validateSubvention,
        isValidDepartmentCode,
        isValidRNA,
        isValidSIRET,
        isValidEntityType,
        isValidURL,
        sanitizeInput,
        sanitizeHTML,
        validateSearchQuery,
        validateFilters,
        validatePagination,
        validateDataArray,
        containsSQLInjection,
        containsXSS
    };
})();

export default Validation;
