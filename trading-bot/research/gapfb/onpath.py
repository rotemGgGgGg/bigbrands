"""Iter 66 — overnight path shape on GapFB-C days: share of the gap built late (08:00→09:29) vs early (prior 15:59→02:00),
and whether the 08:30 data move is in the gap direction. Bucketed GapFB-C R per period."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays, trade
from sess24 import build, t2m
CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)
A = arrays(); S = build()
feat = {}
for key in ("A", "B"):
    days, X = S[key]; c = X[:, :, 3]
    for i in range(1, len(days)):
        pc = c[i - 1, t2m("15:59")]; op = X[i, t2m("09:30"), 0]; gap = op - pc
        if gap == 0: continue
        late = (c[i, t2m("09:29")] - c[i, t2m("08:00")]) / gap; early = (c[i, t2m("02:00")] - pc) / gap
        feat[days[i]] = (late, early)
rows = []
for per, rr in A.items():
    for d, g, o, h, l, c, a in rr:
        r = trade(o, h, l, c, a, g, *CFG)
        if r is not None and d in feat: rows.append((per, r, *feat[d]))
T = pd.DataFrame(rows, columns=["per", "R", "late", "early"])
for col in ("late", "early"):
    T["b"] = pd.cut(T[col], [-np.inf, 0, 0.33, 0.66, np.inf])
    print(f"\n## share of gap built {col}"); print(T.groupby(["b", "per"], observed=True).R.agg(["count", "mean"]).unstack("per").round(3).to_string())
