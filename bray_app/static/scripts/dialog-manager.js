/**
 * DialogManager - Universal Dialog and Toast Notification System with AJAX Support
 * Usage: Simply include this script and call DialogManager methods anywhere
 */



const DialogManager = (() => {
  // Inject styles once
  const injectStyles = () => {
    if (document.getElementById('dialog-manager-styles')) return;

    const style = document.createElement('style');
    style.id = 'dialog-manager-styles';
    style.textContent = `
      .dm-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        animation: dm-fadeIn 0.3s ease;
      }

      .dm-dialog {
        background: white;
        border-radius: 12px;
        padding: 24px;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        animation: dm-slideUp 0.3s ease;
      }

      .dm-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }

      .dm-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
      }

      .dm-icon.confirm { background: #fff8e1; color: #f9a825; }
      .dm-icon.alert { background: #e3f2fd; color: #1976d2; }
      .dm-icon.warning { background: #fff3e0; color: #f57c00; }
      .dm-icon.error { background: #ffebee; color: #d32f2f; }

      .dm-title {
        font-size: 18px;
        font-weight: 600;
        color: #333;
        margin: 0;
      }

      .dm-message {
        color: #666;
        font-size: 14px;
        line-height: 1.5;
        margin-bottom: 20px;
      }

      .dm-buttons {
        display: flex;
        gap: 10px;
        justify-content: flex-end;
      }

      .dm-btn {
        padding: 10px 20px;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
      }

      .dm-btn:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
      }

      .dm-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .dm-btn-primary {
        background: #E21A34;
        color: white;
      }

      .dm-btn-primary:hover:not(:disabled) {
        background: #c9162e;
      }

      .dm-btn-secondary {
        background: #f5f5f5;
        color: #666;
      }

      .dm-btn-secondary:hover:not(:disabled) {
        background: #e0e0e0;
      }

      .dm-btn-secondary:hover:not(:disabled) {
        background: #e0e0e0;
      }

      .dm-btn-danger {
        background: #dc3545;
        color: white;
      }

      .dm-btn-danger:hover:not(:disabled) {
        background: #c82333;
      }

      .dm-btn-info {
        background: #2563eb;
        color: white;
      }

      .dm-btn-info:hover:not(:disabled) {
        background: #1d4ed8;
      }

      /* Loading Spinner */
      .dm-loading {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
      }

      .dm-spinner {
        width: 50px;
        height: 50px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #E21A34;
        border-radius: 50%;
        animation: dm-spin 1s linear infinite;
      }

      .dm-loading-text {
        color: #666;
        font-size: 14px;
      }

      /* Toast Container */
      .dm-toast-container {
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10000;
        display: flex;
        flex-direction: column;
        gap: 10px;
        align-items: center;
      }

      .dm-toast {
        background: white;
        border-radius: 8px;
        padding: 16px 24px;
        min-width: 300px;
        max-width: 500px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        gap: 12px;
        animation: dm-toastSlide 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        position: relative;
        overflow: hidden;
      }

      .dm-toast::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
      }

      .dm-toast.success {
        background: #22c55e;
        color: white;
      }

      .dm-toast.success::before {
        background: #16a34a;
      }

      .dm-toast.error {
        background: #ef4444;
        color: white;
      }

      .dm-toast.error::before {
        background: #dc2626;
      }

      .dm-toast.warning {
        background: #f59e0b;
        color: white;
      }

      .dm-toast.warning::before {
        background: #d97706;
      }

      .dm-toast.info {
        background: #3b82f6;
        color: white;
      }

      .dm-toast.info::before {
        background: #2563eb;
      }

      .dm-toast-icon {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        font-weight: bold;
        flex-shrink: 0;
        background: rgba(255, 255, 255, 0.2);
      }

      .dm-toast-content {
        flex: 1;
      }

      .dm-toast-message {
        font-size: 14px;
        font-weight: 500;
      }

      .dm-toast-close {
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 20px;
        padding: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0.8;
        transition: opacity 0.2s;
      }

      .dm-toast-close:hover {
        opacity: 1;
      }

      /* Ripple Effect */
      .dm-toast.ripple {
        overflow: hidden;
      }

      .dm-ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: dm-ripple-animation 0.6s ease-out;
        pointer-events: none;
      }

      @keyframes dm-fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
      }

      @keyframes dm-slideUp {
        from {
          opacity: 0;
          transform: translateY(20px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      @keyframes dm-toastSlide {
        from {
          opacity: 0;
          transform: translateY(-20px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      @keyframes dm-toastFadeOut {
        from {
          opacity: 1;
          transform: translateY(0);
        }
        to {
          opacity: 0;
          transform: translateY(-20px);
        }
      }

      @keyframes dm-spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }

      @keyframes dm-ripple-animation {
        to {
          transform: scale(4);
          opacity: 0;
        }
      }
    `;
    document.head.appendChild(style);
  };

  // Create toast container if not exists
  const getToastContainer = () => {
    let container = document.getElementById('dm-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'dm-toast-container';
      container.className = 'dm-toast-container';
      document.body.appendChild(container);
    }
    return container;
  };

  // Show loading dialog
  const showLoading = (message = 'Processing...', subtitle = 'Please wait') => {
    injectStyles();

    // Remove any existing overlay to prevent stacking
    const existingOverlay = document.querySelector('.dm-overlay');
    if (existingOverlay) {
      existingOverlay.remove();
    }

    const overlay = document.createElement('div');
    overlay.className = 'dm-overlay';
    overlay.id = 'dm-loading-overlay';

    overlay.innerHTML = `
      <div class="dm-dialog">
        <div class="dm-loading">
          <div class="dm-spinner"></div>
          <div>
            <div class="dm-title" style="text-align: center; margin-bottom: 8px;">${message}</div>
            <div class="dm-loading-text" style="text-align: center;">${subtitle}</div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    return overlay;
  };

  // Close loading dialog
  const closeLoading = () => {
    const overlay = document.getElementById('dm-loading-overlay');
    if (overlay) {
      overlay.style.animation = 'dm-fadeIn 0.2s ease reverse';
      setTimeout(() => overlay.remove(), 200);
    }
  };

  // Show dialog
  const showDialog = (options) => {
    injectStyles();

    // Remove any existing overlay (loading or dialog) to prevent stacking
    const existingOverlay = document.querySelector('.dm-overlay');
    if (existingOverlay) {
      existingOverlay.remove();
    }

    const {
      type = 'confirm',
      title = 'Are you sure?',
      message = '',
      confirmText = 'Yes',
      denyText = '',
      cancelText = 'Cancel',
      confirmButtonClass = 'dm-btn-primary',
      onConfirm = () => { },
      onDeny = () => { },
      onCancel = () => { },
      reverseButtons = true,
      allowOutsideClick = false
    } = options;

    const icons = {
      confirm: '⚠️',
      alert: 'ℹ️',
      warning: '⚠️',
      error: '❌',
      question: '❓'
    };

    const overlay = document.createElement('div');
    overlay.className = 'dm-overlay';

    // Buttons Construction
    const cancelBtn = `<button class="dm-btn dm-btn-secondary" data-action="cancel">${cancelText}</button>`;
    const confirmBtn = `<button class="dm-btn ${confirmButtonClass}" data-action="confirm">${confirmText}</button>`;
    const denyBtn = denyText ? `<button class="dm-btn dm-btn-danger" data-action="deny">${denyText}</button>` : '';

    // Order: Cancel | Deny | Confirm (if reverse)
    let buttonsHtml = '';
    if (reverseButtons) {
      buttonsHtml = `${cancelBtn}${denyBtn}${confirmBtn}`;
    } else {
      buttonsHtml = `${confirmBtn}${denyBtn}${cancelBtn}`;
    }

    // For Alert type - only confirm
    if (type === 'alert' || type === 'error' || type === 'warning') {
      buttonsHtml = `<button class="dm-btn dm-btn-primary" data-action="confirm">OK</button>`;
    }

    overlay.innerHTML = `
      <div class="dm-dialog">
        <div class="dm-header">
          <div class="dm-icon ${type}">${icons[type] || icons.confirm}</div>
          <h3 class="dm-title">${title}</h3>
        </div>
        ${message ? `<div class="dm-message">${message}</div>` : ''}
        <div class="dm-buttons">
          ${buttonsHtml}
        </div>
      </div>
    `;

    const close = () => {
      overlay.style.animation = 'dm-fadeIn 0.2s ease reverse';
      setTimeout(() => overlay.remove(), 200);
    };

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay && allowOutsideClick) close();

      const action = e.target.dataset.action;
      if (action === 'confirm') {
        close();
        onConfirm();
      } else if (action === 'deny') {
        close();
        onDeny();
      } else if (action === 'cancel') {
        close();
        onCancel();
      }
    });

    document.body.appendChild(overlay);
  };

  // Show toast with ripple effect
  const showToast = (options) => {
    injectStyles();

    const {
      type = 'success',
      message = 'Success',
      duration = 3000,
      ripple = true
    } = options;

    const icons = {
      success: '✓',
      error: '✕',
      warning: '!',
      info: 'i'
    };

    const container = getToastContainer();
    const toast = document.createElement('div');
    toast.className = `dm-toast ${type}${ripple ? ' ripple' : ''}`;

    toast.innerHTML = `
      <div class="dm-toast-icon">${icons[type]}</div>
      <div class="dm-toast-content">
        <div class="dm-toast-message">${message}</div>
      </div>
      <button class="dm-toast-close">×</button>
    `;

    // Ripple effect on toast appearance
    if (ripple) {
      setTimeout(() => {
        const rippleEl = document.createElement('span');
        rippleEl.className = 'dm-ripple';
        rippleEl.style.left = '50%';
        rippleEl.style.top = '50%';
        rippleEl.style.width = rippleEl.style.height = '10px';
        toast.appendChild(rippleEl);
        setTimeout(() => rippleEl.remove(), 600);
      }, 100);
    }

    const remove = () => {
      toast.style.animation = 'dm-toastFadeOut 0.3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    };

    toast.querySelector('.dm-toast-close').addEventListener('click', remove);

    if (duration > 0) {
      setTimeout(remove, duration);
    }

    container.appendChild(toast);
  };

  // Main reusable function for AJAX actions
  const confirmAction = (options) => {
    const {
      title = "Are you sure?",
      text = "",
      confirmText = "Yes",
      cancelText = "Cancel",
      url,
      method = "POST",
      data = null,
      onSuccess = null,
      onError = null,
      reverseButtons = true,
      allowOutsideClick = false
    } = options;

    // if (!url) {
    //   console.error("URL missing for confirmAction");
    //   return;
    // }

    showDialog({
      type: 'confirm',
      title,
      message: text,
      confirmText,
      cancelText,
      reverseButtons,
      allowOutsideClick,
      onCancel: () => {
        // Dialog cancelled, do nothing
      },
      onConfirm: () => {
        // No URL → just execute callback
        if (!url) {
          if (onSuccess) onSuccess();
          return;
        }

        // Show loading
        showLoading("Processing...", "Please wait");

        // Prepare headers
        const headers = {
          "Content-Type": "application/json"
        };

        // Add CSRF token if available
        if (window.CSRF_TOKEN) {
          headers["X-CSRFToken"] = window.CSRF_TOKEN;
        }

        console.log("token", window.CSRF_TOKEN)

        // Make fetch request
        fetch(url, {
          method,
          headers,
          body: data ? JSON.stringify(data) : null
        })
          .then(res => res.json())
          .then(response => {
            closeLoading();

            // Handle both success formats: success: true OR status: 'success'
            if (response.success || response.status === 'success') {
              // Determine toast type from response
              let toastType = 'success';
              let toastDuration = 4000;

              // Check for custom toast type based on abrs_status
              if (response.abrs_status === 'internal_only') {
                toastType = 'warning';
                toastDuration = 5000;
              } else if (response.abrs_status === 'failed') {
                toastType = 'error';
                toastDuration = 5000;
              }

              showToast({
                type: toastType,
                message: response.message || "Success",
                duration: toastDuration,
                ripple: true
              });

              if (onSuccess) onSuccess(response);
            } else {
              showToast({
                type: 'error',
                message: response.message || "Failed",
                duration: 4000,
                ripple: true
              });

              if (onError) onError(response);
            }
          })
          .catch(err => {
            closeLoading();
            showToast({
              type: 'error',
              message: "Server error",
              duration: 3000,
              ripple: true
            });
            console.error(err);
          });
      }
    });
  };

  // Public API
  return {
    confirm: (options) => showDialog({ ...options, type: 'confirm' }),
    alert: (options) => showDialog({ ...options, type: 'alert' }),
    warning: (options) => showDialog({ ...options, type: 'warning' }),
    error: (options) => showDialog({ ...options, type: 'error' }),
    toast: showToast,
    loading: showLoading,
    closeLoading: closeLoading,
    confirmAction: confirmAction // Main AJAX function
  };
})();

if (typeof window !== 'undefined') {
  window.DialogManager = DialogManager;
}

// Example usage:
/*

// 1. AJAX Confirmation with automatic loading and toast (EXACT replacement for your function)
DialogManager.confirmAction({
  title: "Delete User?",
  text: "This action cannot be undone",
  confirmText: "Yes, Delete",
  cancelText: "Cancel",
  url: "/api/delete-user",
  method: "POST",
  data: { userId: 123 },
  reverseButtons: true,
  allowOutsideClick: false,
  onSuccess: (response) => {
    console.log("Success:", response);
    // Refresh table, redirect, etc.
    location.reload();
  },
  onError: (response) => {
    console.log("Error:", response);
  }
});

// 2. Simple confirmation dialog
DialogManager.confirm({
  title: 'Delete Item',
  message: 'Are you sure?',
  confirmText: 'Delete',
  cancelText: 'Cancel',
  reverseButtons: true,
  onConfirm: () => {
    console.log('Confirmed');
  },
  onCancel: () => {
    console.log('Cancelled');
  }
});

// 3. Direct toast notification
DialogManager.toast({
  type: 'success', // success, error, warning, info
  message: 'Operation completed successfully!',
  duration: 3000,
  ripple: true
});

// 4. Manual loading control
DialogManager.loading("Uploading...", "Please wait");
// ... do async work ...
DialogManager.closeLoading();

*/