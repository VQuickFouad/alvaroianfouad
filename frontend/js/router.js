/**
 * Hash-based Single Page Application Router
 * Factorio Security Dashboard
 */

import { setState, getState } from './state.js';
import { renderDashboard, destroyDashboard } from './pages/dashboard.js';
import { renderSecurity, destroySecurity } from './pages/security.js';
import { renderMonitoring, destroyMonitoring } from './pages/monitoring.js';
import { renderLogs, destroyLogs } from './pages/logs.js';
import { renderBackups, destroyBackups } from './pages/backups.js';
import { renderAi, destroyAi } from './pages/ai.js';
import { renderAutomation, destroyAutomation } from './pages/automation.js';
import { renderSettings, destroySettings } from './pages/settings.js';

const ROUTES = {
  dashboard: { title: 'Dashboard', render: renderDashboard, destroy: destroyDashboard },
  security: { title: 'Seguridad', render: renderSecurity, destroy: destroySecurity },
  monitoring: { title: 'Monitorización', render: renderMonitoring, destroy: destroyMonitoring },
  logs: { title: 'Registros', render: renderLogs, destroy: destroyLogs },
  backups: { title: 'Copias de Seguridad', render: renderBackups, destroy: destroyBackups },
  ai: { title: 'Inteligencia Artificial', render: renderAi, destroy: destroyAi },
  automation: { title: 'Automatización', render: renderAutomation, destroy: destroyAutomation },
  settings: { title: 'Configuración', render: renderSettings, destroy: destroySettings }
};

let currentDestroyFn = null;
let routerContainer = null;

/**
 * Initializes the client-side router
 * @param {HTMLElement} container Main content container element
 */
export function initRouter(container) {
  routerContainer = container;

  window.addEventListener('hashchange', handleRoute);
  handleRoute();
}

/**
 * Handle route transition
 */
function handleRoute() {
  const hash = window.location.hash.slice(1).toLowerCase() || 'dashboard';
  const cleanRoute = hash.split('?')[0];

  const targetRoute = ROUTES[cleanRoute] ? cleanRoute : 'dashboard';
  const routeConfig = ROUTES[targetRoute];

  // Call previous page cleanup
  if (currentDestroyFn) {
    try {
      currentDestroyFn();
    } catch (err) {
      console.warn('Error during page cleanup:', err);
    }
    currentDestroyFn = null;
  }

  // Update window title and state
  document.title = `Factorio Security — ${routeConfig.title}`;
  setState({ currentRoute: targetRoute });

  // Scroll to top
  window.scrollTo(0, 0);

  // Render new page
  if (routerContainer) {
    routerContainer.innerHTML = '';
    currentDestroyFn = routeConfig.destroy;
    routeConfig.render(routerContainer);
  }
}
