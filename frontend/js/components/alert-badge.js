/**
 * Alert & Severity Badge Component
 */

import { escapeHtml } from '../utils.js';

const SEVERITY_CONFIG = {
  critical: { label: 'CRÍTICO', class: 'badge-critical', icon: '⛔' },
  high: { label: 'ALTO', class: 'badge-high', icon: '⚠️' },
  medium: { label: 'MEDIO', class: 'badge-medium', icon: '⚡' },
  low: { label: 'BAJO', class: 'badge-low', icon: '🔹' },
  info: { label: 'INFO', class: 'badge-info', icon: 'ℹ️' },
  success: { label: 'ÉXITO', class: 'badge-success', icon: '✓' },
  ok: { label: 'ÓPTIMO', class: 'badge-success', icon: '✓' },
  warning: { label: 'ADVERTENCIA', class: 'badge-medium', icon: '⚠️' },
  error: { label: 'ERROR', class: 'badge-critical', icon: '⛔' },
  pendiente: { label: 'PENDIENTE', class: 'badge-medium', icon: '⏳' },
  aprobada: { label: 'APROBADA', class: 'badge-low', icon: '✓' },
  rechazada: { label: 'RECHAZADA', class: 'badge-neutral', icon: '✕' },
  ejecutada: { label: 'EJECUTADA', class: 'badge-success', icon: '✓' },
  fallida: { label: 'FALLIDA', class: 'badge-critical', icon: '!' },
  caducada: { label: 'CADUCADA', class: 'badge-striped', icon: '⏱' }
};

/**
 * Returns HTML string for an alert/severity badge
 * @param {string} severity 
 * @param {string} customLabel 
 * @param {boolean} showIcon 
 * @returns {string}
 */
export function createSeverityBadge(severity, customLabel = null, showIcon = true) {
  const norm = (severity || 'info').toLowerCase();
  const cfg = SEVERITY_CONFIG[norm] || { label: norm.toUpperCase(), class: 'badge-info', icon: 'ℹ️' };
  const label = customLabel || cfg.label;

  return `
    <span class="badge ${cfg.class}">
      ${showIcon ? `<span class="badge-icon" aria-hidden="true">${cfg.icon}</span>` : ''}
      <span>${escapeHtml(label)}</span>
    </span>
  `;
}
