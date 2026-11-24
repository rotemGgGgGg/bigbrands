// Strategy explorer (sortable, filterable, comparable) and the strategy inspector.
import { api } from "../api.js";
import { $, $$, esc, fmt, signCls, skeleton, emptyState, debounce } from "../util.js";
import { icon } from "../icons.js";
import { state } from "../state.js";
import { sparkline, lineChart, barChart, fanChart } from "../charts.js";

const COLS = [
  ["name", "Strategy", "l"], ["status", "Status", "l"], ["n", "Trades"], ["winRate", "Win %"], ["expectancy", "Avg R"], ["payoff", "Payoff"],
  ["t", "t-stat"], ["maxDD", "Max DD"], ["isAvg", "2012–19"], ["oosAvg", "2020–26"], ["totalR", "Total R"], ["pRandom", "p random"],
];
const ORDER = { LIVE: 0, WATCH: 1, DEAD: 2 };
const SHADES = ["#f5f5f5", "#e74747", "#9a9a9a", "#5e5e5e"];
let ui = { q: "", status: "ALL", sort: "status", dir: 1, picked: new Set() };

export default async function strategies(main, [id]) {
  if (id) return inspector(main, id);
  main.innerHTML = skeleton([60, 48, 420]);
  const all = await api.strategies();
  main.innerHTML = `
  <div class="page wide">
    <div class="page-head fade-in"><div><h1>Strategies</h1><p>${all.length} strategies in the registry · ${all.filter((s) => s.hasTrades).length} with full trade data</p></div>
      <div class="actions"><a class="btn sm" href="#montecarlo">${icon("dice", 14)} Monte Carlo</a><a class="btn sm primary" href="#experiments/new">${icon("plus", 14)} New experiment</a></div></div>
    <div class="row fade-in d1" style="margin-bottom:12px;gap:10px">
      <div class="search" style="width:260px"><label class="sr-only" for="sq">Search strategies</label>${icon("search", 14)}<input id="sq" class="input" placeholder="Search name, market, family…  /" value="${esc(ui.q)}"></div>
      <div class="seg" role="group" aria-label="Status filter">${["ALL", "LIVE", "WATCH", "DEAD"].map((s) => `<button data-s="${s}" aria-pressed="${ui.status === s}">${s === "ALL" ? "All" : s[0] + s.slice(1).toLowerCase()}</button>`).join("")}</div>
      <span class="caption" style="margin-left:auto">Select rows to compare</span>
    </div>
    <div class="table-wrap fade-in d2"><table class="data"><thead><tr><th class="chk"></th>${COLS.map(([k, l, a]) => `<th class="sortable ${a || ""}" data-k="${k}">${l}<span class="arrow">${ui.dir > 0 ? "↑" : "↓"}</span></th>`).join("")}<th>Equity</th></tr></thead><tbody id="rows"></tbody></table></div>
    <div id="compare"></div>
  </div>`;
  const paint = () => {
    const q = ui.q.toLowerCase();
    let rows = all.filter((s) => (ui.status === "ALL" || s.status === ui.status) && (!q || `${s.name} ${s.market} ${s.family} ${s.rule}`.toLowerCase().includes(q)));
    rows.sort((a, b) => {
      const k = ui.sort; let va = k === "status" ? ORDER[a.status] : a[k], vb = k === "status" ? ORDER[b.status] : b[k];
      if (k === "pRandom") { va = parseP(va); vb = parseP(vb); }
      if (va == null && vb == null) return 0; if (va == null) return 1; if (vb == null) return -1;
      return (typeof va === "string" ? va.localeCompare(vb) : va - vb) * ui.dir || (b.oosAvg ?? -9) - (a.oosAvg ?? -9);
    });
    $$("th.sortable", main).forEach((th) => { th.classList.toggle("sorted", th.dataset.k === ui.sort); th.querySelector(".arrow").textContent = ui.dir > 0 ? "↑" : "↓"; });
    $("#rows", main).innerHTML = rows.map(row).join("") || `<tr><td colspan="${COLS.length + 2}">${emptyState(icon("search"), "No strategies match", "Clear the search or the status filter.")}</td></tr>`;
    paintCompare(all);
  };
  $("#sq", main).addEventListener("input", debounce((e) => { ui.q = e.target.value; paint(); }, 120));
  $$(".seg button", main).forEach((b) => b.addEventListener("click", () => { ui.status = b.dataset.s; $$(".seg button", main).forEach((x) => x.setAttribute("aria-pressed", x === b)); paint(); }));
  $$("th.sortable", main).forEach((th) => th.addEventListener("click", () => { if (ui.sort === th.dataset.k) ui.dir *= -1; else { ui.sort = th.dataset.k; ui.dir = th.dataset.k === "name" || th.dataset.k === "status" ? 1 : -1; } paint(); }));
  $("#rows", main).addEventListener("click", (e) => {
    const cb = e.target.closest("input.checkbox");
    if (cb) { const id = cb.dataset.id; cb.checked ? ui.picked.add(id) : ui.picked.delete(id); if (ui.picked.size > 4) { ui.picked.delete(id); cb.checked = false; } paintCompare(all); return; }
    const tr = e.target.closest("tr[data-id]"); if (tr) location.hash = `#strategies/${tr.dataset.id}`;
  });
  $("#rows", main).addEventListener("keydown", (e) => { const tr = e.target.closest("tr[data-id]"); if (tr && e.key === "Enter") location.hash = `#strategies/${tr.dataset.id}`; });
  const slash = (e) => { if (e.key === "/" && !e.target.closest("input,textarea")) { e.preventDefault(); $("#sq", main)?.focus(); } };
  document.addEventListener("keydown", slash);
  state.context = "Strategy explorer: list of all strategies with metrics.";
  paint();
  return () => document.removeEventListener("keydown", slash);
}

const parseP = (p) => (p == null || p === "—" || p === "n.s." ? null : parseFloat(String(p).replace("<", "")));

function row(s) {
  const c = (v, d = 3) => `<span class="${signCls(v)}">${fmt.r(v, d)}</span>`;
  const has = s.hasTrades;
  return `<tr class="clickable" data-id="${s.id}" tabindex="0">
    <td class="chk" onclick="event.stopPropagation()">${has ? `<input type="checkbox" class="checkbox" data-id="${s.id}" ${ui.picked.has(s.id) ? "checked" : ""} aria-label="Compare ${esc(s.name)}">` : ""}</td>
    <td class="name l">${esc(s.name)}<small>${esc(s.market)} · ${esc(s.family)}</small></td>
    <td class="l"><span class="pill ${s.status.toLowerCase()}">${s.status.toLowerCase()}</span></td>
    <td>${has ? fmt.n(s.n) : "—"}</td><td>${has ? fmt.pct(s.winRate) : "—"}</td><td>${has ? c(s.expectancy) : "—"}</td><td>${has ? fmt.n(s.payoff, 2) : "—"}</td>
    <td>${has ? fmt.t(s.t) : "—"}</td><td>${has ? fmt.n(s.maxDD, 1) : "—"}</td><td>${has ? c(s.isAvg) : "—"}</td><td>${has ? c(s.oosAvg) : "—"}</td>
    <td>${has ? c(s.totalR, 1) : "—"}</td><td>${esc(s.pRandom ?? "—")}</td><td>${has ? sparkline(s.spark, 96, 24) : ""}</td></tr>`;
}

async function paintCompare(all) {
  const host = $("#compare"); if (!host) return;
  if (ui.picked.size < 2) { host.innerHTML = ui.picked.size ? `<div class="compare-bar"><span class="caption">Pick one more strategy to compare (up to 4).</span></div>` : ""; return; }
  const ids = [...ui.picked], full = await Promise.all(ids.map((id) => api.strategy(id)));
  host.innerHTML = `<div class="section-title">Comparison <span class="caption">cumulative R, same scale</span><button class="btn ghost sm" id="clear-cmp" style="margin-left:auto">Clear</button></div>
    <div class="grid g-21"><div class="card"><div class="card-body"><div class="legend" style="margin-bottom:8px">${full.map((s, i) => `<span><i style="background:${SHADES[i]}"></i>${esc(s.name)}</span>`).join("")}</div><div id="cmp-chart"></div></div></div>
    <div class="card"><div class="card-body"><table class="data" style="min-width:0"><thead><tr><th class="l">Metric</th>${full.map((s, i) => `<th><span style="color:${SHADES[i]}">●</span></th>`).join("")}</tr></thead><tbody>
      ${[["Trades / yr", (s) => fmt.n(s.perYear)], ["Win %", (s) => fmt.pct(s.winRate)], ["Avg R", (s) => fmt.r(s.expectancy, 3)], ["2020–26", (s) => fmt.r(s.oosAvg, 3)], ["t-stat", (s) => fmt.t(s.t)], ["Max DD", (s) => fmt.n(s.maxDD, 1)], ["Years +", (s) => `${s.posYears}/${s.nYears}`]]
        .map(([l, f]) => `<tr><td class="l" style="font-family:var(--sans)">${l}</td>${full.map((s) => `<td>${f(s)}</td>`).join("")}</tr>`).join("")}</tbody></table></div></div></div>`;
  lineChart($("#cmp-chart", host), { height: 260, area: false, series: full.map((s, i) => ({ name: s.name, points: s.curve, color: SHADES[i], width: i ? 1.2 : 1.6 })), shadeFrom: "2020-01-01" });
  $("#clear-cmp").onclick = () => { ui.picked.clear(); $$("#rows input.checkbox").forEach((c) => (c.checked = false)); paintCompare(all); };
}

async function inspector(main, id) {
  main.innerHTML = skeleton([40, 120, 320, 220]);
  const s = await api.strategy(id);
  state.context = `Viewing strategy "${s.name}" (id ${s.id}, ${s.status}, ${s.market}).`;
  const has = s.hasTrades;
  main.innerHTML = `
  <div class="page wide">
    <a class="crumb fade-in" href="#strategies">${icon("arrowLeft", 13)} Strategies</a>
    <div class="page-head fade-in"><div><div class="row" style="gap:10px"><h1>${esc(s.name)}</h1><span class="pill ${s.status.toLowerCase()}">${s.status.toLowerCase()}</span></div>
      <p>${esc(s.market)} · ${esc(s.family)}${has ? ` · ${fmt.n(s.n)} trades, ${esc(s.first.slice(0, 4))}–${esc(s.last.slice(0, 4))} · units: ${esc(s.units)}` : ""}</p></div>
      <div class="actions"><button class="btn sm" id="ask">${icon("chat", 14)} Ask the agent</button>${has ? `<a class="btn sm" href="#montecarlo/${s.id}">${icon("dice", 14)} Monte Carlo</a>` : ""}<a class="btn sm primary" href="#experiments/new?base=${s.id}">${icon("copy", 14)} New variation</a></div></div>
    ${has ? `<div class="kpis fade-in d1" style="--n:6">
      ${k("Expectancy", fmt.rr(s.expectancy, 3), `t ${fmt.t(s.t)}`, signCls(s.expectancy))}${k("Win rate", fmt.pct(s.winRate), `payoff ${fmt.n(s.payoff, 2)}`)}
      ${k("2012–19", fmt.rr(s.isAvg, 3), `t ${fmt.t(s.isT)} · ${fmt.n(s.isN)} trades`, signCls(s.isAvg))}${k("2020–26", fmt.rr(s.oosAvg, 3), `t ${fmt.t(s.oosT)} · ${fmt.n(s.oosN)} trades`, signCls(s.oosAvg))}
      ${k("Max drawdown", `${fmt.n(s.maxDD, 1)}R`, `worst streak ${s.worstStreak} losses`)}${k("Random-twin p", esc(s.pRandom ?? "—"), `${s.posYears}/${s.nYears} positive years`)}</div>` : ""}
    <div class="grid g-12" style="margin-top:16px">
      <div class="card fade-in d2"><div class="card-head"><span class="card-title">Rules</span></div><div class="card-body">
        <div class="rule-label">Description</div><p class="rule-block">${esc(s.rule)}</p>
        ${s.entry ? `<div class="rule-label">Entry</div><p class="rule-block">${esc(s.entry)}</p>` : ""}
        ${s.exit ? `<div class="rule-label">Exit</div><p class="rule-block">${esc(s.exit)}</p>` : ""}
        ${s.params ? `<div class="rule-label">Parameters</div><div class="params">${Object.entries(s.params).map(([a, b]) => `<span class="param">${esc(a)} <b>${esc(b)}</b></span>`).join("")}</div>` : ""}
        <div class="rule-label">Research notes</div><p class="rule-block muted">${esc(s.note)}</p></div></div>
      <div class="card fade-in d2">${has ? `<div class="card-head"><span class="card-title">Equity</span><span class="card-sub">cumulative R · shaded: out-of-sample</span></div><div class="card-body"><div id="eq"></div><div class="label" style="margin:14px 0 4px">Drawdown</div><div id="dd"></div></div>`
        : `<div class="card-body">${emptyState(icon("database"), "No trade series stored", "This strategy was rejected from summary statistics only. Its verdict and reason are on the left.")}</div>`}</div>
    </div>
    ${has ? `<div class="grid g-21" style="margin-top:16px">
      <div class="card fade-in d3"><div class="card-head"><span class="card-title">By year</span><span class="card-sub">R per calendar year</span></div><div class="card-body"><div id="yr"></div></div></div>
      <div class="card fade-in d3"><div class="card-head"><span class="card-title">Trade statistics</span></div><div class="card-body"><dl class="kv">
        ${[["Trades", fmt.n(s.n)], ["Per year", fmt.n(s.perYear, 1)], ["Average win", fmt.rr(s.avgWin, 2)], ["Average loss", fmt.rr(s.avgLoss, 2)], ["Best trade", fmt.rr(s.best, 2)], ["Worst trade", fmt.rr(s.worst, 2)], ["Total", fmt.rr(s.totalR, 1)], ["Longest losing streak", s.worstStreak], ["Target R:R", s.rr ? `1:${s.rr}` : "—"]].map(([a, b]) => `<dt>${a}</dt><dd>${b}</dd>`).join("")}
      </dl></div></div></div>
      <div class="card fade-in d4" style="margin-top:16px"><div class="card-head"><span class="card-title">Monte Carlo · one year</span><span class="card-sub" id="mc-sub">5,000 bootstrap years of its own trades · $50k, 1% risk per R</span>
        <div class="right"><a class="btn ghost sm" href="#montecarlo/${s.id}">Open lab ${icon("arrowRight", 13)}</a></div></div>
        <div class="card-body"><div id="mc-kpis"></div><div id="mc" style="margin-top:12px"></div></div></div>` : ""}
    <div id="sp-extra"></div>
  </div>`;
  $("#ask", main).onclick = () => import("../app.js").then((m) => m.openPanel({ text: `Give me a short research brief on ${s.name} (id ${s.id}): what drives it, its weakest point, and one test worth running next.` }));
  if (!has) return;
  lineChart($("#eq", main), { height: 230, series: [{ name: "Cumulative R", points: s.curve }], shadeFrom: "2020-01-01" });
  lineChart($("#dd", main), { height: 110, series: [{ name: "Drawdown", points: s.drawdown, color: "#a92e35", fillColor: "#e74747", fillOpacity: 0.18, endDot: false }], zero: true, animate: false });
  barChart($("#yr", main), Object.entries(s.years).map(([y, v]) => ({ label: `'${y.slice(2)}`, value: v, sub: s.yearsN[y] })));
  const capital = 50000;
  api.montecarlo({ strategy: s.id, sims: 5000, capital, riskPct: 1 }).then((mc) => {
    const m = mc.metrics;
    $("#mc-kpis", main).innerHTML = `<div class="kpis" style="--n:5">${k("P(year > 0)", fmt.pct(m.pPositive))}${k("Median year", fmt.usd(m.median - capital), fmt.rr(m.medianR, 1))}${k("5th percentile", fmt.usd(m.p5 - capital), fmt.rr(m.p5R, 1), signCls(m.p5 - capital))}${k("95th percentile", fmt.usd(m.p95 - capital), fmt.rr(m.p95R, 1))}${k("Drawdown, 95th", `${fmt.n(m.dd95Pct, 1)}%`, `median ${fmt.n(m.ddMedianPct, 1)}%`)}</div>`;
    fanChart($("#mc", main), mc, { height: 300, start: capital, ruinLevel: capital * 0.5 });
  }).catch((e) => { $("#mc-kpis", main).innerHTML = `<div class="err-box">${esc(e.message)}</div>`; });
  if (s.id === "sp" || s.id === "sp_B") spSection(main, s.id === "sp" ? "A" : "B");
}

async function spSection(main, key) {
  const sp = await api.sp(); const d = sp?.[key]; if (!d) return;
  const bars = (title, arr, lab) => `<div class="card"><div class="card-head"><span class="card-title">${title}</span></div><div class="card-body"><div class="bars-h">${arr.map((x) => {
    const lim = 0.2, v = Math.max(-lim, Math.min(lim, x.R)), w = (Math.abs(v) / lim) * 50;
    return `<div class="bar-h"><span>${esc(lab(x.k))} <span class="caption">n ${x.n}</span></span><span class="track"><i></i><b class="${x.R < 0 ? "neg" : ""}" style="left:${x.R >= 0 ? 50 : 50 - w}%;width:${Math.max(w, 0.6)}%"></b></span><span class="${signCls(x.R)}">${fmt.r(x.R, 3)}</span></div>`;
  }).join("")}</div></div></div>`;
  $("#sp-extra", main).innerHTML = `<div class="section-title">SP Model breakdown <span class="caption">${esc(d.label)} · from the original Edge Lab SP section</span></div>
    <div class="grid g-3">${bars("By scenario", d.scen, (x) => `S${x}`)}${bars("By side", d.side, (x) => x.toLowerCase())}${bars("By entry hour (NY)", d.hour.filter((x) => x.n >= 30), (x) => `${x}:00`)}</div>
    <div class="section-title">Attempts to fix it</div>
    <div class="table-wrap"><table class="data" style="min-width:720px"><thead><tr><th class="l">Variant</th><th>Trades/yr</th><th>Win %</th><th>R:R</th><th>2012–19</th><th>2020–26</th><th class="l">Note</th></tr></thead><tbody>
    ${sp.variants.map((v) => `<tr><td class="name l">${esc(v.name)}</td><td>${v.per_yr}</td><td>${v.win}</td><td>${v.rr}</td><td class="${signCls(v.is_R)}">${fmt.r(v.is_R, 3)}</td><td class="${signCls(v.oos_R)}">${fmt.r(v.oos_R, 3)}</td><td class="l muted" style="font-family:var(--sans)">${esc(v.note)}</td></tr>`).join("")}</tbody></table></div>`;
}

const k = (l, v, s = "", cls = "") => `<div class="kpi"><div class="kpi-label">${esc(l)}</div><div class="kpi-value ${cls}">${v}</div><div class="kpi-sub">${s}</div></div>`;
