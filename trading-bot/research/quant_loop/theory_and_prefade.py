"""(1) Brownian-motion bound: drift needed for P(+2d before −d) = 70 %.  (2) The one validated edge (pre-open fade) forced into 1:2."""
import sys, os; sys.path.insert(0, "../hunt"); sys.path.insert(0, "..")
import numpy as np, pandas as pd
from scipy.optimize import brentq
P = lambda x: (1 - np.exp(x)) / (np.exp(-2 * x) - np.exp(x))      # x = 2·mu·d/sigma^2, barriers +2d / −d
x70 = brentq(lambda x: P(x) - 0.7, 1e-6, 10); x0 = 1e-9
print(f"no drift: P = {P(1e-9):.3f} (theory 1/3). Needed x = 2·mu·d/sigma² = {x70:.2f} for 70 %.")
for x in (0.05, 0.1, 0.2, 0.3, 0.5): print(f"  x={x}: P(+2 before −1) = {P(x):.3f}")
from prefade import pre_move, trade
s, z = pre_move(60)
rows = []
for zt in (1.5, 2.0, 2.5):
    for a in (0.5, 0.75, 1.0, 1.5):
        b = a / 2                                    # planned 1:2
        R = []
        for d in z[z.abs() > zt].index:
            R.append(((trade(d, -int(np.sign(s[d])), abs(s[d]), a, b, 780)) - 1.0) / (b * abs(s[d])))   # +1 pt stress
        R = pd.Series(R, index=z[z.abs() > zt].index)
        for nm, part in (("2020-23", R.index.year < 2024), ("2024-25H1", (R.index >= pd.Timestamp("2024-01-01", tz=R.index.tz)) & (R.index < pd.Timestamp("2025-07-01", tz=R.index.tz))),
                         ("2025H2-26", R.index >= pd.Timestamp("2025-07-01", tz=R.index.tz))):
            x = R[part]; w = x[x > 0]; lo = x[x <= 0]
            rows.append(dict(z=zt, tp_move=a, sl_move=b, period=nm, n=len(x), win=round(100 * (x > 0).mean(), 1),
                             realized_rr=round(w.mean() / -lo.mean(), 2) if len(lo) else np.nan, exp_R=round(x.mean(), 3)))
pd.set_option("display.width", 200); print(pd.DataFrame(rows).to_string(index=False))
