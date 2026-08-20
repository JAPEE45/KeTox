/**
 * charts.js — KeTox Chart.js chart renderers
 *
 * Exports three functions into the window.KeToxCharts namespace:
 *   renderSHAPChart(features)          — SHAP horizontal bar chart
 *   renderLIMEChart(features)          — LIME horizontal bar chart (green/red)
 *   renderPerformanceChart(model, data) — Grouped bar chart for /performance page
 *
 * All chart instances are stored so they can be destroyed before re-render.
 */

window.KeToxCharts = (() => {
  // Stored Chart.js instances
  const instances = { shap: null, lime: null, performance: null };

  // ─── Shared chart defaults ───────────────────────────────────────────────
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size   = 12;
  Chart.defaults.color       = '#475569'; // slate-600

  // ─── SHAP horizontal bar chart ───────────────────────────────────────────
  /**
   * @param {Array<{feature: string, value: number}>} features
   *   Positive values → push toward TOXIC (red)
   *   Negative values → push toward SAFE (blue-green)
   */
  function renderSHAPChart(features) {
    const ctx = document.getElementById('shap-chart');
    if (!ctx) return;

    if (instances.shap) { instances.shap.destroy(); instances.shap = null; }

    // Sort by absolute value, descending
    const sorted = [...features].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

    const labels = sorted.map(f => f.feature);
    const values = sorted.map(f => f.value);
    const colors = values.map(v =>
      v >= 0 ? 'rgba(220, 38, 38, 0.75)' : 'rgba(13, 148, 136, 0.75)'
    );
    const borderColors = values.map(v =>
      v >= 0 ? 'rgb(220, 38, 38)' : 'rgb(13, 148, 136)'
    );

    instances.shap = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'SHAP Value',
          data: values,
          backgroundColor: colors,
          borderColor: borderColors,
          borderWidth: 1.5,
          borderRadius: 4,
          barThickness: 20,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => {
                const val = ctx.raw;
                const dir = val >= 0 ? '↑ Toward Toxic' : '↓ Toward Safe';
                return ` ${dir}  (SHAP = ${val.toFixed(3)})`;
              }
            }
          }
        },
        scales: {
          x: {
            grid:  { color: '#f1f5f9' },
            border: { dash: [4, 4] },
            ticks: { callback: v => v.toFixed(2) },
            title: {
              display: true,
              text: 'SHAP Value  (+ = Toxic  /  − = Safe)',
              color: '#64748b',
              font: { size: 11 }
            }
          },
          y: {
            grid: { display: false },
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        }
      }
    });
  }

  // ─── LIME horizontal bar chart ───────────────────────────────────────────
  /**
   * @param {Array<{feature: string, weight: number, direction: 'toxic'|'safe'}>} features
   */
  function renderLIMEChart(features) {
    const ctx = document.getElementById('lime-chart');
    if (!ctx) return;

    if (instances.lime) { instances.lime.destroy(); instances.lime = null; }

    // Sort: toxic (positive weight) first, then safe
    const sorted = [...features].sort((a, b) => {
      const signA = a.direction === 'toxic' ?  a.weight : -a.weight;
      const signB = b.direction === 'toxic' ?  b.weight : -b.weight;
      return signB - signA;
    });

    const labels = sorted.map(f => f.feature);
    const values = sorted.map(f => f.direction === 'toxic' ? f.weight : -Math.abs(f.weight));
    const colors = sorted.map(f =>
      f.direction === 'toxic' ? 'rgba(220, 38, 38, 0.75)' : 'rgba(22, 163, 74, 0.75)'
    );
    const borderColors = sorted.map(f =>
      f.direction === 'toxic' ? 'rgb(220, 38, 38)' : 'rgb(22, 163, 74)'
    );

    instances.lime = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'LIME Weight',
          data: values,
          backgroundColor: colors,
          borderColor: borderColors,
          borderWidth: 1.5,
          borderRadius: 4,
          barThickness: 20,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => {
                const f = sorted[ctx.dataIndex];
                const dir = f.direction === 'toxic' ? '⬆ Pushes Toxic' : '⬇ Pushes Safe';
                return ` ${dir}  (weight = ${Math.abs(f.weight).toFixed(3)})`;
              }
            }
          }
        },
        scales: {
          x: {
            grid:  { color: '#f1f5f9' },
            border: { dash: [4, 4] },
            ticks: { callback: v => v.toFixed(2) },
            title: {
              display: true,
              text: 'LIME Weight  (red = Toxic  /  green = Safe)',
              color: '#64748b',
              font: { size: 11 }
            }
          },
          y: {
            grid: { display: false },
            ticks: { font: { family: "'JetBrains Mono', monospace", size: 11 } }
          }
        }
      }
    });
  }

  // ─── Performance grouped bar chart ────────────────────────────────────────
  /**
   * @param {'rf'|'gcn'} model
   * @param {object} data  { sibling, stranger, safe, overall } each with
   *                        { accuracy, sensitivity, specificity, mcc }
   */
  function renderPerformanceChart(model, data) {
    const ctx = document.getElementById('performance-chart');
    if (!ctx) return;

    if (instances.performance) { instances.performance.destroy(); instances.performance = null; }

    const groups = ['Sibling', 'Stranger', 'Safe'];
    const keys   = ['sibling', 'stranger', 'safe'];

    const metrics = [
      { label: 'Accuracy',    key: 'accuracy',    color: 'rgba(30,58,95,0.8)',  border: '#1e3a5f' },
      { label: 'Sensitivity', key: 'sensitivity', color: 'rgba(13,148,136,0.8)', border: '#0d9488' },
      { label: 'Specificity', key: 'specificity', color: 'rgba(37,99,235,0.8)',  border: '#2563eb' },
      { label: 'MCC',         key: 'mcc',         color: 'rgba(217,119,6,0.8)',  border: '#d97706' },
    ];

    const datasets = metrics.map(m => ({
      label: m.label,
      data: keys.map(k => +(data[k][m.key] * 100).toFixed(1)),
      backgroundColor: m.color,
      borderColor: m.border,
      borderWidth: 1.5,
      borderRadius: 5,
    }));

    instances.performance = new Chart(ctx, {
      type: 'bar',
      data: { labels: groups, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { padding: 16, usePointStyle: true, pointStyle: 'rectRounded' }
          },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${ctx.raw.toFixed(1)}%`
            }
          }
        },
        scales: {
          y: {
            min: 60,
            max: 100,
            grid: { color: '#f1f5f9' },
            ticks: { callback: v => v + '%' },
            title: {
              display: true,
              text: 'Score (%)',
              color: '#64748b',
              font: { size: 11 }
            }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  return { renderSHAPChart, renderLIMEChart, renderPerformanceChart };
})();
