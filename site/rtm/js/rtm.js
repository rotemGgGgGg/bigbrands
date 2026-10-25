(() => {
  const PRODUCTS = window.RTM_PRODUCTS;
  const COLLECTIONS = window.RTM_COLLECTIONS;
  const byId = Object.fromEntries(PRODUCTS.map(p => [p.id, p]));
  const $ = s => document.querySelector(s);
  const CART_KEY = 'rtm-cart';

  const fmt = (n, cur = 'USD') =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: cur, maximumFractionDigits: 0 }).format(n);

  const ICONS = {
    summer: '<svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 1.8v3M12 19.2v3M1.8 12h3M19.2 12h3M4.8 4.8l2.1 2.1M17.1 17.1l2.1 2.1M4.8 19.2l2.1-2.1M17.1 6.9l2.1-2.1"/></svg>',
    winter: '<svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" aria-hidden="true"><path d="M12 1.5v21M2.9 6.75l18.2 10.5M2.9 17.25l18.2-10.5"/><path d="M9.3 3.2 12 5.6l2.7-2.4M9.3 20.8 12 18.4l2.7 2.4M3.4 10.2l3.5.9-1.1 3.4M20.6 13.8l-3.5-.9 1.1-3.4M3.4 13.8l3.5-.9-1.1-3.4M20.6 10.2l-3.5.9 1.1 3.4"/></svg>',
    cart: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 3.5h3l2.4 11.2h11.2l2.2-8H7"/><circle cx="9.5" cy="19.5" r="1.4"/><circle cx="17.5" cy="19.5" r="1.4"/></svg>'
  };

  /* ---------- Clock ---------- */
  const clockTime = $('#clockTime'), clockDate = $('#clockDate');
  function tick() {
    const d = new Date();
    clockTime.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    clockTime.dateTime = d.toISOString();
    clockDate.textContent = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase();
  }
  tick();
  setTimeout(() => { tick(); setInterval(tick, 60000); }, 60000 - (Date.now() % 60000) + 50);

  /* ---------- Filtering ---------- */
  let active = new URLSearchParams(location.search).get('c');
  if (!COLLECTIONS.some(c => c.id === active)) active = null;

  const catList = $('#cats'), menuList = $('#menuList');
  catList.innerHTML = COLLECTIONS.map(c => `
    <li><button class="cat cat--${c.id}" data-cat="${c.id}" aria-pressed="false">
      ${ICONS[c.id] || ''}<span>${c.label}</span></button></li>`).join('');
  menuList.innerHTML = `<li><button data-cat="">All Watches</button></li>` +
    COLLECTIONS.map(c => `<li><button data-cat="${c.id}">${c.label}</button></li>`).join('');

  function setCategory(id) {
    active = id || null;
    const url = new URL(location.href);
    active ? url.searchParams.set('c', active) : url.searchParams.delete('c');
    history.replaceState(null, '', url);
    renderGrid();
  }
  catList.addEventListener('click', e => {
    const b = e.target.closest('[data-cat]');
    if (b) setCategory(b.dataset.cat === active ? null : b.dataset.cat);
  });
  menuList.addEventListener('click', e => {
    const b = e.target.closest('[data-cat]');
    if (!b) return;
    setCategory(b.dataset.cat);
    closeDrawer();
  });

  /* ---------- Grid ---------- */
  const grid = $('#grid'), status = $('#gridStatus');
  function renderGrid() {
    const list = active ? PRODUCTS.filter(p => p.collections.includes(active)) : PRODUCTS;
    grid.innerHTML = list.length ? list.map((p, i) => `
      <li class="card" data-accent="${p.accent}">
        <div class="box">
          <img src="${p.image}" alt="${p.brand} ${p.model} in an open black presentation box"
               width="416" height="408" ${i >= 10 ? 'loading="lazy"' : ''} decoding="async" />
        </div>
        <div class="info">
          <div class="brand">${p.brand}</div>
          <div class="model">${p.model}</div>
          <div class="buy">
            <span class="price">${fmt(p.price, p.currency)}</span>
            <button class="mini-cart" data-add="${p.id}" aria-label="Add ${p.brand} ${p.model} to bag">${ICONS.cart}</button>
          </div>
        </div>
      </li>`).join('') : '<li class="empty-grid">No pieces in this collection yet.</li>';

    catList.querySelectorAll('[data-cat]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.cat === active)));
    menuList.querySelectorAll('[data-cat]').forEach(b => b.setAttribute('aria-current', String((b.dataset.cat || null) === active)));
    const label = active ? COLLECTIONS.find(c => c.id === active).label : 'All watches';
    status.textContent = `${label}: ${list.length} pieces`;
  }

  grid.addEventListener('click', e => {
    const b = e.target.closest('[data-add]');
    if (!b) return;
    addToCart(b.dataset.add);
    b.classList.add('added');
    setTimeout(() => b.classList.remove('added'), 900);
  });

  /* ---------- Cart ---------- */
  let cart = {};
  try { cart = JSON.parse(localStorage.getItem(CART_KEY)) || {}; } catch { cart = {}; }
  for (const id in cart) if (!byId[id] || !(cart[id] > 0)) delete cart[id];

  const save = () => { try { localStorage.setItem(CART_KEY, JSON.stringify(cart)); } catch {} };
  function addToCart(id) { cart[id] = (cart[id] || 0) + 1; save(); renderCart(); }
  function setQty(id, q) { q > 0 ? cart[id] = q : delete cart[id]; save(); renderCart(); }

  const lines = $('#cartLines'), empty = $('#cartEmpty'), foot = $('#cartFoot');
  function renderCart() {
    const ids = Object.keys(cart);
    const count = ids.reduce((n, id) => n + cart[id], 0);
    const subtotal = ids.reduce((s, id) => s + byId[id].price * cart[id], 0);
    $('#cartCount').textContent = count;
    $('#cartOpen').setAttribute('aria-label', `Open shopping bag, ${count} item${count === 1 ? '' : 's'}`);
    $('#cartSubtotal').textContent = fmt(subtotal);
    empty.hidden = ids.length > 0;
    foot.hidden = ids.length === 0;
    lines.innerHTML = ids.map(id => {
      const p = byId[id];
      return `<li class="line" data-id="${id}">
        <img src="${p.image}" alt="" width="72" height="72" />
        <div>
          <div class="line-brand">${p.brand}</div>
          <div class="line-model">${p.model}</div>
          <div class="line-price">${fmt(p.price * cart[id], p.currency)}</div>
          <div class="qty">
            <button data-q="-1" aria-label="Decrease quantity">&minus;</button>
            <span aria-label="Quantity">${cart[id]}</span>
            <button data-q="1" aria-label="Increase quantity">+</button>
          </div>
        </div>
        <button class="remove" data-remove aria-label="Remove ${p.brand} ${p.model}">Remove</button>
      </li>`;
    }).join('');
  }
  lines.addEventListener('click', e => {
    const li = e.target.closest('.line');
    if (!li) return;
    const id = li.dataset.id;
    const q = e.target.closest('[data-q]');
    if (q) setQty(id, cart[id] + Number(q.dataset.q));
    else if (e.target.closest('[data-remove]')) setQty(id, 0);
  });

  /* ---------- Drawers ---------- */
  const scrim = $('#scrim');
  let open = null, opener = null;
  function openDrawer(el, btn) {
    if (open) closeDrawer(true);
    open = el; opener = btn;
    el.hidden = false; scrim.hidden = false;
    btn.setAttribute('aria-expanded', 'true');
    requestAnimationFrame(() => { el.classList.add('on'); scrim.classList.add('on'); });
    document.body.style.overflow = 'hidden';
    el.querySelector('[data-close]').focus();
  }
  function closeDrawer(instant) {
    if (!open) return;
    const el = open;
    el.classList.remove('on'); scrim.classList.remove('on');
    opener.setAttribute('aria-expanded', 'false');
    const done = () => { if (open !== el) { el.hidden = true; } if (!open) scrim.hidden = true; };
    open = null;
    instant ? done() : setTimeout(done, 350);
    document.body.style.overflow = '';
    opener.focus();
  }
  $('#cartOpen').addEventListener('click', e => openDrawer($('#cartDrawer'), e.currentTarget));
  $('#menuOpen').addEventListener('click', e => openDrawer($('#menuDrawer'), e.currentTarget));
  scrim.addEventListener('click', () => closeDrawer());
  document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', () => closeDrawer()));
  document.addEventListener('keydown', e => {
    if (!open) return;
    if (e.key === 'Escape') return closeDrawer();
    if (e.key === 'Tab') { // keep focus inside the open drawer
      const f = [...open.querySelectorAll('button, a[href]')].filter(n => !n.closest('[hidden]'));
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  $('#logo').addEventListener('click', e => { e.preventDefault(); setCategory(null); });

  renderGrid();
  renderCart();
})();
