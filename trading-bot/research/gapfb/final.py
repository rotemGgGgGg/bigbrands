"""GapFB-NQ final candidate: gap ≥0.3 % (09:30 open vs prior 15:59 close); 15-min OR (09:30–09:44); trade only in the gap
direction; skip if OR width < W×ATR(14, 1-min) at 09:45; resting stop entry at the OR level until 10:30; stop 2×ATR at the
fill; 5×ATR trailing stop; add-on: after +1 R, add 1 unit at the next open after the first 1-min close back to the 20-EMA
(own 2×ATR stop, exits with the trail); flat 15:55. Cost 2.25 NQ pt per unit round trip (scaled by price)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
def ema(x, n): return pd.Series(x).ewm(span=n, adjust=False).mean().values
def day(o, h, l, c, a, g, W, addon=True):
    if abs(g) < 0.003: return None
    s = 1 if g > 0 else -1; orh, orl = h[:15].max(), l[:15].min()
    if (orh - orl) < W * a[15]: return None
    lvl = orh if s == 1 else orl; win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
    if not win.any(): return None
    j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e
    E = ema(c, 20); armed = False; e2 = sl2 = px2 = px = None
    for k in range(j, 386):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl):
            px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl))
            if e2 is not None and px2 is None: px2 = px if s * (px - sl2) > 0 else (min(o[k], sl2) if s == 1 else max(o[k], sl2))
            break
        if e2 is not None and px2 is None and ((l[k] <= sl2) if s == 1 else (h[k] >= sl2)): px2 = min(o[k], sl2) if s == 1 else max(o[k], sl2)
        best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
        if s * (best - e) >= st: armed = True
        if addon and armed and e2 is None and k + 1 < 386 and ((c[k] <= E[k]) if s == 1 else (c[k] >= E[k])):
            e2 = o[k + 1]; sl2 = e2 - s * 2 * a[k + 1]
    if px is None: px = c[385]
    r = (s * (px - e) - 2.25 * e / 17000) / st
    if e2 is not None:
        if px2 is None: px2 = px
        r += (s * (px2 - e2) - 2.25 * e2 / 17000) / abs(e2 - sl2)
    return r, r if e2 is None else None
if __name__ == "__main__":
    A = arrays()
    for W, add in ((0, False), (0, True), (3.5, False), (3.5, True), (4, False), (4, True)):
        allr = []; line = []
        for per, rows in A.items():
            R = []
            for d, g, o, h, l, c, a in rows:
                x = day(o, h, l, c, a, g, W, add)
                if x is not None: R.append(x[0]); allr.append((d, x[0]))
            R = np.array(R); w = R > 0; yrs = (rows[-1][0] - rows[0][0]).days / 365.25
            line.append(f"{per}: {len(R)/yrs:.0f}/yr win={100*w.mean():4.1f}% rr={R[w].mean()/-R[~w].mean():.2f} R/day={R.mean():+.3f}")
        T = pd.DataFrame(allr, columns=["day", "R"]); r = T.R.values; eq = np.cumsum(r)
        ls = max(len(x) for x in "".join("L" if v <= 0 else "W" for v in r).split("W")); y = T.groupby(T.day.dt.year).R.sum()
        print(f"W{W} addon={add}: " + " | ".join(line))
        print(f"    total {r.sum():+.0f}R  maxDD {(np.maximum.accumulate(eq)-eq).max():.1f}R  streak {ls}  years+ {(y>0).sum()}/{len(y)}  "
              + " ".join(f"{i}:{v:+.0f}" for i, v in y.items()), flush=True)
