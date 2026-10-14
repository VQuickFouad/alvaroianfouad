/**
 * Reusable Data Table Component
 */

import { escapeHtml } from '../utils.js';

/**
 * Generates an HTML data table with responsive wrapper
 * @param {Object} options
 * @param {Array<{ key: string, header: string, render?: (val: any, row: any) => string, className?: string, width?: string }>} options.columns
 * @param {Array<any>} options.data
 * @param {string} options.emptyMessage
 * @param {string} options.rowClassName
 * @param {string} options.rowIdPrefix
 * @returns {string} HTML string
 */
export function createTable({
  columns = [],
  data = [],
  emptyMessage = 'No se encontraron registros.',
  rowClassName = '',
  rowIdPrefix = 'row'
} = {}) {
  if (!data || data.length === 0) {
    return `
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              ${columns.map(col => `<th style="${col.width ? `width:${col.width};` : ''}">${escapeHtml(col.header)}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colspan="${columns.length}" style="text-align: center; padding: 36px 16px; color: var(--text-muted);">
                <div style="font-size: 1.5rem; margin-bottom: 8px;">📂</div>
                ${escapeHtml(emptyMessage)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  const thead = `
    <thead>
      <tr>
        ${columns.map(col => `<th class="${col.className || ''}" style="${col.width ? `width:${col.width};` : ''}">${escapeHtml(col.header)}</th>`).join('')}
      </tr>
    </thead>
  `;

  const rows = data.map((row, idx) => {
    const rowId = row.id ? `${rowIdPrefix}-${row.id}` : `${rowIdPrefix}-${idx}`;
    const cells = columns.map(col => {
      const val = row[col.key];
      const cellContent = col.render ? col.render(val, row) : escapeHtml(val ?? '—');
      return `<td class="${col.className || ''}">${cellContent}</td>`;
    }).join('');

    return `<tr class="${rowClassName}" data-id="${row.id || idx}" id="${rowId}">${cells}</tr>`;
  }).join('');

  return `
    <div class="table-responsive">
      <table class="data-table">
        ${thead}
        <tbody>
          ${rows}
        </tbody>
      </table>
    </div>
  `;
}
