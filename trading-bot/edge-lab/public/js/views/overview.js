// Overview: the state of the research at a glance. Every number comes from /api/overview (registry + trades + store).
import { api } from "../api.js";
import { $, esc, fmt, signCls, skeleton, emptyState } from "../util.js";
import { icon } from "../icons.js";
import { sparkline, lineChart } from "../charts.js";

export default async function overview(main) {
  main.innerHTML = skeleton([60, 90, 300]);
  const [o, best] = await Promise.all([api.overview(), null]);
  const b = o.best;
  main.innerHTML = `
  <div class="page">
    <div class="page-head fade-in"><div><h1>Overview</h1><p>Research data updated ${esc(o.updated || "—")}</p></div>
      <div class="actions"><a class="btn sm" href="#strategies">${icon("strategies", 14)} Strategies</a><a class="btn sm primary" href="#experiments/new">${icon("plus", 14)} New experiment</a></div></div>

    <div class="kpis fade-in d1" style="--n:5">
      ${kpi("Strategies tested", o.counts.total, "registry entries")}
      ${kpi("Live", o.counts.live, "passed every gate")}
      ${kpi("Watching", o.counts.watch, "promising, not proven")}
      ${kpi("Rejected", o.counts.dead, "in the graveyard")}
      ${kpi("Theories screened", o.theoriesTested ? `${(o.theoriesTested / 1e6).toFixed(2)}M` : "—", "factories, all variants")}
    </div>

    <div class="grid g-21" style="margin-top:16px">
      <div class="card fade-in d2">
        <div class="card-head"><span class="card-title">Best out-of-sample</span><span class="card-sub">${b ? esc(b.name) : ""}</span>
          ${b ? `<div class="right"><a class="btn ghost sm" href="#strategies/${b.id}">Inspect ${icon("arrowRight", 13)}</a></div>` : ""}</div>
        <div class="card-body">${b ? `
          <div class="row" style="gap:28px;margin-bottom:6px">
            ${mini("2020–26 avg", fmt.rr(b.oosAvg, 3), signCls(b.oosAvg))}${mini("t-stat", fmt.t(b.oosT))}${mini("Win rate", fmt.pct(b.winRate))}${mini("Trades / yr", fmt.n(b.perYear))}${mini("Random-twin p", esc(b.pRandom ?? "—"))}
          </div><div id="best-chart"></div>` : emptyState(icon("strategies"), "No live strategy yet", "Strategies appear here once they pass the gates.")}
        </div>
      </div>
      <div class="card fade-in d3">
        <div class="card-head"><span class="card-title">Latest activity</span><div class="right"><a class="btn ghost sm" href="#history">All</a></div></div>
        <div class="card-body" style="padding-top:6px"><div class="list">${o.activity.slice(0, 6).map(activity).join("") || `<div class="caption">No activity yet.</div>`}</div></div>
      </div>
    </div>

    <div class="grid g-21" style="margin-top:16px">
      <div class="card fade-in d3">
        <div class="card-head"><span class="card-title">Live strategies</span><span class="card-sub">avg expectancy ${fmt.rr(o.liveExpectancy, 3)}</span></div>
        <div class="card-body" style="padding-top:6px"><div class="list">${o.live.map(liveRow).join("")}</div></div>
      </div>
      <div class="card fade-in d4">
        <div class="card-head"><span class="card-title">Recent experiments</span><div class="right"><a class="btn ghost sm" href="#experiments">All</a></div></div>
        <div class="card-body" style="padding-top:6px">${o.recentExperiments.length ? `<div class="list">${o.recentExperiments.map((x) => `<a class="list-item" href="#experiments/${x.id}"><span class="li-icon">${icon("flask", 13)}</span><div class="li-main"><div class="li-title">${esc(x.name)}</div><div class="li-sub">${esc(x.baseName || "New strategy")} · ${fmt.ago(x.createdAt)}</div></div><span class="pill ${x.status}">${x.status}</span></a>`).join("")}</div>`
          : emptyState(icon("flask"), "No experiments yet", "Duplicate a strategy, change one rule, and let the agent test it.", `<a class="btn sm" href="#experiments/new">${icon("plus", 13)} New experiment</a>`)}</div>
      </div>
    </div>

    ${o.book ? `<div class="section-title fade-in d4">The book <span class="caption">${esc(o.book.name)} · ${esc(o.book.window)} · from the original research run</span></div>
    <div class="kpis fade-in d5" style="--n:6">${kpi("Sharpe", o.book.sharpe, "out-of-sample")}${kpi("CAGR", `${o.book.cagr}%`, "")}${kpi("Max drawdown", `${o.book.maxdd}%`, "")}${kpi("Positive years", o.book.pos_years, "")}${kpi("Prop payout", `${o.book.prop_pass}%`, `vs ${o.book.prop_zero}% at zero edge`)}${kpi("Theories", fmt.n(o.theoriesTested), "screened in total")}</div>` : ""}

    <div class="section-title fade-in d5">Method <span class="caption">the same four gates for every idea</span></div>
    <div class="kpis fade-in d5" style="--n:4">
      ${gate("Gate 1", "Choose on 2012–19", "Parameters are picked on the first eight years only.")}
      ${gate("Gate 2", "Judge once on 2020–26", "One look at the later years, no re-tuning after it.")}
      ${gate("Gate 3", "Beat a random twin", "Shifted clocks, shuffled days, random direction. p = share of twins that did as well.")}
      ${gate("Gate 4", "Survive Monte Carlo", "Trades resampled into thousands of years: losing-year odds and drawdown.")}
    </div>
  </div>`;
  if (b) { const s = await api.strategy(b.id); lineChart($("#best-chart", main), { height: 300, series: [{ name: "Cumulative R", points: s.curve }], shadeFrom: "2020-01-01", label: `${s.name} equity` }); }
}

const kpi = (l, v, s) => `<div class="kpi"><div class="kpi-label">${esc(l)}</div><div class="kpi-value">${typeof v === "string" ? v : esc(v)}</div><div class="kpi-sub">${esc(s)}</div></div>`;
const mini = (l, v, cls = "") => `<div><div class="label">${esc(l)}</div><div class="mono ${cls}" style="font-size:17px;margin-top:2px">${v}</div></div>`;
const gate = (k, t, d) => `<div class="kpi"><div class="kpi-label mono">${k}</div><div style="font-size:13.5px;margin-top:6px;font-weight:500">${t}</div><div class="caption" style="margin-top:4px;white-space:normal">${d}</div></div>`;

function liveRow(s) {
  return `<a class="list-item" href="#strategies/${s.id}"><div class="li-main"><div class="li-title">${esc(s.name)}</div><div class="li-sub">${esc(s.market)} · ${fmt.n(s.perYear)}/yr · win ${fmt.pct(s.winRate)}</div></div>${sparkline(s.spark, 110, 28)}<div class="li-right"><div class="${signCls(s.oosAvg)}">${fmt.rr(s.oosAvg, 3)}</div><div class="caption">2020–26</div></div></a>`;
}

function activity(a) {
  const ic = { commit: "git", experiment: "flask", agent: "cpu", conversation: "chat", settings: "settings", data: "database" }[a.type] || "history";
  const href = a.experimentId ? `#experiments/${a.experimentId}` : a.conversationId ? `#research/${a.conversationId}` : "#history";
  return `<a class="list-item" href="${href}"><span class="li-icon">${icon(ic, 13)}</span><div class="li-main"><div class="li-title">${esc(a.title)}</div><div class="li-sub">${a.type === "commit" ? `commit ${esc(a.id)} · ` : ""}${fmt.ago(a.at)}</div></div></a>`;
}
