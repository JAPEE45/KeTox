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

  const PBPK_GAUGE_MAX = 3.0;

  const MIN_LOADING_MS = 5000;

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

  let stepInterval = null;
  const PIPELINE_STEPS = [
    {
      title: "Extracting Molecular Descriptors & 2048-bit Fingerprints...",
      step: 1,
    },
    {
      title:
        "Computing Graph Attention Network (GCN/GAT) Topology Embeddings...",
      step: 2,
    },
    { title: "Simulating PBPK Steady-State Clearance (Css)...", step: 3 },
    {
      title: "Synthesizing Random Forest + GCN Ensemble Consensus...",
      step: 4,
    },
  ];

  function startStepAnimation() {
    let currentStep = 0;
    const stageText = document.getElementById("loading-stage-text");

    function updateStep(idx) {
      if (stageText && PIPELINE_STEPS[idx]) {
        stageText.textContent = PIPELINE_STEPS[idx].title;
      }
    }

    updateStep(0);
    if (stepInterval) clearInterval(stepInterval);
    stepInterval = setInterval(() => {
      currentStep = (currentStep + 1) % PIPELINE_STEPS.length;
      updateStep(currentStep);
    }, 1200);
  }

  function stopStepAnimation() {
    if (stepInterval) {
      clearInterval(stepInterval);
      stepInterval = null;
    }
  }

  function showLoading() {
    const mainGrid = document.getElementById("main-content-grid");
    if (mainGrid) {
      mainGrid.classList.remove("flex-1", "justify-center", "-mt-16");
      mainGrid.classList.add("pt-4", "sm:pt-8", "pb-12", "sm:pb-16");
    }

    const predictSec = document.getElementById("predict-section");
    if (predictSec) {
      predictSec.classList.remove("max-w-xl");
      predictSec.classList.add("predict-sticky-bottom");
    }

    if (resultsSection) {
      resultsSection.classList.remove("revealed");
      resultsSection.style.display = "none";
    }
    const rightSidebar = document.getElementById("right-sidebar");
    if (rightSidebar) rightSidebar.style.display = "none";

    if (loadingState) {
      loadingState.style.display = "flex";
      startStepAnimation();
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtnText && (submitBtnText.textContent = "Analyzing…");
    }
  }

  function hideLoading() {
    stopStepAnimation();
    if (loadingState) {
      loadingState.style.display = "none";
    }
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
      mainGrid.classList.remove("pt-8", "pb-16", "pt-4", "pb-12");
    }

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
    window.destroyParticles?.();

    const mainGrid = document.getElementById("main-content-grid");
    if (mainGrid) {
      mainGrid.classList.remove("flex-1", "justify-center", "-mt-16");
      mainGrid.classList.add("pt-8", "pb-16");
    }

    const gridWrapper = document.getElementById("results-grid-wrapper");
    if (gridWrapper) {
      gridWrapper.classList.add("lg:grid-cols-[1fr_340px]");
      gridWrapper.style.gridTemplateColumns = "";
    }

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
          hideResults();
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
        hideResults();
        showError(
          "Network error — could not reach the prediction server. Is Flask running?",
        );
      } finally {
        hideLoading();
      }
    });

  function renderResults(data) {
    renderVerdictCard(data);
    renderModelComparison(data.models);
    renderSimilarityCard(data.similarity, data.compound_name);
    renderPBPKCard(data.pbpk);
    renderExplainability(data.shap, data.lime);

    const previewImg = document.getElementById("structure-preview-img");
    if (previewImg && data.structure_image_url) {
      previewImg.src = data.structure_image_url;
      previewImg.alt = `2D molecular structure of ${data.compound_name || "compound"}`;
    }

    setText(
      "preview-compound-name",
      data.compound_name || "Molecule Structure",
    );
    setText(
      "preview-compound-formula",
      data.formula ? `Formula: ${data.formula}` : "",
    );
    const previewSmiles = document.getElementById("preview-compound-smiles");
    if (previewSmiles) {
      previewSmiles.textContent = data.smiles || "";
      previewSmiles.title = data.smiles || "";
    }

    const heatmapImg = document.getElementById("heatmap-img");
    if (heatmapImg && data.heatmap) {
      heatmapImg.src = data.heatmap;
    }

    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function renderVerdictCard(data) {
    const isToxic = data.verdict === "toxic";
    const pct = Math.round(data.confidence * 100);
    const card = document.getElementById("verdict-card");
    if (!card) return;
    setText("verdict-badge", isToxic ? "TOXIC" : "SAFE");
    const badge = document.getElementById("verdict-badge");
    if (badge) {
      badge.className =
        "text-5xl font-black leading-none " +
        (isToxic ? "text-red-700" : "text-green-700");
    }

    setText("verdict-compound-name", data.compound_name || "Molecule");
    setText("verdict-compound-formula", data.formula || "--");
    const smilesEl = document.getElementById("verdict-compound-smiles");
    if (smilesEl) {
      smilesEl.textContent = data.smiles || "--";
      const smilesWrapper = document.getElementById(
        "verdict-compound-smiles-wrapper",
      );
      if (smilesWrapper) smilesWrapper.title = data.smiles || "";
    }

    const confEl = document.getElementById("verdict-confidence");
    if (confEl) {
      confEl.textContent = "0%";
      confEl.className =
        "text-7xl font-black leading-none " +
        (isToxic ? "text-red-700" : "text-green-700");
      animateCounter(confEl, pct, 700, "%", 0);
    }

    const summaryEl = document.getElementById("verdict-summary");
    if (summaryEl) summaryEl.innerHTML = data.summary;

    setText(
      "verdict-ensemble",
      `Models: Random Forest: ${Math.round(data.models.random_forest.probability * 100)}% · GCN: ${Math.round(data.models.gcn.probability * 100)}%`,
    );
  }

  function renderModelComparison(models) {
    renderModelCard("rf", "Random Forest", models.random_forest);
    renderModelCard("gcn", "Graph Conv. Network", models.gcn);
  }

  function renderModelCard(id, name, model) {
    const isToxic = model.label === "toxic";
    const pct = Math.round(model.probability * 100);

    setText(`${id}-label`, name);

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

    const colorClass = isToxic ? "bg-red-700" : "bg-green-600";
    animateProgressBar(`${id}-bar`, pct, colorClass);
  }

  function renderSimilarityCard(sim, compoundName) {
    animateCounter(
      document.getElementById("tanimoto-value"),
      sim.tanimoto,
      700,
      "",
      2,
    );

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

    if (compoundName) {
      setText("similarity-input-label", `Input: ${compoundName}`);
    }

    setText("similarity-description", sim.category_description);
  }

  function renderPBPKCard(pbpk) {
    const cssEl = document.getElementById("css-value");
    if (cssEl) animateCounter(cssEl, pbpk.css_mg_per_L, 700, "", 2);

    const labelEl = document.getElementById("css-label");
    if (labelEl) {
      labelEl.textContent = pbpk.css_label;
      labelEl.className =
        pbpk.css_label === "Elevated" ? "badge-elevated" : "badge-normal";
    }

    const pbpkFill = document.getElementById("pbpk-gauge-fill");
    if (pbpkFill) animateGauge(pbpkFill, pbpk.css_mg_per_L / PBPK_GAUGE_MAX);

    const threshEl = document.getElementById("css-threshold");
    if (threshEl)
      threshEl.textContent = pbpk.css_threshold.toFixed(1) + " mg/L";

    const markerEl = document.getElementById("pbpk-threshold-marker");
    if (markerEl) {
      const markerPct = (pbpk.css_threshold / PBPK_GAUGE_MAX) * 100;
      markerEl.style.left = markerPct.toFixed(1) + "%";
    }

    const noteEl = document.getElementById("pbpk-note");
    if (noteEl) noteEl.textContent = pbpk.css_note;
  }

  function renderExplainability(shap, lime) {
    window._lastSHAP = shap;
    window._lastLIME = lime;
    setTimeout(() => {
      KeToxCharts.renderSHAPChart(shap);
      KeToxCharts.renderLIMEChart(lime);
    }, 80);
    switchTab("shap");
  }

  function switchTab(tabName) {
    document
      .querySelectorAll(".tab-panel")
      .forEach((p) => p.classList.remove("active"));
    document
      .querySelectorAll("[data-tab]")
      .forEach((b) => b.classList.remove("btn-tab-active"));

    const panel = document.getElementById(`tab-${tabName}`);
    if (panel) panel.classList.add("active");

    const btn = document.querySelector(`[data-tab="${tabName}"]`);
    if (btn) btn.classList.add("btn-tab-active");

    if (tabName === "shap" && instances_exist("shap"))
      KeToxCharts.renderSHAPChart(window._lastSHAP);
    if (tabName === "lime" && instances_exist("lime"))
      KeToxCharts.renderLIMEChart(window._lastLIME);
  }

  function instances_exist(name) {
    return window[`_last${name.toUpperCase()}`] !== undefined;
  }

  const setText = window.setText;
  const animateCounter = window.animateCounter;
  const animateGauge = window.animateGauge;
  const animateProgressBar = window.animateProgressBar;

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-tab]").forEach((btn) => {
      btn.addEventListener("click", () => {
        switchTab(btn.getAttribute("data-tab"));
      });
    });

    const errorCloseBtn = document.getElementById("error-close-btn");
    if (errorCloseBtn) errorCloseBtn.addEventListener("click", hideError);

    try {
      const urlParams = new URLSearchParams(window.location.search);
      const queryParam =
        urlParams.get("compound") ||
        urlParams.get("q") ||
        urlParams.get("smiles");
      if (queryParam && compoundInput) {
        compoundInput.value = queryParam;
        if (form) {
          setTimeout(() => {
            form.dispatchEvent(
              new Event("submit", { cancelable: true, bubbles: true }),
            );
          }, 200);
        }
      }
    } catch (e) {
      console.warn("Could not read URL query params:", e);
    }
  });

  window.hideError = hideError;
  window.switchTab = switchTab;
})();
