/**
 * Status Indicator Component (LED dot / signal indicator)
 */

import { escapeHtml } from '../utils.js';

const STATUS_LABELS = {
  active: 'Activo',
  online: 'En Línea',
  running: 'En Ejecución',
  success: 'Correcto',
  healthy: 'Saludable',
  warning: 'Advertencia',
  pendiente: 'Pendiente',
  inactive: 'Inactivo',
  offline: 'Desconectado',
  danger: 'Crítico',
  error: 'Fallo',
  unknown: 'Desconocido'
};

/**
 * Returns HTML string for a colored status dot with label
 * @param {string} status 'active' | 'inactive' | 'warning' | 'unknown' etc.
 * @param {string} customLabel optional custom text
 * @param {boolean} pulse animate subtle ripple pulse
 * @returns {string}
 */
export function createStatusDot(status = 'active', customLabel = null, pulse = true) {
  const norm = (status || 'unknown').toLowerCase();
  let dotClass = 'unknown';

  if (['active', 'online', 'running', 'success', 'healthy', 'ok'].includes(norm)) {
    dotClass = 'active';
  } else if (['warning', 'pendiente', 'warning'].includes(norm)) {
    dotClass = 'warning';
  } else if (['inactive', 'offline', 'danger', 'error', 'critical', 'failed'].includes(norm)) {
    dotClass = 'inactive';
  }

  const label = customLabel || STATUS_LABELS[norm] || norm;
  const pulseClass = pulse ? 'pulse' : '';

  return `
    <span class="status-indicator">
      <span class="status-dot ${dotClass} ${pulseClass}" aria-hidden="true"></span>
      <span>${escapeHtml(label)}</span>
    </span>
  `;
}
