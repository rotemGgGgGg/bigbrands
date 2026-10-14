"""R-based view of the pre-open fade: risk = b·|pre-move| points. Fixed-$ risk sizing on MNQ."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from prefade import pre_move, trade, DAYS
pd.set_option("display.width", 250)
def runR(L, zt, a, b, te, extra=0.0):
    s, z = pre_move(L); out = []
    for d in z[z.abs() > zt].index:
        risk = b * abs(s[d]); pts = trade(d, -int(np.sign(s[d])), abs(s[d]), a, b, te) - extra
        out.append((d, pts, risk, pts / risk))
    return pd.DataFrame(out, columns=["d", "pts", "risk", "R"]).set_index("d")
rows = []
for L, zt in ((60, 1.5), (60, 2.0), (90, 1.75), (90, 2.0)):
    for a, b in ((0.5, 1.0), (0.5, 1.5), (0.75, 1.0), (0.75, 1.5), (1.0, 1.0), (1.0, 1.5)):
        x = runR(L, zt, a, b, 780, extra=1.0)       # +1 pt extra slippage as the base case
        isd = x.index.year < 2024; R = x.R
        cs = R.cumsum(); st = cur = ls = lc = 0
        for v in R: cur = cur + 1 if v > 0 else 0; st = max(st, cur); lc = lc + 1 if v <= 0 else 0; ls = max(ls, lc)
        rows.append(dict(L=L, z=zt, tp=a, sl=b, n=len(x), per_yr=round(len(x) / 6.75, 1), win=round(100 * (R > 0).mean(), 1),
                         avgR=round(R.mean(), 3), IS_R=round(R[isd].mean(), 3), OOS_R=round(R[~isd].mean(), 3),
                         RR=round(R[R > 0].mean() / -R[R <= 0].mean(), 2), totR=round(R.sum(), 1), maxddR=round((cs - cs.cummax()).min(), 1),
                         wst=st, lst=ls, med_stop_pts=round(x.risk.median()), p90_stop=round(x.risk.quantile(.9))))
print(pd.DataFrame(rows).to_string())
