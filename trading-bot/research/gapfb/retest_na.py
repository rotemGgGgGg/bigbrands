"""Iter 68 (queue 70) — Noise-Area first break and NA-FVG scalp on REAL NQ 2010–19 (+ MNQ 2020–23 / 2024–26), sess24 grid.
NA: per-minute noise = 14-day mean of |close_k / open − 1|; bounds max(open, prev close)·(1+noise_k) / min(..)·(1−noise_k),
checked at :59/:29 marks (every 30 min from 09:59); first close outside → follow at next open, hold to 15:55 (σ units).
NA-FVG: after the break, first retrace into a 1-min FVG in the trend direction within 60 min → limit at the gap edge,
TP 0.10×σ_day, SL 1.5×σ_day (the '92 %' config). Cost 2.25 pt scaled."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
S = build(); R0 = t2m("09:30")
def run(days, X):
    o, h, l, c = (X[:, R0:R0 + 390, i] for i in range(4))
    pcs = X[:, t2m("15:59"), 3]; pc = np.r_[np.nan, pcs[:-1]]
    move = np.abs(c / o[:, :1] - 1); dsig = pd.Series(move[:, 385]).rolling(14).mean().shift().values
    marks = [29 + 30 * j for j in range(12)]; na, fv = [], []
    for i in range(15, len(days)):
        if not np.isfinite(pc[i]) or not np.isfinite(dsig[i]): continue
        nz = move[i - 14:i].mean(0); o0 = o[i, 0]; ub = max(o0, pc[i]) * (1 + nz); lb = min(o0, pc[i]) * (1 - nz)
        hit = None
        for k in marks:
            if c[i, k] > ub[k]: hit = (k, 1); break
            if c[i, k] < lb[k]: hit = (k, -1); break
        if hit is None: continue
        k, s = hit; sc = dsig[i] * o0; e = o[i, k + 1]
        na.append((s * (c[i, 385] - e) - 2.25 * e / 17000) / sc)
        gap = None
        for j in range(k + 3, min(k + 60, 385)):
            if gap is None:
                if s == 1 and h[i, j - 2] < l[i, j]: gap = l[i, j]
                if s == -1 and l[i, j - 2] > h[i, j]: gap = h[i, j]
                continue
            tick = o0 / 17000 * 0.25
            if (l[i, j] <= gap - tick) if s == 1 else (h[i, j] >= gap + tick):
                e = gap; tp = e + s * 0.10 * sc; sl = e - s * 1.5 * sc; px = None
                for m in range(j, 386):
                    if (l[i, m] <= sl) if s == 1 else (h[i, m] >= sl): px = sl if m == j else (min(o[i, m], sl) if s == 1 else max(o[i, m], sl)); break
                    if m > j and ((h[i, m] >= tp) if s == 1 else (l[i, m] <= tp)): px = tp; break
                if px is None: px = c[i, 385]
                fv.append(s * (px - e) - 2.25 * e / 17000); break
    return np.array(na), np.array(fv)
for nm, (days, X), msk in (("2010-19", S["A"], None), ("2020-23", S["B"], "lt"), ("2024-26", S["B"], "ge")):
    if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
    na, fv = run(days, X)
    print(f"{nm} NA break→close: n={len(na)} win={100*(na>0).mean():4.1f}% avg={na.mean():+.3f}σ | NA-FVG 0.1/1.5: n={len(fv)} "
          f"win={100*(fv>0).mean():4.1f}% avg={fv.mean():+.2f} pts ({fv.mean()/ (X[:, R0, 0].mean()/17000):+.2f} MNQ-pt-equiv)", flush=True)
