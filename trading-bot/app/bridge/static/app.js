"use strict";
/* Single-page dashboard. No build step, no external files — works offline inside the desktop window. */

// ── session token: the desktop app opens /?t=<token>; keep it for this window only ──
const qs = new URLSearchParams(location.search);
if (qs.get("t")) { sessionStorage.setItem("t", qs.get("t")); history.replaceState(null, "", location.pathname + location.hash); }
const TOKEN = sessionStorage.getItem("t") || "";

const $ = (s, r = document) => r.querySelector(s);

// ── chrome-ribbon background: a local SVG that drifts slowly; the switch in My Account freezes it ──
const bgOn = () => { try { return localStorage.getItem("bg") !== "off"; } catch { return true; } };
function mountBackdrop() { document.getElementById("backdrop").classList.toggle("still", !bgOn()); }
mountBackdrop();
const esc = (x) => String(x ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const money = (v) => { const n = Number(v || 0); return `<span class="${n > 0 ? "pos" : n < 0 ? "neg" : ""}">${n >= 0 ? "+" : "−"}$${Math.abs(n).toFixed(2)}</span>`; };
const fmtTime = (iso) => iso ? new Date(iso).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" }) : "—";

async function api(path, method = "GET", body) {
  const r = await fetch(path, { method, headers: { "X-Token": TOKEN, ...(body ? { "Content-Type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).detail || msg; } catch { /* keep statusText */ }
    if (r.status === 401) msg = "Session expired — reopen the app.";
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return r.json();
}
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove("show"), 2600); }
async function act(fn, ok) { try { await fn(); if (ok) toast(ok); refresh(); } catch (e) { toast("⚠ " + e.message); } }

// ── icons ──
const I = {
  dash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
  plug: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 2v6M15 2v6M6 8h12v3a6 6 0 0 1-12 0V8zM12 17v5"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/><path d="M12 8v5"/><circle cx="12" cy="16" r=".6"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 5a2 2 0 0 1 2-2h6v18H5a2 2 0 0 1-2-2V5zM21 5a2 2 0 0 0-2-2h-6v18h6a2 2 0 0 0 2-2V5z"/></svg>',
  cal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/><circle cx="12" cy="15" r="2.5"/></svg>',
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 4h16v12H8l-4 4V4z"/></svg>',
  share: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="9" r="2"/><path d="M21 15l-5-5-11 11"/></svg>',
  bank: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 10l9-6 9 6M5 10v8M9 10v8M15 10v8M19 10v8M3 21h18"/></svg>',
};

const PAGES = [
  ["dashboard", "Live Dashboard", I.dash], ["connections", "Connections", I.plug], ["risk", "Risk Management", I.shield],
  ["journal", "Trade Journal", I.book], ["news", "News Alerts", I.cal, "PRO"], ["feedback", "Feedback", I.chat], ["snapshot", "Share a Snapshot", I.share],
];
$("#nav").innerHTML = PAGES.map(([id, label, icon, badge]) => `<button data-page="${id}">${icon}<span>${label}</span>${badge ? `<em class="badge">${badge}</em>` : ""}</button>`).join("");

let S = null;           // last /api/state
let NEWS = null;        // last /api/news
let page = location.hash.slice(1) || "dashboard";

function go(p) { page = p; location.hash = p; render(); }
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-page]");
  if (b) { go(b.dataset.page); return; }
  const a = e.target.closest("[data-act]");
  if (a) handlers[a.dataset.act]?.(a.dataset, a);
});
window.addEventListener("hashchange", () => { page = location.hash.slice(1) || "dashboard"; render(); });

// ── data ──
async function refresh() {
  try {
    S = await api("/api/state");
    if (!NEWS || Date.now() - NEWS._at > 300000) { NEWS = await api("/api/news"); NEWS._at = Date.now(); }
    if (["dashboard"].includes(page)) render();
    renderSetup();
    $("#brand").textContent = S.brand;
    document.title = S.brand;
  } catch (e) { if (!S) $("#main").innerHTML = `<div class="panel empty">${esc(e.message)}</div>`; }
}

// ── pages ──
function topbar() {
  return `<section class="panel topbar">
    <div class="stats">
      <div class="live ${S.dry_run ? "test" : ""}"><i></i>${S.dry_run ? "TEST MODE" : "LIVE"}</div>
      <div class="stat"><div class="k">Realized P&L</div><div class="v">${money(S.realized)}</div></div>
      <div class="stat"><div class="k">Open Positions</div><div class="v">${S.open_positions}</div></div>
      <div class="stat"><div class="k">Average Dispatch</div><div class="v ${S.avg_ms == null ? "na" : ""}">${S.avg_ms == null ? "n/a" : S.avg_ms + " ms"}</div></div>
    </div>
    <div class="seg">
      <button data-act="followAll" data-on="false">Disable All Followers</button>
      <button data-act="followAll" data-on="true">Enable All Followers</button>
      <button class="amber" data-act="cancelAll">Cancel All Orders</button>
      <button class="red" data-act="flattenAll">Flatten All</button>
    </div>
  </section>`;
}

function untilText(iso) {
  const ms = new Date(iso) - Date.now();
  if (ms <= 0) return "now";
  const d = Math.floor(ms / 864e5), h = Math.floor(ms % 864e5 / 36e5), m = Math.floor(ms % 36e5 / 6e4);
  return d ? `in ${d}d ${h}h` : h ? `in ${h}h ${m}m` : `in ${m}m`;
}
function agoText(iso) {
  const ms = Date.now() - new Date(iso);
  const d = Math.floor(ms / 864e5), h = Math.floor(ms / 36e5), m = Math.floor(ms / 6e4);
  return d ? `${d}d ago` : h ? `${h}h ago` : `${m}m ago`;
}
function newsbar() {
  const n = NEWS || {};
  const nx = n.next ? `${esc(n.next.title)} · ${untilText(n.next.time)}` : (n.error ? esc(n.error) : "No high-impact USD release this week");
  const ls = n.last ? `${esc(n.last.title)} <small>· ${agoText(n.last.time)}</small>` : "—";
  return `<section class="panel newsbar">
    <div class="nb hot">${I.cal}<div style="min-width:0"><div class="k">Next high-impact release</div><div class="t">${nx}</div></div></div>
    <div class="sep"></div>
    <div class="nb">${I.bank}<div style="min-width:0"><div class="k">Latest official release</div><div class="t">${ls}</div></div></div>
    <div class="links"><a data-page="news">Read</a><a data-page="news">News alerts</a></div>
  </section>`;
}

function followersTable() {
  const head = ["Follow", "Connection", "Group", "Account", "Symbol", "Side", "Realized P&L", "Qty", "Micros Only", "Ratio", "Actions"];
  const rows = S.rows.map((r) => `<tr>
    <td><button class="switch ${r.follow ? "on" : ""}" data-act="follow" data-id="${esc(r.id)}" data-on="${!r.follow}" title="Follow the leader"></button></td>
    <td><b>${esc(r.name)}</b></td><td>${esc(r.group) || "—"}</td><td>${esc(r.account) || "—"}</td>
    <td>${esc(r.symbol) || "—"}</td><td><span class="side-pill ${r.side}">${r.side}</span></td>
    <td>${money(r.realized)}</td><td>${r.qty}</td><td>${r.micros_only ? "Yes" : "No"}</td><td>×${r.ratio}</td>
    <td><button class="icon-btn" data-act="edit" data-id="${esc(r.id)}">Edit</button><button class="icon-btn" data-act="flattenOne" data-id="${esc(r.id)}">Flatten</button></td>
  </tr>`).join("");
  return `<section class="panel"><div class="tablewrap"><table>
    <thead><tr>${head.map((h) => `<th>${h.toUpperCase()}</th>`).join("")}</tr></thead>
    <tbody>${rows || `<tr><td colspan="11" class="empty">No accounts connected. Add connections to get started.<br><button class="btn-white" data-page="connections">Go to Connections →</button></td></tr>`}</tbody>
  </table></div></section>
  <div class="note">Realized P&L is today's, estimated from the leader's signals — your broker statement is the final number.</div>`;
}

function healthPanel() {
  const h = S.health;
  const msg = h.status === "HEALTHY" ? "Every selected account is in sync, with no incidents in the latest window."
    : `${h.failures ? h.failures + " failed dispatch(es). " : ""}${h.out_of_sync ? h.out_of_sync + " account(s) out of sync with the leader." : ""}`;
  const m = (k, v) => `<div><div class="k">${k}</div><div class="v">${v}</div></div>`;
  return `<section class="panel health">
    <div class="health-head"><div><h3>Copier Health</h3><div class="sub">Live account sync, with the last 30 minutes of execution and connection state.</div></div>
    <div class="status ${h.status === "HEALTHY" ? "" : "bad"}">${h.status}</div></div>
    <div class="metrics">${m("FAILURES", h.failures)}${m("RISK BLOCKS", h.risk_blocks)}${m("OUT OF SYNC", h.out_of_sync)}${m("PROTECTED SKIPS", h.protected)}${m("AVERAGE DISPATCH", h.avg_ms == null ? '<span class="na" style="color:var(--blue)">n/a</span>' : h.avg_ms + " ms")}</div>
    <div class="health-foot">${msg}</div>
  </section>`;
}

const views = {
  dashboard() { return `<div class="page">${topbar()}${newsbar()}${followersTable()}${healthPanel()}${activity()}</div>`; },

  async connections() {
    const cons = await api("/api/connections");
    const set = await api("/api/settings");
    const cards = cons.map((c) => `<div class="panel card">
      <h4>${esc(c.name)} <button class="switch ${c.enabled ? "on" : ""}" data-act="follow" data-id="${esc(c.id)}" data-on="${!c.enabled}"></button></h4>
      <div class="kv"><span>Group</span><b>${esc(c.group) || "—"}</b><span>Account</span><b>${esc(c.broker_account) || "—"}</b>
      <span>Ratio</span><b>×${c.multiplier}</b><span>Micros only</span><b>${c.micros_only ? "Yes" : "No"}</b>
      <span>Endpoint</span><b class="mono">${esc(c.url)}</b>
      <span>Template</span><b class="${Object.keys(c.template_open || {}).length && !JSON.stringify(c.template_open).includes("PASTE") ? "pos" : "warn"}">${Object.keys(c.template_open || {}).length && !JSON.stringify(c.template_open).includes("PASTE") ? "ready" : "missing token"}</b></div>
      <div class="row" style="margin-top:14px"><button class="btn small" data-act="edit" data-id="${esc(c.id)}">Edit</button>
      <button class="btn small" data-act="del" data-id="${esc(c.id)}">Remove</button></div></div>`).join("");
    return `<div class="page">
      <div><div class="h1">Connections</div><p class="lead">Each connection is one prop account that follows your TradingView strategy through PickMyTrade.</p></div>
      <div class="row"><button class="btn-white" data-act="add">+ Add connection</button><button class="btn" data-act="test">Send a test signal</button></div>
      <div class="cards">${cards || '<div class="panel card">No connections yet.</div>'}</div>
      <section class="panel card"><h4>Leader — TradingView</h4>
        <p class="lead">Create an alert on your strategy, tick <b>Webhook URL</b> and paste the address below. Put this JSON in the alert message:</p>
        <div class="kv" style="margin:12px 0"><span>Webhook URL</span><b class="mono">${esc((set.public_url || "https://YOUR-PUBLIC-ADDRESS") + "/webhook")}</b></div>
        <div class="codebox mono" id="alertJson">${esc(alertJson(set.webhook_secret))}</div>
        <div class="row" style="margin-top:10px"><button class="btn small" data-act="copy" data-src="alertJson">Copy alert message</button></div>
      </section></div>`;
  },

  async risk() {
    const cons = await api("/api/connections");
    const set = await api("/api/settings");
    const f = (c, k, label, type = "number", step = "1") => `<label>${label}<input data-rule="${k}" data-id="${esc(c.id)}" type="${type}" step="${step}" value="${esc(c.rules[k])}"></label>`;
    const cards = cons.map((c) => `<section class="panel card"><h4>${esc(c.name)}</h4>
      <div class="grid3">${f(c, "entry_start", "Entries from (NY)", "time")}${f(c, "entry_end", "Entries until (NY)", "time")}${f(c, "flatten_at", "Flatten all at (NY)", "time")}
      ${f(c, "max_contracts", "Max contracts")}${f(c, "max_trades_per_day", "Max trades / day")}${f(c, "daily_loss_limit", "Daily loss limit $", "number", "50")}
      ${f(c, "trailing_dd", "Trailing drawdown $", "number", "100")}${f(c, "dd_buffer", "Keep this far from the drawdown $", "number", "50")}${f(c, "profit_target", "Profit target $ (0 = off)", "number", "100")}</div>
      <div class="row" style="margin-top:14px"><button class="btn green small" data-act="saveRules" data-id="${esc(c.id)}">Save rules</button></div></section>`).join("");
    return `<div class="page">
      <div><div class="h1">Risk Management</div><p class="lead">Rules block new entries only. Exits always go through.</p></div>
      <section class="panel card"><h4>Global</h4><div class="grid3">
        <label>Kill switch — block every new entry<button class="btn ${S.kill ? "red" : ""}" data-act="kill" data-on="${!S.kill}">${S.kill ? "ON — entries blocked" : "Off"}</button></label>
        <label>News blackout (minutes around high-impact USD news, 0 = off)<input id="blackout" type="number" min="0" value="${set.news_blackout_min}"></label>
        <label>&nbsp;<button class="btn green" data-act="saveBlackout">Save</button></label></div></section>
      ${cards || '<div class="panel card">Add a connection first.</div>'}</div>`;
  },

  async journal() {
    const j = await api("/api/journal");
    const s = j.stats;
    const t = (k, v) => `<div class="panel tile"><div class="k">${k}</div><div class="v">${v}</div></div>`;
    const rows = j.trades.map((x) => `<tr><td>${fmtTime(x.closed)}</td><td>${esc(x.account)}</td><td>${esc(x.strategy)}</td><td>${esc(x.symbol)}</td>
      <td><span class="side-pill ${x.side}">${x.side}</span></td><td>${x.qty}</td><td>${x.entry}</td><td>${x.exit}</td><td>${money(x.pnl)}</td></tr>`).join("");
    return `<div class="page"><div><div class="h1">Trade Journal</div><p class="lead">Every round trip the copier closed, estimated from the leader's prices.</p></div>
      <div class="tiles">${t("Trades", s.trades)}${t("Win rate", s.win_rate + "%")}${t("Net", money(s.net))}${t("Avg win", money(s.avg_win))}${t("Avg loss", money(-s.avg_loss))}</div>
      <section class="panel"><div class="tablewrap"><table><thead><tr>${["Closed", "Account", "Strategy", "Symbol", "Side", "Qty", "Entry", "Exit", "P&L"].map((h) => `<th>${h.toUpperCase()}</th>`).join("")}</tr></thead>
      <tbody>${rows || '<tr><td colspan="9" class="empty">No closed trades yet.</td></tr>'}</tbody></table></div></section></div>`;
  },

  async news() {
    NEWS = await api("/api/news"); NEWS._at = Date.now();
    const rows = NEWS.events.map((e) => `<tr><td>${fmtTime(e.time)}</td><td><span class="impact ${esc(e.impact)}">${esc(e.impact)}</span></td><td><b>${esc(e.title)}</b></td><td>${esc(e.forecast) || "—"}</td><td>${esc(e.previous) || "—"}</td></tr>`).join("");
    return `<div class="page"><div><div class="h1">News Alerts</div><p class="lead">This week's USD calendar. Set a blackout in Risk Management to stop new entries around high-impact releases.</p></div>
      ${NEWS.error ? `<div class="panel card warn">${esc(NEWS.error)}</div>` : ""}
      <section class="panel"><div class="tablewrap"><table><thead><tr><th>TIME</th><th>IMPACT</th><th>EVENT</th><th>FORECAST</th><th>PREVIOUS</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="5" class="empty">No events loaded.</td></tr>'}</tbody></table></div></section></div>`;
  },

  feedback() {
    return `<div class="page"><div><div class="h1">Feedback</div><p class="lead">Found a bug or want a feature? It's saved in the app's log.</p></div>
      <section class="panel card"><textarea id="fb" placeholder="What should we improve?" style="min-height:160px;font-family:var(--font);font-size:14px"></textarea>
      <div class="row" style="margin-top:12px"><button class="btn green" data-act="feedback">Send</button></div></section></div>`;
  },

  snapshot() {
    return `<div class="page"><div><div class="h1">Share a Snapshot</div><p class="lead">A clean image of today's numbers — no account numbers on it.</p></div>
      <section class="panel card"><canvas id="snap" width="1200" height="630" style="width:100%;max-width:900px;border-radius:14px"></canvas>
      <div class="row" style="margin-top:12px"><button class="btn green" data-act="download">Download PNG</button></div></section></div>`;
  },

  refer() { return placeholder("Refer & Earn", "Invite a friend and you both get a month free. Referral links arrive with accounts in a later version."); },
  upgrade() { return placeholder("Upgrade Plan", "Everything is unlocked in this build. Plans arrive with the cloud version."); },

  async account() {
    const s = await api("/api/settings");
    return `<div class="page"><div><div class="h1">My Account</div><p class="lead">App settings. Saved in ${esc(s.home)}</p></div>
      <section class="panel card"><h4>Mode <span class="${s.dry_run ? "warn" : "pos"}">${s.dry_run ? "TEST — nothing is sent" : "LIVE — orders are sent"}</span></h4>
        <p class="lead">Test mode runs every rule and logs what it would send, without sending. Go live only after a test signal looks right.</p>
        <div class="row" style="margin-top:10px">${s.dry_run ? '<button class="btn red" data-act="mode" data-live="true">Go LIVE</button>' : '<button class="btn" data-act="mode" data-live="false">Back to test mode</button>'}</div></section>
      <section class="panel card"><h4>Appearance <button class="switch ${bgOn() ? "on" : ""}" data-act="bg" title="Animated background"></button></h4>
        <p class="lead">Slow-moving chrome ribbon behind the app. Off = a still image.</p></section>
      <section class="panel card"><h4>Webhook</h4><div class="grid2">
        <label>Public address TradingView can reach (tunnel or VPS)<input id="pub" placeholder="https://my-tunnel.example.com" value="${esc(s.public_url)}"></label>
        <label>Webhook secret (inside the alert JSON)<input readonly class="mono" value="${esc(s.webhook_secret)}"></label></div>
        <div class="row" style="margin-top:12px"><button class="btn green small" data-act="savePub">Save address</button><button class="btn small" data-act="regen">New secret</button></div>
        <p class="lead" style="margin-top:12px">The app listens on port ${s.port}. TradingView only posts to ports 80/443, so expose it with a tunnel (e.g. Cloudflare Tunnel → http://localhost:${s.port}) and paste the tunnel address above.</p></section></div>`;
  },
};

function placeholder(title, text) { return `<div class="page"><div><div class="h1">${title}</div></div><section class="panel card empty">${text}</section></div>`; }
function activity() {
  const KIND = { signal: "Leader signal", order: "Dispatched", skip: "Skipped", flatten: "Flatten", cancel: "Cancel", kill: "Kill switch", account: "Connection" };
  const rows = S.events.slice(0, 15).map((e) => `<tr><td>${fmtTime(e.ts)}</td><td>${KIND[e.kind] || esc(e.kind)}</td><td>${esc(e.account) || "—"}</td><td class="mono" style="white-space:normal;text-align:left">${esc(summary(e))}</td></tr>`).join("");
  return `<section class="panel"><div class="tablewrap"><table><thead><tr><th>TIME</th><th>EVENT</th><th>CONNECTION</th><th style="text-align:left">DETAIL</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="4" class="empty">No activity yet. Send a test signal from Connections.</td></tr>'}</tbody></table></div></section>`;
}
function summary(e) {
  const d = e.data || {};
  if (e.kind === "signal") return `${d.action} ${d.contracts} ${d.symbol} @ ${d.price} → ${d.position}${d.test ? " (test)" : ""}`;
  if (e.kind === "order" || e.kind === "skip") return `${d.reason}${d.qty ? " · qty " + d.qty : ""}${d.status != null ? " · " + d.status : ""}${d.ms ? " · " + d.ms + " ms" : ""}`;
  return JSON.stringify(d);
}
function alertJson(secret) {
  return JSON.stringify({ secret, strategy: "{{strategy.order.comment}}", symbol: "{{ticker}}", action: "{{strategy.order.action}}",
    contracts: "{{strategy.order.contracts}}", position: "{{strategy.market_position}}", price: "{{strategy.order.price}}", id: "{{strategy.order.id}}" }, null, 2);
}

const TEMPLATE_OPEN = { symbol: "{{symbol}}", date: "{{time}}", data: "{{side}}", quantity: "{{qty}}", risk_percentage: 0, price: "{{price}}",
  tp: 0, percentage_tp: 0, dollar_tp: 0, sl: 0, dollar_sl: 0, percentage_sl: 0, trail: 0, trail_stop: 0, trail_trigger: 0, trail_freq: 0,
  update_tp: false, update_sl: false, breakeven: 0, token: "PASTE_YOUR_PICKMYTRADE_TOKEN", account_id: "PASTE_THE_TRADOVATE_ACCOUNT_ID" };
const TEMPLATE_CLOSE = { symbol: "{{symbol}}", date: "{{time}}", data: "close", quantity: "{{qty}}", price: "{{price}}",
  token: "PASTE_YOUR_PICKMYTRADE_TOKEN", account_id: "PASTE_THE_TRADOVATE_ACCOUNT_ID" };

function connectionForm(c) {
  const v = c || { name: "", group: "", broker_account: "", url: "https://api.pickmytrade.io/v2/add-trade-data", multiplier: 1, micros_only: false,
    template_open: TEMPLATE_OPEN, template_close: TEMPLATE_CLOSE, template_cancel: {} };
  return `<h3>${c ? "Edit connection" : "Add connection"}</h3>
    <div class="grid2"><label>Name<input id="f_name" value="${esc(v.name)}" placeholder="Lucid 50K #1"></label>
    <label>Group<input id="f_group" value="${esc(v.group)}" placeholder="Evals"></label>
    <label>Broker account (shown in the table)<input id="f_acc" value="${esc(v.broker_account)}" placeholder="LT12345"></label>
    <label>Ratio (× leader contracts)<input id="f_ratio" type="number" step="0.5" min="0.5" value="${v.multiplier}"></label>
    <label>PickMyTrade webhook URL<input id="f_url" value="${esc(v.url)}"></label>
    <label>Micros only (NQ→MNQ, ES→MES)<select id="f_micro"><option value="0">No</option><option value="1" ${v.micros_only ? "selected" : ""}>Yes</option></select></label></div>
    <p class="lead" style="margin:14px 0 6px">Paste the JSON from PickMyTrade's alert builder. Use {{side}} {{qty}} {{symbol}} {{price}} {{time}} where the values go.</p>
    <label>Open order JSON<textarea id="f_open">${esc(JSON.stringify(v.template_open, null, 2))}</textarea></label>
    <label style="margin-top:10px">Close / flatten JSON<textarea id="f_close">${esc(JSON.stringify(v.template_close, null, 2))}</textarea></label>
    <label style="margin-top:10px">Cancel orders JSON (optional)<textarea id="f_cancel" style="min-height:60px">${esc(JSON.stringify(v.template_cancel || {}, null, 2))}</textarea></label>
    <div class="row" style="margin-top:16px;justify-content:flex-end"><button class="btn" data-act="closeModal">Cancel</button>
    <button class="btn green" data-act="saveConn" data-id="${c ? esc(c.id) : ""}">Save</button></div>`;
}
function modal(html) { $("#modalBody").innerHTML = html; $("#modal").classList.add("open"); }
function closeModal() { $("#modal").classList.remove("open"); }
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });

const handlers = {
  followAll: (d) => act(() => api(`/api/followers?on=${d.on}`, "POST"), d.on === "true" ? "All followers enabled" : "All followers disabled"),
  follow: (d) => act(async () => { await api(`/api/connections/${d.id}/follow?on=${d.on}`, "POST"); if (page !== "dashboard") render(); }),
  cancelAll: () => act(() => api("/api/cancel", "POST"), "Cancel sent"),
  flattenAll: () => { if (confirm("Close every open position on every connection?")) act(() => api("/api/flatten", "POST"), "Flatten sent"); },
  flattenOne: (d) => { if (confirm("Close this connection's position?")) act(() => api(`/api/connections/${d.id}/flatten`, "POST"), "Flatten sent"); },
  add: () => modal(connectionForm(null)),
  edit: async (d) => { const cons = await api("/api/connections"); modal(connectionForm(cons.find((c) => c.id === d.id))); },
  closeModal,
  del: (d) => { if (confirm("Remove this connection?")) act(async () => { await api(`/api/connections/${d.id}`, "DELETE"); render(); }, "Removed"); },
  saveConn: async (d) => {
    let open, close, cancel;
    try { open = JSON.parse($("#f_open").value || "{}"); close = JSON.parse($("#f_close").value || "{}"); cancel = JSON.parse($("#f_cancel").value || "{}"); }
    catch (e) { toast("⚠ The JSON isn't valid: " + e.message); return; }
    const cons = await api("/api/connections");
    const old = cons.find((c) => c.id === d.id);
    const body = { name: $("#f_name").value.trim() || "Connection", group: $("#f_group").value.trim(), broker_account: $("#f_acc").value.trim(),
      url: $("#f_url").value.trim(), multiplier: Number($("#f_ratio").value) || 1, micros_only: $("#f_micro").value === "1",
      template_open: open, template_close: close, template_cancel: cancel, rules: old ? old.rules : undefined };
    act(async () => { await api(d.id ? `/api/connections/${d.id}` : "/api/connections", d.id ? "PUT" : "POST", body); closeModal(); render(); }, "Saved");
  },
  test: () => act(async () => { const r = await api("/api/test-signal", "POST"); toast(`Test signal: ${r.results.filter((x) => x.send).length} of ${r.results.length} would send`); }),
  copy: (d) => { navigator.clipboard.writeText($("#" + d.src).textContent).then(() => toast("Copied"), () => toast("Copy failed — select and copy")); },
  kill: (d) => act(async () => { await api(`/api/kill?on=${d.on}`, "POST"); S = await api("/api/state"); render(); }, d.on === "true" ? "Entries blocked" : "Entries allowed"),
  saveBlackout: () => act(() => api("/api/settings", "PUT", { news_blackout_min: Number($("#blackout").value) || 0 }), "Saved"),
  saveRules: async (d) => {
    const cons = await api("/api/connections");
    const c = cons.find((x) => x.id === d.id);
    document.querySelectorAll(`[data-rule][data-id="${CSS.escape(d.id)}"]`).forEach((el) => { c.rules[el.dataset.rule] = el.type === "number" ? Number(el.value) : el.value; });
    act(() => api(`/api/connections/${d.id}`, "PUT", c), "Rules saved");
  },
  feedback: () => { const t = $("#fb").value.trim(); if (!t) return; act(async () => { await api("/api/feedback", "POST", { text: t }); $("#fb").value = ""; }, "Thanks — saved"); },
  download: () => { const a = document.createElement("a"); a.download = "snapshot.png"; a.href = $("#snap").toDataURL("image/png"); a.click(); },
  mode: (d) => {
    if (d.live === "true" && !confirm("Go LIVE? Orders will be sent to every following connection.")) return;
    act(async () => { await api("/api/settings", "PUT", { dry_run: d.live !== "true" }); render(); }, d.live === "true" ? "LIVE" : "Test mode");
  },
  bg: () => { try { localStorage.setItem("bg", bgOn() ? "off" : "on"); } catch { /* storage blocked */ } mountBackdrop(); render(); },
  savePub: () => act(async () => { await api("/api/settings", "PUT", { public_url: $("#pub").value }); }, "Saved"),
  regen: () => { if (confirm("Make a new secret? Update the TradingView alert message afterwards.")) act(async () => { await api("/api/settings", "PUT", { regenerate_secret: true }); render(); }, "New secret"); },
};

function drawSnapshot() {
  const c = $("#snap"); if (!c || !S) return;
  const g = c.getContext("2d");
  const grd = g.createLinearGradient(0, 0, 1200, 630); grd.addColorStop(0, "#1c1c1f"); grd.addColorStop(1, "#000000");
  g.fillStyle = grd; g.fillRect(0, 0, 1200, 630);
  g.fillStyle = "#f5f5f7"; g.font = "800 44px Segoe UI, Arial"; g.fillText(S.brand, 70, 110);
  g.fillStyle = "#9a9aa2"; g.font = "600 24px Segoe UI, Arial"; g.fillText(new Date().toLocaleDateString(), 70, 155);
  const tiles = [["REALIZED P&L", (S.realized >= 0 ? "+" : "−") + "$" + Math.abs(S.realized).toFixed(2), S.realized >= 0 ? "#34d399" : "#f43f5e"],
    ["FOLLOWERS", String(S.rows.filter((r) => r.follow).length), "#f5f5f7"], ["COPIER", S.health.status, S.health.status === "HEALTHY" ? "#34d399" : "#facc15"]];
  tiles.forEach(([k, v, col], i) => {
    const x = 70 + i * 360;
    g.strokeStyle = "rgba(255,255,255,.28)"; g.lineWidth = 2; g.beginPath(); g.roundRect(x, 240, 320, 220, 22); g.stroke();
    g.fillStyle = "#9a9aa2"; g.font = "700 20px Segoe UI, Arial"; g.fillText(k, x + 30, 290);
    let fs = 52; do { g.font = `800 ${fs}px Segoe UI, Arial`; fs -= 2; } while (g.measureText(v).width > 260 && fs > 20);
    g.fillStyle = col; g.fillText(v, x + 30, 380);
  });
  g.fillStyle = "#66666e"; g.font = "500 18px Segoe UI, Arial"; g.fillText("Estimated from leader signals.", 70, 560);
}

async function render() {
  document.querySelectorAll("[data-page]").forEach((b) => b.classList.toggle("active", b.dataset.page === page && !!b.closest(".nav")));
  if (!S) return;
  const v = views[page] || views.dashboard;
  try {
    const html = await v();
    $("#main").innerHTML = html;
    if (page === "snapshot") drawSnapshot();
  } catch (e) { $("#main").innerHTML = `<div class="panel empty">${esc(e.message)}</div>`; }
}

function renderSetup() {
  const st = S.setup;
  const next = st.steps.find((s) => !s.done);
  $("#setup").style.display = st.done === st.total ? "none" : "";
  $("#setupN").textContent = String(Math.min(st.done + 1, st.total));
  $("#setupText").textContent = `Setup ${st.done}/${st.total}`;
  const where = { connection: "connections", template: "connections", signal: "connections", live: "account" };
  $("#setupList").innerHTML = `<div class="k" style="font-weight:700;margin-bottom:6px">Get set up</div>` + st.steps.map((s) =>
    `<div class="step ${s.done ? "done" : ""}" data-page="${where[s.key]}"><div class="dot">${s.done ? "✓" : ""}</div><span>${esc(s.title)}</span></div>`).join("")
    + (next ? "" : "");
}
$("#setupPill").addEventListener("click", () => $("#setup").classList.toggle("open"));
$("#signout").addEventListener("click", () => {
  if (window.pywebview?.api?.quit) { if (confirm("Close the app? The copier stops.")) window.pywebview.api.quit(); }
  else toast("Close this window to sign out.");
});

refresh().then(render);
setInterval(refresh, 3000);
