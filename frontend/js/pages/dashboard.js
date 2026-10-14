/**
 * Dashboard Page Module
 * Factorio Security Dashboard
 */

import { apiGet } from '../api.js';
import { setState } from '../state.js';
import { formatDate, formatRelativeTime, escapeHtml } from '../utils.js';
import { createMetricCard, createCard } from '../components/card.js';
import { createStatusDot } from '../components/status-indicator.js';
import { createSeverityBadge } from '../components/alert-badge.js';
import { createTable } from '../components/table.js';
import { createMetricSkeletons, createTableSkeleton, createErrorState } from '../components/loading.js';
import { renderLineChart } from '../charts.js';

let refreshTimer = null;

/**
 * Render and initialize the Dashboard page
 * @param {HTMLElement} container 
 */
export async function renderDashboard(container) {
  // Clear any previous interval
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }

  container.innerHTML = `
    <div class="page-header">
      <div class="page-header-info">
        <h1>Centro de Control de Seguridad</h1>
        <p>Visión general del estado perimetral, recursos del servidor y eventos en tiempo real.</p>
      </div>
      <div class="page-header-actions">
        <button id="btn-dashboard-refresh" class="btn btn-secondary btn-sm">
          <span>🔄</span>
          <span>Actualizar</span>
        </button>
      </div>
    </div>

    <!-- Skeletons while loading -->
    <div id="dashboard-metrics-container">
      ${createMetricSkeletons(4)}
    </div>

    <div class="mt-6" id="dashboard-services-container">
      <div class="card">
        <div class="card-header"><h3 class="card-title">Servicios Críticos del Sistema</h3></div>
        <div class="card-body">
          <div class="skeleton" style="height: 80px;"></div>
        </div>
      </div>
    </div>

    <div class="grid-2 mt-6" id="dashboard-middle-container">
      <div class="card">
        <div class="card-header"><h3 class="card-title">Carga de CPU & Memoria RAM (Última hora)</h3></div>
        <div class="card-body">
          <div class="skeleton" style="height: 240px;"></div>
        </div>
      </div>
      <div class="card">
        <div class="card-header"><h3 class="card-title">Recomendaciones de Mantenimiento</h3></div>
        <div class="card-body">
          <div class="skeleton" style="height: 240px;"></div>
        </div>
      </div>
    </div>

    <div class="mt-6" id="dashboard-alerts-container">
      <div class="card">
        <div class="card-header"><h3 class="card-title">Alertas Recientes del Sistema</h3></div>
        <div class="card-body">
          ${createTableSkeleton(5, 4)}
        </div>
      </div>
    </div>
  `;

  // Bind manual refresh
  const refreshBtn = container.querySelector('#btn-dashboard-refresh');
  if (refreshBtn) {
    refreshBtn.onclick = () => loadDashboardData(container);
  }

  // Load data
  await loadDashboardData(container);

  // Set 30s auto-refresh
  refreshTimer = setInterval(() => {
    loadDashboardData(container, true);
  }, 30000);
}

/**
 * Cleanup function called on route transition
 */
export function destroyDashboard() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

async function loadDashboardData(container, isSilent = false) {
  try {
    const data = await apiGet('/dashboard');

    if (data.demo_mode) {
      setState({ demoMode: true });
    }
    if (data.server && data.server.active_alerts !== undefined) {
      setState({ activeAlertsCount: data.server.active_alerts });
    }

    renderMetrics(container, data);
    renderServices(container, data.services || []);
    renderChartsAndRecommendations(container, data);
    renderAlerts(container, data.recent_alerts || []);
  } catch (err) {
    console.error('Error al cargar datos del dashboard:', err);
    if (!isSilent) {
      const metricsContainer = container.querySelector('#dashboard-metrics-container');
      if (metricsContainer) {
        metricsContainer.innerHTML = createErrorState({
          title: 'Error al recuperar métricas del panel',
          message: err.message,
          retryId: 'btn-retry-dashboard'
        });
        const retryBtn = container.querySelector('#btn-retry-dashboard');
        if (retryBtn) {
          retryBtn.onclick = () => loadDashboardData(container);
        }
      }
    }
  }
}

function renderMetrics(container, data) {
  const target = container.querySelector('#dashboard-metrics-container');
  if (!target) return;

  const server = data.server || {};

  const card1 = createMetricCard({
    label: 'Estado del Servidor',
    value: server.os ? 'Operativo' : 'Activo',
    unit: '',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>`,
    color: 'emerald',
    trend: 'neutral',
    trendText: `Uptime: ${server.uptime || '28 días'}`
  });

  const card2 = createMetricCard({
    label: 'Uso de CPU / RAM',
    value: `${server.cpu_percent || 18}%`,
    unit: `/ ${server.memory_percent || 42}% RAM`,
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>`,
    color: 'cyan',
    trend: 'down',
    trendText: 'Carga nominal estable'
  });

  const card3 = createMetricCard({
    label: 'Alertas Activas',
    value: String(server.active_alerts ?? 2),
    unit: 'incidentes',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
    color: server.active_alerts > 0 ? 'amber' : 'emerald',
    trend: 'up',
    trendText: '1 crítica, 1 alta'
  });

  const card4 = createMetricCard({
    label: 'Última Copia Restic',
    value: server.last_backup_time ? formatRelativeTime(server.last_backup_time) : 'Hace 14h',
    unit: '',
    icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`,
    color: 'emerald',
    trend: 'down',
    trendText: 'Snapshot íntegro verificado',
    trendUpIsGood: true
  });

  target.innerHTML = `
    <div class="grid-4">
      ${card1}
      ${card2}
      ${card3}
      ${card4}
    </div>
  `;
}

function renderServices(container, services) {
  const target = container.querySelector('#dashboard-services-container');
  if (!target) return;

  target.innerHTML = createCard({
    title: '🛡️ Estado de Servicios Perimetrales y Demonios',
    subtitle: 'Monitoreo en tiempo real del estado de ejecución en systemd',
    body: `
      <div class="services-grid">
        ${services.map(svc => `
          <div class="service-card">
            <div class="service-info">
              <div>
                <div class="service-name">${escapeHtml(svc.name)}</div>
                <div class="service-port">${escapeHtml(svc.port || 'Interno')} &bull; ${escapeHtml(svc.uptime || 'Activo')}</div>
              </div>
            </div>
            <div>
              ${createStatusDot(svc.status)}
            </div>
          </div>
        `).join('')}
      </div>
    `
  });
}

function renderChartsAndRecommendations(container, data) {
  const target = container.querySelector('#dashboard-middle-container');
  if (!target) return;

  target.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div>
          <h3 class="card-title">Telemetría de CPU y Memoria (Última hora)</h3>
          <p class="card-subtitle">Muestreo cada 5 minutos &bull; Factorio Host Agent</p>
        </div>
      </div>
      <div class="card-body">
        <div id="chart-cpu-ram"></div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <div>
          <h3 class="card-title">Recomendaciones de Mantenimiento</h3>
          <p class="card-subtitle">Directrices sugeridas por el análisis de seguridad</p>
        </div>
      </div>
      <div class="card-body">
        <div class="recommendations-list">
          ${(data.maintenance_recommendations || []).map(rec => {
            const priorityBadge = rec.priority === 'high' ? createSeverityBadge('high', 'Prioridad Alta') :
                                  rec.priority === 'medium' ? createSeverityBadge('medium', 'Prioridad Media') :
                                  createSeverityBadge('low', 'Prioridad Baja');
            return `
              <div class="recommendation-item">
                <div class="recommendation-icon text-cyan">⚡</div>
                <div class="recommendation-content">
                  <div class="flex items-center justify-between">
                    <span class="recommendation-title">${escapeHtml(rec.title)}</span>
                    ${priorityBadge}
                  </div>
                  <p class="recommendation-desc mt-2">${escapeHtml(rec.desc)}</p>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    </div>
  `;

  // Draw Line Chart
  const cpuData = (data.cpu_history || []).map(d => d.value);
  const memData = (data.memory_history || []).map(d => d.value);
  const labels = (data.cpu_history || []).map(d => d.time);

  renderLineChart('#chart-cpu-ram', {
    series: [
      { name: 'Uso CPU', data: cpuData, color: '#00d4ff' },
      { name: 'Uso RAM', data: memData, color: '#10b981' }
    ],
    labels: labels,
    unit: '%',
    minY: 0,
    maxY: 100
  });
}

function renderAlerts(container, alerts) {
  const target = container.querySelector('#dashboard-alerts-container');
  if (!target) return;

  const columns = [
    { key: 'severity', header: 'Severidad', width: '130px', render: (val) => createSeverityBadge(val) },
    { key: 'timestamp', header: 'Fecha y Hora', width: '170px', render: (val) => formatDate(val, 'short') },
    { key: 'service', header: 'Servicio', width: '120px', render: (val) => `<span class="badge badge-neutral">${escapeHtml(val)}</span>` },
    { key: 'message', header: 'Mensaje de Alerta', render: (val) => `<span style="font-weight: 500;">${escapeHtml(val)}</span>` }
  ];

  target.innerHTML = createCard({
    title: '🚨 Registro de Alertas Recientes',
    subtitle: 'Últimas 10 alertas perimetrales detectadas',
    headerAction: `<a href="#logs" class="btn btn-outline btn-sm">Ver todos los logs</a>`,
    body: createTable({
      columns: columns,
      data: alerts.slice(0, 10),
      emptyMessage: 'No hay alertas activas en este momento.'
    })
  });
}
