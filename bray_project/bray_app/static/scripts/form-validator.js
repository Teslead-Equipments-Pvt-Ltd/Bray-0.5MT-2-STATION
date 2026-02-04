/**
 * ==========================================
 *  Production-Grade Form Validation System
 * ==========================================
 * 
 * Features:
 * - Inline validation while typing/selecting
 * - Async validation with debouncing (400ms)
 * - Race condition prevention via AbortController
 * - No errors shown on initial render (only after touched)
 * - Separate sync and async validation
 * - Bootstrap-compatible error display
 */

/**
 * Standard Debounce Function
 * Prevents function from being called too frequently.
 */
const debounce = (func, wait) => {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
};

/**
 * Form Validator Class
 * Handles synchronous and asynchronous validation, state management, and UI updates.
 */
class FormValidator {
    constructor(formId, config) {
        this.form = document.getElementById(formId);
        if (!this.form) return;

        this.config = config; // { fieldName: { rules: [], asyncRule: fn } }
        this.state = {}; // { fieldName: { touched, valid, error, pending, abortController } }
        this.subscribers = new Set(); // For validity change listeners

        this.init();
    }

    init() {
        // Initialize state for each field
        Object.keys(this.config).forEach(fieldName => {
            this.state[fieldName] = {
                touched: false,
                valid: false,
                error: null,
                pending: false,
                abortController: null
            };

            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                // Input event for text-like fields (typing)
                if (field.tagName === 'INPUT' || field.tagName === 'TEXTAREA') {
                    field.addEventListener('input', (e) => this.handleInput(fieldName, e.target.value));
                    field.addEventListener('blur', () => this.handleBlur(fieldName));
                }
                // Change event for selects/radios
                else if (field.tagName === 'SELECT') {
                    field.addEventListener('change', (e) => this.handleInput(fieldName, e.target.value));
                    field.addEventListener('blur', () => this.handleBlur(fieldName));
                }
            }
        });
    }

    /**
     * Handle user input (typing/selecting)
     */
    handleInput(fieldName, value) {
        // Mark touched immediately upon interaction
        this.state[fieldName].touched = true;

        // Clear previous async abort if exists
        if (this.state[fieldName].abortController) {
            this.state[fieldName].abortController.abort();
        }

        // Synchronous Validation First
        const syncError = this.runSyncValidation(fieldName, value);

        if (syncError) {
            this.updateState(fieldName, { valid: false, error: syncError, pending: false });
            this.renderError(fieldName);
            return;
        }

        // If Sync passes, check if Async is needed
        if (this.config[fieldName].asyncRule) {
            this.updateState(fieldName, { valid: false, error: null, pending: true });
            this.renderPending(fieldName);
            this.debouncedAsyncValidate(fieldName, value);
        } else {
            // Valid (Sync only)
            this.updateState(fieldName, { valid: true, error: null, pending: false });
            this.renderSuccess(fieldName);
        }
    }

    handleBlur(fieldName) {
        // Ensure touched is true and re-validate to show errors if user tabbed through
        this.state[fieldName].touched = true;
        const field = this.form.querySelector(`[name="${fieldName}"]`);
        if (field) this.handleInput(fieldName, field.value);
    }

    /**
     * Run all synchronous rules for a field
     */
    runSyncValidation(fieldName, value) {
        const rules = this.config[fieldName].rules || [];
        for (const rule of rules) {
            // Function rule
            if (typeof rule.test === 'function') {
                if (!rule.test(value, this.form)) return rule.message;
            }
            // Regex rule
            else if (rule.test instanceof RegExp) {
                if (!rule.test.test(value)) return rule.message;
            }
        }
        return null;
    }

    /**
     * Debounced Async Validation
     */
    debouncedAsyncValidate = debounce(async (fieldName, value) => {
        // Create new AbortController for this request
        const controller = new AbortController();
        this.state[fieldName].abortController = controller;

        try {
            const isValid = await this.config[fieldName].asyncRule(value, controller.signal, this.form);

            // If aborted, validation loop handles it via catch or simply by being overwritten
            if (controller.signal.aborted) return;

            if (isValid === true) {
                this.updateState(fieldName, { valid: true, error: null, pending: false });
                this.renderSuccess(fieldName);
            } else {
                // If returns true/false or string message
                const msg = typeof isValid === 'string' ? isValid : 'Validation failed';
                this.updateState(fieldName, { valid: false, error: msg, pending: false });
                this.renderError(fieldName);
            }
        } catch (error) {
            if (error.name === 'AbortError') return; // Ignore aborted requests
            console.error("Validation Error", error);
        }
    }, 400); // 400ms debounce

    updateState(fieldName, updates) {
        this.state[fieldName] = { ...this.state[fieldName], ...updates };
        this.notifySubscribers();
    }

    /**
     * Render Error UI
     */
    renderError(fieldName) {
        if (!this.state[fieldName].touched) return;

        const field = this.form.querySelector(`[name="${fieldName}"]`);
        if (!field) return;

        field.classList.add('is-invalid');
        if (field.classList.contains('is-valid')) field.classList.remove('is-valid');

        // Find or create invalid-feedback
        const container = field.parentElement;
        let errorDiv = container.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            container.appendChild(errorDiv);
        }
        errorDiv.style.display = 'block';
        errorDiv.textContent = this.state[fieldName].error;
    }

    /**
     * Render Success UI
     */
    renderSuccess(fieldName) {
        const field = this.form.querySelector(`[name="${fieldName}"]`);
        if (!field) return;

        field.classList.remove('is-invalid');

        const errorDiv = field.parentElement.querySelector('.invalid-feedback');
        if (errorDiv) errorDiv.style.display = 'none';
    }

    renderPending(fieldName) {
        // Remove invalid class so it looks neutral while checking
        const field = this.form.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.classList.remove('is-invalid');
            field.classList.remove('is-valid');
        }
    }

    /**
     * Force Validation on Submit
     */
    async validateAll() {
        const validations = Object.keys(this.config).map(async (fieldName) => {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            this.state[fieldName].touched = true; // Mark all as touched

            // Sync check
            const syncError = this.runSyncValidation(fieldName, field ? field.value : '');
            if (syncError) {
                this.updateState(fieldName, { valid: false, error: syncError, pending: false });
                this.renderError(fieldName);
                return false;
            }

            // Async check (await it immediately without debounce for submit)
            if (this.config[fieldName].asyncRule) {
                try {
                    const res = await this.config[fieldName].asyncRule(field.value, null, this.form);
                    if (res !== true) {
                        const msg = typeof res === 'string' ? res : 'Validation failed';
                        this.updateState(fieldName, { valid: false, error: msg, pending: false });
                        this.renderError(fieldName);
                        return false;
                    }
                } catch (e) {
                    return false;
                }
            }

            this.updateState(fieldName, { valid: true, error: null, pending: false });
            this.renderSuccess(fieldName);
            return true;
        });

        const results = await Promise.all(validations);
        return results.every(r => r === true);
    }

    notifySubscribers() {
        // Can be used to disable submit button dynamically
    }

    reset() {
        // Reset form and state
        this.form.reset();
        Object.keys(this.state).forEach(key => {
            this.state[key] = {
                touched: false, valid: false, error: null, pending: false, abortController: null
            };
            const field = this.form.querySelector(`[name="${key}"]`);
            if (field) {
                field.classList.remove('is-invalid', 'is-valid');
                const err = field.parentElement.querySelector('.invalid-feedback');
                if (err) err.style.display = 'none';
            }
        });
    }
}

// --- Common Validation Rules ---
const ValidationRules = {
    required: { test: (val) => val && val.trim().length > 0, message: 'This field is required' },
    noDigits: { test: /^[^\d]+$/, message: 'Digits are not allowed' },
    alphanumeric: { test: /^[a-zA-Z0-9]+$/, message: 'Only letters and numbers allowed' },
    alphanumericSpace: { test: /^[a-zA-Z0-9\s]+$/, message: 'Only letters, numbers and spaces allowed' },
    email: { test: (val) => !val || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val), message: 'Invalid email format' },
    mobile: { test: (val) => !val || /^\d{10}$/.test(val), message: 'Must be 10 digits' },
    minLength: (len) => ({ test: (val) => val.length >= len, message: `Must be at least ${len} characters` }),
    maxLength: (len) => ({ test: (val) => val.length <= len, message: `Must be at most ${len} characters` }),
    numeric: { test: /^\d+$/, message: 'Only numbers allowed' },
    decimal: { test: /^\d+(\.\d+)?$/, message: 'Invalid number format' },
};
