/**
 * Sidebar Navigation Component
 */

import { getState, subscribe } from '../state.js';

const NAV_ITEMS = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    hash: '#dashboard',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>`
  },
  {
    id: 'security',
    label: 'Seguridad',
    hash: '#security',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`
  },
  {
    id: 'monitoring',
    label: 'Monitorización',
    hash: '#monitoring',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`
  },
  {
    id: 'logs',
    label: 'Registros',
    hash: '#logs',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>`
  },
  {
    id: 'backups',
    label: 'Copias de Seguridad',
    hash: '#backups',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>`
  },
  {
    id: 'ai',
    label: 'Inteligencia Artificial',
    hash: '#ai',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 0-4 4c0 1.5.8 2.8 2 3.5V11H7a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h3v1.5c-1.2.7-2 2-2 3.5a4 4 0 0 0 8 0c0-1.5-.8-2.8-2-3.5V17h3a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-3V9.5c1.2-.7 2-2 2-3.5a4 4 0 0 0-4-4z"></path></svg>`
  },
  {
    id: 'automation',
    label: 'Automatización',
    hash: '#automation',
    badgeKey: 'pendingActionsCount',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>`
  },
  {
    id: 'settings',
    label: 'Configuración',
    hash: '#settings',
    icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>`
  }
];

/**
 * Initializes and manages the Left Sidebar
 * @param {HTMLElement} container 
 */
export function initSidebar(container) {
  if (!container) return;

  function render() {
    const { currentRoute, pendingActionsCount } = getState();

    container.innerHTML = `
      <div class="sidebar-header">
        <div class="sidebar-logo">
          <img src="assets/logo.svg" alt="Factorio Logo" style="width: 32px; height: 32px;" />
        </div>
        <div class="sidebar-brand">
          <span class="sidebar-brand-name">
            Factorio Tech
            <span class="sidebar-brand-badge">PRO</span>
          </span>
          <span class="sidebar-brand-sub">Security Operations Center</span>
        </div>
      </div>

      <nav class="sidebar-nav" role="navigation" aria-label="Menú principal">
        <span class="nav-section-title">Navegación</span>
        ${NAV_ITEMS.map(item => {
          const isActive = currentRoute === item.id;
          const badgeCount = item.badgeKey ? (getState()[item.badgeKey] || 0) : 0;

          return `
            <a href="${item.hash}" class="nav-item ${isActive ? 'active' : ''}" data-route="${item.id}">
              <span class="nav-icon">${item.icon}</span>
              <span>${item.label}</span>
              ${badgeCount > 0 ? `
                <span class="nav-badge badge-medium">${badgeCount}</span>
              ` : ''}
            </a>
          `;
        }).join('')}
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-user">
          <div class="sidebar-avatar">FT</div>
          <div class="sidebar-user-info">
            <span class="sidebar-user-name">sysadmin</span>
            <span class="sidebar-user-role">Operador de Seguridad</span>
          </div>
        </div>
      </div>
    `;

    // Close mobile drawer on item click
    const links = container.querySelectorAll('.nav-item');
    links.forEach(link => {
      link.addEventListener('click', () => {
        container.classList.remove('open');
        const backdrop = document.getElementById('sidebar-backdrop');
        if (backdrop) backdrop.classList.remove('active');
      });
    });
  }

  // Subscribe to state changes
  subscribe(() => render());
  render();
}
