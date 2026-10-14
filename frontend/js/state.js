/**
 * State Management for Factorio Security Dashboard
 * Simple reactive store with subscriber notifications
 */

const initialState = {
  demoMode: true,
  currentRoute: 'dashboard',
  systemStatus: null,
  activeAlertsCount: 2,
  pendingActionsCount: 2,
  autoRefreshInterval: 30,
  lastUpdated: new Date(),
  sidebarCollapsed: false,
  mobileSidebarOpen: false
};

let state = { ...initialState };
const listeners = new Set();

/**
 * Get current state snapshot
 * @returns {typeof initialState}
 */
export function getState() {
  return { ...state };
}

/**
 * Update state and notify all subscribers
 * @param {Partial<typeof initialState>} updates 
 */
export function setState(updates) {
  const prevState = { ...state };
  state = { ...state, ...updates };
  notify(state, prevState);
}

/**
 * Subscribe to state changes
 * @param {(state: typeof initialState, prevState: typeof initialState) => void} listener 
 * @returns {() => void} Unsubscribe function
 */
export function subscribe(listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function notify(currState, prevState) {
  listeners.forEach((listener) => {
    try {
      listener(currState, prevState);
    } catch (err) {
      console.error('Error en listener de estado:', err);
    }
  });
}
