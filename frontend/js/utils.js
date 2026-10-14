/**
 * Utilities & Helper Functions
 * Factorio Security Dashboard
 */

/**
 * Format bytes to human readable format (B, KB, MB, GB, TB)
 * @param {number} bytes 
 * @param {number} decimals 
 * @returns {string}
 */
export function formatBytes(bytes, decimals = 1) {
  if (bytes === 0 || bytes === undefined || bytes === null) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
  if (i < 0) return bytes + ' B';
  const val = parseFloat((bytes / Math.pow(k, i)).toFixed(dm));
  return `${val} ${sizes[i]}`;
}

/**
 * Format percentage
 * @param {number} value 
 * @param {number} decimals 
 * @returns {string}
 */
export function formatPercent(value, decimals = 1) {
  if (value === undefined || value === null || isNaN(value)) return '0%';
  return `${Number(value).toFixed(decimals)}%`;
}

/**
 * Format Date to Spanish localized string
 * @param {string|Date|number} dateInput 
 * @param {'full'|'date'|'time'|'short'} mode 
 * @returns {string}
 */
export function formatDate(dateInput, mode = 'full') {
  if (!dateInput) return '—';
  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return String(dateInput);

  const pad = (n) => String(n).padStart(2, '0');
  const d = pad(date.getDate());
  const m = pad(date.getMonth() + 1);
  const y = date.getFullYear();
  const h = pad(date.getHours());
  const min = pad(date.getMinutes());
  const s = pad(date.getSeconds());

  if (mode === 'date') return `${d}/${m}/${y}`;
  if (mode === 'time') return `${h}:${min}:${s}`;
  if (mode === 'short') return `${d}/${m} ${h}:${min}`;
  return `${d}/${m}/${y} ${h}:${min}:${s}`;
}

/**
 * Format relative time in Spanish (e.g. "hace 5 min")
 * @param {string|Date|number} dateInput 
 * @returns {string}
 */
export function formatRelativeTime(dateInput) {
  if (!dateInput) return '—';
  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return String(dateInput);

  const now = new Date();
  const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffSec < 0) {
    const futureSec = Math.abs(diffSec);
    if (futureSec < 60) return `en ${futureSec} s`;
    if (futureSec < 3600) return `en ${Math.floor(futureSec / 60)} min`;
    if (futureSec < 86400) return `en ${Math.floor(futureSec / 3600)} h`;
    return `en ${Math.floor(futureSec / 86400)} días`;
  }

  if (diffSec < 5) return 'justo ahora';
  if (diffSec < 60) return `hace ${diffSec} s`;
  if (diffSec < 3600) return `hace ${Math.floor(diffSec / 60)} min`;
  if (diffSec < 86400) return `hace ${Math.floor(diffSec / 3600)} h`;
  if (diffSec < 2592000) return `hace ${Math.floor(diffSec / 86400)} d`;
  return formatDate(date, 'date');
}

/**
 * Format duration in seconds (e.g. "2m 15s")
 * @param {number} seconds 
 * @returns {string}
 */
export function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0s';
  const s = Math.floor(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const remSec = s % 60;
  if (m < 60) return `${m}m ${remSec}s`;
  const h = Math.floor(m / 60);
  const remMin = m % 60;
  return `${h}h ${remMin}m`;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} str 
 * @returns {string}
 */
export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Truncate text to a maximum length with ellipsis
 * @param {string} str 
 * @param {number} max 
 * @returns {string}
 */
export function truncateText(str, max = 50) {
  if (!str) return '';
  if (str.length <= max) return str;
  return str.substring(0, max) + '...';
}

/**
 * Debounce a function
 * @param {Function} func 
 * @param {number} wait 
 * @returns {Function}
 */
export function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Delay execution for ms milliseconds
 * @param {number} ms 
 * @returns {Promise<void>}
 */
export function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
