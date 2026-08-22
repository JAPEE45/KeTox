(() => {
  "use strict";

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".tooltip-wrapper").forEach((wrapper) => {
      wrapper.addEventListener("click", (e) => {
        e.stopPropagation();
        wrapper.classList.toggle("active");
      });
    });
    document.addEventListener("click", () => {
      document
        .querySelectorAll(".tooltip-wrapper.active")
        .forEach((el) => el.classList.remove("active"));
    });
  });

  /**
   * @param {HTMLElement} fillEl
   * @param {number} ratio
   */
  function animateGauge(fillEl, ratio) {
    fillEl.style.width = "0%";
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        fillEl.style.width = `${Math.min(1, Math.max(0, ratio)) * 100}%`;
      });
    });
  }

  /**
   * @param {string} barId
   * @param {number} pct
   * @param {string} colorClass
   */
  function animateProgressBar(barId, pct, colorClass) {
    const el = document.getElementById(barId);
    if (!el) return;
    el.style.width = "0%";
    if (colorClass)
      el.className = el.className.replace(/bg-\S+/, "") + " " + colorClass;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.width = `${Math.min(100, Math.max(0, pct))}%`;
      });
    });
  }

  function scrollToResults() {
    const el = document.getElementById("results-section");
    if (!el) return;
    const offset = 80;
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top, behavior: "smooth" });
  }

  /**
   * @param {HTMLElement} el
   * @param {number} target
   * @param {number} duration
   * @param {string} suffix
   * @param {number} decimals
   */
  function animateCounter(
    el,
    target,
    duration = 600,
    suffix = "",
    decimals = 0,
  ) {
    if (!el) return;
    const start = performance.now();
    function update(ts) {
      const elapsed = ts - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;
      el.textContent = current.toFixed(decimals) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  /**
   * @param {string} id
   * @param {string|number} text
   */
  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  window.animateGauge = animateGauge;
  window.animateProgressBar = animateProgressBar;
  window.animateCounter = animateCounter;
  window.scrollToResults = scrollToResults;
  window.setText = setText;
})();
