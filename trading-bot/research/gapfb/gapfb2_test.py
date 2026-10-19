"""Step 3: TEST 2024-26, opened once, for three configs fixed BEFORE looking (all from the dominant TRAIN+VALIDATE family):
A simplest: 15-min OR, gap direction only, stop 2×ATR, entries until 10:30, exit 15:55, gap ≥ 0.3 %
B = A + stop to break-even after +2 R          C = A + 5×ATR trailing stop
Also: per-year R, max drawdown, longest losing streak over 2010-26."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays, trade
A = arrays()
CFG = {"A simple": (15, "with", 2.0, 0, 0, 60, 385, 0.003, 1.0), "B +BE@2R": (15, "with", 2.0, 2.0, 0, 60, 385, 0.003, 1.0),
       "C +trail5ATR": (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)}
for nm, cfg in CFG.items():
    allr = []
    print(f"=== {nm}")
    for per, rows in A.items():
        R = []; 
        for d, g, o, h, l, c, a in rows:
            r = trade(o, h, l, c, a, g, *cfg)
            if r is not None: R.append(r); allr.append((d, r))
        R = np.array(R); w = R > 0; yrs = (rows[-1][0] - rows[0][0]).days / 365.25
        print(f"  {per}: n={len(R)} ({len(R)/yrs:.0f}/yr) win={100*w.mean():.1f}% rr={R[w].mean()/-R[~w].mean():.2f} avgR={R.mean():+.3f} t={R.mean()/R.std()*np.sqrt(len(R)):.2f}")
    T = pd.DataFrame(allr, columns=["day", "R"]); r = T.R.values; eq = np.cumsum(r)
    ls = max(len(x) for x in "".join("L" if v <= 0 else "W" for v in r).split("W"))
    y = T.groupby(T.day.dt.year).R.sum()
    print(f"  ALL: n={len(r)} avgR={r.mean():+.3f} total={r.sum():+.0f}R maxDD={(np.maximum.accumulate(eq)-eq).max():.1f}R streak={ls} "
          f"years+ {(y>0).sum()}/{len(y)} |", " ".join(f"{i}:{v:+.0f}" for i, v in y.items()))
    T.to_csv(f"final_{nm.split()[0]}.csv", index=False)
