// Portfolio engine: combines strategies by weight on a daily grid (sum of each strategy's R per calendar day),
// then measures the combined curve, drawdown, correlation, risk contribution, return distribution and a
// daily-bootstrap Monte Carlo. Weights are in R units: weight 1 = one unit of that strategy's R.
import { mean, std, corr, maxDrawdown, cumsum, downsample, histogram } from "./stats.mjs";
import { simulate } from "./montecarlo.mjs";

export function portfolio(data, weights, opts = {}) {
  const ids = Object.keys(weights).filter((id) => +weights[id] > 0 && data.series(id));
  if (!ids.length) throw new Error("Choose at least one strategy with trade data and a weight above 0.");
  const daily = {}, first = [], last = [];
  for (const id of ids) {
    const s = data.series(id), m = new Map();
    s.t.forEach((t, i) => { const d = t.slice(0, 10); m.set(d, (m.get(d) || 0) + s.r[i]); });
    daily[id] = m; first.push(s.t[0].slice(0, 10)); last.push(s.t[s.t.length - 1].slice(0, 10));
  }
  // Overlap period only, so no strategy contributes zeros for years it was not tested.
  const start = first.sort().at(-1), end = last.sort()[0];
  const days = [...new Set(ids.flatMap((id) => [...daily[id].keys()]))].filter((d) => d >= start && d <= end).sort();
  if (days.length < 20) throw new Error("The selected strategies overlap on fewer than 20 trading days.");
  const mat = ids.map((id) => days.map((d) => daily[id].get(d) || 0));
  const w = ids.map((id) => +weights[id]);
  const combo = days.map((_, j) => ids.reduce((acc, _, i) => acc + w[i] * mat[i][j], 0));

  const curve = cumsum(combo); let peak = 0; const dd = curve.map((v) => { peak = Math.max(peak, v); return v - peak; });
  const years = {}; days.forEach((d, j) => { const y = d.slice(0, 4); years[y] = (years[y] || 0) + combo[j]; });
  const months = {}; days.forEach((d, j) => { const m = d.slice(0, 7); months[m] = (months[m] || 0) + combo[j]; });

  // Risk contribution: RC_i = w_i (Σw)_i / wᵀΣw, Σ = daily covariance.
  const means = mat.map(mean), cov = mat.map((a, i) => mat.map((b, k) => covar(a, b, means[i], means[k])));
  const sw = cov.map((row) => row.reduce((acc, c, k) => acc + c * w[k], 0)), tot = w.reduce((acc, wi, i) => acc + wi * sw[i], 0);
  const spanYears = Math.max((Date.parse(end) - Date.parse(start)) / 3.15576e10, 0.1), perYear = days.length / spanYears;
  const sd = std(combo);
  const idx = downsample(days.map((_, i) => i), 500);

  return {
    ids, weights: Object.fromEntries(ids.map((id, i) => [id, w[i]])), period: { start, end, days: days.length },
    metrics: {
      totalR: curve.at(-1), annualR: mean(combo) * perYear, sharpe: sd > 0 ? (mean(combo) / sd) * Math.sqrt(perYear) : null,
      maxDD: maxDrawdown(curve), posYears: Object.values(years).filter((v) => v > 0).length, nYears: Object.keys(years).length,
      posMonths: (100 * Object.values(months).filter((v) => v > 0).length) / Object.keys(months).length,
    },
    curve: idx.map((i) => [days[i], +curve[i].toFixed(3)]), drawdown: idx.map((i) => [days[i], +dd[i].toFixed(3)]),
    years, correlation: { ids, matrix: mat.map((a) => mat.map((b) => corr(a, b))) },
    riskContribution: ids.map((id, i) => ({ id, pct: tot > 0 ? (100 * w[i] * sw[i]) / tot : null })),
    monthly: histogram(Object.values(months), 28),
    montecarlo: simulate(combo, { sims: opts.sims ?? 3000, horizon: Math.round(perYear), capital: opts.capital ?? 50000, riskPct: opts.riskPct ?? 1, seed: 7, points: 50 }),
    note: "Daily grid over the period where every selected strategy has data. Units: R per weight unit.",
  };
}

function covar(a, b, ma, mb) { let s = 0; for (let i = 0; i < a.length; i++) s += (a[i] - ma) * (b[i] - mb); return s / (a.length - 1); }
