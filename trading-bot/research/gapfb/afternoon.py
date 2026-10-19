"""Iter 65 — afternoon continuation on GapFB days: if at 13:30 price is ≥ x×ATR beyond the 09:30 open in the gap direction
(morning worked), trade the 13:30–13:44 range break in that direction until 14:30; stop 2×ATR, 5×ATR trail, exit 15:55."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np
from gapfb2 import arrays
A = arrays()
def go(rows, x, need_gap=True):
    out = []
    for d, g, o, h, l, c, a in rows:
        if need_gap and abs(g) < 0.003: continue
        s = 1 if g > 0 else -1; t0 = 240
        if s * (c[t0 - 1] - o[0]) < x * a[t0]: continue
        rh, rl = h[t0:t0 + 15].max(), l[t0:t0 + 15].min(); lvl = rh if s == 1 else rl
        win = (h[t0 + 15:t0 + 61] >= lvl) if s == 1 else (l[t0 + 15:t0 + 61] <= lvl)
        if not win.any(): continue
        j = t0 + 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e; px = None
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
            best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
        if px is None: px = c[385]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for x in (0, 3, 6, 10):
    line = []
    for per, rows in A.items():
        R = go(rows, x); w = R > 0; line.append(f"{per}: n={len(R)} win={100*w.mean():4.1f}% R={R.mean():+.3f}")
    print(f"afternoon cont x={x:2d}ATR | " + " | ".join(line), flush=True)
