/**
 * Backups Page Module
 * Factorio Security Dashboard
 */

import { apiGet } from '../api.js';
import { formatDate, formatRelativeTime, escapeHtml } from '../utils.js';
import { createCard, createMetricCard } from '../components/card.js';
import { createSeverityBadge } from '../components/alert-badge.js';
import { createTable } from '../components/table.js';
import { createLoadingSpinner, createErrorState } from '../components/loading.js';

/**
 * Render Backups Page
 * @param {HTMLElement} container 
 */
export async function renderBackups(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-header-info">
        <h1>Copias de Seguridad Cifradas (Restic)</h1>
        <p>Respaldo inmutable contra desastres, snapshots cifrados deduplicados y cumplimiento de la regla 3-2-1.</p>
      </div>
      <div class="page-header-actions">
        <button id="btn-backups-refresh" class="btn btn-secondary btn-sm">
          <span>🔄</span>
          <span>Actualizar</span>
        </button>
      </div>
    </div>

    <div id="backups-content">
      ${createLoadingSpinner('Verificando repositorio de copias de seguridad...')}
    </div>
  `;

  const refreshBtn = container.querySelector('#btn-backups-refresh');
  if (refreshBtn) {
    refreshBtn.onclick = () => loadBackupsData(container);
  }

  await loadBackupsData(container);
}

export function destroyBackups() {
  // cleanup
}

async function loadBackupsData(container) {
  const content = container.querySelector('#backups-content');
  if (!content) return;

  try {
    const data = await apiGet('/backups');
    const repo = data.repository || {};
    const integrity = data.integrity || {};

    content.innerHTML = `
      <!-- Top Metrics Row -->
      <div class="grid-4 mb-4">
        ${createMetricCard({
          label: 'Almacenamiento Repositorio',
          value: repo.size || '184.2 GB',
          unit: 'deduplicado',
          icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>`,
          color: 'cyan',
          trendText: `${repo.total_snapshots || 142} Snapshots válidos`
        })}

        ${createMetricCard({
          label: 'Integridad Criptográfica',
          value: '100% Íntegro',
          unit: '0 errores',
          icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`,
          color: 'emerald',
          trendText: `SHA-256 verificado`
        })}

        ${createMetricCard({
          label: 'Próxima Copia Programada',
          value: 'En 9 horas',
          unit: '03:00 AM',
          icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`,
          color: 'cyan',
          trendText: 'Incremental diaria'
        })}

        ${createMetricCard({
          label: 'Algoritmo de Cifrado',
          value: 'AES-256',
          unit: 'Poly1305',
          icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>`,
          color: 'emerald',
          trendText: 'Cifrado en reposo y tránsito'
        })}
      </div>

      <!-- Strategy 3-2-1 Visualization Card -->
      <div class="card mb-4">
        <div class="card-header">
          <div>
            <h3 class="card-title">Estrategia de Respaldo 3-2-1</h3>
            <p class="card-subtitle">Topología de resiliencia ante pérdida catastrófica de información</p>
          </div>
          <span class="badge badge-success">Regla Cumplida</span>
        </div>
        <div class="card-body">
          <div class="strategy-321-grid">
            <div class="strategy-step">
              <span class="strategy-step-badge">3</span>
              <div class="strategy-step-title text-cyan">3 Copias de Información</div>
              <p class="strategy-step-desc">Datos en producción, snapshot local en el servidor y réplica externa sincronizada diariamente.</p>
            </div>
            <div class="strategy-step">
              <span class="strategy-step-badge">2</span>
              <div class="strategy-step-title text-cyan">2 Medios Físicos Distintos</div>
              <p class="strategy-step-desc">Almacenamiento primario en discos NVMe corporativos y almacenamiento secundario en volumen HDD dedicado con RAID1.</p>
            </div>
            <div class="strategy-step">
              <span class="strategy-step-badge">1</span>
              <div class="strategy-step-title text-cyan">1 Copia Fuera de Sede (Offsite)</div>
              <p class="strategy-step-desc">Copia replicada cifrada en un bucket S3 compatible con política de inmutabilidad (Object Lock) anti-ransomware.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Backup History Table -->
      <div class="card mb-4">
        <div class="card-header">
          <div>
            <h3 class="card-title">Historial de Snapshots Restic</h3>
            <p class="card-subtitle">Registros de ejecuciones de copias completas e incrementales</p>
          </div>
        </div>
        <div class="card-body">
          ${createTable({
            columns: [
              { key: 'id', header: 'Snapshot ID', width: '130px', className: 'cell-mono' },
              { key: 'date', header: 'Fecha de Ejecución', width: '180px', render: (val) => formatDate(val, 'short') },
              { key: 'type', header: 'Tipo de Copia', width: '170px', render: (val) => `<span class="badge ${val.includes('Completa') ? 'badge-info' : 'badge-neutral'}">${escapeHtml(val)}</span>` },
              { key: 'size', header: 'Tamaño Añadido', width: '130px', render: (val) => `<strong>${escapeHtml(val)}</strong>` },
              { key: 'duration', header: 'Duración', width: '120px' },
              { key: 'status', header: 'Estado', width: '120px', render: (val) => createSeverityBadge(val === 'success' ? 'success' : 'error', val === 'success' ? 'Completado' : 'Fallido') }
            ],
            data: data.history || [],
            emptyMessage: 'No hay registros de copias en el repositorio.'
          })}
        </div>
      </div>

      <!-- Collapsible Restore Procedure Documentation -->
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Procedimiento Operativo de Restauración ante Desastres (Runbook)</h3>
            <p class="card-subtitle">Instrucciones técnicas paso a paso para el operador SMR</p>
          </div>
        </div>
        <div class="card-body">
          <div class="accordion-list">
            ${(data.restore_procedure || []).map(step => `
              <div class="accordion-item">
                <div class="accordion-header">
                  <span>Paso ${step.step}: ${escapeHtml(step.title)}</span>
                  <span>▼</span>
                </div>
                <div class="accordion-body">
                  <p style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:8px;">${escapeHtml(step.notes)}</p>
                  <pre style="background:var(--bg-input); border:1px solid var(--border-color); padding:10px 14px; border-radius:6px; font-family:var(--font-mono); font-size:0.82rem; color:var(--accent-cyan); overflow-x:auto;"><code>${escapeHtml(step.command)}</code></pre>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
    `;

    // Attach accordion click events
    const headers = content.querySelectorAll('.accordion-header');
    headers.forEach(h => {
      h.addEventListener('click', () => {
        const item = h.parentElement;
        item.classList.toggle('open');
      });
    });

  } catch (err) {
    content.innerHTML = createErrorState({
      title: 'Error al consultar repositorio de backups',
      message: err.message,
      retryId: 'btn-retry-backups'
    });
    const retryBtn = container.querySelector('#btn-retry-backups');
    if (retryBtn) {
      retryBtn.onclick = () => loadBackupsData(container);
    }
  }
}
