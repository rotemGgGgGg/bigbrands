// Pure metric derivation shared by the server (data.mjs) and the static build (api-static.js).
import { mean, std, tstat, maxDrawdown, cumsum, downsample } from "./stats.mjs";

/** Registry entry + its trade series -> every metric the app shows. */
export function enrich(s, tr) {
  const base = {
    id: s.id, name: s.name, market: s.market, status: s.status, family: s.family, rule: s.rule, note: s.note,
    entry: s.entry || null, exit: s.exit || null, params: s.params || null, rr: s.rr ?? null, pRandom: s.p ?? null, hasTrades: !!tr,
    mc: s.mc ? { p_year_pos: s.mc.p_year_pos, median_year: s.mc.median_year, p5_year: s.mc.p5_year, p95_dd: s.mc.p95_dd } : null,
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

/** Summary row without the heavy curves, for lists. */
export function summary(s) {
  const { curve, drawdown, years, yearsN, ...rest } = s;
  return { ...rest, spark: curve ? downsample(curve.map((c) => c[1]), 60) : null };
}
