"""Iter 52 (queue 54) — zone breakouts at the open on gap days (gap ≥0.3 %), gap direction only: trigger = overnight high/low
(18:00–09:29) or prior RTH high/low or 15-min OR (base), entry window 09:30–10:30 (zone must be beyond the 09:30 open),
stop 2×ATR + 5×ATR trail, exit 15:55. Uses the 24 h grid (sess24.pkl)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
S = build(); R0 = t2m("09:30"); E1 = t2m("10:30"); X1 = t2m("15:55")
def go(days, X, zone):
    o, h, l, c, a = (X[:, :, i] for i in range(5)); out = []
    for i in range(1, len(days)):
        pc = c[i - 1, t2m("15:59")]; g = o[i, R0] / pc - 1
        if abs(g) < 0.003: continue
        s = 1 if g > 0 else -1
        if zone == "or15": lvl = h[i, R0:R0 + 15].max() if s == 1 else l[i, R0:R0 + 15].min(); w0 = R0 + 15
        elif zone == "onhl": lvl = h[i, :R0].max() if s == 1 else l[i, :R0].min(); w0 = R0
        elif zone == "pdhl": lvl = h[i - 1, R0:X1].max() if s == 1 else l[i - 1, R0:X1].min(); w0 = R0
        if zone != "or15" and s * (lvl - o[i, R0]) <= 0: continue          # already beyond at the open → no breakout to trade
        win = (h[i, w0:E1] >= lvl) if s == 1 else (l[i, w0:E1] <= lvl)
        if not win.any(): continue
        j = w0 + np.argmax(win); e = max(lvl, o[i, j]) if s == 1 else min(lvl, o[i, j]); A = a[i, j]; st = 2 * A; sl = e - s * st; best = e; px = None
        for k in range(j, X1 + 1):
            if (l[i, k] <= sl) if s == 1 else (h[i, k] >= sl): px = sl if k == j else (min(o[i, k], sl) if s == 1 else max(o[i, k], sl)); break
            best = max(best, h[i, k]) if s == 1 else min(best, l[i, k]); sl = max(sl, best - 5 * A) if s == 1 else min(sl, best + 5 * A)
        if px is None: px = c[i, X1]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for zone in ("or15", "onhl", "pdhl"):
    line = []
    for nm, (days, X), msk in (("2010-19", S["A"], None), ("2020-23", S["B"], "lt"), ("2024-26", S["B"], "ge")):
        if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
        R = go(days, X, zone); w = R > 0
        line.append(f"{nm}: n={len(R)} win={100*w.mean():4.1f}% rr={R[w].mean()/-R[~w].mean():.2f} R={R.mean():+.3f}")
    print(f"{zone:5s} | " + " | ".join(line), flush=True)
