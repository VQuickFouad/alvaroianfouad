/**
 * AI Assistant Page Module
 * Factorio Security Dashboard
 */

import { apiGet, apiPost } from '../api.js';
import { escapeHtml } from '../utils.js';
import { createCard } from '../components/card.js';
import { createLoadingSpinner, createErrorState } from '../components/loading.js';
import { showToast } from '../components/toast.js';

let isAnalyzing = false;

/**
 * Render AI Assistant Page
 * @param {HTMLElement} container 
 */
export async function renderAi(container) {
  container.innerHTML = `
    <div class="page-header">
      <div class="page-header-info">
        <h1>Asistente Inteligente de Seguridad y Diagnóstico</h1>
        <p>Correlación avanzada de eventos mediante modelos LLM locales (Ollama) o motor heurístico de reglas.</p>
      </div>
    </div>

    <!-- AI Provider Status Bar -->
    <div id="ai-status-container">
      <div class="skeleton" style="height: 40px; margin-bottom: 20px;"></div>
    </div>

    <!-- Quick Analysis Presets & Query Input -->
    <div class="card mb-4">
      <div class="card-header">
        <div>
          <h3 class="card-title">Consultas Rápidas de Seguridad</h3>
          <p class="card-subtitle">Seleccione una investigación predefinida o introduzca una pregunta personalizada</p>
        </div>
      </div>
      <div class="card-body">
        <div class="ai-query-presets">
          <button class="ai-preset-btn" data-query="Analizar eventos recientes">
            <span>🛡️</span>
            <span>Analizar eventos recientes</span>
          </button>
          <button class="ai-preset-btn" data-query="¿Por qué el servidor está lento?">
            <span>⚡</span>
            <span>¿Por qué el servidor está lento?</span>
          </button>
          <button class="ai-preset-btn" data-query="Identificar patrones sospechosos">
            <span>🔍</span>
            <span>Identificar patrones sospechosos</span>
          </button>
          <button class="ai-preset-btn" data-query="Resumen de seguridad">
            <span>📊</span>
            <span>Resumen de seguridad</span>
          </button>
        </div>

        <div class="ai-input-wrap">
          <input type="text" id="ai-custom-input" class="input" placeholder="Escriba una consulta de seguridad (ej. '¿Hay tráfico inusual en el puerto 2222?')..." />
          <button id="btn-submit-ai" class="btn btn-primary">
            <span>Consultar IA</span>
            <span>➤</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Analysis Results Output Area -->
    <div id="ai-response-container">
      <!-- Default state -->
    </div>
  `;

  // Attach Preset buttons
  const presetBtns = container.querySelectorAll('.ai-preset-btn');
  const input = container.querySelector('#ai-custom-input');
  const submitBtn = container.querySelector('#btn-submit-ai');

  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.getAttribute('data-query');
      if (input) input.value = q;
      executeAnalysis(container, q);
    });
  });

  if (submitBtn && input) {
    submitBtn.onclick = () => {
      const query = input.value.trim();
      if (!query) {
        showToast({ title: 'Entrada requerida', message: 'Por favor, introduzca una consulta para el asistente.', type: 'warning' });
        return;
      }
      executeAnalysis(container, query);
    };

    input.onkeydown = (e) => {
      if (e.key === 'Enter') {
        submitBtn.click();
      }
    };
  }

  // Load Status and default analysis
  await loadAiStatus(container);
  executeAnalysis(container, 'Resumen de seguridad');
}

export function destroyAi() {
  isAnalyzing = false;
}

async function loadAiStatus(container) {
  const statusWrap = container.querySelector('#ai-status-container');
  if (!statusWrap) return;

  try {
    const status = await apiGet('/ai/status');
    statusWrap.innerHTML = `
      <div class="ai-header-status">
        <span class="status-dot active"></span>
        <span style="font-weight: 600;">Motor Activo:</span>
        <span class="text-cyan">${escapeHtml(status.provider || 'Ollama (Llama-3-Security-8B)')}</span>
        <span style="color: var(--text-muted);">&bull; Modelo: ${escapeHtml(status.model || 'llama3-security:8b')}</span>
        <span style="color: var(--text-muted);">&bull; Endpoint: ${escapeHtml(status.endpoint || '127.0.0.1:11434')}</span>
      </div>
    `;
  } catch (err) {
    statusWrap.innerHTML = `
      <div class="ai-header-status" style="border-color: rgba(245, 158, 11, 0.4); background: rgba(245, 158, 11, 0.08);">
        <span class="status-dot warning"></span>
        <span>Asistente LLM externo no disponible. Utilizando <strong>Motor Heurístico de Reglas Locales</strong>.</span>
      </div>
    `;
  }
}

async function executeAnalysis(container, query) {
  const outputWrap = container.querySelector('#ai-response-container');
  const submitBtn = container.querySelector('#btn-submit-ai');
  if (!outputWrap || isAnalyzing) return;

  isAnalyzing = true;
  if (submitBtn) submitBtn.disabled = true;

  outputWrap.innerHTML = `
    <div class="card">
      <div class="card-body">
        ${createLoadingSpinner(`Correlacionando trazas de registros y analizando: "${escapeHtml(query)}"...`)}
      </div>
    </div>
  `;

  try {
    const result = await apiPost('/ai/analyze', { query });
    renderAnalysisResult(outputWrap, result, query);
  } catch (err) {
    outputWrap.innerHTML = createErrorState({
      title: 'Error en el motor de análisis',
      message: err.message,
      retryId: 'btn-retry-ai'
    });
    const retryBtn = outputWrap.querySelector('#btn-retry-ai');
    if (retryBtn) {
      retryBtn.onclick = () => executeAnalysis(container, query);
    }
  } finally {
    isAnalyzing = false;
    if (submitBtn) submitBtn.disabled = false;
  }
}

function renderAnalysisResult(target, result, query) {
  const confidence = result.confidence || 90;
  const confidenceColor = confidence >= 85 ? 'text-emerald' : (confidence >= 70 ? 'text-amber' : 'text-rose');

  target.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div>
          <h3 class="card-title">
            <span>🧠</span>
            <span>Informe Diagnóstico: "${escapeHtml(query)}"</span>
          </h3>
          <p class="card-subtitle">Generado por ${escapeHtml(result.provider || 'Motor de Seguridad')}</p>
        </div>
        <span class="badge badge-info">Análisis Completado</span>
      </div>
      <div class="card-body">
        <!-- Confidence Bar -->
        <div class="ai-confidence-box">
          <div style="font-size: 1.2rem;">📊</div>
          <div style="flex: 1;">
            <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 4px;">
              <span style="font-weight: 600;">Nivel de Confianza del Modelo</span>
              <span class="${confidenceColor}" style="font-weight: 700;">${confidence}%</span>
            </div>
            <div style="height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; overflow: hidden;">
              <div style="height: 100%; width: ${confidence}%; background: linear-gradient(90deg, #00d4ff, #10b981);"></div>
            </div>
          </div>
        </div>

        <!-- Analysis Text -->
        <div style="margin-bottom: 24px;">
          <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">Conclusión Técnica</h4>
          <p style="font-size: 0.9rem; line-height: 1.6; color: var(--text-primary); background: rgba(0, 212, 255, 0.04); padding: 14px 18px; border-radius: 8px; border-left: 3px solid var(--accent-cyan);">
            ${escapeHtml(result.analysis)}
          </p>
        </div>

        <!-- Evidences -->
        ${result.evidence && result.evidence.length ? `
          <div style="margin-bottom: 24px;">
            <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">Evidencias y Registros Correlacionados</h4>
            <ul class="ai-evidence-list">
              ${result.evidence.map(ev => `
                <li class="ai-evidence-item">${escapeHtml(ev)}</li>
              `).join('')}
            </ul>
          </div>
        ` : ''}

        <!-- Recommended Actions -->
        ${result.recommendations && result.recommendations.length ? `
          <div>
            <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 12px;">Acciones Recomendadas por la IA</h4>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${result.recommendations.map((rec, i) => `
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); border-radius: 6px;">
                  <span style="font-size: 0.85rem; color: var(--text-primary);">${i + 1}. ${escapeHtml(rec)}</span>
                  <a href="#automation" class="btn btn-outline btn-sm" style="font-size: 0.75rem;">Gestionar</a>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    </div>
  `;
}
