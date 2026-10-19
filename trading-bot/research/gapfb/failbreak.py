"""Failed-breakout reversal on gap days: after the 15-min OR is broken in the gap direction (≤10:30), if a 1-minute bar
CLOSES back inside the OR within N minutes of the break → enter the opposite way at the next open. Stop = break extreme
+ 0.25×ATR (structural), target k×stop or 5×ATR trail, exit 15:55. Also the same on non-gap days."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd, itertools
from gapfb2 import arrays
A = arrays()
def go(rows, N, tgt, gapmode):
    out = []
    for d, g, o, h, l, c, a in rows:
        if gapmode == "gap" and abs(g) < 0.003: continue
        if gapmode == "nogap" and abs(g) >= 0.003: continue
        gs = 1 if g > 0 else -1
        orh, orl = h[:15].max(), l[:15].min(); lvl = orh if gs == 1 else orl
        win = (h[15:61] > lvl) if gs == 1 else (l[15:61] < lvl)
        if not win.any(): continue
        j = 15 + np.argmax(win)
        back = (c[j:j + N] < lvl) if gs == 1 else (c[j:j + N] > lvl)
        if not back.any(): continue
        k = j + np.argmax(back) + 1; s = -gs; e = o[k]
        ext = h[j:k].max() if gs == 1 else l[j:k].min(); sl = ext - s * 0.25 * a[k]; st = abs(e - sl)
        if st <= 0 or not np.isfinite(st): continue
        tp = e + s * tgt * st if tgt else None; best = e; px = None; A_ = a[k]
        for m in range(k, 386):
            if (l[m] <= sl) if s == 1 else (h[m] >= sl): px = min(o[m], sl) if s == 1 else max(o[m], sl); break
            if tp is not None and ((h[m] >= tp) if s == 1 else (l[m] <= tp)): px = tp; break
            if tp is None:
                best = max(best, h[m]) if s == 1 else min(best, l[m]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
        if px is None: px = c[385]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for N, tgt, gm in itertools.product((5, 15, 30), (2.0, 3.0, None), ("gap", "nogap")):
    line = []
    for nm, rows in A.items():
        R = go(rows, N, tgt, gm); w = R > 0
        line.append(f"{nm}: n={len(R):4d} win={100*w.mean():4.1f}% R={R.mean():+.3f}" if len(R) else f"{nm}: -")
    print(f"N{N:2d} tgt {str(tgt):4s} {gm:5s} | " + " | ".join(line), flush=True)
