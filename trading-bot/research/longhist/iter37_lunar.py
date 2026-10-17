"""Iter 39 (queue) — lunar folklore (Dichev & Janes 2003, Yuan-Zheng-Zhu 2006: higher returns in the ±7 days around the new moon).
Phase from the mean synodic month (29.530589 d, reference new moon 2000-01-06 18:14 UTC). Day-level check (open→close in σ units)
and 1:2 brackets at 09:30 (long in the new-moon half, short in the full-moon half; k·σ stop, 2k target). Placebo: phase shifted by
random offsets (500 draws) → p-value of the new-minus-full spread."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd
exec(open("iter26_web.py").read().split("\nres = []")[0])
REF = pd.Timestamp("2000-01-06 18:14"); SYN = 29.530589
rng = np.random.default_rng(3)
for per, o, h, l, c, dow in grids():
    if per == "2012-19":
        f0 = frame("NSXUSD"); days = RTH(f0[f0.index.notna()][:"2019-12-31"]).days
    else:
        import lib; days = lib.DAYS[(lib.YR < 2024) if per == "2020-23" else (lib.YR >= 2024)]
    days = pd.DatetimeIndex(days); ph = (((days - REF) / pd.Timedelta(days=1)) % SYN).values
    O = o[:, 0]; C = c[:, 389]; sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    ok = np.isfinite(sig); r = (C / O - 1) / sig
    def spread(p): nm = (p < 7.4) | (p > 22.1); return np.nanmean(r[ok & nm]) - np.nanmean(r[ok & ~nm])
    s0 = spread(ph); null = np.array([spread((ph + rng.uniform(0, SYN)) % SYN) for _ in range(500)])
    out = [f"{per}: new-full spread {s0:+.3f}σ, placebo p={(null >= s0).mean():.2f}"]
    for k in (0.25, 0.4):
        R = []
        for i in np.nonzero(ok)[0]:
            s = 1 if (ph[i] < 7.4 or ph[i] > 22.1) else -1; e = O[i]; st = k * sig[i] * e
            px, _, _ = walk(o[i], h[i], l[i], c[i], 0, s, e, e - s * st, e + s * 2 * st, 389); R.append((s * (px - e) - 2.25 * e / 17000) / st)
        R = np.array(R); out.append(f"k{k}: n={len(R)} win={100*(R>0).mean():.1f}% R={R.mean():+.3f}")
    print(" | ".join(out))
