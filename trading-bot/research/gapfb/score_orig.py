"""Iter 63 — quality score on the ORIGINAL alert-bot GapFB (5-min OR, both sides, 2 trades/day, 2:1 target) and its no-TP
variant (3×ATR stop, exit 15:55, 1 trade). The OR-direction point uses the first 5 minutes (known at 09:35, no look-ahead)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb import run, periods
P = periods()
for nm, dd in P.items():
    sc = {}; prev = None
    for d, g in dd:
        o, h, l, c = (g[k].values for k in ("open", "high", "low", "close"))
        if prev is not None:
            gap = o[0] / prev[3] - 1; s = 1 if gap > 0 else -1
            sc[d] = int(s * (prev[3] - prev[0]) <= 0) + int((s == 1 and o[0] > prev[1]) or (s == -1 and o[0] < prev[2])) + int(s * (c[4] - o[0]) > 0)
        prev = (o[0], h.max(), l.min(), c[389])
    for label, kw in (("alert bot 2:1", dict(thr=0.003)), ("no-TP 3ATR 15:55 1/day", dict(thr=0.003, cut=385, tlast=385, max_tr=1, sl_atr=3.0, rr=1e9))):
        T = run(dd, **kw); T["score"] = T.day.map(sc)
        out = [f"score>={k}: n={len(x)} win={100*(x.R>0).mean():4.1f}% R={x.R.mean():+.3f}" for k in (0, 2) for x in [T[T.score >= k]]]
        print(f"{nm} {label:24s} | " + " | ".join(out), flush=True)
