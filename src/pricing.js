const UA = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
  "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
};
const VAT = 0.18;

/* ---------- Zap: every Israeli store Zap tracks ---------- */
function findOfferNodes(node, out = []) {
  if (Array.isArray(node)) node.forEach((n) => findOfferNodes(n, out));
  else if (node && typeof node === "object") {
    if (node.offers && Array.isArray(node.offers.offers)) out.push(node);
    Object.values(node).forEach((v) => findOfferNodes(v, out));
  }
  return out;
}

function parseZapModel(html, url) {
  const out = [];
  for (const m of html.matchAll(/<script[^>]*application\/ld(?:\+|&#x2B;|&#43;)json[^>]*>([\s\S]*?)<\/script>/gi)) {
    let data;
    try { data = JSON.parse(m[1]); } catch { continue; }
    for (const p of findOfferNodes(data)) {
      for (const o of p.offers.offers) {
        const t = o.shippingDetails?.deliveryTime?.transitTime;
        out.push({
          source: "Zap", region: "IL", store: o.seller?.name || "?", title: p.name,
          image: typeof p.image === "string" ? p.image : p.image?.[0] || "",
          price: Number(o.price), currency: o.priceCurrency || "ILS",
          shipping: Number(o.shippingDetails?.shippingRate?.value || 0),
          delivery: t ? `${t.minValue}-${t.maxValue} ימים` : "", url,
        });
      }
    }
  }
  return out;
}

async function searchZap(query, maxModels = 8) {
  const res = await fetch("https://www.zap.co.il/search.aspx?keyword=" + encodeURIComponent(query), { headers: UA });
  if (!res.ok) throw new Error("Zap החזיר " + res.status);
  const html = await res.text();
  let items;
  const canonical = html.match(/<link rel="canonical" href="([^"]*model\.aspx\?modelid=\d+)"/);
  if (canonical) items = parseZapModel(html, canonical[1]);
  else {
    const ids = [...new Set([...html.matchAll(/data-model-id="(\d+)"/g)].map((m) => m[1]))].slice(0, maxModels);
    const pages = await Promise.all(ids.map(async (id) => {
      const url = "https://www.zap.co.il/model.aspx?modelid=" + id;
      try { return parseZapModel(await (await fetch(url, { headers: UA })).text(), url); } catch { return []; }
    }));
    items = pages.flat();
  }
  // Zap falls back to loosely related models when nothing matches; keep titles containing every query word.
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  return items.filter((i) => words.every((w) => (i.title || "").toLowerCase().includes(w)));
}

/* ---------- Google Shopping via SerpAPI (paid key) ---------- */
async function searchGoogle(query, apiKey, country) {
  if (!apiKey) throw new Error("חסר מפתח SERPAPI_KEY");
  const params = new URLSearchParams({ engine: "google_shopping", q: query, gl: country, hl: country === "il" ? "iw" : "en", num: "100", api_key: apiKey });
  const data = await (await fetch("https://serpapi.com/search.json?" + params)).json();
  if (data.error) throw new Error(data.error);
  return (data.shopping_results || []).filter((r) => r.extracted_price).map((r) => ({
    source: "Google", region: country.toUpperCase(), store: r.source || "?", title: r.title, image: r.thumbnail || "",
    price: r.extracted_price, currency: country === "il" ? "ILS" : "USD",
    shipping: /free|חינם/i.test(r.delivery || "") ? 0 : null, delivery: r.delivery || "", url: r.product_link || r.link,
  }));
}

/* ---------- eBay Browse API (free key), listings that ship to Israel ---------- */
let ebayToken = null, ebayTokenExp = 0;
async function searchEbay(query, id, secret) {
  if (!id || !secret) throw new Error("חסרים מפתחות eBay");
  if (!ebayToken || Date.now() > ebayTokenExp) {
    const t = await (await fetch("https://api.ebay.com/identity/v1/oauth2/token", {
      method: "POST",
      headers: { Authorization: "Basic " + btoa(`${id}:${secret}`), "Content-Type": "application/x-www-form-urlencoded" },
      body: "grant_type=client_credentials&scope=" + encodeURIComponent("https://api.ebay.com/oauth/api_scope"),
    })).json();
    if (!t.access_token) throw new Error("eBay auth נכשל");
    ebayToken = t.access_token; ebayTokenExp = Date.now() + (t.expires_in - 60) * 1000;
  }
  const params = new URLSearchParams({ q: query, limit: "100", filter: "deliveryCountry:IL,buyingOptions:{FIXED_PRICE}" });
  const data = await (await fetch("https://api.ebay.com/buy/browse/v1/item_summary/search?" + params, {
    headers: { Authorization: "Bearer " + ebayToken, "X-EBAY-C-MARKETPLACE-ID": "EBAY_US", "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=IL" },
  })).json();
  if (data.errors) throw new Error(data.errors[0]?.message);
  return (data.itemSummaries || []).map((i) => {
    const s = i.shippingOptions?.[0]?.shippingCost;
    return {
      source: "eBay", region: i.itemLocation?.country || "INT", store: i.seller?.username || "?", title: i.title,
      image: i.image?.imageUrl || "", price: Number(i.price.value), currency: i.price.currency,
      shipping: s ? Number(s.value) : null, delivery: i.condition || "", url: i.itemWebUrl,
    };
  });
}

/* ---------- merge, convert to ILS, estimate import VAT ---------- */
let rates = null, ratesAt = 0;
async function getRates() {
  if (!rates || Date.now() - ratesAt > 6 * 3600e3) {
    rates = (await (await fetch("https://open.er-api.com/v6/latest/USD")).json()).rates;
    ratesAt = Date.now();
  }
  return rates;
}

const ACCESSORY = /\b(charger|adapter|case|sleeve|bag|battery|keyboard cover|skin|screen protector|cable|replacement|parts?|hinge|motherboard|fan)\b|מטען|תיק|סוללה|כבל|מגן מסך|חלקים/i;
const cache = new Map();

export async function searchPrices(query, sources, env) {
  const key = query.toLowerCase() + "|" + sources.join(",");
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < 30 * 60e3) return { ...hit.data, cached: true };

  const jobs = {
    zap: () => searchZap(query),
    google_il: () => searchGoogle(query, env.SERPAPI_KEY, "il"),
    google_us: () => searchGoogle(query, env.SERPAPI_KEY, "us"),
    ebay: () => searchEbay(query, env.EBAY_CLIENT_ID, env.EBAY_CLIENT_SECRET),
  };
  const active = sources.filter((s) => jobs[s]);
  const [r, ...settled] = await Promise.all([getRates(), ...active.map((s) => jobs[s]().then((v) => ({ ok: v }), (e) => ({ err: e.message })))]);

  const status = {};
  let items = [];
  active.forEach((s, i) => {
    if (settled[i].ok) { status[s] = { ok: true, count: settled[i].ok.length }; items.push(...settled[i].ok); }
    else status[s] = { ok: false, error: settled[i].err };
  });

  const limitUsd = Number(env.VAT_FREE_LIMIT_USD || 75);
  const toILS = (a, c) => (c === "ILS" ? a : (a / r[c]) * r.ILS);
  items = items
    .filter((i) => i.price > 0 && r[i.currency] && !ACCESSORY.test(i.title || ""))
    .map((i) => {
      const base = toILS(i.price, i.currency), ship = i.shipping == null ? 0 : toILS(i.shipping, i.currency);
      const vat = i.region !== "IL" && (i.price + (i.shipping || 0)) / r[i.currency] > limitUsd ? (base + ship) * VAT : 0;
      return { ...i, priceILS: Math.round(base), shippingILS: i.shipping == null ? null : Math.round(ship), vatILS: Math.round(vat), totalILS: Math.round(base + ship + vat) };
    });

  // Prices far below the median are almost always accessories or the wrong model.
  const totals = items.map((i) => i.totalILS).sort((a, b) => a - b);
  const median = totals[Math.floor(totals.length / 2)] || 0;
  items = items.filter((i) => i.totalILS >= median * 0.35).sort((a, b) => a.totalILS - b.totalILS);

  const data = { query, status, usdIls: +r.ILS.toFixed(3), count: items.length, items };
  cache.set(key, { at: Date.now(), data });
  return data;
}
