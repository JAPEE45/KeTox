/**
 * ui.js — KeTox UI Helpers
 * Tooltips, gauge bars, scroll helpers, nav highlighting.
 *
 * Wrapped in an IIFE to avoid polluting global scope.
 * Public functions are explicitly exported to window.* so external scripts
 * (predict.js, performance.html inline scripts) can call them.
 */
(() => {
  'use strict';

  // ─── Tooltips ──────────────────────────────────────────────────────────────
  // On mobile, tap toggles; on desktop, CSS hover handles it.
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tooltip-wrapper').forEach(wrapper => {
      wrapper.addEventListener('click', e => {
        e.stopPropagation();
        wrapper.classList.toggle('active');
      });
    });
    document.addEventListener('click', () => {
      document.querySelectorAll('.tooltip-wrapper.active')
        .forEach(el => el.classList.remove('active'));
    });
  });

  // ─── Nav active state ──────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    document.querySelectorAll('[data-nav-path]').forEach(link => {
      const linkPath = link.getAttribute('data-nav-path');
      const isActive =
        (linkPath === '/' && path === '/') ||
        (linkPath !== '/' && path.startsWith(linkPath));
      if (isActive) link.classList.add('nav-link-active');
    });
  });

  // ─── Gauge bar ─────────────────────────────────────────────────────────────
  /**
   * Animates a .gauge-fill element to the given ratio (0–1).
   * @param {HTMLElement} fillEl
   * @param {number} ratio  0.0 – 1.0
   */
  function animateGauge(fillEl, ratio) {
    fillEl.style.width = '0%';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        fillEl.style.width = `${Math.min(1, Math.max(0, ratio)) * 100}%`;
      });
    });
  }

  // ─── Progress bar ──────────────────────────────────────────────────────────
  /**
   * Fills a progress bar element to the given percentage.
   * @param {string} barId
   * @param {number} pct  0–100
   * @param {string} colorClass  CSS color class to apply
   */
  function animateProgressBar(barId, pct, colorClass) {
    const el = document.getElementById(barId);
    if (!el) return;
    el.style.width = '0%';
    if (colorClass) el.className = el.className.replace(/bg-\S+/, '') + ' ' + colorClass;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.width = `${Math.min(100, Math.max(0, pct))}%`;
      });
    });
  }

  // ─── Smooth scroll to results ──────────────────────────────────────────────
  function scrollToResults() {
    const el = document.getElementById('results-section');
    if (!el) return;
    const offset = 80; // account for sticky nav
    const top = el.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top, behavior: 'smooth' });
  }

  // ─── Number counter animation ──────────────────────────────────────────────
  /**
   * Animates a number from 0 to target, updating element's textContent.
   * @param {HTMLElement} el
   * @param {number} target
   * @param {number} duration ms
   * @param {string} suffix  e.g. '%' or ' mg/L'
   * @param {number} decimals
   */
  function animateCounter(el, target, duration = 600, suffix = '', decimals = 0) {
    if (!el) return;
    const start = performance.now();
    function update(ts) {
      const elapsed = ts - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;
      el.textContent = current.toFixed(decimals) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  // ─── setText helper (shared with performance.html inline scripts) ──────────
  /**
   * Sets the textContent of an element by ID. Null-safe.
   * @param {string} id
   * @param {string|number} text
   */
  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  // ─── Public API ────────────────────────────────────────────────────────────
  // These functions are used by predict.js and page-level scripts.
  window.animateGauge       = animateGauge;
  window.animateProgressBar = animateProgressBar;
  window.animateCounter     = animateCounter;
  window.scrollToResults    = scrollToResults;
  window.setText            = setText;

})();
