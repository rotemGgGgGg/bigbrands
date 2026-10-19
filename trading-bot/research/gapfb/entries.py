"""Iter 57 (queue 58) — GapFB-C entry refinements: buffer b×ATR beyond the OR level; skip when OR width > w×ATR or < w0×ATR;
entry window to 10:00 / 10:30 / 11:00. Base trade (2×ATR stop, 5×ATR trail, exit 15:55)."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
A = arrays()
def go(rows, buf=0.0, wmax=99, wmin=0, cut=60):
    out = []
    for d, g, o, h, l, c, a in rows:
        if abs(g) < 0.003: continue
        s = 1 if g > 0 else -1; orh, orl = h[:15].max(), l[:15].min(); A15 = a[15]
        if not (wmin <= (orh - orl) / A15 < wmax): continue
        lvl = (orh + buf * A15) if s == 1 else (orl - buf * A15)
        win = (h[15:cut + 1] >= lvl) if s == 1 else (l[15:cut + 1] <= lvl)
        if not win.any(): continue
        j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e; px = None
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
            best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
        if px is None: px = c[385]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
V = {"base": {}, "buffer 0.25ATR": dict(buf=0.25), "buffer 0.5ATR": dict(buf=0.5), "OR width <4ATR": dict(wmax=4),
     "OR width >=4ATR": dict(wmin=4), "OR width <6ATR": dict(wmax=6), "cut 10:00": dict(cut=30), "cut 11:00": dict(cut=90)}
for nm, kw in V.items():
    line = []
    for per, rows in A.items():
        R = go(rows, **kw); w = R > 0; line.append(f"{per}: n={len(R)} win={100*w.mean():4.1f}% R={R.mean():+.3f}")
    print(f"{nm:16s} | " + " | ".join(line), flush=True)
