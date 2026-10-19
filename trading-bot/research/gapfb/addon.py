"""Iter 55 (queue 56) — pyramiding GapFB-C: after the base trade reaches +x R (MFE), add a 2nd unit on the first 1-minute
close back to the 20-EMA (of 1-minute closes) in trade direction; the add-on shares the trailing stop (5×ATR from best) but
gets its own initial stop 2×ATR. Report base R, add-on R (per unit risk), and combined per day."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
A = arrays()
def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values
def go(rows, x):
    base, add = [], []
    for d, g, o, h, l, c, a in rows:
        if abs(g) < 0.003: continue
        s = 1 if g > 0 else -1; orh, orl = h[:15].max(), l[:15].min(); lvl = orh if s == 1 else orl
        win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
        if not win.any(): continue
        j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e
        E = ema(c, 20); armed = False; e2 = None; sl2 = None; px = None; px2 = None
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl):
                px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl))
                if e2 is not None and px2 is None: px2 = px if s * (px - sl2) > 0 else (min(o[k], sl2) if s == 1 else max(o[k], sl2))
                break
            if e2 is not None and px2 is None and ((l[k] <= sl2) if s == 1 else (h[k] >= sl2)): px2 = min(o[k], sl2) if s == 1 else max(o[k], sl2)
            best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
            if s * (best - e) >= x * st: armed = True
            if armed and e2 is None and k + 1 < 386 and ((c[k] <= E[k]) if s == 1 else (c[k] >= E[k])):
                e2 = o[k + 1]; sl2 = e2 - s * 2 * a[k + 1]
        if px is None: px = c[385]
        base.append((s * (px - e) - 2.25 * e / 17000) / st)
        if e2 is not None:
            if px2 is None: px2 = px
            add.append((s * (px2 - e2) - 2.25 * e2 / 17000) / abs(e2 - sl2))
    return np.array(base), np.array(add)
if __name__ == "__main__":
  for x in (1.0, 2.0, 3.0):
    line = []
    for nm, rows in A.items():
        b, ad = go(rows, x); line.append(f"{nm}: base={b.mean():+.3f} addon n={len(ad)} win={100*(ad>0).mean():4.1f}% R={ad.mean():+.3f}")
    print(f"add after +{x}R | " + " | ".join(line), flush=True)
