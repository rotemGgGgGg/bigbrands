"use strict";
/* Performance page: 16 years of backtested results (static/perf.json), stock-style chart with range buttons.
   Loaded after app.js; uses its globals ($, esc, views, render, page). No external libraries. */

const PERF = { data: null, strat: "all", range: "1Y", risk: 1, acct: 10000, hover: null };
const PERF_STRATS = [["all", "Portfolio"], ["gapfb", "GapFB"], ["prefade", "Pre-Fade"], ["opex", "Opex"]];
const PERF_RANGES = ["1M", "3M", "YTD", "1Y", "2Y", "5Y", "ALL"];
try { const s = JSON.parse(localStorage.getItem("perf") || "{}"); Object.assign(PERF, { risk: s.risk || 1, acct: s.acct || 10000 }); } catch { /* ignore */ }

async function perfLoad() {
  if (!PERF.data) PERF.data = await (await fetch("/static/perf.json", { cache: "no-cache" })).json();
  return PERF.data;
}

function perfSeries() {
  const rows = PERF.data.rows, col = { gapfb: 1, prefade: 2, opex: 3 }[PERF.strat];
  const last = new Date(rows[rows.length - 1][0] + "T00:00:00");
  const back = { "1M": 31, "3M": 92, "1Y": 366, "2Y": 731, "5Y": 1827 }[PERF.range];
  let start = new Date(rows[0][0] + "T00:00:00");
  if (PERF.range === "YTD") start = new Date(last.getFullYear(), 0, 1);
  else if (back) start = new Date(last - back * 864e5);
  const sel = rows.filter((r) => new Date(r[0] + "T00:00:00") >= start);
  const trades = [];
  let cum = 0;
  const pts = sel.map((r) => {
    const vals = col ? [r[col]] : [r[1], r[2], r[3]];
    vals.forEach((v) => { if (v !== 0) trades.push(v); });
    cum += vals.reduce((a, b) => a + b, 0);
    return { d: r[0], R: cum };
  });
  return { pts, trades, start: sel[0]?.[0], end: sel[sel.length - 1]?.[0] };
}

function perfStats(s) {
  const t = s.trades, w = t.filter((x) => x > 0), l = t.filter((x) => x <= 0);
  let peak = 0, dd = 0;
  s.pts.forEach((p) => { peak = Math.max(peak, p.R); dd = Math.max(dd, peak - p.R); });
  const yrs = {};
  let prev = 0;
  s.pts.forEach((p) => { const y = p.d.slice(0, 4); yrs[y] = (yrs[y] || 0) + (p.R - prev); prev = p.R; });
  const per = {};
  const rows = PERF.data.rows, col = { gapfb: 1, prefade: 2, opex: 3 }[PERF.strat];
  rows.filter((r) => r[0] >= s.start && r[0] <= s.end).forEach((r) => {
    const y = r[0].slice(0, 4), vals = (col ? [r[col]] : [r[1], r[2], r[3]]).filter((v) => v !== 0);
    per[y] = per[y] || { n: 0, w: 0 };
    per[y].n += vals.length; per[y].w += vals.filter((v) => v > 0).length;
  });
  return {
    n: t.length, win: t.length ? (100 * w.length) / t.length : 0,
    rr: w.length && l.length ? (w.reduce((a, b) => a + b, 0) / w.length) / -(l.reduce((a, b) => a + b, 0) / l.length) : 0,
    total: s.pts.length ? s.pts[s.pts.length - 1].R : 0, dd, years: yrs, per,
  };
}

const pct = (R) => R * PERF.risk;                         // simple % of the account at `risk` % per R
const usd = (R) => (R * PERF.risk / 100) * PERF.acct;
const sgn = (v, d = 1) => (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(d);

views.performance = async () => {
  await perfLoad();
  const s = perfSeries(), st = perfStats(s), up = st.total >= 0;
  const segS = PERF_STRATS.map(([k, l]) => `<button class="${PERF.strat === k ? "on" : ""}" data-act="perfStrat" data-k="${k}">${l}</button>`).join("");
  const segR = PERF_RANGES.map((r) => `<button class="${PERF.range === r ? "on" : ""}" data-act="perfRange" data-k="${r}">${r}</button>`).join("");
  const years = Object.entries(st.years).map(([y, R]) => {
    const p = st.per[y] || { n: 0, w: 0 }, w = Math.min(100, Math.abs(pct(R)) * 1.5);
    return `<tr><td><b>${y}</b></td><td class="${R >= 0 ? "pos" : "neg"}">${sgn(R)}R</td><td class="${R >= 0 ? "pos" : "neg"}">${sgn(pct(R))}%</td>
      <td>${R >= 0 ? "+" : "−"}$${Math.abs(usd(R)).toLocaleString(undefined, { maximumFractionDigits: 0 })}</td><td>${p.n}</td>
      <td>${p.n ? Math.round((100 * p.w) / p.n) : 0}%</td><td><div class="pbar"><i class="${R >= 0 ? "up" : "dn"}" style="width:${w}%"></i></div></td></tr>`;
  }).reverse().join("");
  return `<div class="page perf">
  <section class="panel perf-head">
    <div class="perf-title">
      <div class="k">NQ OPENING-EDGE · ${esc(PERF_STRATS.find(([k]) => k === PERF.strat)[1].toUpperCase())}</div>
      <div class="big ${up ? "pos" : "neg"}">${sgn(pct(st.total))}%</div>
      <div class="sub"><span class="${up ? "pos" : "neg"}">${up ? "+" : "−"}$${Math.abs(usd(st.total)).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        · ${sgn(st.total)}R · ${esc(s.start)} → ${esc(s.end)}</div>
    </div>
    <div class="perf-ctrl">
      <div class="seg">${segS}</div>
      <div class="perf-inputs">
        <label>Risk / trade<select id="perfRisk">${[0.5, 1, 2].map((r) => `<option value="${r}" ${PERF.risk === r ? "selected" : ""}>${r}%</option>`).join("")}</select></label>
        <label>Account $<input id="perfAcct" type="number" min="100" step="100" value="${PERF.acct}"></label>
      </div>
    </div>
  </section>
  <section class="panel perf-chart">
    <div class="chart-wrap"><canvas id="perfCanvas"></canvas><div class="perf-tip" id="perfTip"></div></div>
    <div class="seg ranges">${segR}</div>
  </section>
  <section class="perf-stats">
    ${[["Trades", st.n], ["Win rate", st.win.toFixed(0) + "%"], ["Risk : reward", "1 : " + st.rr.toFixed(2)],
       ["Max drawdown", "−" + pct(st.dd).toFixed(1) + "%"], ["Per year", sgn(pct(st.total) / Math.max(1, (new Date(s.end) - new Date(s.start)) / 3.156e10)) + "%"],
       ["Years +", Object.values(st.years).filter((v) => v > 0).length + " / " + Object.keys(st.years).length]]
      .map(([k, v]) => `<div class="panel stat-tile"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("")}
  </section>
  <section class="panel"><div class="tablewrap"><table>
    <thead><tr><th>YEAR</th><th>R</th><th>RETURN</th><th>P&amp;L</th><th>TRADES</th><th>WIN</th><th></th></tr></thead>
    <tbody>${years}</tbody></table></div></section>
  <div class="note">${esc(PERF.data.source)} Simple (non-compounded) returns at ${PERF.risk}% risk per trade. Backtest — not a promise of future results.</div>
</div>`;
};

function drawPerf() {
  const cv = $("#perfCanvas"); if (!cv || !PERF.data) return;
  const s = perfSeries(), pts = s.pts; if (!pts.length) return;
  const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
  cv.width = W * dpr; cv.height = H * dpr;
  const g = cv.getContext("2d"); g.scale(dpr, dpr);
  const ys = pts.map((p) => pct(p.R)), lo = Math.min(0, ...ys), hi = Math.max(0, ...ys), pad = (hi - lo) * 0.08 || 1;
  const L = 8, Rr = 58, T = 14, B = 26, x = (i) => L + (i / Math.max(1, pts.length - 1)) * (W - L - Rr), y = (v) => T + (1 - (v - lo + pad) / (hi - lo + 2 * pad)) * (H - T - B);
  const up = ys[ys.length - 1] >= 0, col = up ? "#34d399" : "#f43f5e";
  g.font = "600 11px Segoe UI, system-ui, sans-serif"; g.fillStyle = "#66666e"; g.strokeStyle = "rgba(255,255,255,.07)"; g.lineWidth = 1;
  const span = hi - lo + 2 * pad, raw = span / 4, mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((v) => v >= raw) || 10 * mag;
  for (let v = Math.ceil((lo - pad) / step) * step; v <= hi + pad; v += step) {
    const yy = y(v); g.beginPath(); g.moveTo(L, yy); g.lineTo(W - Rr, yy); g.stroke();
    g.fillText((v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(step < 1 ? 1 : 0) + "%", W - Rr + 8, yy + 4);
  }
  g.setLineDash([3, 4]); g.strokeStyle = "rgba(255,255,255,.25)"; g.beginPath(); g.moveTo(L, y(0)); g.lineTo(W - Rr, y(0)); g.stroke(); g.setLineDash([]);
  const nx = Math.max(2, Math.min(6, Math.floor((W - L - Rr) / 95), pts.length)); g.fillStyle = "#66666e";
  for (let k = 0; k < nx; k++) { const i = Math.round((k / Math.max(1, nx - 1)) * (pts.length - 1)); const lab = pts[i].d.slice(0, PERF.range === "1M" || PERF.range === "3M" ? 10 : 7);
    g.fillText(lab, Math.min(Math.max(L, x(i) - 24), W - Rr - 60), H - 8); }
  const grad = g.createLinearGradient(0, T, 0, H - B); grad.addColorStop(0, up ? "rgba(52,211,153,.28)" : "rgba(244,63,94,.28)"); grad.addColorStop(1, "rgba(0,0,0,0)");
  g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(x(i), y(ys[i])) : g.moveTo(x(i), y(ys[i])))); g.lineTo(x(pts.length - 1), H - B); g.lineTo(x(0), H - B); g.closePath();
  g.fillStyle = grad; g.fill();
  g.beginPath(); pts.forEach((p, i) => (i ? g.lineTo(x(i), y(ys[i])) : g.moveTo(x(i), y(ys[i])))); g.strokeStyle = col; g.lineWidth = 2; g.lineJoin = "round"; g.stroke();
  const tip = $("#perfTip");
  if (PERF.hover != null) {
    const i = PERF.hover, xx = x(i), yy = y(ys[i]);
    g.strokeStyle = "rgba(255,255,255,.35)"; g.beginPath(); g.moveTo(xx, T); g.lineTo(xx, H - B); g.stroke();
    g.fillStyle = col; g.beginPath(); g.arc(xx, yy, 4.5, 0, 7); g.fill(); g.strokeStyle = "#000"; g.lineWidth = 2; g.stroke();
    tip.style.display = "block"; tip.style.left = Math.min(Math.max(0, xx - 70), W - 150) + "px";
    tip.innerHTML = `<b>${esc(pts[i].d)}</b><br><span class="${ys[i] >= 0 ? "pos" : "neg"}">${sgn(ys[i])}%</span> · ${ys[i] >= 0 ? "+" : "−"}$${Math.abs(usd(pts[i].R)).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  } else tip.style.display = "none";
  const pick = (ev) => {
    const r = cv.getBoundingClientRect(), cx = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
    PERF.hover = Math.max(0, Math.min(pts.length - 1, Math.round(((cx - L) / (W - L - Rr)) * (pts.length - 1)))); drawPerf();
  };
  cv.onmousemove = pick; cv.ontouchstart = pick; cv.ontouchmove = (e) => { e.preventDefault(); pick(e); };
  cv.onmouseleave = () => { PERF.hover = null; drawPerf(); };
}

function perfSave() { try { localStorage.setItem("perf", JSON.stringify({ risk: PERF.risk, acct: PERF.acct })); } catch { /* ignore */ } }
handlers.perfStrat = (d) => { PERF.strat = d.k; PERF.hover = null; render(); };
handlers.perfRange = (d) => { PERF.range = d.k; PERF.hover = null; render(); };
document.addEventListener("change", (e) => {
  if (e.target.id === "perfRisk") { PERF.risk = Number(e.target.value); perfSave(); render(); }
  if (e.target.id === "perfAcct") { PERF.acct = Math.max(100, Number(e.target.value) || 10000); perfSave(); render(); }
});
window.addEventListener("resize", () => { if (page === "performance") drawPerf(); });
