// Research data layer: reads the Edge Lab registry (research/lab/data.json) and the per-trade series
// (research/lab/trades.json), and derives every metric the app shows from the actual trades.
import fs from "node:fs";
import path from "node:path";
import { mean, std, tstat, maxDrawdown, cumsum, downsample } from "./stats.mjs";

export class ResearchData {
  constructor(labDir) {
    this.labDir = labDir;
    this.files = { registry: path.join(labDir, "data.json"), trades: path.join(labDir, "trades.json") };
    this.cache = null; this.stamp = "";
  }

  /** Reload when either file changed on disk (the research agent or build.py may rewrite them). */
  load() {
    const st = Object.values(this.files).map((f) => (fs.existsSync(f) ? fs.statSync(f).mtimeMs : 0)).join("|");
    if (this.cache && st === this.stamp) return this.cache;
    if (!fs.existsSync(this.files.registry)) throw new Error(`Registry not found: ${this.files.registry}. Run python3 build.py in research/lab.`);
    const reg = JSON.parse(fs.readFileSync(this.files.registry, "utf8"));
    const trades = fs.existsSync(this.files.trades) ? JSON.parse(fs.readFileSync(this.files.trades, "utf8")) : {};
    const strategies = reg.strategies.map((s) => this.#enrich(s, trades[s.id] || (s.series && trades[s.series])));
    this.cache = { meta: { updated: reg.updated, theoriesTested: reg.theories_tested, book: reg.book, files: this.fileInfo() }, strategies, sp: reg.sp || null, trades };
    this.stamp = st;
    return this.cache;
  }

  fileInfo() {
    return Object.entries(this.files).map(([k, f]) => ({ key: k, path: f, exists: fs.existsSync(f), modified: fs.existsSync(f) ? fs.statSync(f).mtime.toISOString() : null }));
  }

  /** Raw trade returns for one strategy (null when the strategy has no trade series). */
  series(id) {
    const d = this.load(); const s = d.strategies.find((x) => x.id === id);
    if (!s) return null;
    const tr = d.trades[id] || (s.series && d.trades[s.series]);
    return tr ? { t: tr.t, r: tr.r, units: tr.units } : null;
  }

  #enrich(s, tr) {
    const base = {
      id: s.id, name: s.name, market: s.market, status: s.status, family: s.family, rule: s.rule, note: s.note,
      entry: s.entry || null, exit: s.exit || null, params: s.params || null, rr: s.rr ?? null, pRandom: s.p ?? null, hasTrades: !!tr,
    };
    if (!tr) return base;
    const r = tr.r, t = tr.t, years = {}, yearsN = {};
    const isR = [], oosR = [];
    let streak = 0, worstStreak = 0;
    r.forEach((x, i) => {
      const y = +t[i].slice(0, 4);
      years[y] = (years[y] || 0) + x; yearsN[y] = (yearsN[y] || 0) + 1;
      (y <= 2019 ? isR : oosR).push(x);
      streak = x < 0 ? streak + 1 : 0; if (streak > worstStreak) worstStreak = streak;
    });
    const wins = r.filter((x) => x > 0), losses = r.filter((x) => x < 0);
    const curve = cumsum(r);
    let peak = 0; const dd = curve.map((v) => { peak = Math.max(peak, v); return v - peak; });
    const spanYears = Math.max((Date.parse(t[t.length - 1]) - Date.parse(t[0])) / 3.15576e10, 1);
    const pts = downsample(r.map((_, i) => i), 400);
    return {
      ...base, units: tr.units, n: r.length, perYear: r.length / spanYears, first: t[0], last: t[t.length - 1],
      winRate: (100 * wins.length) / r.length, avgWin: mean(wins), avgLoss: mean(losses), payoff: wins.length && losses.length ? mean(wins) / -mean(losses) : null,
      expectancy: mean(r), sd: std(r), t: tstat(r), totalR: curve[curve.length - 1], maxDD: maxDrawdown(curve), worstStreak,
      best: Math.max(...r), worst: Math.min(...r),
      isAvg: isR.length ? mean(isR) : null, isT: tstat(isR), oosAvg: oosR.length ? mean(oosR) : null, oosT: tstat(oosR), isN: isR.length, oosN: oosR.length,
      years, yearsN, posYears: Object.values(years).filter((v) => v > 0).length, nYears: Object.keys(years).length,
      curve: pts.map((i) => [t[i].slice(0, 10), +curve[i].toFixed(3)]), drawdown: pts.map((i) => [t[i].slice(0, 10), +dd[i].toFixed(3)]),
    };
  }
}

/** Summary row without the heavy curves, for lists. */
export function summary(s) {
  const { curve, drawdown, years, yearsN, ...rest } = s;
  return { ...rest, spark: curve ? downsample(curve.map((c) => c[1]), 60) : null };
}
