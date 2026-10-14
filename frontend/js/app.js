/**
 * Main Application Entry Point
 * Factorio Security Dashboard — Factorio Tech Solutions
 */

import { initSidebar } from './components/sidebar.js';
import { initNavbar } from './components/navbar.js';
import { initRouter } from './router.js';
import { getState, subscribe, setState } from './state.js';
import { apiGet, getIsDemoFallback } from './api.js';

document.addEventListener('DOMContentLoaded', async () => {
  const appContainer = document.getElementById('app');
  if (!appContainer) return;

  try {
    const response = await fetch('/api/auth/status', { credentials: 'same-origin' });
    if (!response.ok) throw new Error(`No se pudo comprobar la sesión (HTTP ${response.status}).`);
    const auth = await response.json();
    if (!auth.authenticated) {
      renderAuthGate(appContainer, auth.configured);
      return;
    }
    startApplication();
  } catch (error) {
    renderAuthError(appContainer, error.message);
  }
});

function renderAuthGate(appContainer, configured) {
  appContainer.innerHTML = `
    <main style="min-height:100vh;display:grid;place-items:center;padding:24px;background:#0a0e17;color:#f8fafc;font-family:Inter,system-ui,sans-serif">
      <section style="width:min(100%,440px);padding:32px;border:1px solid #263347;border-radius:14px;background:#111827">
        <h1 style="margin:0 0 8px;color:#00d4ff">Factorio Tech Solutions</h1>
        <p style="margin:0 0 24px;color:#a7b2c4">${configured ? 'Inicia sesión para continuar.' : 'Crea la cuenta administradora inicial.'}</p>
        <form id="auth-form" style="display:grid;gap:14px">
          ${configured ? '' : `
            <label style="display:grid;gap:6px">Token de configuración
              <input name="setup_token" type="password" required autocomplete="off" style="padding:12px;border-radius:7px;border:1px solid #344256;background:#0a0e17;color:#fff">
            </label>
          `}
          <label style="display:grid;gap:6px">Usuario
            <input name="username" required maxlength="100" autocomplete="username" style="padding:12px;border-radius:7px;border:1px solid #344256;background:#0a0e17;color:#fff">
          </label>
          <label style="display:grid;gap:6px">Contraseña
            <input name="password" type="password" required minlength="${configured ? 1 : 12}" autocomplete="${configured ? 'current-password' : 'new-password'}" style="padding:12px;border-radius:7px;border:1px solid #344256;background:#0a0e17;color:#fff">
          </label>
          ${configured ? '' : '<p style="margin:0;color:#a7b2c4;font-size:.85rem">La contraseña debe tener al menos 12 caracteres. El token se configura en AUTH_SETUP_TOKEN del archivo .env.</p>'}
          <p id="auth-error" role="alert" style="margin:0;color:#fb7185"></p>
          <button type="submit" style="padding:12px;border:0;border-radius:7px;background:#0284c7;color:white;font-weight:700;cursor:pointer">${configured ? 'Iniciar sesión' : 'Crear administrador'}</button>
        </form>
      </section>
    </main>
  `;

  const form = appContainer.querySelector('#auth-form');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    const errorNode = form.querySelector('#auth-error');
    button.disabled = true;
    errorNode.textContent = '';
    const values = Object.fromEntries(new FormData(form).entries());
    const endpoint = configured ? '/api/auth/login' : '/api/auth/setup';
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(values)
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `Solicitud rechazada (HTTP ${response.status}).`);
      if (configured) {
        window.location.reload();
      } else {
        renderAuthGate(appContainer, true);
      }
    } catch (error) {
      errorNode.textContent = error.message;
      button.disabled = false;
    }
  });
}

function renderAuthError(appContainer, message) {
  appContainer.innerHTML = `
    <main style="min-height:100vh;display:grid;place-items:center;padding:24px;background:#0a0e17;color:#f8fafc;font-family:Inter,system-ui,sans-serif">
      <section style="max-width:560px;padding:28px;border:1px solid #7f1d1d;border-radius:12px;background:#111827">
        <h1 style="color:#fb7185">No se pudo iniciar la aplicación</h1>
        <p id="auth-load-error"></p>
        <button id="auth-retry">Reintentar</button>
      </section>
    </main>
  `;
  appContainer.querySelector('#auth-load-error').textContent = message;
  appContainer.querySelector('#auth-retry').addEventListener('click', () => window.location.reload());
}

function startApplication() {
  const sidebarEl = document.getElementById('sidebar');
  const navbarEl = document.getElementById('top-navbar-container');
  const mainContentEl = document.getElementById('main-content');
  const demoBannerEl = document.getElementById('demo-banner');
  const sidebarBackdropEl = document.getElementById('sidebar-backdrop');
  const appContainer = document.getElementById('app');

  initSidebar(sidebarEl);
  initNavbar(navbarEl);
  initRouter(mainContentEl);

  function syncDemoBanner(state) {
    if (!demoBannerEl) return;
    if (state.demoMode || getIsDemoFallback()) {
      demoBannerEl.classList.remove('hidden');
      if (appContainer) appContainer.classList.add('has-demo-banner');
    } else {
      demoBannerEl.classList.add('hidden');
      if (appContainer) appContainer.classList.remove('has-demo-banner');
    }
  }

  subscribe(syncDemoBanner);
  syncDemoBanner(getState());

  if (sidebarBackdropEl) {
    sidebarBackdropEl.addEventListener('click', () => {
      if (sidebarEl) sidebarEl.classList.remove('open');
      sidebarBackdropEl.classList.remove('active');
    });
  }

  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
      if (sidebarEl) sidebarEl.classList.remove('open');
      if (sidebarBackdropEl) sidebarBackdropEl.classList.remove('active');
    }
  });

  apiGet('/system/status')
    .then((status) => {
      if (status?.demo_mode !== undefined) setState({ demoMode: Boolean(status.demo_mode) });
    })
    .catch((error) => console.error('No se pudo obtener el estado inicial:', error));
}
