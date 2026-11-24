// Monte Carlo engine: i.i.d. bootstrap of a strategy's own trade returns (the same method the original
// Edge Lab page used for its "5,000 one-year paths"), extended with capital, sizing and risk of ruin.
import { rng, pctSorted, histogram } from "./stats.mjs";

const Q = [5, 25, 50, 75, 95];

/**
 * @param {number[]} returns  per-trade (or per-day) returns in R
 * @param {object} o  sims, horizon (steps per path), capital, riskPct (% of equity risked per 1R),
 *                    sizing 'fixed' (risk % of starting capital) | 'compound' (risk % of current equity),
 *                    ruinPct (equity drawdown from start that counts as ruin), seed, points (samples on the fan)
 */
export function simulate(returns, o = {}) {
  const sims = clamp(Math.round(o.sims ?? 5000), 100, 20000);
  const horizon = clamp(Math.round(o.horizon ?? returns.length), 5, 5000);
  const capital = Math.max(+o.capital || 50000, 1);
  const riskPct = clamp(+(o.riskPct ?? 1), 0.01, 20) / 100;
  const sizing = o.sizing === "compound" ? "compound" : "fixed";
  const ruinLevel = capital * (1 - clamp(+(o.ruinPct ?? 50), 1, 100) / 100);
  const points = clamp(Math.round(o.points ?? 60), 10, 200);
  if (returns.length < 5) throw new Error("Not enough trades to simulate (need at least 5).");

  const rand = rng(o.seed ?? 2026), n = returns.length;
  const marks = Array.from({ length: points + 1 }, (_, i) => Math.round((i * horizon) / points));
  const atMark = marks.map(() => new Float64Array(sims));
  const finals = new Float64Array(sims), maxDDpct = new Float64Array(sims), finalR = new Float64Array(sims);
  let ruined = 0;
  const t0 = performance.now();

  for (let s = 0; s < sims; s++) {
    let eq = capital, peak = capital, dd = 0, sumR = 0, ruin = false, m = 1;
    atMark[0][s] = capital;
    for (let k = 1; k <= horizon; k++) {
      const r = returns[Math.floor(rand() * n)];
      sumR += r;
      eq += sizing === "fixed" ? r * riskPct * capital : r * riskPct * eq;
      if (eq > peak) peak = eq;
      const d = (peak - eq) / peak; if (d > dd) dd = d;
      if (!ruin && eq <= ruinLevel) ruin = true;
      if (sizing === "compound" && eq <= 0) eq = 0;
      while (m < marks.length && marks[m] === k) { atMark[m][s] = eq; m++; }
    }
    finals[s] = eq; maxDDpct[s] = dd * 100; finalR[s] = sumR; if (ruin) ruined++;
  }

  const fan = atMark.map((col, i) => { const c = Float64Array.from(col).sort(); return { step: marks[i], q: Q.map((q) => pctSorted(c, q)) }; });
  const fs_ = Float64Array.from(finals).sort(), dd_ = Float64Array.from(maxDDpct).sort(), r_ = Float64Array.from(finalR).sort();
  return {
    config: { sims, horizon, capital, riskPct: riskPct * 100, sizing, ruinPct: 100 * (1 - ruinLevel / capital), seed: o.seed ?? 2026, sampleSize: n, method: "i.i.d. bootstrap of the strategy's own returns" },
    fan,
    metrics: {
      pPositive: (100 * finals.filter((x) => x > capital).length) / sims,
      median: pctSorted(fs_, 50), p5: pctSorted(fs_, 5), p95: pctSorted(fs_, 95),
      medianR: pctSorted(r_, 50), p5R: pctSorted(r_, 5), p95R: pctSorted(r_, 95),
      ddMedianPct: pctSorted(dd_, 50), dd95Pct: pctSorted(dd_, 95), riskOfRuin: (100 * ruined) / sims,
    },
    ending: histogram(Array.from(finals), 36),
    ms: Math.round(performance.now() - t0),
  };
}

function clamp(x, lo, hi) { return Math.min(hi, Math.max(lo, Number.isFinite(x) ? x : lo)); }
