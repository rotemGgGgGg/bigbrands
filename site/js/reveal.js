/* ============================================================
   BIG BRANDS — scroll reveal
   ------------------------------------------------------------
   • Headings write themselves in word-by-word as they scroll into view.
   • Body paragraphs / list items fade up on scroll.
   • Respects prefers-reduced-motion (shows everything, no animation).
   • Idempotent scan() — safe to call again after JS renders content.
   • Zero dependencies. Loaded site-wide.
   ============================================================ */
(function () {
  "use strict";

  const REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const SUPPORTED = "IntersectionObserver" in window;
  if (REDUCED || !SUPPORTED) return; // leave all text fully visible

  /* headings that get the word-by-word treatment */
  const WORD_SEL = [
    ".intro-title", ".pdp-name", ".section-bar",
    ".legal-page h1", ".legal-page h2",
    ".section > h2", ".section-title", "h1.page-title",
  ].join(",");

  /* body text that gets a simple fade-up */
  const UP_SEL = [
    ".legal-page p", ".legal-page li", ".legal-page h3",
    ".pdp-desc", ".lead",
  ].join(",");

  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) { e.target.classList.add("rv-in"); io.unobserve(e.target); }
    }
  }, { threshold: 0.15, rootMargin: "0px 0px -6% 0px" });

  /* Split an element's text into per-word spans, preserving nested inline
     elements (e.g. the <span> inside .section-bar) as single units. */
  function splitWords(el) {
    if (el.dataset.rvDone) return;
    if (!el.textContent.trim()) return;
    const frag = document.createDocumentFragment();
    let i = 0;
    [...el.childNodes].forEach((node) => {
      if (node.nodeType === 3) {
        node.textContent.split(/(\s+)/).forEach((part) => {
          if (!part) return;
          if (!part.trim()) { frag.appendChild(document.createTextNode(part)); return; }
          const w = document.createElement("span");
          w.className = "rv-w"; w.textContent = part;
          w.style.setProperty("--rw", i++);
          frag.appendChild(w);
        });
      } else if (node.nodeType === 1) {
        node.classList.add("rv-w");
        node.style.setProperty("--rw", i++);
        frag.appendChild(node);
      } else {
        frag.appendChild(node);
      }
    });
    el.textContent = "";
    el.appendChild(frag);
    el.dataset.rvDone = "1";
    el.classList.add("rv-split");
    io.observe(el);
  }

  function markUp(el) {
    if (el.dataset.rvDone) return;
    if (el.closest(".rv-split")) return;
    el.dataset.rvDone = "1";
    el.classList.add("rv-up");
    io.observe(el);
  }

  function scan() {
    document.querySelectorAll(WORD_SEL).forEach((el) => {
      if (el.closest(".rv-up") || el.dataset.rvDone) return;
      splitWords(el);
    });
    document.querySelectorAll(UP_SEL).forEach(markUp);
  }

  window.BBReveal = { scan };

  const boot = () => { scan(); setTimeout(scan, 400); setTimeout(scan, 1200); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
