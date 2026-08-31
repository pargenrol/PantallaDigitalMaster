/**
 * Modo presbicia: agranda el texto pequeño (etiquetas, botones, listas...)
 * en /master y en las vistas de tablet, sin tocar padding ni layout.
 * Recordado por navegador (localStorage), no por usuario/sesión.
 *
 * La app fija casi todos los tamaños de letra en px, muchos como estilo
 * inline, sin ninguna variable CSS central que escalar — así que en vez de
 * sobreescribir reglas por selector (habría que enumerar cientos, una por
 * una, tanto en master.css/tablet.css como en cada plantilla), se recorre
 * el DOM y se reescribe el font-size YA RESUELTO de cada elemento (el que
 * gane la cascada, venga de un fichero CSS o de un style inline) — funciona
 * igual en cualquier página sin tocar plantilla por plantilla.
 */
(function () {
  "use strict";
  const STORAGE_KEY = "pdm-presbicia";
  const SCALE = 1.35;
  const MIN_PX = 7;  // no tocar texto ya grande (títulos, números destacados)
  const MAX_PX = 19;

  function scaleElement(el) {
    if (el.dataset.presbiciaBase) return; // ya procesado
    const current = parseFloat(window.getComputedStyle(el).fontSize);
    if (!current || current < MIN_PX || current > MAX_PX) return;
    el.dataset.presbiciaBase = "1";
    el.style.setProperty("font-size", (current * SCALE).toFixed(1) + "px", "important");
  }

  function scaleTree(root) {
    if (!root || root.nodeType !== 1) return;
    scaleElement(root);
    root.querySelectorAll("*").forEach(scaleElement);
  }

  function unscaleAll() {
    document.querySelectorAll("[data-presbicia-base]").forEach((el) => {
      el.style.removeProperty("font-size");
      delete el.dataset.presbiciaBase;
    });
  }

  let observer = null;
  function startObserving() {
    if (observer) return;
    observer = new MutationObserver((mutations) => {
      mutations.forEach((m) => m.addedNodes.forEach(scaleTree));
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }
  function stopObserving() {
    if (observer) { observer.disconnect(); observer = null; }
  }

  function setToggleVisual(btn, on) {
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.classList.toggle("active", on);
    if (btn.dataset.presbiciaFloating) {
      btn.style.background = on ? "rgba(200,144,42,.85)" : "rgba(0,0,0,.55)";
    }
  }

  function apply(on) {
    document.body.classList.toggle("presbicia-on", on);
    if (on) { scaleTree(document.body); startObserving(); }
    else { stopObserving(); unscaleAll(); }
    document.querySelectorAll("[data-presbicia-toggle]").forEach((btn) => setToggleVisual(btn, on));
  }

  function toggle() {
    const on = !document.body.classList.contains("presbicia-on");
    localStorage.setItem(STORAGE_KEY, on ? "1" : "0");
    apply(on);
  }

  function injectFloatingToggleIfNeeded() {
    if (document.querySelector("[data-presbicia-toggle]")) return; // la página ya trae su propio botón
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.presbiciaToggle = "1";
    btn.dataset.presbiciaFloating = "1";
    btn.title = "Modo presbicia (texto más grande)";
    btn.setAttribute("aria-label", "Modo presbicia");
    btn.setAttribute("aria-pressed", "false");
    btn.textContent = "🔍";
    btn.style.cssText = "position:fixed;bottom:10px;left:10px;z-index:9999;width:36px;height:36px;" +
      "border-radius:50%;border:1px solid rgba(255,255,255,.35);background:rgba(0,0,0,.55);" +
      "color:#fff;font-size:16px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center;";
    document.body.appendChild(btn);
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-presbicia-toggle]");
    if (btn) toggle();
  });

  document.addEventListener("DOMContentLoaded", () => {
    injectFloatingToggleIfNeeded();
    const stored = localStorage.getItem(STORAGE_KEY) === "1";
    if (stored) apply(true);
  });
})();
