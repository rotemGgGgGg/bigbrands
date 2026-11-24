// Small statistics helpers shared by the data, Monte Carlo and portfolio engines.

export const sum = (a) => { let s = 0; for (const x of a) s += x; return s; };
export const mean = (a) => (a.length ? sum(a) / a.length : NaN);

export function std(a) {
  if (a.length < 2) return NaN;
  const m = mean(a); let s = 0;
  for (const x of a) s += (x - m) ** 2;
  return Math.sqrt(s / (a.length - 1));
}

/** t-statistic of the mean (mean / standard error). */
export function tstat(a) {
  const s = std(a);
  return a.length > 2 && s > 0 ? (mean(a) / s) * Math.sqrt(a.length) : 0;
}

/** Linear-interpolated percentile of a sorted array, q in [0, 100]. */
export function pctSorted(sorted, q) {
  if (!sorted.length) return NaN;
  const pos = ((sorted.length - 1) * q) / 100, lo = Math.floor(pos), hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

export function corr(a, b) {
  const ma = mean(a), mb = mean(b); let sab = 0, saa = 0, sbb = 0;
  for (let i = 0; i < a.length; i++) { const x = a[i] - ma, y = b[i] - mb; sab += x * y; saa += x * x; sbb += y * y; }
  return saa > 0 && sbb > 0 ? sab / Math.sqrt(saa * sbb) : 0;
}

/** Deterministic PRNG (mulberry32) so a Monte Carlo run with a seed is reproducible. */
export function rng(seed = 2026) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Max drawdown of a cumulative curve, in the curve's units (positive number). */
export function maxDrawdown(curve) {
  let peak = 0, dd = 0;
  for (const v of curve) { if (v > peak) peak = v; if (peak - v > dd) dd = peak - v; }
  return dd;
}

export function cumsum(a) { const out = new Array(a.length); let s = 0; for (let i = 0; i < a.length; i++) { s += a[i]; out[i] = s; } return out; }

/** Keep at most n points of a series, always including the last. */
export function downsample(arr, n) {
  if (arr.length <= n) return arr;
  const step = arr.length / n, out = [];
  for (let i = 0; i < n; i++) out.push(arr[Math.floor(i * step)]);
  out.push(arr[arr.length - 1]);
  return out;
}

export function histogram(values, bins = 30) {
  if (!values.length) return { edges: [], counts: [] };
  let lo = Infinity, hi = -Infinity;
  for (const v of values) { if (v < lo) lo = v; if (v > hi) hi = v; }
  if (hi === lo) hi = lo + 1;
  const w = (hi - lo) / bins, counts = new Array(bins).fill(0);
  for (const v of values) counts[Math.min(bins - 1, Math.floor((v - lo) / w))]++;
  return { edges: Array.from({ length: bins + 1 }, (_, i) => lo + i * w), counts };
}
