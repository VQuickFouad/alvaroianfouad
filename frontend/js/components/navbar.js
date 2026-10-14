/**
 * Top Navigation Bar Component
 */

import { getState, setState, subscribe } from '../state.js';
import { openModal } from './modal.js';
import { createSeverityBadge } from './alert-badge.js';
import { apiPost } from '../api.js';

/**
 * Initializes and renders the Top Navigation Bar
 * @param {HTMLElement} container 
 */
export function initNavbar(container) {
  if (!container) return;

  function render() {
    const { demoMode, activeAlertsCount, currentRoute } = getState();

    const routeNames = {
      dashboard: 'Panel General',
      security: 'Seguridad Perimetral',
      monitoring: 'Telemetría y Rendimiento',
      logs: 'Auditoría y Registros',
      backups: 'Copias de Seguridad',
      ai: 'Asistente de IA',
      automation: 'Automatización y Tareas',
      settings: 'Configuración del Sistema'
    };

    const title = routeNames[currentRoute] || 'Factorio Security Dashboard';

    container.innerHTML = `
      <div class="top-navbar">
        <div class="navbar-left">
          <button id="btn-mobile-menu" class="mobile-toggle" aria-label="Abrir Menú">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <div>
            <span class="navbar-page-title">${title}</span>
            <span class="navbar-subtitle">Factorio Tech Solutions &bull; Linux SMR v2.4</span>
          </div>
        </div>

        <div class="navbar-actions">
          <!-- Notification Bell -->
          <button id="btn-notifications-bell" class="btn-icon" style="position: relative;" title="Alertas activas" aria-label="Alertas activas">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            </svg>
            ${activeAlertsCount > 0 ? `
              <span style="position: absolute; top: 2px; right: 2px; width: 8px; height: 8px; background: var(--accent-rose); border-radius: 50%; box-shadow: 0 0 6px var(--accent-rose);"></span>
            ` : ''}
          </button>

          <!-- Quick Settings Gear -->
          <a href="#settings" class="btn-icon" title="Configuración" aria-label="Ir a Configuración">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
          </a>
          <button id="btn-logout" class="btn btn-secondary btn-sm" type="button">Cerrar sesión</button>
        </div>
      </div>
    `;

    // Bind Mobile menu button
    const mobileBtn = container.querySelector('#btn-mobile-menu');
    if (mobileBtn) {
      mobileBtn.onclick = () => {
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebar-backdrop');
        if (sidebar && backdrop) {
          sidebar.classList.toggle('open');
          backdrop.classList.toggle('active');
        }
      };
    }

    const logoutBtn = container.querySelector('#btn-logout');
    if (logoutBtn) {
      logoutBtn.onclick = async () => {
        logoutBtn.disabled = true;
        try {
          await apiPost('/auth/logout', {});
          window.location.reload();
        } catch (error) {
          console.error('No se pudo cerrar la sesión:', error);
          logoutBtn.disabled = false;
        }
      };
    }

    // Bind Notifications modal
    const notifBtn = container.querySelector('#btn-notifications-bell');
    if (notifBtn) {
      notifBtn.onclick = () => {
        openModal({
          title: '🚨 Centro de Alertas Perimetrales',
          content: `
            <div style="display:flex; flex-direction:column; gap:12px;">
              <div style="padding:12px; background:rgba(239, 68, 68, 0.1); border-left:3px solid var(--accent-rose); border-radius:4px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                  <span style="font-weight:700; color:#f87171;">Ataque de fuerza bruta SSH</span>
                  ${createSeverityBadge('critical')}
                </div>
                <p style="font-size:0.82rem; color:var(--text-secondary);">IP 194.26.29.112 bloqueada por Fail2ban tras 10 intentos fallidos repetidos.</p>
                <div style="font-size:0.75rem; color:var(--text-muted); margin-top:6px;">Hace 12 minutos &bull; Servicio Fail2ban</div>
              </div>

              <div style="padding:12px; background:rgba(249, 115, 22, 0.1); border-left:3px solid var(--accent-amber); border-radius:4px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                  <span style="font-weight:700; color:#fb923c;">Escaneo SYN perimetral</span>
                  ${createSeverityBadge('high')}
                </div>
                <p style="font-size:0.82rem; color:var(--text-secondary);">Sondeo de puertos 8080 y 9000 mitigado por política DROP en cortafuegos UFW.</p>
                <div style="font-size:0.75rem; color:var(--text-muted); margin-top:6px;">Hace 25 minutos &bull; Servicio UFW</div>
              </div>
            </div>
          `,
          footer: `
            <a href="#logs" onclick="document.getElementById('modal-close-btn').click();" class="btn btn-outline btn-sm">Ver todos los registros</a>
            <button class="btn btn-secondary btn-sm" onclick="document.getElementById('modal-close-btn').click();">Cerrar</button>
          `
        });
      };
    }
  }

  // Subscribe to changes
  subscribe(() => render());
  render();
}
