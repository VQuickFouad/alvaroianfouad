/**
 * Logs Page Module
 * Factorio Security Dashboard
 */

import { apiGet } from '../api.js';
import { formatDate, escapeHtml, truncateText } from '../utils.js';
import { createCard } from '../components/card.js';
import { createSeverityBadge } from '../components/alert-badge.js';
import { createTable } from '../components/table.js';
import { createLoadingSpinner, createErrorState } from '../components/loading.js';
import { openModal } from '../components/modal.js';
import { showToast } from '../components/toast.js';

let allEntries = [];
let filteredEntries = [];
let currentPage = 1;
const pageSize = 8;

let currentFilters = {
  service: 'all',
  severity: 'all',
  search: ''
};

/**
 * Render Logs Page
 * @param {HTMLElement} container 
 */
export async function renderLogs(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-header-info">
        <h1>Visor y Auditoría de Registros del Sistema</h1>
        <p>Inspección centralizada de eventos de seguridad (syslog, auth.log, nginx, fail2ban y UFW).</p>
      </div>
      <div class="page-header-actions">
        <button id="btn-export-csv" class="btn btn-secondary btn-sm">
          <span>📥</span>
          <span>Exportar CSV</span>
        </button>
        <button id="btn-logs-refresh" class="btn btn-secondary btn-sm">
          <span>🔄</span>
          <span>Actualizar</span>
        </button>
      </div>
    </div>

    <!-- Stats Summary Row -->
    <div class="logs-stats-bar" id="logs-stats-container">
      <div class="skeleton" style="height: 60px; width: 100%;"></div>
    </div>

    <!-- Filter Bar -->
    <div class="logs-filter-bar">
      <div style="flex: 1; min-width: 220px;">
        <input type="text" id="filter-search" class="input" placeholder="Buscar texto, IP, mensaje..." value="${escapeHtml(currentFilters.search)}">
      </div>
      <div style="min-width: 160px;">
        <select id="filter-service" class="select">
          <option value="all">Todos los Servicios</option>
          <option value="fail2ban">fail2ban</option>
          <option value="sshd">sshd</option>
          <option value="ufw">ufw</option>
          <option value="nginx">nginx</option>
          <option value="crowdsec">crowdsec</option>
          <option value="kernel">kernel</option>
          <option value="systemd">systemd</option>
          <option value="restic">restic</option>
          <option value="postgresql">postgresql</option>
        </select>
      </div>
      <div style="min-width: 150px;">
        <select id="filter-severity" class="select">
          <option value="all">Cualquier Severidad</option>
          <option value="critical">Crítico</option>
          <option value="error">Error</option>
          <option value="warning">Advertencia</option>
          <option value="info">Informativo</option>
        </select>
      </div>
      <button id="btn-clear-filters" class="btn btn-outline btn-sm">Limpiar</button>
    </div>

    <!-- Table Container -->
    <div id="logs-table-container">
      ${createLoadingSpinner('Recuperando registros de auditoría...')}
    </div>
  `;

  // Attach event handlers
  const searchInput = container.querySelector('#filter-search');
  const serviceSelect = container.querySelector('#filter-service');
  const severitySelect = container.querySelector('#filter-severity');
  const clearBtn = container.querySelector('#btn-clear-filters');
  const exportBtn = container.querySelector('#btn-export-csv');
  const refreshBtn = container.querySelector('#btn-logs-refresh');

  if (searchInput) {
    searchInput.oninput = (e) => {
      currentFilters.search = e.target.value.toLowerCase();
      currentPage = 1;
      applyFilters(container);
    };
  }

  if (serviceSelect) {
    serviceSelect.onchange = (e) => {
      currentFilters.service = e.target.value;
      currentPage = 1;
      applyFilters(container);
    };
  }

  if (severitySelect) {
    severitySelect.onchange = (e) => {
      currentFilters.severity = e.target.value;
      currentPage = 1;
      applyFilters(container);
    };
  }

  if (clearBtn) {
    clearBtn.onclick = () => {
      currentFilters = { service: 'all', severity: 'all', search: '' };
      if (searchInput) searchInput.value = '';
      if (serviceSelect) serviceSelect.value = 'all';
      if (severitySelect) severitySelect.value = 'all';
      currentPage = 1;
      applyFilters(container);
    };
  }

  if (exportBtn) {
    exportBtn.onclick = () => exportToCsv();
  }

  if (refreshBtn) {
    refreshBtn.onclick = () => loadLogsData(container);
  }

  await loadLogsData(container);
}

export function destroyLogs() {
  allEntries = [];
  filteredEntries = [];
}

async function loadLogsData(container) {
  try {
    const data = await apiGet('/logs');
    allEntries = data.entries || [];
    renderStats(container, data.stats || {});
    applyFilters(container);
  } catch (err) {
    const tableContainer = container.querySelector('#logs-table-container');
    if (tableContainer) {
      tableContainer.innerHTML = createErrorState({
        title: 'Error al recuperar registros de auditoría',
        message: err.message,
        retryId: 'btn-retry-logs'
      });
      const retryBtn = container.querySelector('#btn-retry-logs');
      if (retryBtn) {
        retryBtn.onclick = () => loadLogsData(container);
      }
    }
  }
}

function renderStats(container, stats) {
  const statsWrap = container.querySelector('#logs-stats-container');
  if (!statsWrap) return;

  statsWrap.innerHTML = `
    <div class="log-stat-pill">
      <span class="log-stat-num text-cyan">${(stats.total || allEntries.length).toLocaleString()}</span>
      <span class="log-stat-title">Total Registros</span>
    </div>
    <div class="log-stat-pill">
      <span class="log-stat-num text-rose">${stats.critical || 0}</span>
      <span class="log-stat-title">Críticos</span>
    </div>
    <div class="log-stat-pill">
      <span class="log-stat-num" style="color: #fb923c;">${stats.error || 0}</span>
      <span class="log-stat-title">Errores</span>
    </div>
    <div class="log-stat-pill">
      <span class="log-stat-num text-amber">${stats.warning || 0}</span>
      <span class="log-stat-title">Advertencias</span>
    </div>
    <div class="log-stat-pill">
      <span class="log-stat-num text-emerald">${(stats.info || 0).toLocaleString()}</span>
      <span class="log-stat-title">Informativos</span>
    </div>
  `;
}

function applyFilters(container) {
  filteredEntries = allEntries.filter(item => {
    // Service filter
    if (currentFilters.service !== 'all' && item.service.toLowerCase() !== currentFilters.service.toLowerCase()) {
      return false;
    }
    // Severity filter
    if (currentFilters.severity !== 'all' && item.severity.toLowerCase() !== currentFilters.severity.toLowerCase()) {
      return false;
    }
    // Search query
    if (currentFilters.search) {
      const matchMsg = item.message && item.message.toLowerCase().includes(currentFilters.search);
      const matchSvc = item.service && item.service.toLowerCase().includes(currentFilters.search);
      const matchHost = item.host && item.host.toLowerCase().includes(currentFilters.search);
      const matchDet = item.details && item.details.toLowerCase().includes(currentFilters.search);
      if (!matchMsg && !matchSvc && !matchHost && !matchDet) {
        return false;
      }
    }
    return true;
  });

  renderTable(container);
}

function renderTable(container) {
  const tableWrap = container.querySelector('#logs-table-container');
  if (!tableWrap) return;

  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const pageEntries = filteredEntries.slice(startIndex, startIndex + pageSize);

  const columns = [
    { key: 'severity', header: 'Severidad', width: '120px', render: (val) => createSeverityBadge(val) },
    { key: 'timestamp', header: 'Timestamp', width: '160px', render: (val) => formatDate(val, 'short') },
    { key: 'service', header: 'Servicio', width: '120px', render: (val) => `<span class="badge badge-neutral">${escapeHtml(val)}</span>` },
    {
      key: 'message',
      header: 'Mensaje de Registro (Click para expandir)',
      render: (val) => `<div class="log-message-cell">${escapeHtml(val)}</div>`
    }
  ];

  const tableHtml = createTable({
    columns: columns,
    data: pageEntries,
    emptyMessage: 'No se encontraron registros que coincidan con los criterios de búsqueda.',
    rowClassName: 'log-row-clickable'
  });

  const paginationHtml = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px; padding:0 8px;">
      <span style="font-size:0.85rem; color:var(--text-secondary);">
        Mostrando ${filteredEntries.length > 0 ? startIndex + 1 : 0} a ${Math.min(startIndex + pageSize, filteredEntries.length)} de ${filteredEntries.length} registros
      </span>
      <div style="display:flex; gap:8px;">
        <button id="btn-page-prev" class="btn btn-secondary btn-sm" ${currentPage <= 1 ? 'disabled' : ''}>Anterior</button>
        <span style="display:inline-flex; align-items:center; font-size:0.85rem; padding:0 8px;">Página ${currentPage} de ${totalPages}</span>
        <button id="btn-page-next" class="btn btn-secondary btn-sm" ${currentPage >= totalPages ? 'disabled' : ''}>Siguiente</button>
      </div>
    </div>
  `;

  tableWrap.innerHTML = createCard({
    title: 'Detalle de Trazas de Seguridad',
    subtitle: 'Haga clic en cualquier fila para inspeccionar metadatos y payload completo',
    body: tableHtml + paginationHtml
  });

  // Attach pagination clicks
  const prevBtn = tableWrap.querySelector('#btn-page-prev');
  const nextBtn = tableWrap.querySelector('#btn-page-next');
  if (prevBtn) {
    prevBtn.onclick = () => {
      if (currentPage > 1) {
        currentPage--;
        renderTable(container);
      }
    };
  }
  if (nextBtn) {
    nextBtn.onclick = () => {
      if (currentPage < totalPages) {
        currentPage++;
        renderTable(container);
      }
    };
  }

  // Row click opens Modal
  const rows = tableWrap.querySelectorAll('.log-row-clickable');
  rows.forEach(row => {
    row.addEventListener('click', () => {
      const id = row.getAttribute('data-id');
      const entry = allEntries.find(e => String(e.id) === String(id)) || pageEntries[parseInt(id, 10)];
      if (entry) {
        openLogDetailModal(entry);
      }
    });
  });
}

function openLogDetailModal(entry) {
  openModal({
    title: `🔎 Evento de Auditoría: ${escapeHtml(entry.id || 'Registro')}`,
    content: `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; align-items:center; gap:8px;">
            ${createSeverityBadge(entry.severity)}
            <span class="badge badge-neutral">${escapeHtml(entry.service)}</span>
          </div>
          <span style="font-size:0.8rem; color:var(--text-muted);">${formatDate(entry.timestamp, 'full')}</span>
        </div>

        <div>
          <label class="form-label">Mensaje Completo:</label>
          <div style="background:var(--bg-input); border:1px solid var(--border-color); border-radius:6px; padding:12px; font-family:var(--font-mono); font-size:0.85rem; color:#fff; word-break:break-all;">
            ${escapeHtml(entry.message)}
          </div>
        </div>

        ${entry.details ? `
          <div>
            <label class="form-label">Contexto / Detalle Técnico:</label>
            <div style="background:rgba(15,23,42,0.8); border:1px solid var(--border-color); border-radius:6px; padding:12px; font-size:0.85rem; color:var(--text-secondary);">
              ${escapeHtml(entry.details)}
            </div>
          </div>
        ` : ''}

        <div class="grid-2">
          <div>
            <label class="form-label">Host de Origen:</label>
            <div class="code-font" style="font-size:0.85rem;">${escapeHtml(entry.host || 'factorio-prod-srv01')}</div>
          </div>
          <div>
            <label class="form-label">PID del Proceso:</label>
            <div class="code-font" style="font-size:0.85rem;">${escapeHtml(String(entry.pid || '1'))}</div>
          </div>
        </div>
      </div>
    `,
    footer: `
      <button class="btn btn-secondary btn-sm" onclick="document.getElementById('modal-close-btn').click();">Cerrar</button>
    `
  });
}

function exportToCsv() {
  if (!filteredEntries.length) {
    showToast({ title: 'Exportación', message: 'No hay datos filtrados para exportar.', type: 'warning' });
    return;
  }

  const headers = ['ID', 'Timestamp', 'Servicio', 'Severidad', 'Mensaje', 'Host', 'Detalles'];
  const rows = filteredEntries.map(e => [
    `"${e.id || ''}"`,
    `"${e.timestamp || ''}"`,
    `"${e.service || ''}"`,
    `"${e.severity || ''}"`,
    `"${(e.message || '').replace(/"/g, '""')}"`,
    `"${e.host || ''}"`,
    `"${(e.details || '').replace(/"/g, '""')}"`
  ]);

  const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', `factorio_logs_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  showToast({ title: 'Exportación Exitosa', message: `${filteredEntries.length} registros exportados a CSV.`, type: 'success' });
}
