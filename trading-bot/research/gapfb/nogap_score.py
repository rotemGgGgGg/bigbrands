"""Iter 86 (queue 87) — OR-follow on NON-gap days (|gap| < 0.3 %) with a quality score; direction = sign of the 09:30–09:44
move. Points: yesterday's RTH candle AGAINST the direction; OR width ≥ 4×ATR; 09:44 close in the outer 25 % of the OR in the
direction. Entry stop at the OR edge in that direction ≤10:30, stop 2×ATR, 5×ATR trail, exit 15:55."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np
from gapfb2 import arrays
A = arrays()
def go(rows, smin):
    out = []
    for i in range(1, len(rows)):
        d, g, o, h, l, c, a = rows[i]; _, _, po, ph, pl, pc, _ = rows[i - 1]
        if abs(g) >= 0.003: continue
        s = 1 if c[14] > o[0] else -1; orh, orl = h[:15].max(), l[:15].min()
        if orh <= orl: continue
        loc = (c[14] - orl) / (orh - orl); loc = loc if s == 1 else 1 - loc
        sc = int(s * (pc[389] - po[0]) <= 0) + int((orh - orl) >= 4 * a[15]) + int(loc >= 0.75)
        if sc < smin: continue
        lvl = orh if s == 1 else orl; win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
        if not win.any(): continue
        j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e; px = None
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
            best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
        if px is None: px = c[385]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for smin in (0, 1, 2, 3):
    print(f"non-gap score≥{smin} | " + " | ".join(f"{p}: n={len(R)} win={100*(R>0).mean():4.1f}% R={R.mean():+.3f}" for p, rows in A.items() for R in [go(rows, smin)]), flush=True)
