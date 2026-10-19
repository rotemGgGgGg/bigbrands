"""Iter 54 (queue 55) — day-2 continuation: the session after a GapFB-C trade (any gap the next day, or no gap required).
Condition on day-1 outcome (winner = R>0, or day-1 close in trade direction beyond the entry). Day 2: 15-min OR break in the
day-1 direction, entry ≤10:30, stop 2×ATR + 5×ATR trail, exit 15:55. Uses gapfb2 arrays (RTH)."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays, trade
A = arrays(); CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)
def day2(o, h, l, c, a, s):
    orh, orl = h[:15].max(), l[:15].min(); lvl = orh if s == 1 else orl
    win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
    if not win.any(): return None
    j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e
    for k in range(j, 386):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
        best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
    else: px = c[385]
    return (s * (px - e) - 2.25 * e / 17000) / st
for cond in ("any_trade", "winner", "loser"):
    line = []
    for nm, rows in A.items():
        R = []
        for i in range(len(rows) - 1):
            d, g, o, h, l, c, a = rows[i]; r1 = trade(o, h, l, c, a, g, *CFG)
            if r1 is None: continue
            if cond == "winner" and r1 <= 0: continue
            if cond == "loser" and r1 > 0: continue
            s = 1 if g > 0 else -1; _, g2, o2, h2, l2, c2, a2 = rows[i + 1]
            r = day2(o2, h2, l2, c2, a2, s)
            if r is not None: R.append(r)
        R = np.array(R); w = R > 0
        line.append(f"{nm}: n={len(R)} win={100*w.mean():4.1f}% R={R.mean():+.3f}")
    print(f"day2 after {cond:9s} | " + " | ".join(line), flush=True)
