"""Iter 30b — check of the opex-Friday short-at-open signal (iter 30): per-year, vs non-opex Fridays, and a placebo
(random Friday of each month, 2000 draws) → p-value of the opex mean R. Stop 0.25σ, target 0.5σ, exit close."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd
exec(open("iter30_calendar.py").read().split("\nres = []")[0])
rng = np.random.default_rng(7)
for per, o, h, l, c, dow in grids():
    if per == "2012-19":
        f0 = frame("NSXUSD"); days = RTH(f0[f0.index.notna()][:"2019-12-31"]).days
    else:
        import lib; days = lib.DAYS[(lib.YR < 2024) if per == "2020-23" else (lib.YR >= 2024)]
    days = pd.DatetimeIndex(days); C = cal(days)
    mv = np.abs(c[:, 389] / o[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
    def r(i, k=0.25):
        e = o[i, 0]; st = k * sig[i] * e
        px, _, _ = walk(o[i], h[i], l[i], c[i], 0, -1, e, e + st, e - 2 * st, 389)
        return (e - px - 2.25 * e / 17000) / st
    ok = np.isfinite(sig); R = np.array([r(i) if ok[i] else np.nan for i in range(len(o))])
    fri = (days.weekday == 4) & ok
    op = C["opex"] & ok; nf = fri & ~C["opex"]
    ym = days.year * 12 + days.month
    groups = [np.nonzero(fri & (ym == k))[0] for k in np.unique(ym[op])]
    groups = [g for g in groups if len(g)]
    draws = np.array([np.nanmean([R[rng.choice(g)] for g in groups]) for _ in range(2000)])
    m = np.nanmean(R[op])
    print(f"{per}: opex n={op.sum()} R={m:+.3f} win={100*(R[op]>0).mean():.0f}% | other Fridays n={nf.sum()} R={np.nanmean(R[nf]):+.3f} "
          f"| placebo p={(draws>=m).mean():.3f}")
    yr = pd.Series(R[op], index=days[op].year).groupby(level=0).agg(["count", "mean"]).round(2)
    print("   per year:", dict(zip(yr.index, zip(yr["count"], yr["mean"]))))
