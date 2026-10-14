/**
 * Loading Spinners, Skeletons & State Indicators
 */

import { escapeHtml } from '../utils.js';

/**
 * Returns HTML string for a centered spinner
 * @param {string} text 
 * @returns {string}
 */
export function createLoadingSpinner(text = 'Cargando telemetría de seguridad...') {
  return `
    <div class="state-container">
      <div class="spinner spinner-lg"></div>
      <p class="mt-4 text-secondary">${escapeHtml(text)}</p>
    </div>
  `;
}

/**
 * Returns HTML string for skeleton metric cards
 * @param {number} count 
 * @returns {string}
 */
export function createMetricSkeletons(count = 4) {
  let html = `<div class="grid-${count}">`;
  for (let i = 0; i < count; i++) {
    html += `
      <div class="card metric-card">
        <div class="skeleton skeleton-text short" style="height: 12px; margin-bottom: 14px;"></div>
        <div class="skeleton skeleton-text" style="height: 28px; width: 70%; margin-bottom: 12px;"></div>
        <div class="skeleton skeleton-text short" style="height: 10px;"></div>
      </div>
    `;
  }
  html += `</div>`;
  return html;
}

/**
 * Returns HTML string for skeleton table rows
 * @param {number} rows 
 * @param {number} cols 
 * @returns {string}
 */
export function createTableSkeleton(rows = 5, cols = 4) {
  let rowHtml = '';
  for (let i = 0; i < rows; i++) {
    rowHtml += `
      <tr>
        ${Array.from({ length: cols }).map(() => `
          <td><div class="skeleton skeleton-text" style="height: 14px; margin: 0;"></div></td>
        `).join('')}
      </tr>
    `;
  }

  return `
    <div class="table-responsive">
      <table class="data-table">
        <tbody>
          ${rowHtml}
        </tbody>
      </table>
    </div>
  `;
}

/**
 * Returns HTML string for an Error state with a retry button
 * @param {Object} options
 * @param {string} options.title
 * @param {string} options.message
 * @param {string} options.retryId ID of button for binding
 * @returns {string}
 */
export function createErrorState({
  title = 'Error de Conexión',
  message = 'No se ha podido sincronizar con la API de seguridad del servidor.',
  retryId = 'btn-retry-action'
} = {}) {
  return `
    <div class="card">
      <div class="state-container">
        <div class="state-icon text-rose">⚠️</div>
        <h3 class="state-title">${escapeHtml(title)}</h3>
        <p class="state-desc">${escapeHtml(message)}</p>
        <button id="${retryId}" class="btn btn-primary">
          <span>🔄</span>
          <span>Reintentar Conexión</span>
        </button>
      </div>
    </div>
  `;
}

/**
 * Returns HTML string for an empty state
 * @param {Object} options
 * @param {string} options.title
 * @param {string} options.message
 * @param {string} options.icon
 * @returns {string}
 */
export function createEmptyState({
  title = 'Sin Datos Registrados',
  message = 'Actualmente no hay elementos disponibles en este apartado.',
  icon = '📋'
} = {}) {
  return `
    <div class="state-container">
      <div class="state-icon">${icon}</div>
      <h3 class="state-title">${escapeHtml(title)}</h3>
      <p class="state-desc">${escapeHtml(message)}</p>
    </div>
  `;
}
