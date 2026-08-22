window.KeToxCharts = (() => {
  // Stored Chart.js instances
  const instances = {
    shap: null,
    lime: null,
    performance: null,
    historyTimeline: null,
    agreementDonut: null,
    distribution: null,
    similarityHistory: null
  };

  // ─── Shared chart defaults ───────────────────────────────────────────────
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size   = 12;
  Chart.defaults.color       = '#475569'; // slate-600

  // ─── SHAP horizontal bar chart ───────────────────────────────────────────
  function renderSHAPChart(features) {
    const ctx = document.getElementById('shap-chart');
    if (!ctx) return;

    if (instances.shap) { instances.shap.destroy(); instances.shap = null; }

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
  function renderLIMEChart(features) {
    const ctx = document.getElementById('lime-chart');
    if (!ctx) return;

    if (instances.lime) { instances.lime.destroy(); instances.lime = null; }

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

  // ─── Historical Prediction Trajectory / Timeline Chart ─────────────────────
  /**
   * Multi-line / area chart tracking chronological predictions
   * @param {Array<object>} timeline - array of prediction objects
   * @param {'both'|'rf'|'gcn'} modelScope - active view
   */
  function renderPredictionHistoryTimeline(timeline, modelScope = 'both') {
    const ctx = document.getElementById('history-timeline-chart');
    if (!ctx) return;

    if (instances.historyTimeline) {
      instances.historyTimeline.destroy();
      instances.historyTimeline = null;
    }

    if (!timeline || timeline.length === 0) return;

    const labels = timeline.map(item => {
      const name = item.compound_name || "Compound";
      return name.length > 14 ? name.substring(0, 12) + "…" : name;
    });

    const rfData = timeline.map(item => +(item.rf_prob * 100).toFixed(1));
    const gcnData = timeline.map(item => +(item.gcn_prob * 100).toFixed(1));
    const ensData = timeline.map(item => +(item.confidence * 100).toFixed(1));

    const datasets = [];

    if (modelScope === 'both' || modelScope === 'rf') {
      datasets.push({
        label: 'Random Forest Probability',
        data: rfData,
        borderColor: '#0d9488', // teal-600
        backgroundColor: 'rgba(13, 148, 136, 0.08)',
        fill: modelScope === 'rf',
        borderWidth: 2.5,
        pointBackgroundColor: '#0d9488',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.3
      });
    }

    if (modelScope === 'both' || modelScope === 'gcn') {
      datasets.push({
        label: 'GCN Probability',
        data: gcnData,
        borderColor: '#6366f1', // indigo-500
        backgroundColor: 'rgba(99, 102, 241, 0.08)',
        fill: modelScope === 'gcn',
        borderWidth: 2.5,
        pointBackgroundColor: '#6366f1',
        pointBorderColor: '#ffffff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.3
      });
    }

    if (modelScope === 'both') {
      datasets.push({
        label: 'Ensemble Consensus',
        data: ensData,
        borderColor: '#0f172a', // slate-900
        borderDash: [5, 5],
        borderWidth: 2,
        pointBackgroundColor: '#0f172a',
        pointRadius: 3,
        tension: 0.2,
        fill: false
      });
    }

    // Safety Threshold line
    const thresholdData = timeline.map(() => 45.0);
    datasets.push({
      label: 'Toxicity Threshold (45%)',
      data: thresholdData,
      borderColor: 'rgba(220, 38, 38, 0.5)',
      borderDash: [3, 3],
      borderWidth: 1.5,
      pointRadius: 0,
      fill: false,
      hoverRadius: 0
    });

    instances.historyTimeline = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 12,
              padding: 14,
              usePointStyle: true
            }
          },
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.95)',
            titleFont: { weight: 'bold', size: 13 },
            bodySpacing: 5,
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              title: (tooltipItems) => {
                const idx = tooltipItems[0].dataIndex;
                const item = timeline[idx];
                return `${item.compound_name} ${item.formula ? `(${item.formula})` : ''}`;
              },
              afterTitle: (tooltipItems) => {
                const idx = tooltipItems[0].dataIndex;
                const item = timeline[idx];
                const agree = item.agreement || "";
                const tox = item.verdict === 'toxic' ? '⚠️ Toxic' : '✅ Safe';
                return `Verdict: ${tox} · ${agree}`;
              },
              label: ctx => ` ${ctx.dataset.label}: ${ctx.raw.toFixed(1)}%`
            }
          }
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            grid: { color: '#f1f5f9' },
            ticks: {
              callback: v => v + '%',
              stepSize: 20
            },
            title: {
              display: true,
              text: 'Inhibition Probability (%)',
              color: '#64748b',
              font: { size: 11 }
            }
          },
          x: {
            grid: { color: '#f8fafc' },
            ticks: {
              maxRotation: 45,
              minRotation: 25,
              font: { size: 10 }
            }
          }
        }
      }
    });
  }

  // ─── Model Agreement Donut Chart ──────────────────────────────────────────
  function renderModelAgreementDonut(stats) {
    const ctx = document.getElementById('agreement-donut-chart');
    if (!ctx) return;

    if (instances.agreementDonut) {
      instances.agreementDonut.destroy();
      instances.agreementDonut = null;
    }

    const astats = (stats && stats.agreement_stats) || {};
    const bothToxic = astats.both_toxic || 0;
    const bothSafe = astats.both_safe || 0;
    const rfToxicGcnSafe = astats.rf_toxic_gcn_safe || 0;
    const rfSafeGcnToxic = astats.rf_safe_gcn_toxic || 0;

    const dataValues = [bothToxic, bothSafe, rfToxicGcnSafe, rfSafeGcnToxic];
    const labels = [
      'Both Agree Toxic',
      'Both Agree Safe',
      'RF Toxic / GCN Safe (Divergent)',
      'RF Safe / GCN Toxic (Divergent)'
    ];

    instances.agreementDonut = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{
          data: dataValues,
          backgroundColor: [
            '#dc2626', // Red - Both toxic
            '#16a34a', // Green - Both safe
            '#f59e0b', // Amber - RF toxic
            '#3b82f6'  // Blue - GCN toxic
          ],
          borderColor: '#ffffff',
          borderWidth: 2.5,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 10,
              padding: 12,
              font: { size: 11 }
            }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const count = ctx.raw;
                const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
                return ` ${ctx.label}: ${count} (${pct}%)`;
              }
            }
          }
        }
      }
    });
  }

  // ─── Confidence Distribution Bar Chart ────────────────────────────────────
  function renderConfidenceDistributionChart(distribution, modelScope = 'both') {
    const ctx = document.getElementById('distribution-chart');
    if (!ctx) return;

    if (instances.distribution) {
      instances.distribution.destroy();
      instances.distribution = null;
    }

    const dist = distribution || { rf: [0,0,0,0,0], gcn: [0,0,0,0,0], ensemble: [0,0,0,0,0] };
    const bins = ['0–20% (Safe)', '20–40% (Low)', '40–60% (Borderline)', '60–80% (Moderate)', '80–100% (Toxic)'];

    const datasets = [];
    if (modelScope === 'both' || modelScope === 'rf') {
      datasets.push({
        label: 'Random Forest',
        data: dist.rf,
        backgroundColor: 'rgba(13, 148, 136, 0.75)',
        borderColor: '#0d9488',
        borderWidth: 1.5,
        borderRadius: 4
      });
    }
    if (modelScope === 'both' || modelScope === 'gcn') {
      datasets.push({
        label: 'GCN',
        data: dist.gcn,
        backgroundColor: 'rgba(99, 102, 241, 0.75)',
        borderColor: '#6366f1',
        borderWidth: 1.5,
        borderRadius: 4
      });
    }
    if (modelScope === 'both') {
      datasets.push({
        label: 'Ensemble',
        data: dist.ensemble,
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        borderColor: '#0f172a',
        borderWidth: 1.5,
        borderRadius: 4
      });
    }

    instances.distribution = new Chart(ctx, {
      type: 'bar',
      data: { labels: bins, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { boxWidth: 12, padding: 12 }
          },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} compounds`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: '#f1f5f9' },
            ticks: { stepSize: 1 },
            title: {
              display: true,
              text: 'Compound Count',
              color: '#64748b',
              font: { size: 11 }
            }
          },
          x: {
            grid: { display: false },
            ticks: { font: { size: 10 } }
          }
        }
      }
    });
  }

  // ─── Similarity Class Average Breakdown Chart ──────────────────────────────
  function renderSimilarityCategoryBarChart(simBreakdown, modelScope = 'both') {
    const ctx = document.getElementById('similarity-history-chart');
    if (!ctx) return;

    if (instances.similarityHistory) {
      instances.similarityHistory.destroy();
      instances.similarityHistory = null;
    }

    const categories = ['Sibling-like', 'Stranger-like', 'Safe-like'];
    const sb = simBreakdown || {};

    const rfAverages = categories.map(cat => (sb[cat]?.rf_avg ? +(sb[cat].rf_avg * 100).toFixed(1) : 0));
    const gcnAverages = categories.map(cat => (sb[cat]?.gcn_avg ? +(sb[cat].gcn_avg * 100).toFixed(1) : 0));
    const ensAverages = categories.map(cat => (sb[cat]?.ens_avg ? +(sb[cat].ens_avg * 100).toFixed(1) : 0));

    const datasets = [];
    if (modelScope === 'both' || modelScope === 'rf') {
      datasets.push({
        label: 'Random Forest Avg Prob',
        data: rfAverages,
        backgroundColor: 'rgba(13, 148, 136, 0.85)',
        borderColor: '#0d9488',
        borderWidth: 1.5,
        borderRadius: 4
      });
    }
    if (modelScope === 'both' || modelScope === 'gcn') {
      datasets.push({
        label: 'GCN Avg Prob',
        data: gcnAverages,
        backgroundColor: 'rgba(99, 102, 241, 0.85)',
        borderColor: '#6366f1',
        borderWidth: 1.5,
        borderRadius: 4
      });
    }
    if (modelScope === 'both') {
      datasets.push({
        label: 'Ensemble Avg Conf',
        data: ensAverages,
        backgroundColor: 'rgba(15, 23, 42, 0.85)',
        borderColor: '#0f172a',
        borderWidth: 1.5,
        borderRadius: 4
      });
    }

    instances.similarityHistory = new Chart(ctx, {
      type: 'bar',
      data: { labels: categories, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, padding: 12 } },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${ctx.raw.toFixed(1)}%`
            }
          }
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            grid: { color: '#f1f5f9' },
            ticks: { callback: v => v + '%' },
            title: {
              display: true,
              text: 'Avg Inhibition Risk (%)',
              color: '#64748b',
              font: { size: 11 }
            }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  return {
    renderSHAPChart,
    renderLIMEChart,
    renderPerformanceChart,
    renderPredictionHistoryTimeline,
    renderModelAgreementDonut,
    renderConfidenceDistributionChart,
    renderSimilarityCategoryBarChart
  };
})();

