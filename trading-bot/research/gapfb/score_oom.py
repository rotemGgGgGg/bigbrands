"""Iter 62 — out-of-market check: GapFB-C + quality score ≥ 2 (rules fixed on NQ) applied unchanged to SPX and gold CFDs."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb import prep
from gapfb2 import trade
from load import frame
CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)
for nm, p in (("SPX", "SPXUSD"), ("GOLD", "XAUUSD")):
    days = prep(frame(p)); rows = []; prev = None
    for d, g in days:
        o, h, l, c, a = (g[k].values.astype(float) for k in ("open", "high", "low", "close", "atr"))
        if prev is not None:
            gap = o[0] / prev[3] - 1; r = trade(o, h, l, c, a, gap, *CFG)
            if r is not None:
                s = 1 if gap > 0 else -1
                sc = int(s * (prev[3] - prev[0]) <= 0) + int((s == 1 and o[0] > prev[1]) or (s == -1 and o[0] < prev[2])) + int(s * (c[14] - o[0]) > 0)
                rows.append((d, r, sc))
        prev = (o[0], h.max(), l.min(), c[389])
    T = pd.DataFrame(rows, columns=["day", "R", "score"]); T["per"] = np.select([T.day.dt.year < 2020, T.day.dt.year < 2024], ["2012-19", "2020-23"], "2024-25")
    for k in (0, 2):
        x = T[T.score >= k].groupby("per").R.agg(["count", "mean"]).round(3)
        print(f"{nm} score>={k}: " + " | ".join(f"{p}: n={int(r['count'])} R={r['mean']:+.3f}" for p, r in x.iterrows()))
