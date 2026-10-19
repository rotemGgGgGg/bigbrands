"""Export the GapFB-NQ (score ≥ 2) trade list with timestamps/prices for comparison with TradingView or manual trades.
Usage: python3 export_trades.py 2025-01-01 2026-10-06  → trades_compare.csv (NY time; MNQ prices = NQ prices)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
a0, a1 = pd.Timestamp(sys.argv[1]), pd.Timestamp(sys.argv[2])
rows_all = [r for rr in arrays().values() for r in rr]
out = []
for i in range(1, len(rows_all)):
    d, g, o, h, l, c, a = rows_all[i]
    if not (a0 <= d <= a1) or abs(g) < 0.003: continue
    _, _, po, ph, pl, pc, _ = rows_all[i - 1]; s = 1 if g > 0 else -1
    score = int(s * (pc[389] - po[0]) <= 0) + int((s == 1 and o[0] > ph.max()) or (s == -1 and o[0] < pl.min())) + int(s * (c[14] - o[0]) > 0)
    orh, orl = h[:15].max(), l[:15].min(); lvl = orh if s == 1 else orl
    base = dict(date=d.date(), gap_pct=round(100 * g, 2), side="LONG" if s == 1 else "SHORT", score=score, or_high=orh, or_low=orl, order_level=lvl)
    if score < 2: out.append(dict(base, result="skipped (score<2)")); continue
    win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
    if not win.any(): out.append(dict(base, result="no fill by 10:30")); continue
    j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A = a[j]; st = 2 * A; sl = e - s * st; best = e; px = None; why = "15:55"
    for k in range(j, 386):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); why = "stop/trail"; break
        best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A) if s == 1 else min(sl, best + 5 * A)
    else: k = 385
    if px is None: px = c[385]
    t = lambda m: f"{(570 + m)//60:02d}:{(570 + m)%60:02d}"
    pts = s * (px - e); out.append(dict(base, fill_time=t(j), entry=round(e, 2), atr=round(A, 2), init_stop=round(e - s * st, 2),
                                        exit_time=t(k), exit=round(px, 2), exit_reason=why, pts=round(pts, 2), R=round((pts - 2.25) / st, 2),
                                        usd_1MNQ=round((pts - 2.25) * 2, 2), result="trade"))
T = pd.DataFrame(out); T.to_csv("trades_compare.csv", index=False)
x = T[T.result == "trade"]; print(T.result.value_counts().to_string()); print(f"trades {len(x)} win {100*(x.R>0).mean():.0f}% avg R {x.R.mean():+.2f} total ${x.usd_1MNQ.sum():,.0f} per 1 MNQ")
print(x.tail(8)[["date", "side", "fill_time", "entry", "init_stop", "exit_time", "exit", "exit_reason", "R"]].to_string(index=False))
