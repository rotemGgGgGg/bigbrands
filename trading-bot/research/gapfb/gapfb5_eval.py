"""Lucid 50K eval simulation for GapFB-C on NQ (MNQ $2/pt): target +$3,000, EOD trailing drawdown $2,000 (locks at +$100 above
start once balance reaches start+$2,100), 50 % consistency (best day ≤ 50 % of total profit at pass), cost 2.25 pt/contract.
Sizing: contracts = floor(risk$ / (stop_pts × $2)), min 1. Start an attempt on every trading day 2020-01 → 2026-06; report
pass %, median trading days to pass, by risk level. Attempts that run out of data are dropped."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
A = arrays(); CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)
def trade_pts(o, h, l, c, a, gap, orm, direction, stop, be, trail, cut, ex, gmin, gmax):
    if not (gmin <= abs(gap) < gmax): return None
    orh, orl = h[:orm].max(), l[:orm].min(); gs = 1 if gap > 0 else -1
    lvl = orh if gs == 1 else orl; hit = np.nonzero((h[orm:cut + 1] >= lvl) if gs == 1 else (l[orm:cut + 1] <= lvl))[0]
    if not len(hit): return None
    j = hit[0] + orm; s = gs; e = max(orh, o[j]) if s == 1 else min(orl, o[j]); A_ = a[j]; st = stop * A_; sl = e - s * st; best = e
    for k in range(j, ex + 1):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
        best = max(best, h[k]) if s == 1 else min(best, l[k])
        if trail: sl = max(sl, best - trail * A_) if s == 1 else min(sl, best + trail * A_)
    else: px = c[ex]
    return s * (px - e), st
days = [r for rows in A.values() for r in rows]
D = []
for d, g, o, h, l, c, a in days:
    t = trade_pts(o, h, l, c, a, g, *CFG); D.append((d, t))
D = [(d, t) for d, t in D if d >= pd.Timestamp("2020-01-01")]
def attempt(i0, risk):
    bal = 0.0; peak = 0.0; floor = -2000.0; best_day = 0.0; n = 0
    for d, t in D[i0:]:
        n += 1
        if t is not None:
            pts, st = t; q = max(1, int(risk // (st * 2))); pnl = q * (pts - 2.25) * 2
            bal += pnl; best_day = max(best_day, pnl)
        if bal <= floor: return False, n
        peak = max(peak, bal); floor = min(100.0, peak - 2000.0) if peak < 2100 else 100.0
        if bal >= 3000 and best_day <= 0.5 * bal: return True, n
    return None, n
for risk in (100, 200, 300, 400, 600):
    res = [attempt(i, risk) for i in range(0, len(D) - 60, 5)]
    res = [r for r in res if r[0] is not None]; p = [n for ok, n in res if ok]; f = [n for ok, n in res if not ok]
    print(f"risk ${risk:4d}/trade: attempts={len(res)} pass={100*len(p)/len(res):5.1f}%  median days to pass={np.median(p) if p else 0:.0f}  "
          f"median days to fail={np.median(f) if f else 0:.0f}")
