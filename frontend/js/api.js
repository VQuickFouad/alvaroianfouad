/**
 * Same-origin API client for the Factorio Security Dashboard.
 */

const API_BASE = '/api';

export function getIsDemoFallback() {
  return false;
}

export function setDemoFallback() {
  // Kept for compatibility with existing imports; API failures are never replaced with mock data.
}

export async function apiGet(path) {
  return request(path, { method: 'GET', headers: { 'Accept': 'application/json' } });
}

export async function apiPost(path, data) {
  return request(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...csrfHeader()
    },
    body: JSON.stringify(data)
  });
}

export async function apiPut(path, data) {
  return request(path, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...csrfHeader()
    },
    body: JSON.stringify(data)
  });
}

async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'same-origin'
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch {
      // Use the HTTP status when the response body is not JSON.
    }
    throw new Error(`API: ${detail}`);
  }
  return response.json();
}

function csrfHeader() {
  const cookie = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith('factorio_csrf='));
  if (!cookie) return {};
  return { 'X-CSRF-Token': decodeURIComponent(cookie.slice('factorio_csrf='.length)) };
}
