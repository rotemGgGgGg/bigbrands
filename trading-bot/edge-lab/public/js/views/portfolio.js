// Portfolio Lab: weight strategies, see the combined curve, drawdown, correlation, risk contribution,
// monthly distribution and a portfolio Monte Carlo. All computed on the server from the trade series.
import { api } from "../api.js";
import { $, $$, esc, fmt, signCls, skeleton, debounce } from "../util.js";
import { icon } from "../icons.js";
import { state } from "../state.js";
import { lineChart, heatmap, histChart, fanChart } from "../charts.js";

let weights = null;
const PRESETS = { "Gotobi + RDM": { gotobi: 1, rdm: 1 }, "All live": null, "Equal (all)": "all" };

export default async function portfolio(main) {
  main.innerHTML = skeleton([60, 520]);
  const list = (await api.strategies()).filter((s) => s.hasTrades);
  const names = Object.fromEntries(list.map((s) => [s.id, s.name]));
  weights = weights || { gotobi: 1, rdm: 1 };
  main.innerHTML = `
  <div class="page wide">
    <div class="page-head fade-in"><div><h1>Portfolio Lab</h1><p>Combine strategies on a daily grid. Weights are in R units per strategy.</p></div>
      <div class="actions">${Object.keys(PRESETS).map((p) => `<button class="btn sm" data-preset="${esc(p)}">${esc(p)}</button>`).join("")}</div></div>
    <div class="mc-layout">
      <div class="card mc-controls fade-in d1"><div class="card-head"><span class="card-title">Allocation</span><span class="card-sub">0 = excluded</span></div><div class="card-body"><div class="alloc" id="alloc"></div></div></div>
      <div class="stack" style="min-width:0">
        <div id="kpis" class="fade-in d2"></div>
        <div class="card fade-in d2"><div class="card-head"><span class="card-title">Combined equity</span><span class="card-sub" id="period"></span></div><div class="card-body"><div id="eq"></div><div class="label" style="margin:14px 0 4px">Drawdown</div><div id="dd"></div></div></div>
        <div class="grid g-2">
          <div class="card fade-in d3"><div class="card-head"><span class="card-title">Correlation</span><span class="card-sub">daily R</span></div><div class="card-body" style="overflow-x:auto"><div id="corr"></div></div></div>
          <div class="card fade-in d3"><div class="card-head"><span class="card-title">Risk contribution</span><span class="card-sub">share of portfolio variance</span></div><div class="card-body"><div class="bars-h" id="rc"></div></div></div>
        </div>
        <div class="grid g-2">
          <div class="card fade-in d4"><div class="card-head"><span class="card-title">Monthly returns</span><span class="card-sub">distribution, R</span></div><div class="card-body"><div id="hist"></div></div></div>
          <div class="card fade-in d4"><div class="card-head"><span class="card-title">Portfolio Monte Carlo</span><span class="card-sub">one year, daily bootstrap · $50k, 1% per R</span></div><div class="card-body"><div id="pmc"></div><div class="caption" id="pmc-k" style="margin-top:8px"></div></div></div>
        </div>
        <div class="caption" id="note"></div>
      </div>
    </div>
  </div>`;
  const paintAlloc = () => {
    $("#alloc", main).innerHTML = list.map((s) => { const w = weights[s.id] || 0; return `<div class="alloc-row ${w ? "" : "off"}"><span class="nm" title="${esc(s.name)} · ${s.status.toLowerCase()}"><i class="${s.status.toLowerCase()}"></i>${esc(s.name)}</span><input type="range" min="0" max="3" step="0.25" value="${w}" data-id="${s.id}" aria-label="Weight for ${esc(s.name)}"><span class="w">${w.toFixed(2)}</span></div>`; }).join("");
  };
  paintAlloc();
  const run = debounce(async () => {
    state.context = `Portfolio Lab weights: ${Object.entries(weights).filter(([, w]) => w > 0).map(([id, w]) => `${names[id]} ${w}`).join(", ")}.`;
    try {
      const p = await api.portfolio({ weights });
      const m = p.metrics;
      $("#kpis", main).innerHTML = `<div class="kpis" style="--n:6">${k("Total", fmt.rr(m.totalR, 1), "", signCls(m.totalR))}${k("Per year", fmt.rr(m.annualR, 1), "average", signCls(m.annualR))}${k("Sharpe", fmt.n(m.sharpe, 2), "annualised, daily")}${k("Max drawdown", `${fmt.n(m.maxDD, 1)}R`)}${k("Positive years", `${m.posYears}/${m.nYears}`)}${k("Positive months", fmt.pct(m.posMonths, 0))}</div>`;
      $("#period", main).textContent = `${fmt.date(p.period.start)} – ${fmt.date(p.period.end)} · ${fmt.n(p.period.days)} trading days`;
      lineChart($("#eq", main), { height: 240, series: [{ name: "Portfolio R", points: p.curve }], shadeFrom: "2020-01-01" });
      lineChart($("#dd", main), { height: 100, series: [{ name: "Drawdown", points: p.drawdown, color: "#a92e35", fillColor: "#e74747", fillOpacity: 0.18, endDot: false }], animate: false });
      heatmap($("#corr", main), p.correlation.ids.map((id) => names[id]), p.correlation.matrix);
      $("#rc", main).innerHTML = p.riskContribution.map((r) => `<div class="bar-h"><span title="${esc(names[r.id])}">${esc(names[r.id])}</span><span class="track"><b style="left:0;width:${Math.max(0, Math.min(100, r.pct ?? 0))}%"></b></span><span>${fmt.pct(r.pct, 0)}</span></div>`).join("");
      histChart($("#hist", main), p.monthly, { xFmt: (v) => fmt.r(v, 1) });
      const mc = p.montecarlo; fanChart($("#pmc", main), mc, { height: 220, start: 50000, xLabel: "days" });
      $("#pmc-k", main).textContent = `P(year > 0) ${fmt.pct(mc.metrics.pPositive)} · median ${fmt.usd(mc.metrics.median - 50000)} · 5th pct ${fmt.usd(mc.metrics.p5 - 50000)} · drawdown 95th ${fmt.n(mc.metrics.dd95Pct, 1)}%`;
      $("#note", main).textContent = `${p.note} Gotobi and RDM are in normalised R units (1 = their average 2012–19 trade), the others in R after costs.`;
    } catch (e) { $("#kpis", main).innerHTML = `<div class="err-box"><b>Cannot build this portfolio.</b> ${esc(e.message)}</div>`; }
  }, 220);
  $("#alloc", main).addEventListener("input", (e) => { const r = e.target.closest("input[type=range]"); if (!r) return; weights[r.dataset.id] = +r.value; r.parentElement.querySelector(".w").textContent = (+r.value).toFixed(2); r.parentElement.classList.toggle("off", !+r.value); run(); });
  $$("[data-preset]", main).forEach((b) => b.addEventListener("click", () => {
    const p = PRESETS[b.dataset.preset];
    weights = p === "all" ? Object.fromEntries(list.map((s) => [s.id, 1])) : p === null ? Object.fromEntries(list.filter((s) => s.status === "LIVE").map((s) => [s.id, 1])) : { ...p };
    paintAlloc(); run();
  }));
  run();
}

const k = (l, v, s = "", cls = "") => `<div class="kpi"><div class="kpi-label">${esc(l)}</div><div class="kpi-value ${cls}">${v}</div><div class="kpi-sub">${s}</div></div>`;
