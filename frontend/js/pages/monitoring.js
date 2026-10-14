/**
 * Monitoring Page Module
 * Factorio Security Dashboard
 */

import { apiGet } from '../api.js';
import { formatPercent, escapeHtml } from '../utils.js';
import { createCard } from '../components/card.js';
import { createTable } from '../components/table.js';
import { createLoadingSpinner, createErrorState } from '../components/loading.js';
import { renderLineChart, renderBarChart } from '../charts.js';

let selectedRange = '1h';

/**
 * Render Monitoring Page
 * @param {HTMLElement} container 
 */
export async function renderMonitoring(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-header-info">
        <h1>Monitorización y Rendimiento de Infraestructura</h1>
        <p>Telemetría en tiempo real: CPU, memoria, particiones de disco, tráfico de red y procesos activos.</p>
      </div>
      <div class="page-header-actions">
        <div class="filter-tabs" id="monitoring-time-tabs">
          <button class="filter-tab ${selectedRange === '1h' ? 'active' : ''}" data-range="1h">1h</button>
          <button class="filter-tab ${selectedRange === '6h' ? 'active' : ''}" data-range="6h">6h</button>
          <button class="filter-tab ${selectedRange === '24h' ? 'active' : ''}" data-range="24h">24h</button>
          <button class="filter-tab ${selectedRange === '7d' ? 'active' : ''}" data-range="7d">7d</button>
        </div>
      </div>
    </div>

    <div id="monitoring-content">
      ${createLoadingSpinner('Recopilando telemetría de monitoreo...')}
    </div>
  `;

  // Bind range selector tabs
  const tabs = container.querySelectorAll('.filter-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      selectedRange = tab.getAttribute('data-range');
      loadMonitoringData(container);
    });
  });

  await loadMonitoringData(container);
}

export function destroyMonitoring() {
  // cleanup if necessary
}

async function loadMonitoringData(container) {
  const content = container.querySelector('#monitoring-content');
  if (!content) return;

  try {
    const data = await apiGet(`/monitoring?range=${selectedRange}`);

    content.innerHTML = `
      <!-- Optional Netdata Integration Banner -->
      ${data.netdata_url ? `
        <div class="netdata-banner">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div style="font-size: 1.6rem; color: var(--accent-cyan);">⚡</div>
            <div>
              <div style="font-weight: 700; color: var(--text-primary);">Servidor Netdata Local Conectado</div>
              <div style="font-size: 0.8rem; color: var(--text-secondary);">Métricas de alta resolución por segundo disponibles en ${escapeHtml(data.netdata_url)}</div>
            </div>
          </div>
          <a href="${escapeHtml(data.netdata_url)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm">
            <span>Abrir Netdata</span>
            <span>↗</span>
          </a>
        </div>
      ` : ''}

      <!-- Top Row: CPU Usage & Memory Usage -->
      <div class="grid-2 mb-4">
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Carga de CPU (%)</h3>
              <p class="card-subtitle">Porcentaje de ocupación de núcleos</p>
            </div>
          </div>
          <div class="card-body">
            <div id="chart-cpu-usage"></div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Consumo de Memoria RAM</h3>
              <p class="card-subtitle">Uso de memoria residente vs total (16 GB)</p>
            </div>
          </div>
          <div class="card-body">
            <div id="chart-mem-usage"></div>
          </div>
        </div>
      </div>

      <!-- Middle Row: Disk Usage & Network I/O -->
      <div class="grid-2 mb-4">
        <!-- Disk Usage -->
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Ocupación de Disco por Partición</h3>
              <p class="card-subtitle">Almacenamiento montado en el servidor</p>
            </div>
          </div>
          <div class="card-body">
            <div id="chart-disk-partitions"></div>
            <div class="mt-4" style="display:flex; flex-direction:column; gap:8px;">
              ${(data.disk_partitions || []).map(p => `
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; border-bottom:1px solid rgba(255,255,255,0.04); padding-bottom:4px;">
                  <span class="code-font" style="font-weight:600; color:var(--text-primary);">${escapeHtml(p.mount)}</span>
                  <span style="color:var(--text-secondary);">${p.used_gb} GB de ${p.total_gb} GB (${p.percent}%)</span>
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <!-- Network I/O -->
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Tráfico de Red (Mbps)</h3>
              <p class="card-subtitle">Entrada (RX) vs Salida (TX) en interfaz eth0</p>
            </div>
          </div>
          <div class="card-body">
            <div id="chart-network-io"></div>
          </div>
        </div>
      </div>

      <!-- Bottom: Top 10 Processes Table -->
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Procesos Principales (Top 10 por uso de CPU)</h3>
            <p class="card-subtitle">Lectura directa desde el subsistema /proc en tiempo real</p>
          </div>
        </div>
        <div class="card-body">
          ${createTable({
            columns: [
              { key: 'pid', header: 'PID', width: '90px', className: 'cell-mono' },
              { key: 'name', header: 'Comando / Proceso', render: (val) => `<strong class="code-font" style="color:var(--accent-cyan);">${escapeHtml(val)}</strong>` },
              { key: 'user', header: 'Usuario', width: '130px', render: (val) => `<span class="badge badge-neutral">${escapeHtml(val)}</span>` },
              { key: 'cpu_percent', header: 'CPU %', width: '100px', render: (val) => `<span style="font-weight:700;">${val}%</span>` },
              { key: 'memory_percent', header: 'RAM %', width: '100px', render: (val) => `<span>${val}%</span>` },
              { key: 'status', header: 'Estado', width: '120px', render: (val) => `<span class="badge badge-success">${escapeHtml(val)}</span>` }
            ],
            data: data.processes || [],
            emptyMessage: 'No se encontraron procesos en ejecución.'
          })}
        </div>
      </div>
    `;

    // Render Charts
    if (data.cpu_usage) {
      renderLineChart('#chart-cpu-usage', {
        series: [{ name: 'CPU %', data: data.cpu_usage.map(d => d.value), color: '#00d4ff' }],
        labels: data.cpu_usage.map(d => d.time),
        unit: '%',
        minY: 0,
        maxY: 100
      });
    }

    if (data.memory_usage) {
      renderLineChart('#chart-mem-usage', {
        series: [
          { name: 'RAM %', data: data.memory_usage.map(d => d.percent), color: '#10b981' }
        ],
        labels: data.memory_usage.map(d => d.time),
        unit: '%',
        minY: 0,
        maxY: 100
      });
    }

    if (data.disk_partitions) {
      renderBarChart('#chart-disk-partitions', {
        data: data.disk_partitions.map(p => ({
          label: p.mount,
          value: p.percent,
          color: p.percent > 85 ? '#ef4444' : (p.percent > 75 ? '#f59e0b' : '#00d4ff')
        })),
        unit: '%'
      });
    }

    if (data.network_io) {
      renderLineChart('#chart-network-io', {
        series: [
          { name: 'Entrada (RX)', data: data.network_io.map(d => d.in_mbps), color: '#00d4ff' },
          { name: 'Salida (TX)', data: data.network_io.map(d => d.out_mbps), color: '#8b5cf6' }
        ],
        labels: data.network_io.map(d => d.time),
        unit: ' Mbps'
      });
    }

  } catch (err) {
    content.innerHTML = createErrorState({
      title: 'Error al recuperar telemetría de monitorización',
      message: err.message,
      retryId: 'btn-retry-monitoring'
    });
    const retryBtn = container.querySelector('#btn-retry-monitoring');
    if (retryBtn) {
      retryBtn.onclick = () => loadMonitoringData(container);
    }
  }
}
