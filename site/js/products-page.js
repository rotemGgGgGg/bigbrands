/* Filtered listing page: products.html?brand=HP  or  ?category=ניידים */

(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const ils = (n) => "₪ " + Number(n).toLocaleString("he-IL");
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const BRAND_SLUG = { HP: "hp", Dell: "dell", Apple: "apple", Lenovo: "lenovo", ASUS: "asus", Sony: "sony" };
  function brandColor(b) {
    return ({ HP: "#0096d6", Dell: "#007db8", Apple: "#1d1d1f", Lenovo: "#e2231a", ASUS: "#00539b", Sony: "#111418" })[b] || "#1f7ae0";
  }
  function deviceSVG(accent, category) {
    accent = accent || "#1f7ae0";
    const gid = "scr-" + Math.random().toString(36).slice(2, 8);
    const grad = `<defs><linearGradient id="${gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${accent}"/><stop offset="1" stop-color="#0a1f44"/></linearGradient></defs>`;
    if (/אוזני|headphone|אודיו|audio/i.test(category || "")) {
      return `<svg class="device" viewBox="0 0 240 170" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="אוזניות">${grad}
        <path d="M54 106V92a66 66 0 0 1 132 0v14" fill="none" stroke="url(#${gid})" stroke-width="13" stroke-linecap="round"/>
        <rect x="38" y="100" width="36" height="56" rx="15" fill="#1b2330"/>
        <rect x="45" y="107" width="22" height="42" rx="11" fill="url(#${gid})"/>
        <rect x="166" y="100" width="36" height="56" rx="15" fill="#1b2330"/>
        <rect x="173" y="107" width="22" height="42" rx="11" fill="url(#${gid})"/></svg>`;
    }
    return `<svg class="device" viewBox="0 0 240 160" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="מחשב נייד">${grad}
      <rect x="50" y="18" width="140" height="90" rx="9" fill="#1b2330"/>
      <rect x="57" y="25" width="126" height="76" rx="5" fill="url(#${gid})"/>
      <rect x="66" y="38" width="48" height="7" rx="3.5" fill="rgba(255,255,255,.9)"/>
      <rect x="66" y="52" width="78" height="6" rx="3" fill="rgba(255,255,255,.55)"/>
      <rect x="66" y="64" width="60" height="6" rx="3" fill="rgba(255,255,255,.38)"/>
      <path d="M32 108h176l12 20a5 5 0 0 1-5 7H25a5 5 0 0 1-5-7z" fill="#cfd6e2"/>
      <rect x="98" y="114" width="44" height="6" rx="3" fill="#9aa6bd"/></svg>`;
  }
  window.__productFallback = function (img) {
    const span = document.createElement("span");
    span.innerHTML = deviceSVG(img.getAttribute("data-accent") || "#1f7ae0", img.getAttribute("data-cat") || "");
    img.replaceWith(span.firstElementChild);
  };
  function media(p) {
    if (p.image)
      return `<img class="device" src="${esc(p.image)}" alt="${esc(p.name)}" loading="lazy" data-accent="${brandColor(p.brand)}" data-cat="${esc(p.category || "")}" style="object-fit:contain" onerror="window.__productFallback(this)"/>`;
    return deviceSVG(brandColor(p.brand), p.category);
  }

  function params() {
    const u = new URLSearchParams(location.search);
    return { brand: u.get("brand"), category: u.get("category") };
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
    const { brand, category } = params();
    let list = Store.getProducts();
    let title = "כל המוצרים";

    if (brand) { list = list.filter((p) => p.brand === brand); title = "מוצרי " + brand; }
    else if (category) { list = list.filter((p) => p.category === category); title = category; }

    $("#pageTitle").textContent = title;
    document.title = title + " — BIG BRANDS";
    $("#pageCount").textContent = list.length + " מוצרים";

    if (!list.length) { $("#grid").innerHTML = ""; $("#empty").hidden = false; return; }
    $("#empty").hidden = true;

    $("#grid").innerHTML = list.map((p) => `
      <article class="p-card" data-id="${p.id}">
        ${p.badge ? `<span class="badge">${esc(p.badge)}</span>` : ""}
        ${media(p)}
        <div class="pname">${esc(p.name)}</div>
        <div class="pspecs">${esc(p.specs || "")}</div>
        <div class="prow">
          <span class="pprice">${ils(p.price)}</span>
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
    }
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
