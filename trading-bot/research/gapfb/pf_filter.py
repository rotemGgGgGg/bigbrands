"""Iter 70 — Pre-Fade filtered by the overnight move known at 08:59: |c(08:59)/prior RTH close − 1| < x (small 'gap so far').
GapFB days (gap ≥0.3 %) were where PF lost (−0.31 R vs +0.23 R). Three periods, real NQ."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from portfolio_edges import run, S
from sess24 import t2m
for x in (None, 0.002, 0.003, 0.005, 0.008):
    line = []
    for nm, key, msk in (("2010-19", "A", None), ("2020-23", "B", "lt"), ("2024-26", "B", "ge")):
        days, X = S[key]
        if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
        pf = dict(run(days, X)["PF"]); c = X[:, :, 3]; idx = {d: i for i, d in enumerate(days)}
        R = []
        for d, r in pf.items():
            i = idx[d]
            if i == 0: continue
            g = c[i, t2m("08:59")] / c[i - 1, t2m("15:59")] - 1
            if x is None or abs(g) < x: R.append(r)
        R = np.array(R); line.append(f"{nm}: n={len(R)} win={100*(R>0).mean():4.1f}% R={R.mean():+.3f}")
    print(f"PF |ON move|<{x} | " + " | ".join(line), flush=True)
