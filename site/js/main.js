/* ============================================================
   BIG BRANDS — storefront behavior
   ============================================================ */

(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const ils = (n) => "₪ " + Number(n).toLocaleString("he-IL");

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  /* ---------- brand helpers ---------- */
  const BRAND_SLUG = { HP: "hp", Dell: "dell", Apple: "apple", Lenovo: "lenovo", ASUS: "asus", Sony: "sony" };
  const BRAND_EXT  = { ASUS: "svg" }; // per-brand logo file extension (default: png)
  function brandColor(brand) {
    return ({
      HP: "#0096d6", Dell: "#007db8", Apple: "#1d1d1f",
      Lenovo: "#e2231a", ASUS: "#00539b", Sony: "#111418",
    })[brand] || "#1f7ae0";
  }

  // Clean fallback wordmark (used only if a real logo file is missing).
  function brandFallbackSVG(name) {
    const c = brandColor(name);
    return `<svg viewBox="0 0 160 60" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${escapeHtml(name)}" style="height:56px;max-width:140px">
      <text x="80" y="40" text-anchor="middle" font-family="Arial, Heebo, sans-serif" font-weight="800" font-size="30" letter-spacing="1" fill="${c}">${escapeHtml(name)}</text>
    </svg>`;
  }
  // Real logo image with graceful fallback to the wordmark.
  window.__brandFallback = function (img) {
    const name = img.getAttribute("data-brand");
    const span = document.createElement("span");
    span.innerHTML = brandFallbackSVG(name);
    img.replaceWith(span.firstElementChild);
  };
  function brandLogoImg(name) {
    const slug = BRAND_SLUG[name] || name.toLowerCase();
    const ext = BRAND_EXT[name] || "png";
    return `<img src="assets/brands/${slug}.${ext}" alt="${escapeHtml(name)}" data-brand="${escapeHtml(name)}" onerror="window.__brandFallback(this)" />`;
  }

  /* ---------- clean category-aware product graphic (shared engine) ---------- */
  function deviceSVG(accent, category) { return window.deviceGraphic(accent, category); }
  window.__productFallback = function (img) {
    const span = document.createElement("span");
    span.innerHTML = deviceSVG(img.getAttribute("data-accent") || "#1f7ae0", img.getAttribute("data-cat") || "");
    img.replaceWith(span.firstElementChild);
  };
  function productMedia(p) {
    if (p.image) {
      return `<img class="device" decoding="async" src="${escapeHtml(p.image)}" alt="${escapeHtml(p.name)}" loading="lazy"
        data-accent="${brandColor(p.brand)}" data-cat="${escapeHtml(p.category || "")}" style="object-fit:contain" onerror="window.__productFallback(this)"/>`;
    }
    return deviceSVG(brandColor(p.brand), p.category);
  }

  /* ---------- nav + category dropdown ---------- */
  function renderNav() {
    const cats = Store.categories();
    $("#navList").innerHTML = cats
      .slice(1)
      .map((c) => `<li><a href="products.html?category=${encodeURIComponent(c)}">${escapeHtml(c)}</a></li>`)
      .join("");

    const menu = $("#catMenu");
    menu.innerHTML = cats
      .map((c, i) => `<li role="option" data-val="${escapeHtml(c)}"${i === 0 ? ' class="active"' : ""}>${escapeHtml(c)}</li>`)
      .join("");
  }

  function initDropdown() {
    const dd = $("#catDropdown");
    const toggle = $("#catToggle");
    const menu = $("#catMenu");
    const label = $("#catLabel");

    const close = () => { dd.classList.remove("open"); toggle.setAttribute("aria-expanded", "false"); };
    const open = () => { dd.classList.add("open"); toggle.setAttribute("aria-expanded", "true"); };

    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      dd.classList.contains("open") ? close() : open();
    });
    menu.addEventListener("click", (e) => {
      const li = e.target.closest("li");
      if (!li) return;
      label.textContent = li.dataset.val;
      menu.querySelectorAll("li").forEach((x) => x.classList.toggle("active", x === li));
      close();
    });
    document.addEventListener("click", (e) => { if (!dd.contains(e.target)) close(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  }

  /* ---------- hero carousel ---------- */
  let slideIndex = 0, slideTimer = null, slideEls = [];

  function slideHTML(s) {
    if (s.image) {
      const fb = s.fallbackImage
        ? ` onerror="this.onerror=null;this.src='${escapeHtml(s.fallbackImage)}'"`
        : "";
      const img = `<img class="banner-img" src="${escapeHtml(s.image)}" alt="${escapeHtml(s.alt || "")}"${fb}/>`;
      return `<a class="slide banner" href="${escapeHtml(s.link || "#")}">${img}</a>`;
    }
    return `
      <div class="slide" style="--slide-accent:${s.accent || "#1f7ae0"}">
        <div class="glow" style="--slide-accent:${s.accent || "#1f7ae0"}"></div>
        <div class="copy">
          <span class="eyebrow">${escapeHtml(s.eyebrow || "")}</span>
          <h2>${escapeHtml(s.title || "")}</h2>
          <p>${escapeHtml(s.subtitle || "")}</p>
          <a class="cta" href="${escapeHtml(s.link || "#")}">${escapeHtml(s.cta || "")}
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="m15 6-6 6 6 6"/></svg>
          </a>
        </div>
        <div class="visual">${deviceSVG(s.accent)}</div>
      </div>`;
  }

  function renderHero() {
    const slides = Store.heroSlides();
    $("#slides").innerHTML = slides.map(slideHTML).join("");
    $("#heroDots").innerHTML = slides
      .map((_, i) => `<button data-i="${i}" aria-label="שקופית ${i + 1}"></button>`)
      .join("");

    slideEls = Array.from($("#slides").children);
    showSlide(0);
    startAuto();

    $("#heroNext").onclick = () => { go(1); restartAuto(); };
    $("#heroPrev").onclick = () => { go(-1); restartAuto(); };
    $("#heroDots").querySelectorAll("button").forEach((b) =>
      (b.onclick = () => { showSlide(Number(b.dataset.i)); restartAuto(); }));

    const car = $("#carousel");
    car.addEventListener("mouseenter", stopAuto);
    car.addEventListener("mouseleave", startAuto);
  }
  function showSlide(i) {
    if (!slideEls.length) return;
    slideIndex = (i + slideEls.length) % slideEls.length;
    slideEls.forEach((el, idx) => el.classList.toggle("active", idx === slideIndex));
    document.querySelectorAll("#heroDots button")
      .forEach((d, idx) => d.classList.toggle("active", idx === slideIndex));
  }
  const go = (dir) => showSlide(slideIndex + dir);
  const startAuto = () => { stopAuto(); slideTimer = setInterval(() => go(1), 5500); };
  const stopAuto = () => slideTimer && clearInterval(slideTimer);
  const restartAuto = () => { stopAuto(); startAuto(); };

  /* ---------- featured 3 ---------- */
  function renderFeatured() {
    $("#featuredGrid").innerHTML = Store.featured()
      .map((f) => {
        const p = Store.getProduct(f.productId) || Store.getProducts()[0];
        if (!p) return "";
        return `
        <a class="feat-card" href="product.html?id=${encodeURIComponent(p.id)}" data-id="${p.id}">
          <div class="tag">${escapeHtml(f.tag)}</div>
          <div class="media">${productMedia(p)}</div>
          <div class="pname">${escapeHtml(p.name)}</div>
          <div class="pprice">${p.price ? ils(p.price) : "לבירור מחיר"}${p.wasPrice ? ` <s class="pwas">${ils(p.wasPrice)}</s>` : ""}</div>
        </a>`;
      })
      .join("");
  }

  /* ---------- brand tiles (pressable) ---------- */
  function renderBrandTiles() {
    $("#brandTiles").innerHTML = Store.brands()
      .map(
        (b) => `
      <a class="brand-tile" href="products.html?brand=${encodeURIComponent(b)}" style="--tile-accent:${brandColor(b)}" aria-label="מוצרי ${escapeHtml(b)}">
        <div class="blogo">${brandLogoImg(b)}</div>
        <span class="go-pill">לכל מוצרי ${escapeHtml(b)}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="m15 6-6 6 6 6"/></svg>
        </span>
      </a>`
      )
      .join("");
  }

  /* ---------- partners ---------- */
  function partnerLogoSVG(kind, name) {
    const map = {
      Pizza: { c: "#e3000f", t: "Pizza" }, Wine: { c: "#7a4b2b", t: "דרך היין" },
      Community: { c: "#2aa0d6", t: "מתנ\"סים" }, Post: { c: "#e3000f", t: "ePost" },
    };
    const m = map[kind] || { c: "#0a1f44", t: name };
    return `<svg viewBox="0 0 160 56" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${escapeHtml(name)}" style="height:56px">
      <rect x="6" y="10" width="148" height="36" rx="10" fill="${m.c}" opacity="0.10"/>
      <text x="80" y="35" text-anchor="middle" font-family="Heebo, Arial" font-weight="800" font-size="20" fill="${m.c}">${escapeHtml(m.t)}</text>
    </svg>`;
  }
  window.__partnerFallback = function (img) {
    const span = document.createElement("span");
    span.innerHTML = partnerLogoSVG(img.getAttribute("data-kind"), img.getAttribute("data-name") || "");
    img.replaceWith(span.firstElementChild);
  };
  function partnerLogo(p) {
    if (p.image)
      return `<img class="plogo-img" src="${escapeHtml(p.image)}" alt="${escapeHtml(p.name)}" loading="lazy" data-kind="${escapeHtml(p.logo || "")}" data-name="${escapeHtml(p.name)}" onerror="window.__partnerFallback(this)" />`;
    return partnerLogoSVG(p.logo, p.name);
  }
  function renderPartners() {
    $("#partnersGrid").innerHTML = Store.partners()
      .map(
        (p) => `
      <article class="partner">
        <div class="plogo">${partnerLogo(p)}</div>
        <p class="quote">${escapeHtml(p.quote)}</p>
        <div class="person">${escapeHtml(p.person)}</div>
      </article>`
      )
      .join("");
  }

  /* ---------- cart ---------- */
  let cart = 0;
  document.addEventListener("click", (e) => {
    if (e.target.closest(".add")) {
      e.preventDefault();
      cart++;
      const el = $("#cartCount");
      el.textContent = cart;
      el.animate([{ transform: "scale(1)" }, { transform: "scale(1.5)" }, { transform: "scale(1)" }],
        { duration: 300, easing: "ease" });
    }
  });

  /* ---------- tilt hover (makes media feel touchable) ---------- */
  function initTilt() {
    const sel = ".feat-card, .p-card";
    document.querySelectorAll(sel).forEach((card) => {
      const media = card.querySelector(".device, .media .device, .media img, img.device");
      if (!media) return;
      card.addEventListener("mousemove", (e) => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        media.style.transform = `rotateY(${x * 12}deg) rotateX(${-y * 12}deg) scale(1.06)`;
      });
      card.addEventListener("mouseleave", () => { media.style.transform = ""; });
    });
  }

  /* ---------- scroll reveal ---------- */
  function initReveal() {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        const el = en.target;
        el.classList.add("in");
        if (el.hasAttribute("data-stagger")) {
          const kids = el.children;
          for (let i = 0; i < kids.length; i++) kids[i].style.transitionDelay = i * 60 + "ms";
        }
        io.unobserve(el);
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
  }

  /* ---------- theme + header ---------- */
  function initTheme() {
    const KEY = "bigbrands.theme";
    const saved = localStorage.getItem(KEY);
    if (saved) document.documentElement.dataset.theme = saved;
    const btn = $("#themeToggle");
    if (btn) btn.onclick = () => {
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
    renderHero();
    renderFeatured();
    renderBrandTiles();
    renderPartners();
    initTilt();
    initReveal();
    initTheme();
    initHeader();
    $("#year").textContent = new Date().getFullYear();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
