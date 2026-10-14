/**
 * Toast Notification System
 */

import { escapeHtml } from '../utils.js';

let container = null;

function getToastContainer() {
  if (!container || !document.body.contains(container)) {
    container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
  }
  return container;
}

const TOAST_ICONS = {
  success: '✓',
  error: '✕',
  warning: '⚠️',
  info: 'ℹ️'
};

/**
 * Display a toast notification
 * @param {Object} options
 * @param {string} options.title
 * @param {string} options.message
 * @param {'success'|'error'|'warning'|'info'} options.type
 * @param {number} options.duration ms
 */
export function showToast({
  title = '',
  message = '',
  type = 'info',
  duration = 4500
} = {}) {
  const root = getToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const icon = TOAST_ICONS[type] || 'ℹ️';

  toast.innerHTML = `
    <div class="toast-icon">${icon}</div>
    <div class="toast-content">
      ${title ? `<div class="toast-title">${escapeHtml(title)}</div>` : ''}
      <div class="toast-message">${escapeHtml(message)}</div>
    </div>
    <button class="toast-close" aria-label="Cerrar notificación">&times;</button>
  `;

  root.appendChild(toast);

  const closeBtn = toast.querySelector('.toast-close');
  const dismiss = () => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 200);
  };

  closeBtn.addEventListener('click', dismiss);

  if (duration > 0) {
    setTimeout(dismiss, duration);
  }
}
