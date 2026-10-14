/**
 * SVG Chart Library for Factorio Security Dashboard
 * High-performance, responsive SVG charts without external dependencies
 */

import { escapeHtml } from './utils.js';

/**
 * Render an SVG Line Chart with multiple series, grid, axes and hover tooltips
 * @param {HTMLElement|string} target 
 * @param {Object} options 
 */
export function renderLineChart(target, options = {}) {
  const container = typeof target === 'string' ? document.querySelector(target) : target;
  if (!container) return;

  const {
    series = [],
    labels = [],
    unit = '%',
    minY = 0,
    maxY = null,
    showLegend = true
  } = options;

  container.innerHTML = '';
  container.classList.add('chart-container');

  if (!series.length || !labels.length) {
    container.innerHTML = '<div class="state-container"><p class="text-muted">Sin datos de telemetría disponibles</p></div>';
    return;
  }

  // Calculate bounds
  let computedMaxY = maxY;
  if (computedMaxY === null) {
    let highest = 0;
    series.forEach(s => {
      s.data.forEach(v => {
        if (v > highest) highest = v;
      });
    });
    computedMaxY = highest > 0 ? Math.ceil(highest * 1.15) : 100;
  }

  const width = 640;
  const height = 240;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 30;

  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const numPoints = labels.length;
  const stepX = numPoints > 1 ? plotWidth / (numPoints - 1) : plotWidth;

  const getYCoord = (val) => {
    const range = computedMaxY - minY;
    if (range <= 0) return padTop + plotHeight;
    const ratio = (val - minY) / range;
    return padTop + plotHeight - (ratio * plotHeight);
  };

  const getXCoord = (index) => padLeft + (index * stepX);

  // Build SVG string
  let svg = `
    <svg viewBox="0 0 ${width} ${height}" class="svg-chart" preserveAspectRatio="none">
      <defs>
  `;

  // Gradients for series
  series.forEach((s, idx) => {
    const color = s.color || '#00d4ff';
    svg += `
      <linearGradient id="lineGrad-${idx}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${color}" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="${color}" stop-opacity="0.0"/>
      </linearGradient>
    `;
  });

  svg += `
      </defs>
      <!-- Gridlines & Y-Axis Labels -->
      <g class="chart-grid">
  `;

  const yTicks = 4;
  for (let i = 0; i <= yTicks; i++) {
    const tickVal = Math.round(minY + (i * ((computedMaxY - minY) / yTicks)));
    const yPos = getYCoord(tickVal);
    svg += `
      <line x1="${padLeft}" y1="${yPos}" x2="${width - padRight}" y2="${yPos}" />
      <text x="${padLeft - 8}" y="${yPos + 4}" text-anchor="end" fill="#64748b" font-size="10" font-family="sans-serif">${tickVal}${unit}</text>
    `;
  }

  svg += `
      </g>
      <!-- X-Axis Labels -->
      <g class="chart-axis">
        <line x1="${padLeft}" y1="${height - padBottom}" x2="${width - padRight}" y2="${height - padBottom}" stroke="#1e293b" stroke-width="1"/>
  `;

  const labelStep = Math.max(1, Math.floor(labels.length / 6));
  labels.forEach((label, idx) => {
    if (idx % labelStep === 0 || idx === labels.length - 1) {
      const xPos = getXCoord(idx);
      svg += `<text x="${xPos}" y="${height - 10}" text-anchor="middle" fill="#64748b" font-size="10">${escapeHtml(label)}</text>`;
    }
  });

  svg += `</g>`;

  // Draw Area & Polyline for each series
  series.forEach((s, idx) => {
    const points = s.data.map((val, i) => `${getXCoord(i)},${getYCoord(val)}`).join(' ');
    const firstX = getXCoord(0);
    const lastX = getXCoord(s.data.length - 1);
    const bottomY = padTop + plotHeight;
    const areaPoints = `${firstX},${bottomY} ${points} ${lastX},${bottomY}`;
    const strokeColor = s.color || '#00d4ff';

    svg += `
      <!-- Series Area Fill -->
      <polygon points="${areaPoints}" fill="url(#lineGrad-${idx})" />
      <!-- Series Line -->
      <polyline points="${points}" fill="none" stroke="${strokeColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
    `;
  });

  // Interactive Hover Points & Overlay
  svg += `<g class="chart-points">`;
  series.forEach((s) => {
    const strokeColor = s.color || '#00d4ff';
    s.data.forEach((val, i) => {
      const x = getXCoord(i);
      const y = getYCoord(val);
      svg += `
        <circle cx="${x}" cy="${y}" r="3.5" fill="#0a0e17" stroke="${strokeColor}" stroke-width="2" class="chart-dot"
                data-series="${escapeHtml(s.name || '')}" data-value="${val}" data-time="${escapeHtml(labels[i])}" data-unit="${unit}">
        </circle>
      `;
    });
  });
  svg += `</g></svg>`;

  // Tooltip Element
  const tooltip = document.createElement('div');
  tooltip.className = 'chart-tooltip';
  container.appendChild(tooltip);

  // Legend (if multiple series or requested)
  if (showLegend && series.length > 0) {
    const legendEl = document.createElement('div');
    legendEl.className = 'chart-legend';
    series.forEach(s => {
      legendEl.innerHTML += `
        <div class="chart-legend-item">
          <span class="chart-legend-color" style="background-color: ${s.color || '#00d4ff'};"></span>
          <span>${escapeHtml(s.name || '')}</span>
        </div>
      `;
    });
    container.parentNode.insertBefore(legendEl, container);
  }

  container.insertAdjacentHTML('beforeend', svg);

  // Add Hover Listeners
  const dots = container.querySelectorAll('.chart-dot');
  dots.forEach(dot => {
    dot.addEventListener('mouseenter', (e) => {
      const seriesName = dot.getAttribute('data-series');
      const val = dot.getAttribute('data-value');
      const time = dot.getAttribute('data-time');
      const u = dot.getAttribute('data-unit');
      
      tooltip.innerHTML = `<strong>${time}</strong><br/>${seriesName ? `${seriesName}: ` : ''}<span style="color:#00d4ff; font-weight:700;">${val}${u}</span>`;
      tooltip.classList.add('visible');

      const rect = container.getBoundingClientRect();
      const dotRect = dot.getBoundingClientRect();
      tooltip.style.left = `${dotRect.left - rect.left + (dotRect.width / 2)}px`;
      tooltip.style.top = `${dotRect.top - rect.top}px`;
    });

    dot.addEventListener('mouseleave', () => {
      tooltip.classList.remove('visible');
    });
  });
}

/**
 * Render an SVG Bar Chart (ideal for failed logins 7 days, disk allocations)
 * @param {HTMLElement|string} target 
 * @param {Object} options 
 */
export function renderBarChart(target, options = {}) {
  const container = typeof target === 'string' ? document.querySelector(target) : target;
  if (!container) return;

  const {
    data = [], // [{ label: '08/10', value: 142, color?: '#00d4ff' }]
    unit = ' eventos',
    color = '#00d4ff',
    height = 220
  } = options;

  container.innerHTML = '';
  container.classList.add('chart-container');

  if (!data.length) {
    container.innerHTML = '<div class="state-container"><p class="text-muted">Sin datos para graficar</p></div>';
    return;
  }

  const width = 600;
  const padLeft = 45;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 35;

  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const maxValue = Math.max(...data.map(d => d.value), 10);
  const computedMaxY = Math.ceil(maxValue * 1.15);

  const barCount = data.length;
  const slotWidth = plotWidth / barCount;
  const barWidth = Math.min(32, slotWidth * 0.6);

  let svg = `
    <svg viewBox="0 0 ${width} ${height}" class="svg-chart">
      <!-- Gridlines -->
      <g class="chart-grid">
  `;

  const ticks = 4;
  for (let i = 0; i <= ticks; i++) {
    const val = Math.round((computedMaxY / ticks) * i);
    const y = padTop + plotHeight - ((val / computedMaxY) * plotHeight);
    svg += `
      <line x1="${padLeft}" y1="${y}" x2="${width - padRight}" y2="${y}" stroke="rgba(255,255,255,0.06)" stroke-dasharray="3 3"/>
      <text x="${padLeft - 8}" y="${y + 4}" text-anchor="end" fill="#64748b" font-size="10">${val}</text>
    `;
  }

  svg += `
      </g>
      <!-- Bars & Labels -->
      <g class="chart-bars">
        <line x1="${padLeft}" y1="${padTop + plotHeight}" x2="${width - padRight}" y2="${padTop + plotHeight}" stroke="#1e293b" stroke-width="1"/>
  `;

  data.forEach((item, idx) => {
    const barHeight = (item.value / computedMaxY) * plotHeight;
    const x = padLeft + (idx * slotWidth) + ((slotWidth - barWidth) / 2);
    const y = padTop + plotHeight - barHeight;
    const barColor = item.color || color;

    svg += `
      <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="4" fill="${barColor}" class="chart-bar"
            data-label="${escapeHtml(item.label)}" data-value="${item.value}" data-unit="${unit}">
      </rect>
      <text x="${x + (barWidth / 2)}" y="${height - 12}" text-anchor="middle" fill="#94a3b8" font-size="11" font-weight="500">
        ${escapeHtml(item.label)}
      </text>
    `;
  });

  svg += `</g></svg>`;

  const tooltip = document.createElement('div');
  tooltip.className = 'chart-tooltip';
  container.appendChild(tooltip);

  container.insertAdjacentHTML('beforeend', svg);

  const bars = container.querySelectorAll('.chart-bar');
  bars.forEach(bar => {
    bar.addEventListener('mouseenter', () => {
      const label = bar.getAttribute('data-label');
      const val = bar.getAttribute('data-value');
      const u = bar.getAttribute('data-unit');

      tooltip.innerHTML = `<strong>${label}</strong><br/><span style="color:#00d4ff; font-weight:700;">${val}${u}</span>`;
      tooltip.classList.add('visible');

      const rect = container.getBoundingClientRect();
      const barRect = bar.getBoundingClientRect();
      tooltip.style.left = `${barRect.left - rect.left + (barRect.width / 2)}px`;
      tooltip.style.top = `${barRect.top - rect.top}px`;
    });

    bar.addEventListener('mouseleave', () => {
      tooltip.classList.remove('visible');
    });
  });
}

/**
 * Render an SVG Donut Gauge Chart for single metric percentage (e.g. Memory, Hardening completion)
 * @param {HTMLElement|string} target 
 * @param {Object} options 
 */
export function renderDonutChart(target, options = {}) {
  const container = typeof target === 'string' ? document.querySelector(target) : target;
  if (!container) return;

  const {
    value = 0,
    max = 100,
    size = 140,
    strokeWidth = 12,
    color = '#00d4ff',
    label = '',
    subtitle = ''
  } = options;

  container.innerHTML = '';
  const percent = Math.min(100, Math.max(0, (value / max) * 100));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percent / 100) * circumference;

  const html = `
    <div class="donut-wrap" style="width: ${size}px; height: ${size}px; margin: 0 auto;">
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
        <circle
          cx="${size / 2}" cy="${size / 2}" r="${radius}"
          fill="transparent"
          stroke="#1e293b"
          stroke-width="${strokeWidth}"
        />
        <circle
          cx="${size / 2}" cy="${size / 2}" r="${radius}"
          fill="transparent"
          stroke="${color}"
          stroke-width="${strokeWidth}"
          stroke-dasharray="${circumference}"
          stroke-dashoffset="${strokeDashoffset}"
          stroke-linecap="round"
          transform="rotate(-90 ${size / 2} ${size / 2})"
          style="transition: stroke-dashoffset 0.8s ease-in-out;"
        />
      </svg>
      <div class="donut-center-label">
        <div class="donut-val">${escapeHtml(label || `${Math.round(percent)}%`)}</div>
        ${subtitle ? `<div class="donut-sub">${escapeHtml(subtitle)}</div>` : ''}
      </div>
    </div>
  `;

  container.innerHTML = html;
}
