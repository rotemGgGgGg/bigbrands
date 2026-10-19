"""Fade of the overnight-high/low break on gap days (gap ≥0.3 %, ON level beyond the 09:30 open, touched 09:30–10:30):
enter AGAINST the gap at the level (limit, fill needs trade-through 1 tick), stop k×ATR beyond, target 2k×ATR (1:2) or
5×ATR trail; exit 15:55. Also prior-day high/low fade. Three periods."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
S = build(); R0 = t2m("09:30"); E1 = t2m("10:30"); X1 = t2m("15:55")
def go(days, X, zone, k, mode):
    o, h, l, c, a = (X[:, :, i] for i in range(5)); out = []
    for i in range(1, len(days)):
        pc = c[i - 1, t2m("15:59")]; g = o[i, R0] / pc - 1
        if abs(g) < 0.003: continue
        gs = 1 if g > 0 else -1
        lvl = (h[i, :R0].max() if gs == 1 else l[i, :R0].min()) if zone == "onhl" else (h[i - 1, R0:X1].max() if gs == 1 else l[i - 1, R0:X1].min())
        if gs * (lvl - o[i, R0]) <= 0: continue
        tick = o[i, R0] / 17000 * 0.25
        win = (h[i, R0:E1] >= lvl + tick) if gs == 1 else (l[i, R0:E1] <= lvl - tick)
        if not win.any(): continue
        j = R0 + np.argmax(win); s = -gs; e = lvl; A = a[i, j]; st = k * A; sl = e - s * st
        tp = e + s * 2 * st if mode == "1:2" else None; best = e; px = None
        for m in range(j, X1 + 1):
            if (l[i, m] <= sl) if s == 1 else (h[i, m] >= sl): px = sl if m == j else (min(o[i, m], sl) if s == 1 else max(o[i, m], sl)); break
            if m > j and tp is not None and ((h[i, m] >= tp) if s == 1 else (l[i, m] <= tp)): px = tp; break
            if tp is None: best = max(best, h[i, m]) if s == 1 else min(best, l[i, m]); sl = max(sl, best - 5 * A) if s == 1 else min(sl, best + 5 * A)
        if px is None: px = c[i, X1]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for zone, k, mode in itertools.product(("onhl", "pdhl"), (1.0, 2.0, 3.0), ("1:2", "trail")):
    line = []
    for nm, (days, X), msk in (("2010-19", S["A"], None), ("2020-23", S["B"], "lt"), ("2024-26", S["B"], "ge")):
        if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
        R = go(days, X, zone, k, mode); w = R > 0
        line.append(f"{nm}: n={len(R)} win={100*w.mean():4.1f}% R={R.mean():+.3f}")
    print(f"fade {zone} stop{k}ATR {mode:5s} | " + " | ".join(line), flush=True)
