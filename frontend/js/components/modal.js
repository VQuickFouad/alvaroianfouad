/**
 * Reusable Modal Dialog Component
 */

import { escapeHtml } from '../utils.js';

let activeCloseCallback = null;

/**
 * Open a modal window
 * @param {Object} options
 * @param {string} options.title
 * @param {string} options.content HTML content
 * @param {string} options.footer HTML buttons or actions
 * @param {string} options.maxWidth e.g. '700px'
 * @param {() => void} options.onClose
 */
export function openModal({
  title = '',
  content = '',
  footer = '',
  maxWidth = '650px',
  onClose = null
} = {}) {
  let backdrop = document.getElementById('modal-backdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.id = 'modal-backdrop';
    backdrop.className = 'modal-backdrop';
    document.body.appendChild(backdrop);
  }

  activeCloseCallback = onClose;

  backdrop.innerHTML = `
    <div class="modal-window" style="max-width: ${maxWidth};" role="dialog" aria-modal="true" aria-labelledby="modal-header-title">
      <div class="modal-header">
        <h3 class="modal-title" id="modal-header-title">${title}</h3>
        <button class="modal-close" id="modal-close-btn" aria-label="Cerrar modal">&times;</button>
      </div>
      <div class="modal-body">
        ${content}
      </div>
      ${footer ? `<div class="modal-footer">${footer}</div>` : ''}
    </div>
  `;

  // Animate in
  requestAnimationFrame(() => {
    backdrop.classList.add('show');
  });

  // Attach event handlers
  const closeBtn = backdrop.querySelector('#modal-close-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', closeModal);
  }

  backdrop.onclick = (e) => {
    if (e.target === backdrop) {
      closeModal();
    }
  };

  document.addEventListener('keydown', handleEscKey);
}

/**
 * Close currently active modal
 */
export function closeModal() {
  const backdrop = document.getElementById('modal-backdrop');
  if (!backdrop) return;

  backdrop.classList.remove('show');
  document.removeEventListener('keydown', handleEscKey);

  if (activeCloseCallback) {
    try {
      activeCloseCallback();
    } catch (err) {
      console.error('Error in modal onClose:', err);
    }
    activeCloseCallback = null;
  }

  setTimeout(() => {
    if (backdrop && !backdrop.classList.contains('show')) {
      backdrop.innerHTML = '';
    }
  }, 250);
}

function handleEscKey(e) {
  if (e.key === 'Escape') {
    closeModal();
  }
}
