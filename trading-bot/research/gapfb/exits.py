"""Iter 56 (queue 57) — GapFB-C exit refinements (base trade only): trail 5×ATR (base) vs tighten to 3×ATR after 14:00 or
after +3 R MFE, partial ½ at +2 R (rest trails), trail 4 / 6 ×ATR, break-even at +1 R. Three periods."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
A = arrays()
def go(rows, trail=5.0, tight=None, tight_after=None, partial=None, be=None):
    out = []
    for d, g, o, h, l, c, a in rows:
        if abs(g) < 0.003: continue
        s = 1 if g > 0 else -1; orh, orl = h[:15].max(), l[:15].min(); lvl = orh if s == 1 else orl
        win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
        if not win.any(): continue
        j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e
        half = None; px = None
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
            best = max(best, h[k]) if s == 1 else min(best, l[k]); mfe = s * (best - e) / st
            if partial and half is None and mfe >= partial: half = e + s * partial * st
            tr = trail
            if tight and ((tight_after == "14:00" and k >= 270) or (tight_after == "3R" and mfe >= 3)): tr = tight
            sl = max(sl, best - tr * A_) if s == 1 else min(sl, best + tr * A_)
            if be and mfe >= be: sl = max(sl, e) if s == 1 else min(sl, e)
        if px is None: px = c[385]
        r = s * (px - e) / st
        if half is not None: r = 0.5 * r + 0.5 * s * (half - e) / st
        out.append(r - 2.25 * e / 17000 / st)
    return np.array(out)
V = {"base trail5": {}, "trail4": dict(trail=4.0), "trail6": dict(trail=6.0), "tight3 after 14:00": dict(tight=3.0, tight_after="14:00"),
     "tight3 after +3R": dict(tight=3.0, tight_after="3R"), "partial 1/2 at +2R": dict(partial=2.0), "BE at +1R": dict(be=1.0)}
for nm, kw in V.items():
    line = []
    for per, rows in A.items():
        R = go(rows, **kw); w = R > 0; line.append(f"{per}: win={100*w.mean():4.1f}% rr={R[w].mean()/-R[~w].mean():.2f} R={R.mean():+.3f}")
    print(f"{nm:20s} | " + " | ".join(line), flush=True)
