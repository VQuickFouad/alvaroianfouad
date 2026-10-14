/**
 * Automation & Orchestration Page Module
 * Factorio Security Dashboard
 */

import { apiGet, apiPost } from '../api.js';
import { formatDate, formatRelativeTime, escapeHtml } from '../utils.js';
import { setState } from '../state.js';
import { createCard } from '../components/card.js';
import { createSeverityBadge } from '../components/alert-badge.js';
import { createTable } from '../components/table.js';
import { createLoadingSpinner, createErrorState } from '../components/loading.js';
import { showToast } from '../components/toast.js';

let automationData = null;

/**
 * Render Automation Page
 * @param {HTMLElement} container 
 */
export async function renderAutomation(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-header-info">
        <h1>Automatización y Respuestas a Incidentes</h1>
        <p>Tareas programadas del sistema (cron) y remediaciones de seguridad con aprobación humana (Human-in-the-Loop).</p>
      </div>
      <div class="page-header-actions">
        <button id="btn-automation-refresh" class="btn btn-secondary btn-sm">
          <span>🔄</span>
          <span>Actualizar</span>
        </button>
      </div>
    </div>

    <div id="automation-content">
      ${createLoadingSpinner('Cargando tareas programadas y remediaciones pendientes...')}
    </div>
  `;

  const refreshBtn = container.querySelector('#btn-automation-refresh');
  if (refreshBtn) {
    refreshBtn.onclick = () => loadAutomationData(container);
  }

  await loadAutomationData(container);
}

export function destroyAutomation() {
  automationData = null;
}

async function loadAutomationData(container) {
  const content = container.querySelector('#automation-content');
  if (!content) return;

  try {
    automationData = await apiGet('/automation');

    const pendingActions = automationData.pending_actions || [];
    setState({ pendingActionsCount: pendingActions.length });

    content.innerHTML = `
      <!-- Pending Actions Section (Human in the loop) -->
      <div class="card mb-4" style="border-color: rgba(245, 158, 11, 0.4);">
        <div class="card-header" style="background: rgba(245, 158, 11, 0.05);">
          <div>
            <h3 class="card-title text-amber">
              <span>⚡</span>
              <span>Acciones Pendientes de Aprobación (${pendingActions.length})</span>
            </h3>
            <p class="card-subtitle">Mitigaciones sugeridas que requieren confirmación expresa del operador</p>
          </div>
          ${pendingActions.length > 0 ? createSeverityBadge('pendiente', `${pendingActions.length} Pendientes`) : createSeverityBadge('success', 'Al día')}
        </div>
        <div class="card-body" id="pending-actions-wrap">
          ${renderPendingActions(pendingActions)}
        </div>
      </div>

      <!-- Scheduled Tasks (Cron) -->
      <div class="card mb-4">
        <div class="card-header">
          <div>
            <h3 class="card-title">Tareas Programadas del Sistema (Cron Jobs)</h3>
            <p class="card-subtitle">Mantenimiento recurrente, rotaciones y sincronización perimetral</p>
          </div>
        </div>
        <div class="card-body">
          ${createTable({
            columns: [
              { key: 'name', header: 'Nombre de la Tarea', render: (val) => `<strong style="color:var(--text-primary);">${escapeHtml(val)}</strong>` },
              {
                key: 'cron',
                header: 'Planificación Cron',
                render: (val, r) => `
                  <div>
                    <span class="badge badge-neutral code-font">${escapeHtml(val)}</span>
                    <span style="font-size:0.75rem; color:var(--text-secondary); margin-left:6px;">${escapeHtml(r.cron_human || '')}</span>
                  </div>
                `
              },
              { key: 'last_run', header: 'Última Ejecución', width: '160px', render: (val) => formatRelativeTime(val) },
              { key: 'next_run', header: 'Próxima Ejecución', width: '160px', render: (val) => formatDate(val, 'short') },
              { key: 'status', header: 'Estado', width: '120px', render: (val) => createSeverityBadge(val === 'active' ? 'success' : 'neutral', val === 'active' ? 'Activo' : 'Pausado') }
            ],
            data: automationData.scheduled_tasks || [],
            emptyMessage: 'No hay tareas programadas configuradas.'
          })}
        </div>
      </div>

      <!-- Action Execution History -->
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Historial de Ejecución de Respuestas</h3>
            <p class="card-subtitle">Registro de auditoría de todas las acciones ejecutadas, rechazadas o caducadas</p>
          </div>
        </div>
        <div class="card-body">
          ${createTable({
            columns: [
              { key: 'id', header: 'ID Acción', width: '110px', className: 'cell-mono' },
              { key: 'title', header: 'Acción Ejecutada', render: (val) => `<strong>${escapeHtml(val)}</strong>` },
              { key: 'status', header: 'Resultado', width: '140px', render: (val) => createSeverityBadge(val) },
              { key: 'executed_at', header: 'Fecha y Hora', width: '180px', render: (val) => formatDate(val, 'short') },
              { key: 'triggered_by', header: 'Iniciado Por', width: '180px', render: (val) => `<span class="badge badge-neutral">${escapeHtml(val)}</span>` }
            ],
            data: automationData.action_history || [],
            emptyMessage: 'No hay histórico de acciones registradas.'
          })}
        </div>
      </div>
    `;

    bindActionButtons(container);

  } catch (err) {
    content.innerHTML = createErrorState({
      title: 'Error al recuperar datos de automatización',
      message: err.message,
      retryId: 'btn-retry-automation'
    });
    const retryBtn = container.querySelector('#btn-retry-automation');
    if (retryBtn) {
      retryBtn.onclick = () => loadAutomationData(container);
    }
  }
}

function renderPendingActions(actions) {
  if (!actions || actions.length === 0) {
    return `
      <div class="state-container" style="padding: 24px;">
        <div class="state-icon text-emerald">✓</div>
        <h4 class="state-title">No hay acciones pendientes</h4>
        <p class="state-desc">El sistema no tiene remediaciones a la espera de confirmación.</p>
      </div>
    `;
  }

  return actions.map(act => `
    <div class="pending-action-card" id="card-${act.id}">
      <div class="pending-action-header">
        <div>
          <span class="badge badge-medium" style="margin-bottom:6px;">Pendiente de Decisión</span>
          <h4 class="pending-action-title">${escapeHtml(act.title)}</h4>
        </div>
        <span style="font-size:0.75rem; color:var(--text-muted);">${formatRelativeTime(act.created_at)}</span>
      </div>

      <p style="font-size:0.88rem; color:var(--text-secondary); margin-bottom:8px;">${escapeHtml(act.description)}</p>

      <div style="font-size:0.82rem; margin-bottom:6px;">
        <strong class="text-cyan">Causa detectada:</strong> ${escapeHtml(act.cause)}
      </div>

      <div class="pending-action-impact">
        <strong>⚠️ Evaluación de Impacto:</strong> ${escapeHtml(act.impact)}
      </div>

      ${act.steps && act.steps.length ? `
        <div>
          <span style="font-size:0.8rem; font-weight:600; text-transform:uppercase; color:var(--text-muted);">Comandos a Ejecutar:</span>
          <ul class="pending-steps-list">
            ${act.steps.map(step => `<li class="code-font" style="color:var(--accent-cyan); font-size:0.8rem;">${escapeHtml(step)}</li>`).join('')}
          </ul>
        </div>
      ` : ''}

      <div style="display:flex; justify-content:flex-end; gap:12px; margin-top:14px;">
        <button class="btn btn-secondary btn-sm btn-reject-action" data-id="${act.id}">
          <span>✕</span>
          <span>Rechazar Acción</span>
        </button>
        <button class="btn btn-success btn-sm btn-approve-action" data-id="${act.id}">
          <span>✓</span>
          <span>Aprobar y Ejecutar</span>
        </button>
      </div>
    </div>
  `).join('');
}

function bindActionButtons(container) {
  const approveBtns = container.querySelectorAll('.btn-approve-action');
  const rejectBtns = container.querySelectorAll('.btn-reject-action');

  approveBtns.forEach(btn => {
    btn.onclick = async () => {
      const id = btn.getAttribute('data-id');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner" style="width:14px; height:14px; border-width:2px;"></span> Ejecutando...';

      try {
        const res = await apiPost(`/automation/actions/${id}/approve`, {});
        showToast({
          title: 'Acción Aprobada',
          message: res.message || 'La mitigación fue ejecutada en el cortafuegos/sistema.',
          type: 'success'
        });

        // Remove from list in UI
        const card = container.querySelector(`#card-${id}`);
        if (card) {
          card.style.opacity = '0';
          setTimeout(() => {
            if (card.parentNode) card.parentNode.removeChild(card);
            // Update badge count
            const remaining = container.querySelectorAll('.pending-action-card').length;
            setState({ pendingActionsCount: remaining });
          }, 300);
        }
      } catch (err) {
        showToast({ title: 'Error al ejecutar', message: err.message, type: 'error' });
        btn.disabled = false;
        btn.innerHTML = '<span>✓</span> <span>Aprobar y Ejecutar</span>';
      }
    };
  });

  rejectBtns.forEach(btn => {
    btn.onclick = async () => {
      const id = btn.getAttribute('data-id');
      btn.disabled = true;
      try {
        const res = await apiPost(`/automation/actions/${id}/reject`, {});
        showToast({
          title: 'Acción Rechazada',
          message: res.message || 'La remediación ha sido descartada por el operador.',
          type: 'info'
        });

        const card = container.querySelector(`#card-${id}`);
        if (card) {
          card.style.opacity = '0';
          setTimeout(() => {
            if (card.parentNode) card.parentNode.removeChild(card);
            const remaining = container.querySelectorAll('.pending-action-card').length;
            setState({ pendingActionsCount: remaining });
          }, 300);
        }
      } catch (err) {
        showToast({ title: 'Error', message: err.message, type: 'error' });
        btn.disabled = false;
      }
    };
  });
}
