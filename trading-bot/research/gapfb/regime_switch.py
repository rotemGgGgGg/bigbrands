"""Iter 87 — regime switch: trade the non-gap OR-follow (and separately GapFB-C) only when the same rule's trailing N trades
(past only) have mean R > 0. No look-ahead: the switch uses closed trades before the day. N = 20 / 40 / 60."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
A = arrays()
def series(rows, gapmode):
    out = []
    for d, g, o, h, l, c, a in rows:
        if (gapmode == "nogap") == (abs(g) >= 0.003): continue
        s = (1 if g > 0 else -1) if gapmode == "gap" else (1 if c[14] > o[0] else -1)
        orh, orl = h[:15].max(), l[:15].min(); lvl = orh if s == 1 else orl
        win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
        if not win.any(): continue
        j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e; px = None
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
            best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
        if px is None: px = c[385]
        out.append((d, (s * (px - e) - 2.25 * e / 17000) / st))
    return pd.Series(dict(out))
for gm in ("nogap", "gap"):
    S = pd.concat([series(rows, gm) for rows in A.values()]).sort_index()
    for N in (0, 20, 40, 60):
        x = S if N == 0 else S[(S.rolling(N).mean().shift() > 0).values]
        per = {p: x[(x.index.year >= a) & (x.index.year <= b)] for p, (a, b) in {"2010-19": (2010, 2019), "2020-23": (2020, 2023), "2024-26": (2024, 2026)}.items()}
        print(f"{gm:5s} switch N={N:2d} | " + " | ".join(f"{p}: n={len(v)} R={v.mean():+.3f}" for p, v in per.items()), flush=True)
