/**
 * Card & Metric Card Components
 */

import { escapeHtml } from '../utils.js';

/**
 * Creates standard card markup
 * @param {Object} options
 * @returns {string} HTML string
 */
export function createCard({
  title = '',
  subtitle = '',
  headerAction = '',
  body = '',
  footer = '',
  className = '',
  id = ''
} = {}) {
  const hasHeader = title || subtitle || headerAction;
  
  return `
    <div class="card ${className}" ${id ? `id="${id}"` : ''}>
      ${hasHeader ? `
        <div class="card-header">
          <div>
            ${title ? `<h3 class="card-title">${title}</h3>` : ''}
            ${subtitle ? `<p class="card-subtitle">${subtitle}</p>` : ''}
          </div>
          ${headerAction ? `<div class="card-header-action">${headerAction}</div>` : ''}
        </div>
      ` : ''}
      <div class="card-body">
        ${body}
      </div>
      ${footer ? `
        <div class="card-footer">
          ${footer}
        </div>
      ` : ''}
    </div>
  `;
}

/**
 * Creates summary metric KPI card
 * @param {Object} options
 * @returns {string} HTML string
 */
export function createMetricCard({
  label = '',
  value = '',
  unit = '',
  icon = '',
  color = 'cyan', // cyan, emerald, amber, rose
  trend = null, // 'up' | 'down' | 'neutral'
  trendText = '',
  trendUpIsGood = false
} = {}) {
  let trendClass = 'trend-neutral';
  let trendArrow = '→';

  if (trend === 'up') {
    trendClass = trendUpIsGood ? 'trend-down' : 'trend-up'; // Note: in CSS, trend-down is emerald, trend-up is rose (alert/cpu)
    trendArrow = '↑';
  } else if (trend === 'down') {
    trendClass = trendUpIsGood ? 'trend-up' : 'trend-down';
    trendArrow = '↓';
  }

  return `
    <div class="card metric-card">
      <div class="metric-header">
        <span class="metric-label">${escapeHtml(label)}</span>
        <div class="metric-icon-wrap ${color}">
          ${icon}
        </div>
      </div>
      <div class="metric-value-wrap">
        <span class="metric-value">${escapeHtml(value)}</span>
        ${unit ? `<span class="metric-unit">${escapeHtml(unit)}</span>` : ''}
      </div>
      ${trendText ? `
        <div class="metric-trend ${trendClass}">
          <span>${trendArrow}</span>
          <span>${escapeHtml(trendText)}</span>
        </div>
      ` : ''}
    </div>
  `;
}
