/**
 * predict.js — KeTox Prediction Form Logic
 *
 * Handles:
 *  - SMILES form submission → fetch /predict → render results
 *  - Loading and error states
 *  - Example chip population
 *  - Tab switching (SHAP / LIME / Heatmap)
 *  - All result section DOM population
 *
 * Scoped in an IIFE to avoid polluting global scope.
 * hideError and switchTab are exposed on window for any external callers.
 */
(() => {
  "use strict";

  // ─── PBPK gauge scale constant ─────────────────────────────────────────────
  // All PBPK gauge fills are computed relative to this maximum (mg/L).
  // Change this one value to rescale the gauge across the entire app.
  const PBPK_GAUGE_MAX = 3.0;

  // ─── Minimum loading display time ──────────────────────────────────────────
  // The fetch + this timer run in parallel via Promise.all(), so the loading
  // screen is shown for at least MIN_LOADING_MS milliseconds.
  //
  // Currently 5 s because the mock server responds in <10 ms and the animated
  // result cards need time to be appreciated.
  //
  // REDUCE THIS once real ML inference is wired in:
  //   • RDKit + RF:   ~200–400 ms  → set to 500
  //   • GCN:          ~1–3 s       → set to 0 (real latency is the floor)
  //   • Full pipeline: measure p95 → use that as the floor
  const MIN_LOADING_MS = 5000;

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

  let errorTimeout = null;

  function showError(msg) {
    if (errorBanner) {
      if (errorMsg) errorMsg.textContent = msg;
      errorBanner.style.display = "flex";
      if (window.lucide) lucide.createIcons();

      // Auto-dismiss after 5 seconds
      if (errorTimeout) clearTimeout(errorTimeout);
      errorTimeout = setTimeout(() => {
        hideError();
      }, 5000);
    }
  }

  function hideError() {
    if (errorBanner) {
      errorBanner.style.display = "none";
      if (errorTimeout) clearTimeout(errorTimeout);
    }
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
      mainGrid.classList.add("flex-1", "justify-center", "-mt-16");
      mainGrid.classList.remove("pt-8", "pb-16");
    }

    // Ensure 1-column grid when results are hidden
    const gridWrapper = document.getElementById("results-grid-wrapper");
    if (gridWrapper) {
      gridWrapper.classList.remove("lg:grid-cols-[1fr_340px]");
      gridWrapper.style.gridTemplateColumns = "";
    }

    const predictSec = document.getElementById("predict-section");
    if (predictSec) {
      predictSec.classList.remove("predict-sticky-bottom");
      predictSec.classList.add("max-w-xl");
    }

    const leftCol = document.getElementById("left-column");
    if (leftCol) leftCol.classList.add("items-center");
  }

  function showResults() {
    // Destroy particle background — it only belongs on the initial landing page
    window.destroyParticles?.();

    const mainGrid = document.getElementById("main-content-grid");
    if (mainGrid) {
      mainGrid.classList.remove("flex-1", "justify-center", "-mt-16");
      mainGrid.classList.add("pt-8", "pb-16");
    }

    // Switch to two-column grid on desktop
    const gridWrapper = document.getElementById("results-grid-wrapper");
    if (gridWrapper) {
      gridWrapper.classList.add("lg:grid-cols-[1fr_340px]");
      gridWrapper.style.gridTemplateColumns = "";
    }

    // Expand left column back to full-width flow (no centering override)
    const leftCol = document.getElementById("left-column");
    if (leftCol) leftCol.classList.remove("items-center");

    const predictSec = document.getElementById("predict-section");
    if (predictSec) {
      predictSec.classList.remove("max-w-xl");
      predictSec.classList.add("predict-sticky-bottom");
    }

    if (resultsSection) {
      resultsSection.style.display = "flex";
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
        // Run the fetch call in parallel with a minimum loading delay timer.
        // See MIN_LOADING_MS at the top of this file to adjust the floor.
        const minLoadingTime = new Promise((resolve) =>
          setTimeout(resolve, MIN_LOADING_MS),
        );

        const fetchPromise = fetch("/predict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            compound_name: compoundName,
            name: compoundName,
            smiles: compoundName,
          }),
        }).then(async (res) => {
          const data = await res.json();
          return { ok: res.ok, data };
        });

        const [fetchResult] = await Promise.all([fetchPromise, minLoadingTime]);
        const { ok, data } = fetchResult;

        if (!ok || data.status === "error") {
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

    // Update the Structure Preview sidebar image & details
    const previewImg = document.getElementById("structure-preview-img");
    if (previewImg && data.structure_image_url) {
      previewImg.src = data.structure_image_url;
      previewImg.alt = `2D molecular structure of ${data.compound_name || "compound"}`;
    }

    setText("preview-compound-name", data.compound_name || "Molecule Structure");
    setText("preview-compound-formula", data.formula ? `Formula: ${data.formula}` : "");
    const previewSmiles = document.getElementById("preview-compound-smiles");
    if (previewSmiles) {
      previewSmiles.textContent = data.smiles || "";
      previewSmiles.title = data.smiles || "";
    }

    // Update the Heatmap image
    const heatmapImg = document.getElementById("heatmap-img");
    if (heatmapImg && data.heatmap) {
      heatmapImg.src = data.heatmap;
    }

    // Re-initialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }
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

    // Compound Name, Formula & SMILES Badges
    setText("verdict-compound-name", data.compound_name || "Molecule");
    setText("verdict-compound-formula", data.formula || "--");
    const smilesEl = document.getElementById("verdict-compound-smiles");
    if (smilesEl) {
      smilesEl.textContent = data.smiles || "--";
      const smilesWrapper = document.getElementById("verdict-compound-smiles-wrapper");
      if (smilesWrapper) smilesWrapper.title = data.smiles || "";
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

    // Summary text
    const summaryEl = document.getElementById("verdict-summary");
    if (summaryEl) summaryEl.innerHTML = data.summary;

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

    // Progress bar — delegate to ui.js animateProgressBar
    const colorClass = isToxic ? "bg-red-700" : "bg-green-600";
    animateProgressBar(`${id}-bar`, pct, colorClass);
  }

  // SimilarityCard
  function renderSimilarityCard(sim, compoundName) {
    animateCounter(
      document.getElementById("tanimoto-value"),
      sim.tanimoto,
      700,
      "",
      2,
    );

    // Animate the Tanimoto similarity gauge bar (id="tanimoto-gauge-fill" in HTML)
    const tanimotoFill = document.getElementById("tanimoto-gauge-fill");
    if (tanimotoFill) animateGauge(tanimotoFill, sim.tanimoto);

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

    // similarity-input-label is optional — shows "Input: <compound>" if present
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

    // Animate PBPK gauge — fills proportionally up to PBPK_GAUGE_MAX (mg/L)
    const pbpkFill = document.getElementById("pbpk-gauge-fill");
    if (pbpkFill) animateGauge(pbpkFill, pbpk.css_mg_per_L / PBPK_GAUGE_MAX);

    // Populate threshold label (id="css-threshold" in the sidebar HTML)
    const threshEl = document.getElementById("css-threshold");
    if (threshEl)
      threshEl.textContent = pbpk.css_threshold.toFixed(1) + " mg/L";

    // Reposition the IC50 threshold marker to the correct proportion
    const markerEl = document.getElementById("pbpk-threshold-marker");
    if (markerEl) {
      const markerPct = (pbpk.css_threshold / PBPK_GAUGE_MAX) * 100;
      markerEl.style.left = markerPct.toFixed(1) + "%";
    }

    const noteEl = document.getElementById("pbpk-note");
    if (noteEl) noteEl.textContent = pbpk.css_note;
  }

  // ExplainabilityTabs — charts
  function renderExplainability(shap, lime) {
    // Cache data so switchTab() can re-render on tab switch
    window._lastSHAP = shap;
    window._lastLIME = lime;
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
  // All helpers are provided by ui.js and exported to window.*
  // Alias them locally so they work inside this IIFE without window. prefix.
  const setText = window.setText;
  const animateCounter = window.animateCounter;
  const animateGauge = window.animateGauge;
  const animateProgressBar = window.animateProgressBar;

  // ─── Wire up tab button clicks + example chips + initial page state ─────────
  document.addEventListener("DOMContentLoaded", () => {
    // Tab button click listeners
    document.querySelectorAll("[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        switchTab(btn.getAttribute("data-tab"));
      });
    });

    // Error close button — replaces inline onclick="hideError()" in HTML
    const errorCloseBtn = document.getElementById("error-close-btn");
    if (errorCloseBtn) errorCloseBtn.addEventListener("click", hideError);

    // Auto-fill and submit if query parameter is provided (e.g. from history table)
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const queryParam = urlParams.get("compound") || urlParams.get("q") || urlParams.get("smiles");
      if (queryParam && compoundInput) {
        compoundInput.value = queryParam;
        if (form) {
          setTimeout(() => {
            form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
          }, 200);
        }
      }
    } catch (e) {
      console.warn("Could not read URL query params:", e);
    }
  });

  // ─── Public API ────────────────────────────────────────────────────────────
  // Expose only what external scripts need.
  window.hideError = hideError;
  window.switchTab = switchTab;
})(); // end IIFE
