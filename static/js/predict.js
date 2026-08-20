/**
 * predict.js — KeTox Prediction Form Logic
 *
 * Handles:
 *  - SMILES form submission → fetch /predict → render results
 *  - Loading and error states
 *  - Example chip population
 *  - Tab switching (SHAP / LIME / Heatmap)
 *  - All result section DOM population
 */

// ─── Example Molecule chips ────────────────────────────────────────────────
// Clicking an example populates the molecule name into the search input.
const EXAMPLES = [
  {
    id: "ex-ketoconazole",
    label: "Ketoconazole",
    type: "toxic",
    value: "Ketoconazole",
  },
  {
    id: "ex-safe",
    label: "Safe compound example",
    type: "safe",
    value: "Aspirin",
  },
  {
    id: "ex-toxic",
    label: "Toxic compound example",
    type: "toxic",
    value: "Fluconazole",
  },
];

// ─── DOM references ────────────────────────────────────────────────────────
const form = document.getElementById("predict-form");
const compoundInput =
  document.getElementById("compound-input") ||
  document.getElementById("smiles-input");
const loadingState = document.getElementById("loading-state");
const errorBanner = document.getElementById("error-banner");
const errorMsg = document.getElementById("error-message");
const resultsSection = document.getElementById("results-section");
const submitBtn = document.getElementById("submit-btn");
const submitBtnText = document.getElementById("submit-btn-text");

// ─── State helpers ─────────────────────────────────────────────────────────
function showLoading() {
  loadingState && (loadingState.style.display = "block");
  resultsSection && resultsSection.classList.remove("revealed");
  resultsSection && (resultsSection.style.display = "none");
  const rightSidebar = document.getElementById("right-sidebar");
  if (rightSidebar) rightSidebar.style.display = "none";
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtnText && (submitBtnText.textContent = "Analyzing…");
  }
}

function hideLoading() {
  loadingState && (loadingState.style.display = "none");
  if (submitBtn) {
    submitBtn.disabled = false;
    submitBtnText && (submitBtnText.textContent = "Run Prediction");
  }
}

function showError(msg) {
  if (errorBanner) errorBanner.style.display = "flex";
  if (errorMsg) errorMsg.textContent = msg;
  hideResults();
}

function hideError() {
  if (errorBanner) errorBanner.style.display = "none";
}

function hideResults() {
  if (resultsSection) {
    resultsSection.style.display = "none";
    resultsSection.classList.remove("revealed");
  }
  const rightSidebar = document.getElementById("right-sidebar");
  if (rightSidebar) rightSidebar.style.display = "none";

  const mainGrid = document.getElementById("main-content-grid");
  if (mainGrid) {
    mainGrid.classList.add("flex-1", "justify-center");
    mainGrid.classList.remove("pt-8", "pb-16");
  }

  const predictSec = document.getElementById("predict-section");
  if (predictSec) {
    predictSec.classList.remove("predict-sticky-bottom");
  }
}

function showResults() {
  const mainGrid = document.getElementById("main-content-grid");
  if (mainGrid) {
    mainGrid.classList.remove("flex-1", "justify-center");
    mainGrid.classList.add("pt-8", "pb-16");
  }

  const predictSec = document.getElementById("predict-section");
  if (predictSec) {
    predictSec.classList.add("predict-sticky-bottom");
  }

  if (resultsSection) {
    resultsSection.style.display = "flex";
    // Trigger stagger animation on next frame
    requestAnimationFrame(() => resultsSection.classList.add("revealed"));
  }

  const rightSidebar = document.getElementById("right-sidebar");
  if (rightSidebar) {
    rightSidebar.style.display = "block";
  }
}

// ─── Form submission ───────────────────────────────────────────────────────
form &&
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const inputEl =
      document.getElementById("compound-input") ||
      document.getElementById("smiles-input");
    const compoundName = inputEl ? inputEl.value.trim() : "";

    if (!compoundName) {
      showError(
        "Please enter a molecule or compound name before running the prediction.",
      );
      return;
    }

    hideError();
    showLoading();

    try {
      const res = await fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          compound_name: compoundName,
          name: compoundName,
          smiles: compoundName,
        }),
      });

      const data = await res.json();

      if (!res.ok || data.status === "error") {
        showError(
          data.message ||
            "Prediction failed. Please check your input and try again.",
        );
        return;
      }

      renderResults(data);
      showResults();
      setTimeout(scrollToResults, 100);
    } catch (err) {
      showError(
        "Network error — could not reach the prediction server. Is Flask running?",
      );
    } finally {
      hideLoading();
    }
  });

// ─── Results rendering ─────────────────────────────────────────────────────
function renderResults(data) {
  renderVerdictCard(data);
  renderModelComparison(data.models);
  renderSimilarityCard(data.similarity, data.compound_name);
  renderPBPKCard(data.pbpk);
  renderExplainability(data.shap, data.lime);
}

// VerdictCard
function renderVerdictCard(data) {
  const isToxic = data.verdict === "toxic";
  const pct = Math.round(data.confidence * 100);
  const card = document.getElementById("verdict-card");
  if (!card) return;

  // No card border styling in new layout — plain text verdict

  // Badge — large text matching prototype
  setText("verdict-badge", isToxic ? "TOXIC" : "SAFE");
  const badge = document.getElementById("verdict-badge");
  if (badge) {
    badge.className =
      "text-5xl font-black leading-none " +
      (isToxic ? "text-red-700" : "text-green-700");
  }

  // Compound Name Tag if present
  if (data.compound_name) {
    setText("verdict-compound-name", data.compound_name);
  }

  // Confidence number — match prototype large sizing
  const confEl = document.getElementById("verdict-confidence");
  if (confEl) {
    confEl.textContent = "0%";
    confEl.className =
      "text-7xl font-black leading-none " +
      (isToxic ? "text-red-700" : "text-green-700");
    animateCounter(confEl, pct, 700, "%", 0);
  }

  // Icon (element removed in prototype layout — null-safe)
  const iconEl = document.getElementById("verdict-icon");
  if (iconEl) {
    iconEl.className =
      "w-16 h-16 rounded-full flex items-center justify-center flex-shrink-0 " +
      (isToxic ? "bg-red-100" : "bg-green-100");
    iconEl.innerHTML = isToxic
      ? `<svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>`
      : `<svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
  }

  // Summary text
  setText("verdict-summary", data.summary);

  // Ensemble label — matches pill in new layout
  setText(
    "verdict-ensemble",
    `Models: Random Forest: ${Math.round(data.models.random_forest.probability * 100)}% · GCN: ${Math.round(data.models.gcn.probability * 100)}%`,
  );
}

// ModelComparisonRow
function renderModelComparison(models) {
  renderModelCard("rf", "Random Forest", models.random_forest);
  renderModelCard("gcn", "Graph Conv. Network", models.gcn);
}

function renderModelCard(id, name, model) {
  const isToxic = model.label === "toxic";
  const pct = Math.round(model.probability * 100);

  // label element removed in new layout — null-safe
  setText(`${id}-label`, name);

  // Verdict: plain bold coloured text (not a badge pill)
  const verdictEl = document.getElementById(`${id}-verdict`);
  if (verdictEl) {
    verdictEl.textContent = isToxic ? "TOXIC" : "SAFE";
    verdictEl.className =
      "text-base font-black " + (isToxic ? "text-red-600" : "text-green-600");
  }

  const probEl = document.getElementById(`${id}-probability`);
  if (probEl) {
    probEl.className =
      "text-3xl font-black " + (isToxic ? "text-red-700" : "text-green-700");
    animateCounter(probEl, pct, 600, "%", 0);
  }

  // Progress bar
  const bar = document.getElementById(`${id}-bar`);
  if (bar) {
    bar.style.width = "0%";
    bar.className =
      "h-full rounded-full transition-all duration-700 " +
      (isToxic ? "bg-red-700" : "bg-green-600");
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        bar.style.width = pct + "%";
      }),
    );
  }
}

// SimilarityCard
function renderSimilarityCard(sim, compoundName) {
  const pct = Math.round(sim.tanimoto * 100);
  animateCounter(
    document.getElementById("tanimoto-value"),
    sim.tanimoto,
    700,
    "",
    2,
  );

  const gaugeFill = document.getElementById("tanimoto-gauge-fill");
  if (gaugeFill) animateGauge(gaugeFill, sim.tanimoto);

  const catEl = document.getElementById("similarity-category");
  if (catEl) {
    catEl.textContent = sim.category;
    const cls =
      {
        "Sibling-like": "badge-sibling",
        "Stranger-like": "badge-stranger",
        "Safe-like": "badge-safe",
      }[sim.category] || "badge-stranger";
    catEl.className = cls;
  }

  if (compoundName) {
    setText("similarity-input-label", `Input: ${compoundName}`);
  }

  setText("similarity-description", sim.category_description);
}

// PBPKCard
function renderPBPKCard(pbpk) {
  const cssEl = document.getElementById("css-value");
  if (cssEl) animateCounter(cssEl, pbpk.css_mg_per_L, 700, "", 2);

  const labelEl = document.getElementById("css-label");
  if (labelEl) {
    labelEl.textContent = pbpk.css_label;
    labelEl.className =
      pbpk.css_label === "Elevated" ? "badge-elevated" : "badge-normal";
  }

  const threshEl = document.getElementById("css-threshold");
  if (threshEl) threshEl.textContent = pbpk.css_threshold.toFixed(1);

  const noteEl = document.getElementById("pbpk-note");
  if (noteEl) noteEl.textContent = pbpk.css_note;
}

// ExplainabilityTabs — charts
function renderExplainability(shap, lime) {
  // Small delay so the tab panels are visible in DOM before Chart.js measures them
  setTimeout(() => {
    KeToxCharts.renderSHAPChart(shap);
    KeToxCharts.renderLIMEChart(lime);
  }, 80);
  // Switch to SHAP tab by default
  switchTab("shap");
}

// ─── Tab switching ─────────────────────────────────────────────────────────
function switchTab(tabName) {
  // Hide all panels
  document
    .querySelectorAll(".tab-panel")
    .forEach((p) => p.classList.remove("active"));
  // Deactivate all tab buttons
  document
    .querySelectorAll("[data-tab]")
    .forEach((b) => b.classList.remove("btn-tab-active"));

  // Show target panel
  const panel = document.getElementById(`tab-${tabName}`);
  if (panel) panel.classList.add("active");

  // Activate button
  const btn = document.querySelector(`[data-tab="${tabName}"]`);
  if (btn) btn.classList.add("btn-tab-active");

  // Re-render chart if switching to SHAP or LIME (canvas needs visible container)
  if (tabName === "shap" && instances_exist("shap"))
    KeToxCharts.renderSHAPChart(window._lastSHAP);
  if (tabName === "lime" && instances_exist("lime"))
    KeToxCharts.renderLIMEChart(window._lastLIME);
}

// Check if chart data has been stored
function instances_exist(name) {
  return window[`_last${name.toUpperCase()}`] !== undefined;
}

// ─── Helpers ───────────────────────────────────────────────────────────────
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ─── Wire up tab button clicks ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchTab(btn.getAttribute("data-tab"));
    });
  });
});

