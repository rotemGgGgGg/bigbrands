(() => {
  const KEY = "bigbrands.cart.v1";
  const WA = "972508808076";
  const $ = (s, r = document) => r.querySelector(s);
  const ils = (n) => Number(n).toLocaleString("he-IL") + " ₪";

  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; } };
  const save = (c) => localStorage.setItem(KEY, JSON.stringify(c));

  const catalog = () => (window.Store?.products?.() || window._PRODUCTS || []);
  const find = (id) => catalog().find((p) => p.id === id);

  const totalQty = (c) => Object.values(c).reduce((a, b) => a + b, 0);
  const totalPrice = (c) => Object.entries(c).reduce((s, [id, q]) => {
    const p = find(id); return s + (p?.price || 0) * q;
  }, 0);

  function updateBadge() {
    const el = $("#cartCount"); if (!el) return;
    const n = totalQty(load());
    el.textContent = n;
    el.animate?.([{ transform: "scale(1)" }, { transform: "scale(1.5)" }, { transform: "scale(1)" }], { duration: 260 });
  }

  function add(id) {
    if (!id || !find(id)) return;
    const c = load(); c[id] = (c[id] || 0) + 1; save(c); updateBadge();
    if ($(".bb-cart.open")) render();
  }
  function setQty(id, q) {
    const c = load();
    if (q <= 0) delete c[id]; else c[id] = q;
    save(c); updateBadge(); render();
  }
  function clearCart() { save({}); updateBadge(); render(); }

  function ensureDrawer() {
    if ($(".bb-cart-scrim")) return;
    const scrim = document.createElement("div");
    scrim.className = "bb-cart-scrim";
    scrim.innerHTML = `
      <aside class="bb-cart" role="dialog" aria-label="עגלת קניות">
        <header class="bb-cart-head">
          <h3>העגלה שלי</h3>
          <button class="bb-cart-x" aria-label="סגור">&times;</button>
        </header>
        <div class="bb-cart-body" id="bbCartBody"></div>
        <footer class="bb-cart-foot" id="bbCartFoot"></footer>
      </aside>`;
    document.body.appendChild(scrim);
    scrim.addEventListener("click", (e) => {
      if (e.target === scrim || e.target.closest(".bb-cart-x")) close();
    });
  }

  function open() { ensureDrawer(); render(); document.body.classList.add("bb-cart-lock"); $(".bb-cart-scrim").classList.add("open"); $(".bb-cart").classList.add("open"); }
  function close() { document.body.classList.remove("bb-cart-lock"); $(".bb-cart-scrim")?.classList.remove("open"); $(".bb-cart")?.classList.remove("open"); }

  function render() {
    const c = load();
    const body = $("#bbCartBody"); const foot = $("#bbCartFoot");
    if (!body || !foot) return;
    const items = Object.entries(c).map(([id, q]) => ({ p: find(id), q })).filter((x) => x.p);
    if (!items.length) {
      body.innerHTML = `<div class="bb-cart-empty">
        <div class="bb-cart-empty-icon">🛒</div>
        <p>העגלה ריקה</p>
        <a class="btn-cta primary" href="products.html">לצפייה במוצרים</a>
      </div>`;
      foot.innerHTML = "";
      return;
    }
    body.innerHTML = items.map(({ p, q }) => `
      <div class="bb-cart-item" data-id="${p.id}">
        <div class="bb-cart-img">${p.image ? `<img src="${p.image}" alt="" loading="lazy">` : ""}</div>
        <div class="bb-cart-info">
          <a class="bb-cart-name" href="product.html?id=${encodeURIComponent(p.id)}">${p.name}</a>
          <div class="bb-cart-price">${p.price ? ils(p.price) : "לבירור מחיר"}</div>
          <div class="bb-cart-qty">
            <button class="bb-qty-btn" data-act="dec" data-id="${p.id}" aria-label="פחות">−</button>
            <span class="bb-qty-n">${q}</span>
            <button class="bb-qty-btn" data-act="inc" data-id="${p.id}" aria-label="עוד">+</button>
            <button class="bb-qty-rm" data-act="rm" data-id="${p.id}" aria-label="הסר">הסר</button>
          </div>
        </div>
      </div>
    `).join("");
    const total = totalPrice(c);
    const lines = items.map(({ p, q }) => `• ${p.name} × ${q}${p.price ? ` — ${ils(p.price * q)}` : ""}`).join("\n");
    const msg = encodeURIComponent(`שלום, אני מעוניין/ת להזמין:\n${lines}\n\nסה״כ: ${ils(total)}`);
    foot.innerHTML = `
      <div class="bb-cart-total"><span>סה״כ</span><b>${ils(total)}</b></div>
      <div class="bb-cart-vat">המחיר כולל מע"מ</div>
      <a class="btn-cta wa bb-cart-checkout" href="https://wa.me/${WA}?text=${msg}" target="_blank" rel="noopener">
        סיום הזמנה בוואטסאפ
      </a>
      <button class="bb-cart-clear" data-act="clear">רוקן עגלה</button>`;
  }

  document.addEventListener("click", (e) => {
    const cartBtn = e.target.closest("#cartBtn");
    if (cartBtn) { e.preventDefault(); open(); return; }
    const addBtn = e.target.closest(".add");
    if (addBtn) {
      e.preventDefault(); e.stopPropagation();
      const id = addBtn.dataset.id || addBtn.closest("[data-id]")?.dataset.id;
      add(id); return;
    }
    const pdpAdd = e.target.closest("#pdpAdd");
    if (pdpAdd) {
      e.preventDefault(); e.stopPropagation();
      const id = new URLSearchParams(location.search).get("id");
      add(id); open(); return;
    }
    const act = e.target.closest("[data-act]");
    if (act) {
      const id = act.dataset.id;
      const c = load();
      if (act.dataset.act === "inc") setQty(id, (c[id] || 0) + 1);
      else if (act.dataset.act === "dec") setQty(id, (c[id] || 0) - 1);
      else if (act.dataset.act === "rm") setQty(id, 0);
      else if (act.dataset.act === "clear") clearCart();
    }
  }, true);

  window.addEventListener("DOMContentLoaded", updateBadge);
})();
