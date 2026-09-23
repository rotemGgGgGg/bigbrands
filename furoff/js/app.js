(() => {
  const C = window.FUROFF;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const ils = (n) => n.toLocaleString("he-IL") + " ₪";

  let selected = C.defaultBundle ?? 0;

  function checkoutUrl(b) {
    const url = `https://${C.shop}/cart/${C.variantId}:${b.qty}`;
    return b.code ? `${url}?discount=${encodeURIComponent(b.code)}` : url;
  }

  // Bundles
  function renderBundles() {
    const box = $("#bundles");
    box.insertAdjacentHTML("beforeend", C.bundles.map((b, i) => {
      const per = Math.round(b.price / b.qty);
      const save = b.compare ? b.compare - b.price : 0;
      return `
        <label class="bundle${b.tag ? " has-tag" : ""}">
          <input type="radio" name="bundle" value="${i}" ${i === selected ? "checked" : ""} />
          ${b.tag ? `<span class="b-tag">${b.tag}</span>` : ""}
          <span class="b-dot" aria-hidden="true"></span>
          <span class="b-main">
            <span class="b-title">${b.title}</span>
            <span class="b-note">${b.note}${b.qty > 1 ? ` · ${ils(per)} ליחידה` : ""}</span>
          </span>
          <span class="b-price">
            <strong>${ils(b.price)}</strong>
            ${b.compare ? `<s>${ils(b.compare)}</s>` : ""}
            ${save ? `<em>חוסכים ${ils(save)}</em>` : ""}
          </span>
        </label>`;
    }).join(""));
    box.addEventListener("change", (e) => {
      if (e.target.name === "bundle") { selected = Number(e.target.value); syncCheckout(); }
    });
    syncCheckout();
  }

  function syncCheckout() {
    const b = C.bundles[selected];
    const url = checkoutUrl(b);
    $("#checkoutBtn").href = url;
    $("#checkoutBtn").textContent = `לתשלום מאובטח — ${ils(b.price)}`;
    $("#stickyBtn").href = url;
    $("#stickyPrice").textContent = ils(b.price);
  }

  // Gallery
  $$(".thumb[data-src]").forEach((t) => t.addEventListener("click", () => {
    $$(".thumb").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    $("#galleryMain").src = t.dataset.src;
  }));

  // Reviews (real ones only; section stays hidden when empty)
  if (C.reviews?.length) {
    $("#revGrid").innerHTML = C.reviews.map((r) => `
      <figure class="rev reveal">
        ${r.photo ? `<img src="${r.photo}" alt="" loading="lazy" />` : ""}
        <div class="stars" aria-label="${r.stars} כוכבים">${"★".repeat(r.stars)}</div>
        <blockquote>${r.text}</blockquote>
        <figcaption><strong>${r.name}</strong>${r.dog ? ` · ${r.dog}` : ""}</figcaption>
      </figure>`).join("");
    $("#reviews").hidden = false;
  }

  // Business text from config
  $$("[data-guarantee]").forEach((el) => (el.textContent = C.guaranteeDays));
  $$("[data-shipping]").forEach((el) => (el.textContent = C.shippingText));
  $("#contactLink").href = `https://${C.shop}/pages/contact`;
  $("#policyLinks").innerHTML = C.policies.map(([t, url]) => `<a href="${url}">${t}</a>`).join("");
  $("#year").textContent = new Date().getFullYear();

  // Sticky bar: show once the hero CTA scrolls away, hide while the buy box is on screen
  const bar = $("#stickyBar");
  let heroGone = false, buyVisible = false;
  const updateBar = () => {
    const show = heroGone && !buyVisible;
    bar.classList.toggle("show", show);
    bar.setAttribute("aria-hidden", String(!show));
    $("#stickyBtn").tabIndex = show ? 0 : -1;
  };
  new IntersectionObserver(([e]) => { heroGone = !e.isIntersecting && e.boundingClientRect.top < 0; updateBar(); })
    .observe($(".hero-cta"));
  new IntersectionObserver(([e]) => { buyVisible = e.isIntersecting; updateBar(); }, { threshold: 0.15 })
    .observe($(".buy-info"));

  // Reveal on scroll
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { threshold: 0.12 });
  $$(".reveal").forEach((el) => io.observe(el));

  renderBundles();
})();
