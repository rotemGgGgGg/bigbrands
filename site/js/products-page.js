/* Filtered listing page: products.html?brand=HP  or  ?category=ניידים */

(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const ils = (n) => Number(n).toLocaleString("he-IL") + " ₪";
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const BRAND_SLUG = { HP: "hp", Dell: "dell", Apple: "apple", Lenovo: "lenovo", ASUS: "asus", Sony: "sony" };
  function brandColor(b) {
    return ({ HP: "#0096d6", Dell: "#007db8", Apple: "#1d1d1f", Lenovo: "#e2231a", ASUS: "#00539b", Sony: "#111418" })[b] || "#1f7ae0";
  }
  function deviceSVG(accent, category) { return window.deviceGraphic(accent, category); }
  function availability(p) {
    if (p.status === "stock") return `<span class="pstock in">● ${esc(p.stock || "במלאי")}</span>`;
    if (p.status === "limited") return `<span class="pstock low">● מלאי מוגבל</span>`;
    if (p.status === "new") return `<span class="pstock in">● חדש במלאי</span>`;
    return `<span class="pstock req">● בהזמנה</span>`;
  }
  window.__productFallback = function (img) {
    const span = document.createElement("span");
    span.innerHTML = deviceSVG(img.getAttribute("data-accent") || "#1f7ae0", img.getAttribute("data-cat") || "");
    img.replaceWith(span.firstElementChild);
  };
  function media(p) {
    if (p.image)
      return `<img class="device" decoding="async" src="${esc(p.image)}" alt="${esc(p.name)}" loading="lazy" data-accent="${brandColor(p.brand)}" data-cat="${esc(p.category || "")}" style="object-fit:contain" onerror="window.__productFallback(this)"/>`;
    return deviceSVG(brandColor(p.brand), p.category);
  }

  function params() {
    const u = new URLSearchParams(location.search);
    return { brand: u.get("brand"), category: u.get("category"), series: u.get("series") };
  }

  const SERIES_LABELS = {
    X: "ThinkPad X · אולטרה-קלים",
    T: "ThinkPad T · עסקיים",
    L: "ThinkPad L · חסכוניים",
    P: "ThinkPad P · תחנות עבודה",
    ThinkCentre: "ThinkCentre · נייחים",
  };
  function renderSeriesFilter(brand, list, activeSeries) {
    const el = $("#seriesFilter");
    if (!el) return;
    if (brand !== "Lenovo") { el.hidden = true; el.innerHTML = ""; return; }
    const seriesFound = [...new Set(list.map((p) => p.series).filter(Boolean))];
    if (!seriesFound.length) { el.hidden = true; return; }
    el.hidden = false;
    const chip = (val, label, active) =>
      `<a class="series-chip${active ? " active" : ""}" href="products.html?brand=Lenovo${val ? "&series=" + encodeURIComponent(val) : ""}">${esc(label)}</a>`;
    el.innerHTML =
      chip("", "כל הסדרות", !activeSeries) +
      seriesFound.map((s) => chip(s, SERIES_LABELS[s] || s, activeSeries === s)).join("");
  }

  function renderNav() {
    $("#navList").innerHTML = Store.categories().slice(1)
      .map((c) => `<li><a href="products.html?category=${encodeURIComponent(c)}">${esc(c)}</a></li>`).join("");
    $("#catMenu").innerHTML = Store.categories()
      .map((c, i) => `<li role="option" data-val="${esc(c)}"${i === 0 ? ' class="active"' : ""}>${esc(c)}</li>`).join("");
  }

  function initDropdown() {
    const dd = $("#catDropdown"), toggle = $("#catToggle"), menu = $("#catMenu"), label = $("#catLabel");
    const close = () => { dd.classList.remove("open"); toggle.setAttribute("aria-expanded", "false"); };
    toggle.addEventListener("click", (e) => { e.stopPropagation(); dd.classList.toggle("open"); });
    menu.addEventListener("click", (e) => {
      const li = e.target.closest("li"); if (!li) return;
      const val = li.dataset.val;
      if (val === "כל המוצרים" || val === "הכל") location.href = "products.html";
      else location.href = "products.html?category=" + encodeURIComponent(val);
    });
    document.addEventListener("click", (e) => { if (!dd.contains(e.target)) close(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
    label.textContent = "הכל";
  }

  function render() {
    const { brand, category, series } = params();
    let list = Store.getProducts();
    let title = "כל המוצרים";

    if (brand) { list = list.filter((p) => p.brand === brand); title = "מוצרי " + brand; }
    else if (category) { list = list.filter((p) => p.category === category); title = category; }

    // Lenovo sub-filter by series
    const brandList = list.slice();
    renderSeriesFilter(brand, brandList, series);
    if (brand === "Lenovo" && series) {
      list = list.filter((p) => p.series === series);
      title += " · " + (SERIES_LABELS[series] || series).split(" · ")[0];
    }

    $("#pageTitle").textContent = title;
    document.title = title + " — BIG BRANDS";
    $("#pageCount").textContent = list.length + " מוצרים";

    if (!list.length) { $("#grid").innerHTML = ""; $("#empty").hidden = false; return; }
    $("#empty").hidden = true;

    $("#grid").innerHTML = list.map((p) => `
      <article class="p-card" data-id="${p.id}">
        ${p.badge ? `<span class="badge">${esc(p.badge)}</span>` : ""}
        ${media(p)}
        <a class="pname" href="product.html?id=${encodeURIComponent(p.id)}">${esc(p.name)}</a>
        <div class="pspecs">${esc(p.specs || "")}</div>
        ${p.bundle ? `<div class="pbundle">📦 ${esc(p.bundle)}</div>` : ""}
        ${availability(p)}
        <div class="prow">
          <span class="pprice">${p.price ? ils(p.price) : "לבירור מחיר"}${p.wasPrice ? ` <s class="pwas">${ils(p.wasPrice)}</s>` : ""}</span>
          <button class="add" aria-label="הוסף לעגלה" title="הוסף לעגלה">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
          </button>
        </div>
      </article>`).join("");

    initTilt();
  }

  function initTilt() {
    document.querySelectorAll(".p-card").forEach((card) => {
      const m = card.querySelector(".device");
      if (!m) return;
      card.addEventListener("mousemove", (e) => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        m.style.transform = `rotateY(${x * 12}deg) rotateX(${-y * 12}deg) scale(1.06)`;
      });
      card.addEventListener("mouseleave", () => { m.style.transform = ""; });
    });
  }

  let cart = 0;
  document.addEventListener("click", (e) => {
    if (e.target.closest(".add")) {
      e.preventDefault(); cart++;
      const el = $("#cartCount"); el.textContent = cart;
      el.animate([{ transform: "scale(1)" }, { transform: "scale(1.5)" }, { transform: "scale(1)" }], { duration: 300 });
      return;
    }
    const card = e.target.closest(".p-card");
    if (card && card.dataset.id) location.href = "product.html?id=" + encodeURIComponent(card.dataset.id);
  });

  function initReveal() {
    const io = new IntersectionObserver((es) => es.forEach((en) => {
      if (!en.isIntersecting) return;
      const el = en.target;
      el.classList.add("in");
      if (el.hasAttribute("data-stagger")) {
        const kids = el.children;
        for (let i = 0; i < kids.length; i++) kids[i].style.transitionDelay = i * 50 + "ms";
      }
      io.unobserve(el);
    }), { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
  }

  function initTheme() {
    const KEY = "bigbrands.theme";
    const saved = localStorage.getItem(KEY);
    if (saved) document.documentElement.dataset.theme = saved;
    $("#themeToggle").onclick = () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem(KEY, next);
    };
  }
  function initHeader() {
    const h = $("#header");
    const onScroll = () => h.classList.toggle("scrolled", window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  function boot() {
    renderNav();
    initDropdown();
    render();
    initReveal();
    initTheme();
    initHeader();
    $("#year").textContent = new Date().getFullYear();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
