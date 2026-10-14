/**
 * Security Page Module
 * Factorio Security Dashboard
 */

import { apiGet } from '../api.js';
import { formatDate, escapeHtml } from '../utils.js';
import { createCard } from '../components/card.js';
import { createStatusDot } from '../components/status-indicator.js';
import { createSeverityBadge } from '../components/alert-badge.js';
import { createTable } from '../components/table.js';
import { createLoadingSpinner, createErrorState } from '../components/loading.js';
import { renderBarChart, renderDonutChart } from '../charts.js';

let hardeningItems = [];

/**
 * Render Security Page
 * @param {HTMLElement} container 
 */
export async function renderSecurity(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-header-info">
        <h1>Seguridad Perimetral y Bastionado (Hardening)</h1>
        <p>Defensa en profundidad: cortafuegos, mitigación de intrusiones, políticas LSM y certificados criptográficos.</p>
      </div>
      <div class="page-header-actions">
        <button id="btn-security-refresh" class="btn btn-secondary btn-sm">
          <span>🔄</span>
          <span>Actualizar</span>
        </button>
      </div>
    </div>

    <div id="security-content">
      ${createLoadingSpinner('Analizando componentes de seguridad perimetral...')}
    </div>
  `;

  const refreshBtn = container.querySelector('#btn-security-refresh');
  if (refreshBtn) {
    refreshBtn.onclick = () => loadSecurityData(container);
  }

  await loadSecurityData(container);
}

export function destroySecurity() {
  hardeningItems = [];
}

async function loadSecurityData(container) {
  const content = container.querySelector('#security-content');
  if (!content) return;

  try {
    const data = await apiGet('/security');
    hardeningItems = data.hardening_checklist ? [...data.hardening_checklist] : [];

    content.innerHTML = `
      <!-- Security Services Grid -->
      <div class="security-status-grid">
        ${(data.services || []).map(svc => {
          const statusClass = svc.status === 'active' ? 'active' : (svc.status === 'warning' ? 'warning' : 'inactive');
          return `
            <div class="sec-service-card ${statusClass}">
              <div class="sec-card-header">
                <span class="sec-card-title">
                  <span>🛡️</span>
                  <span>${escapeHtml(svc.name)}</span>
                </span>
                ${createStatusDot(svc.status)}
              </div>
              <div class="sec-card-meta">
                <div class="sec-meta-row">
                  <span class="sec-meta-label">Configuración:</span>
                  <span style="font-weight: 500;">${escapeHtml(svc.config_summary || 'Estándar')}</span>
                </div>
                <div class="sec-meta-row">
                  <span class="sec-meta-label">Último evento:</span>
                  <span class="code-font" style="font-size: 0.78rem;">${escapeHtml(svc.last_event || 'Sin eventos')}</span>
                </div>
                ${svc.banned_ips_count !== undefined ? `
                  <div class="sec-meta-row">
                    <span class="sec-meta-label">IPs bloqueadas:</span>
                    <span class="badge badge-critical">${svc.banned_ips_count}</span>
                  </div>
                ` : ''}
              </div>
            </div>
          `;
        }).join('')}
      </div>

      <!-- Middle: Bar Chart & TLS Cert Card -->
      <div class="grid-2 mb-4">
        <!-- Failed Logins Chart -->
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Intentos de Autenticación Fallidos (Últimos 7 días)</h3>
              <p class="card-subtitle">Detección de ataques de fuerza bruta en servicio SSH</p>
            </div>
          </div>
          <div class="card-body">
            <div id="chart-failed-logins"></div>
          </div>
        </div>

        <!-- TLS Certificate & Hardening Score -->
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Certificado TLS & Resumen Criptográfico</h3>
              <p class="card-subtitle">Seguridad de la capa de transporte HTTPS</p>
            </div>
            ${data.tls_certificate ? (data.tls_certificate.days_remaining <= 15 ? createSeverityBadge('warning', 'Próximo a expirar') : createSeverityBadge('success', 'Válido')) : ''}
          </div>
          <div class="card-body">
            ${renderTlsCard(data.tls_certificate)}
          </div>
        </div>
      </div>

      <!-- Hardening Checklist & Events Table -->
      <div class="grid-2">
        <!-- Hardening Checklist -->
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Lista de Bastionado (CIS Benchmark)</h3>
              <p class="card-subtitle">Verificación de conformidad con estándares de seguridad Linux</p>
            </div>
            <span id="hardening-percent-badge" class="badge badge-info">75% Completado</span>
          </div>
          <div class="card-body">
            <div class="hardening-progress-wrap">
              <div class="progress-header">
                <span>Nivel de Bastionado</span>
                <span id="hardening-percent-text">75%</span>
              </div>
              <div class="progress-track">
                <div id="hardening-progress-bar" class="progress-fill" style="width: 75%;"></div>
              </div>
            </div>

            <div class="checklist-items" id="hardening-checklist-wrap">
              <!-- Dynamically populated -->
            </div>
          </div>
        </div>

        <!-- Security Events Table -->
        <div class="card">
          <div class="card-header">
            <div>
              <h3 class="card-title">Incidentes Perimetrales Recientes</h3>
              <p class="card-subtitle">Últimas acciones tomadas por el sistema defensivo</p>
            </div>
          </div>
          <div class="card-body">
            ${createTable({
              columns: [
                { key: 'severity', header: 'Severidad', width: '110px', render: (val) => createSeverityBadge(val) },
                { key: 'timestamp', header: 'Hora', width: '90px', render: (val) => formatDate(val, 'time') },
                { key: 'type', header: 'Amenaza', render: (val) => `<strong>${escapeHtml(val)}</strong>` },
                { key: 'source_ip', header: 'Origen IP', className: 'cell-mono', render: (val, r) => `${escapeHtml(val)} <span class="badge badge-neutral">${escapeHtml(r.country || 'EXT')}</span>` },
                { key: 'action', header: 'Mitigación', render: (val) => `<span class="badge badge-success">${escapeHtml(val)}</span>` }
              ],
              data: data.events || [],
              emptyMessage: 'No se registran incidentes sospechosos.'
            })}
          </div>
        </div>
      </div>
    `;

    // Render Bar Chart
    if (data.failed_logins_7d) {
      renderBarChart('#chart-failed-logins', {
        data: data.failed_logins_7d.map(item => ({
          label: item.date,
          value: item.count,
          color: item.count > 300 ? '#ef4444' : (item.count > 150 ? '#f59e0b' : '#00d4ff')
        })),
        unit: ' intentos'
      });
    }

    // Render interactive checklist
    renderChecklist(container);

  } catch (err) {
    content.innerHTML = createErrorState({
      title: 'Error al cargar telemetría de seguridad',
      message: err.message,
      retryId: 'btn-retry-security'
    });
    const retryBtn = container.querySelector('#btn-retry-security');
    if (retryBtn) {
      retryBtn.onclick = () => loadSecurityData(container);
    }
  }
}

function renderTlsCard(cert) {
  if (!cert) {
    return `<div class="state-container"><p class="text-muted">No hay información de certificados TLS.</p></div>`;
  }

  const days = cert.days_remaining || 0;
  const statusColor = days <= 15 ? 'text-amber' : 'text-emerald';

  return `
    <div style="display:flex; flex-direction:column; gap:14px;">
      <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(0, 212, 255, 0.05); padding:12px 16px; border-radius:8px; border:1px solid rgba(0,212,255,0.2);">
        <div>
          <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-muted); font-weight:600;">Dominio Protegido</div>
          <div class="code-font" style="font-size:1.05rem; font-weight:700; color:var(--accent-cyan);">${escapeHtml(cert.domain)}</div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-muted); font-weight:600;">Expira en</div>
          <div style="font-size:1.3rem; font-weight:700;" class="${statusColor}">${days} días</div>
        </div>
      </div>

      <div class="sec-card-meta">
        <div class="sec-meta-row">
          <span class="sec-meta-label">Entidad Emisora:</span>
          <span>${escapeHtml(cert.issuer)}</span>
        </div>
        <div class="sec-meta-row">
          <span class="sec-meta-label">Válido Desde:</span>
          <span>${formatDate(cert.valid_from, 'date')}</span>
        </div>
        <div class="sec-meta-row">
          <span class="sec-meta-label">Fecha Límite:</span>
          <span>${formatDate(cert.valid_to, 'date')}</span>
        </div>
        <div class="sec-meta-row">
          <span class="sec-meta-label">Huella Digital (SHA256):</span>
          <span class="code-font" style="font-size:0.7rem; color:var(--text-muted);">${escapeHtml(cert.fingerprint || '8C:E5:19:4F...')}</span>
        </div>
      </div>
    </div>
  `;
}

function renderChecklist(container) {
  const wrap = container.querySelector('#hardening-checklist-wrap');
  const percentBadge = container.querySelector('#hardening-percent-badge');
  const percentText = container.querySelector('#hardening-percent-text');
  const progressBar = container.querySelector('#hardening-progress-bar');
  if (!wrap) return;

  const total = hardeningItems.length;
  const completed = hardeningItems.filter(i => i.completed).length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  if (percentBadge) percentBadge.textContent = `${percent}% Completado`;
  if (percentText) percentText.textContent = `${percent}% (${completed}/${total})`;
  if (progressBar) progressBar.style.width = `${percent}%`;

  wrap.innerHTML = hardeningItems.map((item, idx) => `
    <label class="checklist-item" for="chk-${idx}">
      <input type="checkbox" id="chk-${idx}" class="checklist-checkbox" ${item.completed ? 'checked' : ''} data-index="${idx}"/>
      <div class="checklist-text">
        <div class="checklist-title ${item.completed ? 'completed' : ''}">${escapeHtml(item.title)}</div>
        <div class="checklist-desc">${escapeHtml(item.desc)}</div>
      </div>
      <span class="badge badge-neutral" style="font-size:0.7rem;">${escapeHtml(item.category || 'Sistema')}</span>
    </label>
  `).join('');

  // Attach change listener
  const checkboxes = wrap.querySelectorAll('.checklist-checkbox');
  checkboxes.forEach(chk => {
    chk.addEventListener('change', (e) => {
      const idx = parseInt(e.target.getAttribute('data-index'), 10);
      if (hardeningItems[idx]) {
        hardeningItems[idx].completed = e.target.checked;
        renderChecklist(container);
      }
    });
  });
}
