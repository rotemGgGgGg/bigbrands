// Monte Carlo Lab: configurable bootstrap of a strategy's own trades (or the current portfolio), large fan chart.
import { api } from "../api.js";
import { $, esc, fmt, signCls, skeleton, toast } from "../util.js";
import { icon } from "../icons.js";
import { state } from "../state.js";
import { fanChart } from "../charts.js";

const cfg = { strategy: null, sims: 5000, horizonYears: 1, capital: 50000, riskPct: 1, sizing: "fixed", ruinPct: 50, seed: 2026 };

export default async function montecarlo(main, [id]) {
  main.innerHTML = skeleton([60, 520]);
  const list = (await api.strategies()).filter((s) => s.hasTrades);
  cfg.strategy = id && list.some((s) => s.id === id) ? id : cfg.strategy || list.find((s) => s.id === "rdm10")?.id || list[0]?.id;
  main.innerHTML = `
  <div class="page wide">
    <div class="page-head fade-in"><div><h1>Monte Carlo</h1><p>Resamples a strategy's own trades into thousands of possible futures.</p></div></div>
    <div class="mc-layout">
      <form class="card mc-controls fade-in d1" id="f"><div class="card-head"><span class="card-title">Simulation</span></div><div class="card-body">
        <label class="field"><span>Strategy</span><select class="select" id="strategy">${list.map((s) => `<option value="${s.id}" ${s.id === cfg.strategy ? "selected" : ""}>${esc(s.name)} · ${s.status.toLowerCase()}</option>`).join("")}</select></label>
        <div class="field"><span>Simulations</span><div class="seg" id="sims">${[1000, 5000, 10000, 20000].map((n) => `<button type="button" data-v="${n}" aria-pressed="${cfg.sims === n}">${n / 1000}k</button>`).join("")}</div></div>
        <div class="field"><span>Horizon</span><div class="seg" id="hz">${[1, 2, 5].map((n) => `<button type="button" data-v="${n}" aria-pressed="${cfg.horizonYears === n}">${n} yr</button>`).join("")}</div><small id="hz-note"></small></div>
        <label class="field"><span>Starting capital ($)</span><input class="input mono" id="capital" type="number" min="1000" step="1000" value="${cfg.capital}"></label>
        <label class="field"><span>Risk per 1R (% of capital)</span><input class="input mono" id="risk" type="number" min="0.05" max="20" step="0.05" value="${cfg.riskPct}"></label>
        <div class="field"><span>Position sizing</span><div class="seg" id="sizing"><button type="button" data-v="fixed" aria-pressed="${cfg.sizing === "fixed"}">Fixed</button><button type="button" data-v="compound" aria-pressed="${cfg.sizing === "compound"}">Compounding</button></div></div>
        <label class="field"><span>Ruin threshold (% loss from start)</span><input class="input mono" id="ruin" type="number" min="1" max="100" step="1" value="${cfg.ruinPct}"></label>
        <label class="field"><span>Seed</span><input class="input mono" id="seed" type="number" value="${cfg.seed}"><small>Same seed, same result.</small></label>
        <button class="btn primary" type="submit" id="run">${icon("play", 13)} Run simulation</button>
      </div></form>
      <div class="stack" style="min-width:0">
        <div id="kpis" class="fade-in d2"></div>
        <div class="card fade-in d3"><div class="card-head"><span class="card-title" id="title">Equity paths</span><span class="card-sub" id="sub"></span></div><div class="card-body"><div id="fan"></div><div class="legend" style="margin-top:10px">
          <span><i style="background:#f5f5f5"></i>Median</span><span><i style="background:rgba(255,255,255,.35);height:6px"></i>25–75%</span><span><i style="background:rgba(255,255,255,.15);height:6px"></i>5–95%</span><span><i style="background:#e74747"></i>Ruin threshold</span><span>Right: ending distribution</span></div></div></div>
        <div class="caption" id="foot"></div>
      </div>
    </div>
  </div>`;
  const seg = (sel, key, cast = Number) => main.querySelectorAll(`${sel} button`).forEach((b) => b.addEventListener("click", () => { cfg[key] = cast(b.dataset.v); main.querySelectorAll(`${sel} button`).forEach((x) => x.setAttribute("aria-pressed", x === b)); run(); }));
  seg("#sims", "sims"); seg("#hz", "horizonYears"); seg("#sizing", "sizing", String);
  $("#strategy", main).addEventListener("change", (e) => { cfg.strategy = e.target.value; history.replaceState(null, "", `#montecarlo/${cfg.strategy}`); run(); });
  $("#f", main).addEventListener("submit", (e) => { e.preventDefault(); run(); });

  async function run() {
    cfg.capital = Math.max(+$("#capital", main).value || 50000, 100); cfg.riskPct = +$("#risk", main).value || 1; cfg.ruinPct = +$("#ruin", main).value || 50; cfg.seed = +$("#seed", main).value || 2026;
    const s = list.find((x) => x.id === cfg.strategy), horizon = Math.max(5, Math.round(s.perYear * cfg.horizonYears));
    $("#hz-note", main).textContent = `${fmt.n(horizon)} trades (${fmt.n(s.perYear, 0)} per year)`;
    state.context = `Monte Carlo Lab: ${s.name}, ${cfg.sims} sims, ${cfg.horizonYears}y, $${cfg.capital}, ${cfg.riskPct}% risk, ${cfg.sizing}.`;
    $("#run", main).disabled = true; $("#fan", main).style.opacity = 0.4;
    try {
      const mc = await api.montecarlo({ strategy: cfg.strategy, sims: cfg.sims, horizon, capital: cfg.capital, riskPct: cfg.riskPct, sizing: cfg.sizing, ruinPct: cfg.ruinPct, seed: cfg.seed, points: 80 });
      const m = mc.metrics, c = cfg.capital;
      $("#kpis", main).innerHTML = `<div class="kpis" style="--n:6">
        ${k("P(positive)", fmt.pct(m.pPositive), `after ${cfg.horizonYears} yr`)}
        ${k("Median outcome", fmt.usd(m.median - c), `${fmt.rr(m.medianR, 1)} · ${fmt.pct((100 * (m.median - c)) / c)}`, signCls(m.median - c))}
        ${k("5th percentile", fmt.usd(m.p5 - c), fmt.rr(m.p5R, 1), signCls(m.p5 - c))}
        ${k("95th percentile", fmt.usd(m.p95 - c), fmt.rr(m.p95R, 1), signCls(m.p95 - c))}
        ${k("Drawdown p95", `${fmt.n(m.dd95Pct, 1)}%`, `median ${fmt.n(m.ddMedianPct, 1)}%`)}
        ${k("Risk of ruin", fmt.pct(m.riskOfRuin, 2), `equity ≤ ${fmt.usdShort(c * (1 - cfg.ruinPct / 100))}`, m.riskOfRuin > 5 ? "neg" : "")}</div>`;
      $("#title", main).textContent = s.name; $("#sub", main).textContent = `${fmt.n(cfg.sims)} paths · ${fmt.n(horizon)} trades · ${cfg.sizing === "fixed" ? "fixed" : "compounding"} ${cfg.riskPct}% per R`;
      fanChart($("#fan", main), mc, { height: 420, start: c, ruinLevel: c * (1 - cfg.ruinPct / 100) });
      $("#foot", main).textContent = `${mc.config.method}. Sample: ${fmt.n(mc.config.sampleSize)} trades (${s.units}). Computed in ${mc.ms} ms, seed ${mc.config.seed}. Trades are drawn independently, so streaks and regime changes are not preserved.`;
    } catch (e) { toast(e.message, "err"); }
    finally { $("#run", main).disabled = false; $("#fan", main).style.opacity = 1; }
  }
  run();
}

const k = (l, v, s = "", cls = "") => `<div class="kpi"><div class="kpi-label">${esc(l)}</div><div class="kpi-value ${cls}">${v}</div><div class="kpi-sub">${s}</div></div>`;
