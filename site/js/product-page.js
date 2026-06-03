/* Product detail page: product.html?id=l1 */

(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const ils = (n) => "₪ " + Number(n).toLocaleString("he-IL");
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const WA_PHONE = "972000000000"; // TODO: real WhatsApp number

  function brandColor(b) {
    return ({ HP: "#0096d6", Dell: "#007db8", Apple: "#1d1d1f", Lenovo: "#e2231a", ASUS: "#00539b", Sony: "#111418" })[b] || "#1f7ae0";
  }
  function deviceSVG(accent, category) { return window.deviceGraphic(accent, category); }
  window.__productFallback = function (img) {
    const span = document.createElement("span");
    span.innerHTML = deviceSVG(img.getAttribute("data-accent") || "#1f7ae0", img.getAttribute("data-cat") || "");
    img.replaceWith(span.firstElementChild);
  };
  function media(p, big) {
    if (p.image)
      return `<img class="device${big ? " big" : ""}" src="${esc(p.image)}" alt="${esc(p.name)}" ${big ? "" : 'loading="lazy"'} data-accent="${brandColor(p.brand)}" data-cat="${esc(p.category || "")}" style="object-fit:contain" onerror="window.__productFallback(this)"/>`;
    return deviceSVG(brandColor(p.brand), p.category);
  }
  function availability(p) {
    if (p.status === "stock") return `<span class="pstock in">● ${esc(p.stock || "במלאי")}</span>`;
    if (p.status === "limited") return `<span class="pstock low">● מלאי מוגבל</span>`;
    if (p.status === "new") return `<span class="pstock in">● חדש במלאי</span>`;
    return `<span class="pstock req">● בהזמנה</span>`;
  }

  function getId() { return new URLSearchParams(location.search).get("id"); }

  function renderNotFound() {
    document.title = "מוצר לא נמצא — BIG BRANDS";
    $("#pdp").innerHTML = `
      <div class="pdp-missing reveal in">
        <h1>המוצר לא נמצא</h1>
        <p>ייתכן שהקישור שגוי או שהמוצר הוסר מהקטלוג.</p>
        <a class="btn-cta" href="products.html">חזרה לכל המוצרים</a>
      </div>`;
  }

  function specRows(p) {
    const parts = String(p.specs || "").split(/\s*\|\s*/).map((s) => s.trim()).filter(Boolean);
    if (!parts.length) return "";
    const check = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 5 5 9-11"/></svg>`;
    return `<ul class="pdp-specs">${parts.map((s) => `<li>${check}<span>${esc(s)}</span></li>`).join("")}</ul>`;
  }

  function relatedCards(p) {
    const rel = Store.getProducts().filter((x) => x.category === p.category && x.id !== p.id).slice(0, 4);
    if (!rel.length) return "";
    return `
      <section class="pdp-related">
        <div class="section-bar reveal">מוצרים נוספים בקטגוריה <span>${esc(p.category)}</span></div>
        <div class="product-grid reveal" data-stagger>
          ${rel.map((r) => `
            <article class="p-card" data-id="${r.id}">
              ${r.badge ? `<span class="badge">${esc(r.badge)}</span>` : ""}
              ${media(r)}
              <a class="pname" href="product.html?id=${encodeURIComponent(r.id)}">${esc(r.name)}</a>
              <div class="pspecs">${esc((r.specs || "").split(/\s*\|\s*/).slice(0, 3).join(" · "))}</div>
              ${availability(r)}
              <div class="prow">
                <span class="pprice">${ils(r.price)}</span>
                <button class="add" data-id="${r.id}" aria-label="הוסף לעגלה" title="הוסף לעגלה">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
                </button>
              </div>
            </article>`).join("")}
        </div>
      </section>`;
  }

  function render(p) {
    document.title = p.name + " — BIG BRANDS";
    const meta = [p.brand, p.mpn].filter(Boolean).join(" · ");
    const waMsg = `היי, אני מעוניין/ת בפרטים והזמנה עבור:\n${p.brand} ${p.name}${p.mpn ? " (" + p.mpn + ")" : ""}\nמחיר מוצג: ${ils(p.price)}`;
    const waLink = `https://wa.me/${WA_PHONE}?text=${encodeURIComponent(waMsg)}`;

    $("#pdp").innerHTML = `
      <nav class="crumbs reveal in" aria-label="מסלול ניווט">
        <a href="index.html">דף הבית</a><span>/</span>
        <a href="products.html?category=${encodeURIComponent(p.category)}">${esc(p.category)}</a><span>/</span>
        <span class="cur">${esc(p.name)}</span>
      </nav>

      <div class="pdp-grid">
        <div class="pdp-media reveal in">${media(p, true)}</div>

        <div class="pdp-info reveal in">
          <div class="pdp-meta">${esc(meta)}</div>
          <h1 class="pdp-name">${esc(p.name)}</h1>
          <div class="pdp-availrow">${availability(p)}<a class="pdp-brandlink" href="products.html?brand=${encodeURIComponent(p.brand)}">עוד ממותג ${esc(p.brand)}</a></div>

          ${p.bundle ? `<div class="pbundle pdp-bundle">📦 ${esc(p.bundle)}</div>` : ""}

          <div class="pdp-pricebox">
            <span class="pdp-price">${ils(p.price)}</span>
            <span class="pdp-vat">המחיר אינו כולל מע"מ</span>
          </div>

          <div class="pdp-cta">
            <button class="btn-cta primary" id="pdpAdd">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="20" r="1.6"/><circle cx="18" cy="20" r="1.6"/><path d="M2 3h3l2.4 12.2a1.5 1.5 0 0 0 1.5 1.2h8.5a1.5 1.5 0 0 0 1.5-1.2L22 7H6"/></svg>
              הוספה להצעת מחיר
            </button>
            <a class="btn-cta wa" href="${waLink}" target="_blank" rel="noopener">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.5 15.2L2 22l4.9-1.5A10 10 0 1 0 12 2Zm5.3 14.2c-.2.6-1.2 1.1-1.7 1.2-.5.1-1 .1-1.7-.1-.4-.1-.9-.3-1.6-.6-2.8-1.2-4.6-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.8s.7-2 .9-2.2c.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.5l.8 1.9c.1.2.1.4 0 .5l-.4.5c-.1.2-.3.3-.1.6.1.3.6 1 1.3 1.6.9.8 1.6 1 1.9 1.2.2.1.4.1.5-.1l.6-.7c.2-.2.3-.2.6-.1l1.8.9c.3.1.4.2.5.3.1.2.1.7-.1 1.3Z"/></svg>
              לבירור והזמנה
            </a>
          </div>

          <div class="pdp-section-title">מפרט טכני</div>
          ${specRows(p)}

          <ul class="pdp-trust">
            <li>אחריות יבואן רשמי</li>
            <li>משלוח לכל הארץ</li>
            <li>תמיכה ושירות אנושי</li>
          </ul>
        </div>
      </div>

      ${relatedCards(p)}
    `;

    $("#pdpAdd").addEventListener("click", () => addToCart());
    initTilt();
    initReveal();
  }

  let cart = 0;
  function addToCart() {
    cart++;
    const el = $("#cartCount");
    el.textContent = cart;
    el.animate([{ transform: "scale(1)" }, { transform: "scale(1.5)" }, { transform: "scale(1)" }], { duration: 300 });
  }

  /* card clicks within related grid: navigate, but + button adds to cart */
  document.addEventListener("click", (e) => {
    if (e.target.closest(".add")) { e.preventDefault(); addToCart(); return; }
    const card = e.target.closest(".p-card");
    if (card && card.dataset.id) location.href = "product.html?id=" + encodeURIComponent(card.dataset.id);
  });

  function initTilt() {
    document.querySelectorAll(".pdp-media, .p-card").forEach((card) => {
      const m = card.querySelector(".device");
      if (!m) return;
      card.addEventListener("mousemove", (e) => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        m.style.transform = `rotateY(${x * 8}deg) rotateX(${-y * 8}deg) scale(1.04)`;
      });
      card.addEventListener("mouseleave", () => { m.style.transform = ""; });
    });
  }

  function renderNav() {
    $("#navList").innerHTML = Store.categories().slice(1)
      .map((c) => `<li><a href="products.html?category=${encodeURIComponent(c)}">${esc(c)}</a></li>`).join("");
    $("#catMenu").innerHTML = Store.categories()
      .map((c, i) => `<li role="option" data-val="${esc(c)}"${i === 0 ? ' class="active"' : ""}>${esc(c)}</li>`).join("");
  }
  function initDropdown() {
    const dd = $("#catDropdown"), toggle = $("#catToggle"), menu = $("#catMenu");
    toggle.addEventListener("click", (e) => { e.stopPropagation(); dd.classList.toggle("open"); });
    menu.addEventListener("click", (e) => {
      const li = e.target.closest("li"); if (!li) return;
      const val = li.dataset.val;
      location.href = (val === "כל המוצרים") ? "products.html" : "products.html?category=" + encodeURIComponent(val);
    });
    document.addEventListener("click", (e) => { if (!dd.contains(e.target)) dd.classList.remove("open"); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") dd.classList.remove("open"); });
  }
  function initReveal() {
    const io = new IntersectionObserver((es) => es.forEach((en) => {
      if (!en.isIntersecting) return;
      const el = en.target; el.classList.add("in");
      if (el.hasAttribute("data-stagger")) {
        const kids = el.children;
        for (let i = 0; i < kids.length; i++) kids[i].style.transitionDelay = i * 50 + "ms";
      }
      io.unobserve(el);
    }), { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    document.querySelectorAll(".reveal:not(.in)").forEach((el) => io.observe(el));
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
    initTheme();
    initHeader();
    $("#year").textContent = new Date().getFullYear();
    const p = Store.getProduct(getId());
    if (p) render(p); else renderNotFound();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
