import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { simulate } from "../server/lib/montecarlo.mjs";
import { tstat, maxDrawdown, pctSorted } from "../server/lib/stats.mjs";
import { ResearchData } from "../server/lib/data.mjs";
import { portfolio } from "../server/lib/portfolio.mjs";

const LAB = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "..", "research", "lab");

test("stats", () => {
  assert.equal(maxDrawdown([1, 3, 2, 0, 4]), 3);
  assert.equal(pctSorted([1, 2, 3, 4, 5], 50), 3);
  assert.ok(Math.abs(tstat([1, -1, 1, -1]) - 0) < 1e-12);
});

test("monte carlo: constant +1R, fixed sizing, gives a deterministic line", () => {
  const m = simulate(new Array(50).fill(1), { sims: 200, horizon: 10, capital: 1000, riskPct: 1 });
  assert.equal(m.metrics.median, 1100); assert.equal(m.metrics.pPositive, 100); assert.equal(m.metrics.riskOfRuin, 0); assert.equal(m.metrics.dd95Pct, 0);
});

test("monte carlo: all losers ruin at the threshold", () => {
  const m = simulate(new Array(20).fill(-1), { sims: 100, horizon: 60, capital: 1000, riskPct: 1, ruinPct: 50 });
  assert.equal(m.metrics.riskOfRuin, 100); assert.equal(m.metrics.pPositive, 0);
});

test("monte carlo is reproducible with a seed", () => {
  const r = Array.from({ length: 300 }, (_, i) => (i % 3 ? -1 : 2.2));
  assert.deepEqual(simulate(r, { seed: 5, sims: 500 }).metrics, simulate(r, { seed: 5, sims: 500 }).metrics);
});

test("research data: metrics match the trade series", () => {
  const d = new ResearchData(LAB); const s = d.load().strategies.find((x) => x.id === "rdm10"); const r = d.series("rdm10").r;
  assert.equal(s.n, r.length); assert.ok(Math.abs(s.expectancy - r.reduce((a, b) => a + b, 0) / r.length) < 1e-12);
  assert.ok(Math.abs(s.winRate - 20.3) < 0.1, `win ${s.winRate}`);           // same as the original Edge Lab page
});

test("portfolio: single strategy with weight 1 reproduces its own total R", () => {
  const d = new ResearchData(LAB); const p = portfolio(d, { rdm10: 1 });
  const total = d.series("rdm10").r.reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(p.metrics.totalR - total) < 1e-6); assert.equal(p.correlation.matrix[0][0], 1);
  assert.ok(Math.abs(p.riskContribution[0].pct - 100) < 1e-9);
});
