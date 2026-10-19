"""Iter 67 (queue 68) — earlier 2020+ edges re-tested on REAL NQ futures 2010–19 (sess24 grid) + MNQ 2020–23 / 2024–26:
 PF  Pre-Open Fade: 08:00→08:59 move |z|>2 (20-day std of that window's return) → fade at 09:00, TP 0.5×move, SL 1.0×move, exit 13:00
 WVB Williams volatility breakout: stop entries at RTH open ± 0.6×yesterday's RTH range, stop 0.5×range, exit 15:55
 OD  open-drive: first-30 extreme at the open, close@10:00 ≥ 0.2σ away → follow at 10:00, stop 0.4σ, target 0.8σ, exit 15:55
Cost 2.25 pt scaled by price/17000. Results in R (risk units)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
S = build()
def walk(o, h, l, c, j, s, e, sl, tp, last):
    for k in range(j, last + 1):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl): return min(o[k], sl) if s == 1 else max(o[k], sl)
        if tp is not None and ((h[k] >= tp) if s == 1 else (l[k] <= tp)): return tp
    return c[last]
R930, X1555 = t2m("09:30"), t2m("15:55")
def run(days, X):
    o, h, l, c = (X[:, :, i] for i in range(4)); res = {"PF": [], "WVB": [], "OD": []}
    t8, t859, t9, t13 = t2m("08:00"), t2m("08:59"), t2m("09:00"), t2m("13:00")
    pre = c[:, t859] / o[:, t8] - 1; sd = pd.Series(pre).rolling(20).std().shift().values
    rng = h[:, R930:X1555].max(1) - l[:, R930:X1555].min(1)
    sig = pd.Series(np.abs(c[:, X1555] / o[:, R930] - 1)).rolling(14).mean().shift().values
    for i in range(21, len(days)):
        # PF
        if sd[i] > 0 and abs(pre[i] / sd[i]) > 2:
            mv = c[i, t859] - o[i, t8]; s = -1 if mv > 0 else 1; e = o[i, t9]; size = abs(mv)
            px = walk(o[i], h[i], l[i], c[i], t9, s, e, e - s * size, e + s * 0.5 * size, t13)
            res["PF"].append((s * (px - e) - 2.25 * e / 17000) / size)
        # WVB
        r = rng[i - 1]; O = o[i, R930]; up, dn = O + 0.6 * r, O - 0.6 * r
        hu = np.nonzero(h[i, R930 + 1:X1555] >= up)[0]; hd = np.nonzero(l[i, R930 + 1:X1555] <= dn)[0]
        tu = hu[0] if len(hu) else 9999; td = hd[0] if len(hd) else 9999
        if tu != td:
            s, j = (1, R930 + 1 + tu) if tu < td else (-1, R930 + 1 + td); e = up if s == 1 else dn; e = max(e, o[i, j]) if s == 1 else min(e, o[i, j])
            px = walk(o[i], h[i], l[i], c[i], j + 1, s, e, e - s * 0.5 * r, None, X1555)
            res["WVB"].append((s * (px - e) - 2.25 * e / 17000) / (0.5 * r))
        # OD
        if np.isfinite(sig[i]):
            sg = sig[i] * O; c30 = c[i, R930 + 29]; mv = (c30 - O) / sg; s = 0
            if mv >= 0.2 and O - l[i, R930:R930 + 30].min() <= 0.05 * sg: s = 1
            if mv <= -0.2 and h[i, R930:R930 + 30].max() - O <= 0.05 * sg: s = -1
            if s:
                j = R930 + 30; e = o[i, j]; st = 0.4 * sg
                px = walk(o[i], h[i], l[i], c[i], j, s, e, e - s * st, e + s * 2 * st, X1555)
                res["OD"].append((s * (px - e) - 2.25 * e / 17000) / st)
    return res
for nm, (days, X), msk in (("2010-19", S["A"], None), ("2020-23", S["B"], "lt"), ("2024-26", S["B"], "ge")):
    if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
    res = run(days, X)
    print(nm, " | ".join(f"{k}: n={len(v)} win={100*(np.array(v)>0).mean():4.1f}% R={np.mean(v):+.3f}" for k, v in res.items()), flush=True)
