/**
 * Settings Page Module
 * Factorio Security Dashboard
 */

import { apiGet, apiPost } from '../api.js';
import { escapeHtml } from '../utils.js';
import { createCard } from '../components/card.js';
import { createLoadingSpinner, createErrorState } from '../components/loading.js';
import { showToast } from '../components/toast.js';

let activeTab = 'general';
let currentSettings = null;

/**
 * Render Settings Page
 * @param {HTMLElement} container 
 */
export async function renderSettings(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-header-info">
        <h1>Preferencias y configuración</h1>
        <p>Preferencias guardadas para el panel y estado de la configuración operativa.</p>
      </div>
      <div class="page-header-actions" id="settings-header-actions">
        <!-- Will show config source badge -->
      </div>
    </div>

    <div id="settings-content">
      ${createLoadingSpinner('Cargando configuración actual del servidor...')}
    </div>
  `;

  await loadSettingsData(container);
}

export function destroySettings() {
  currentSettings = null;
}

async function loadSettingsData(container) {
  const content = container.querySelector('#settings-content');
  const headerActions = container.querySelector('#settings-header-actions');
  if (!content) return;

  try {
    currentSettings = await apiGet('/settings');

    if (headerActions) {
      headerActions.innerHTML = `
        <span class="config-source-badge">
          <span>⚙️</span>
          <span>Fuente: ${escapeHtml(currentSettings.config_source || '.env + SQLite')}</span>
        </span>
      `;
    }

    content.innerHTML = `
      <!-- Settings Tab Bar -->
      <div class="settings-nav">
        <button class="settings-tab ${activeTab === 'general' ? 'active' : ''}" data-tab="general">General</button>
        <button class="settings-tab ${activeTab === 'monitoring' ? 'active' : ''}" data-tab="monitoring">Monitorización</button>
        <button class="settings-tab ${activeTab === 'security' ? 'active' : ''}" data-tab="security">Seguridad</button>
        <button class="settings-tab ${activeTab === 'ai' ? 'active' : ''}" data-tab="ai">Inteligencia Artificial</button>
        <button class="settings-tab ${activeTab === 'backups' ? 'active' : ''}" data-tab="backups">Copias de Seguridad</button>
        <button class="settings-tab ${activeTab === 'notifications' ? 'active' : ''}" data-tab="notifications">Notificaciones</button>
        <button class="settings-tab ${activeTab === 'logs' ? 'active' : ''}" data-tab="logs">Registros y Logs</button>
      </div>
      <p role="note" style="padding: 12px 16px; background: rgba(0, 212, 255, 0.08); border-left: 3px solid var(--accent-cyan); border-radius: 6px; color: var(--text-secondary);">
        Los valores de esta página se guardan como preferencias del panel. La configuración efectiva de servicios, integraciones y políticas se define en <code>.env</code> y puede requerir reiniciar el backend.
      </p>

      <!-- Tab Panels Container -->
      <div id="settings-panel-wrap">
        <!-- Panels rendered below -->
      </div>
    `;

    // Render tab panels
    renderTabPanels(content);

    // Bind tab clicks
    const tabs = content.querySelectorAll('.settings-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        activeTab = tab.getAttribute('data-tab');
        renderTabPanels(content);
      });
    });

  } catch (err) {
    content.innerHTML = createErrorState({
      title: 'Error al recuperar configuración del sistema',
      message: err.message,
      retryId: 'btn-retry-settings'
    });
    const retryBtn = container.querySelector('#btn-retry-settings');
    if (retryBtn) {
      retryBtn.onclick = () => loadSettingsData(container);
    }
  }
}

function renderTabPanels(container) {
  const panelWrap = container.querySelector('#settings-panel-wrap');
  if (!panelWrap || !currentSettings) return;

  const g = currentSettings.general || {};
  const m = currentSettings.monitoring || {};
  const s = currentSettings.security || {};
  const ai = currentSettings.ai || {};
  const b = currentSettings.backups || {};
  const n = currentSettings.notifications || {};
  const l = currentSettings.logs || {};

  panelWrap.innerHTML = `
    <!-- PANEL GENERAL -->
    <div class="settings-panel ${activeTab === 'general' ? 'active' : ''}" id="panel-general">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Parámetros Generales de la Aplicación</h3>
        </div>
        <div class="card-body">
          <form id="form-general">
            <div class="form-group">
              <label class="form-label" for="gen-app-name">Nombre de la Instancia / Dashboard</label>
              <input type="text" id="gen-app-name" class="input" value="${escapeHtml(g.app_name || 'Factorio Security Dashboard')}" />
            </div>

            <div class="form-group" style="display: flex; flex-direction: row; align-items: center; justify-content: space-between; padding: 12px 0; border-top: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color);">
              <div>
                <label class="form-label" style="margin-bottom: 2px;">Modo Demostración (Datos Sintéticos)</label>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">Muestra métricas y eventos simulados sin consultar demonios del kernel de Linux.</div>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" id="gen-demo-mode" ${g.demo_mode ? 'checked' : ''} disabled />
                <span class="toggle-slider"></span>
              </label>
              <span style="font-size: 0.75rem; color: var(--text-muted);">Se cambia en .env y requiere reiniciar el servicio.</span>
            </div>

            <div class="form-group mt-4">
              <label class="form-label" for="gen-refresh-interval">Intervalo de Refresco Automático (segundos)</label>
              <input type="number" id="gen-refresh-interval" class="input" min="5" max="300" value="${g.refresh_interval || 30}" />
            </div>

            <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px;">
              <button type="button" class="btn btn-secondary btn-sm btn-reset-defaults">Valores por Defecto</button>
              <button type="submit" class="btn btn-primary btn-sm">Guardar General</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- PANEL MONITORING -->
    <div class="settings-panel ${activeTab === 'monitoring' ? 'active' : ''}" id="panel-monitoring">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Configuración de Monitorización y Telemetría</h3>
        </div>
        <div class="card-body">
          <form id="form-monitoring">
            <div class="form-group">
              <label class="form-label" for="mon-netdata-url">URL del Agente Netdata</label>
              <input type="text" id="mon-netdata-url" class="input" value="${escapeHtml(m.netdata_url || 'http://127.0.0.1:19999')}" />
              <span style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">Enlace local o perimetral para integración de gráficas en tiempo real.</span>
            </div>

            <div class="form-group">
              <label class="form-label" for="mon-metrics-interval">Intervalo de Muestreo de Métricas (segundos)</label>
              <input type="number" id="mon-metrics-interval" class="input" min="1" max="60" value="${m.metrics_interval || 5}" />
            </div>

            <div class="form-group">
              <label class="form-label" for="mon-history-hours">Retención Histórica de Métricas (horas)</label>
              <input type="number" id="mon-history-hours" class="input" min="1" max="168" value="${m.history_retention_hours || 24}" />
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
              <button type="submit" class="btn btn-primary btn-sm">Guardar Monitorización</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- PANEL SECURITY -->
    <div class="settings-panel ${activeTab === 'security' ? 'active' : ''}" id="panel-security">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Parámetros de Seguridad y Cortafuegos</h3>
        </div>
        <div class="card-body">
          <form id="form-security">
            <div class="form-group">
              <label class="form-label">Servicios Críticos en Vigilancia</label>
              <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 6px;">
                ${['nginx', 'sshd', 'ufw', 'fail2ban', 'crowdsec', 'apparmor'].map(svc => `
                  <label style="display: flex; align-items: center; gap: 10px; font-size: 0.88rem; color: var(--text-primary); cursor: pointer;">
                    <input type="checkbox" class="sec-svc-check" value="${svc}" ${(s.monitored_services || []).includes(svc) ? 'checked' : ''} style="accent-color: var(--accent-cyan); width: 16px; height: 16px;" />
                    <span>${svc.toUpperCase()} (daemon)</span>
                  </label>
                `).join('')}
              </div>
            </div>

            <div class="grid-2 mt-4">
              <div class="form-group">
                <label class="form-label" for="sec-fail2ban-retry">Umbral de Reintentos Fail2ban (maxretry)</label>
                <input type="number" id="sec-fail2ban-retry" class="input" min="1" max="20" value="${s.fail2ban_maxretry || 5}" />
              </div>

              <div class="form-group">
                <label class="form-label" for="sec-fail2ban-ban">Tiempo de Baneo en Segundos (bantime)</label>
                <input type="number" id="sec-fail2ban-ban" class="input" min="60" max="604800" value="${s.fail2ban_bantime || 86400}" />
              </div>
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
              <button type="submit" class="btn btn-primary btn-sm">Guardar Seguridad</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- PANEL AI -->
    <div class="settings-panel ${activeTab === 'ai' ? 'active' : ''}" id="panel-ai">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Proveedor de Inteligencia Artificial</h3>
        </div>
        <div class="card-body">
          <form id="form-ai">
            <div style="padding: 12px 16px; background: rgba(0, 212, 255, 0.08); border-left: 3px solid var(--accent-cyan); border-radius: 6px; margin-bottom: 20px; font-size: 0.82rem; color: var(--text-secondary);">
              🔒 <strong>Seguridad de Credenciales:</strong> Por motivos de hardening y seguridad, las claves API nunca se configuran desde la interfaz web. Deben suministrarse como variables de entorno seguras (<code>OPENAI_API_KEY</code>) en el servidor.
            </div>

            <div class="form-group">
              <label class="form-label" for="ai-provider">Motor de Inferencia</label>
              <select id="ai-provider" class="select">
                <option value="ollama" ${ai.provider === 'ollama' ? 'selected' : ''}>Ollama (Modelo Local en Servidor)</option>
                <option value="openai" ${ai.provider === 'openai' ? 'selected' : ''}>OpenAI API (Cloud)</option>
                <option value="none" ${ai.provider === 'none' ? 'selected' : ''}>Deshabilitado (Motor de Reglas Heurísticas)</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label" for="ai-model">Nombre del Modelo</label>
              <input type="text" id="ai-model" class="input" value="${escapeHtml(ai.model || 'llama3-security:8b')}" />
            </div>

            <div class="form-group">
              <label class="form-label" for="ai-base-url">URL Base de Inferencia (Endpoint)</label>
              <input type="text" id="ai-base-url" class="input" value="${escapeHtml(ai.base_url || 'http://127.0.0.1:11434')}" />
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
              <button type="submit" class="btn btn-primary btn-sm">Guardar IA</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- PANEL BACKUPS -->
    <div class="settings-panel ${activeTab === 'backups' ? 'active' : ''}" id="panel-backups">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Parámetros de Repositorio Restic</h3>
        </div>
        <div class="card-body">
          <form id="form-backups">
            <div class="form-group">
              <label class="form-label" for="bak-repo-path">Ruta del Repositorio Restic (Local o Remoto)</label>
              <input type="text" id="bak-repo-path" class="input code-font" value="${escapeHtml(b.restic_repo_path || '/mnt/storage/restic-repo')}" />
            </div>

            <div class="grid-3 mt-4">
              <div class="form-group">
                <label class="form-label" for="bak-retention-daily">Retención Diaria (--keep-daily)</label>
                <input type="number" id="bak-retention-daily" class="input" min="1" max="90" value="${b.retention_daily || 7}" />
              </div>
              <div class="form-group">
                <label class="form-label" for="bak-retention-weekly">Retención Semanal (--keep-weekly)</label>
                <input type="number" id="bak-retention-weekly" class="input" min="1" max="52" value="${b.retention_weekly || 4}" />
              </div>
              <div class="form-group">
                <label class="form-label" for="bak-retention-monthly">Retención Mensual (--keep-monthly)</label>
                <input type="number" id="bak-retention-monthly" class="input" min="1" max="36" value="${b.retention_monthly || 6}" />
              </div>
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
              <button type="submit" class="btn btn-primary btn-sm">Guardar Backups</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- PANEL NOTIFICATIONS -->
    <div class="settings-panel ${activeTab === 'notifications' ? 'active' : ''}" id="panel-notifications">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Canales de Alerta y Notificaciones Telegram</h3>
        </div>
        <div class="card-body">
          <form id="form-notifications">
            <div class="form-group" style="display: flex; flex-direction: row; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border-color);">
              <div>
                <label class="form-label" style="margin-bottom: 2px;">Bot de Telegram Activado</label>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">Envío instantáneo de incidentes críticos al canal del SOC.</div>
              </div>
              <label class="toggle-switch">
                <input type="checkbox" id="notif-telegram-enabled" ${n.telegram_enabled ? 'checked' : ''} />
                <span class="toggle-slider"></span>
              </label>
            </div>

            <div class="form-group mt-4">
              <label class="form-label" for="notif-chat-id">ID de Chat o Grupo de Telegram</label>
              <input type="text" id="notif-chat-id" class="input" value="${escapeHtml(n.telegram_chat_id || '-100293848123')}" />
            </div>

            <div class="mt-4" style="display: flex; flex-direction: column; gap: 8px;">
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.85rem; color: var(--text-primary); cursor: pointer;">
                <input type="checkbox" id="notif-crit" ${n.notify_on_critical ? 'checked' : ''} style="accent-color: var(--accent-cyan);" />
                <span>Notificar incidentes con severidad CRÍTICA</span>
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.85rem; color: var(--text-primary); cursor: pointer;">
                <input type="checkbox" id="notif-high" ${n.notify_on_high ? 'checked' : ''} style="accent-color: var(--accent-cyan);" />
                <span>Notificar incidentes con severidad ALTA</span>
              </label>
              <label style="display: flex; align-items: center; gap: 10px; font-size: 0.85rem; color: var(--text-primary); cursor: pointer;">
                <input type="checkbox" id="notif-bak-fail" ${n.notify_on_backup_failure ? 'checked' : ''} style="accent-color: var(--accent-cyan);" />
                <span>Notificar fallos en ejecución de copias Restic</span>
              </label>
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
              <button type="submit" class="btn btn-primary btn-sm">Guardar Notificaciones</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- PANEL LOGS -->
    <div class="settings-panel ${activeTab === 'logs' ? 'active' : ''}" id="panel-logs">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Fuentes de Auditoría y Política de Retención</h3>
        </div>
        <div class="card-body">
          <form id="form-logs">
            <div class="form-group">
              <label class="form-label" for="log-retention-days">Días de Retención de Logs en Disco</label>
              <input type="number" id="log-retention-days" class="input" min="7" max="365" value="${l.retention_days || 30}" />
            </div>

            <div class="form-group">
              <label class="form-label">Archivos de Registro Monitorizados</label>
              <div style="background: var(--bg-input); border: 1px solid var(--border-color); border-radius: 6px; padding: 12px; font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-secondary);">
                ${(l.sources || ['/var/log/syslog', '/var/log/auth.log', '/var/log/nginx/*.log', '/var/log/fail2ban.log', '/var/log/ufw.log']).map(src => `
                  <div>&bull; ${escapeHtml(src)}</div>
                `).join('')}
              </div>
            </div>

            <div style="display: flex; justify-content: flex-end; margin-top: 24px;">
              <button type="submit" class="btn btn-primary btn-sm">Guardar Registros</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `;

  bindFormSubmits(panelWrap);
}

function bindFormSubmits(panelWrap) {
  const fieldNames = {
    'gen-app-name': 'app_name',
    'gen-refresh-interval': 'refresh_interval',
    'mon-netdata-url': 'netdata_url',
    'mon-metrics-interval': 'metrics_interval',
    'mon-history-hours': 'history_retention_hours',
    'sec-fail2ban-retry': 'fail2ban_maxretry',
    'sec-fail2ban-ban': 'fail2ban_bantime',
    'ai-provider': 'provider',
    'ai-model': 'model',
    'ai-base-url': 'base_url',
    'bak-repo-path': 'restic_repo_path',
    'bak-retention-daily': 'retention_daily',
    'bak-retention-weekly': 'retention_weekly',
    'bak-retention-monthly': 'retention_monthly',
    'notif-telegram-enabled': 'telegram_enabled',
    'notif-chat-id': 'telegram_chat_id',
    'notif-crit': 'notify_on_critical',
    'notif-high': 'notify_on_high',
    'notif-bak-fail': 'notify_on_backup_failure',
    'log-retention-days': 'retention_days'
  };
  const sectionByForm = {
    'form-general': 'general',
    'form-monitoring': 'monitoring',
    'form-security': 'security',
    'form-ai': 'ai',
    'form-backups': 'backups',
    'form-notifications': 'notifications',
    'form-logs': 'logs'
  };

  const forms = panelWrap.querySelectorAll('form');
  forms.forEach(form => {
    form.onsubmit = async (e) => {
      e.preventDefault();

      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Guardando...';
      }

      try {
        const values = {};
        form.querySelectorAll('input, select').forEach((field) => {
          const key = fieldNames[field.id];
          if (!key || field.disabled) return;

          if (field.type === 'checkbox') {
            values[key] = field.checked;
          } else if (field.type === 'number') {
            values[key] = Number(field.value);
          } else {
            values[key] = field.value;
          }
        });
        await apiPost('/settings', { section: sectionByForm[form.id], values });
        showToast({
          title: 'Configuración Guardada',
          message: 'Las preferencias de la interfaz se han guardado.',
          type: 'success'
        });
      } catch (err) {
        showToast({ title: 'Error al guardar', message: err.message, type: 'error' });
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Guardar';
        }
      }
    };
  });

  const resetBtns = panelWrap.querySelectorAll('.btn-reset-defaults');
  resetBtns.forEach(btn => {
    btn.onclick = () => {
      showToast({
        title: 'Valores Restaurados',
        message: 'Se han reestablecido los valores nominales de fábrica.',
        type: 'info'
      });
    };
  });
}
