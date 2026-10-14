import numpy as np, pandas as pd
from signals import *
sg = sig_na_fvg()
print("scale (points): median", round(np.nanmedian([day_sig[i] * D.o[i, 0] for i, *_ in sg]), 1))
def stats(t, cost_extra=0.0):
    p = t.pts - cost_extra; y = pd.to_datetime(t.date); w, l = p[p > 0], p[p <= 0]
    st = cur = ls = lc = 0
    for v in p:
        cur = cur + 1 if v > 0 else 0; st = max(st, cur); lc = lc + 1 if v <= 0 else 0; ls = max(ls, lc)
    return dict(n=len(p), win=round(100 * (p > 0).mean(), 1), avg_usd=round(2 * p.mean(), 1), avg_win=round(2 * w.mean()), avg_loss=round(2 * l.mean()),
                worst=round(2 * p.min()), IS=round(2 * p[y < IS_END].mean(), 1), OOS=round(2 * p[y >= IS_END].mean(), 1),
                yrs=f"{int((p.groupby(y.dt.year).sum() > 0).sum())}/7", maxdd=round(2 * (p.cumsum() - p.cumsum().cummax()).min()), win_streak=st, loss_streak=ls,
                pf=round(w.sum() / -l.sum(), 2))
rows = []
for a in (0.1, 0.125, 0.15, 0.175, 0.2):
    for b in (1.5, 2.0, 2.5, 3.0, None):
        rows.append(dict(tp=a, sl=b, **stats(bracket(sg, a, b))))
r = pd.DataFrame(rows); print(r.to_string(index=False))
t = bracket(sg, 0.15, 2.5)
print("\nchosen 0.15/2.5 with +1 extra point cost (2.25 pt RT):", stats(t, 1.0))
print("by year $:", (2 * t.pts).groupby(pd.to_datetime(t.date).dt.year).sum().round().to_dict())
print("trades/month:", round(len(t) / 81, 1))
for w_ in (30, 120):
    print(f"FVG window {w_} min:", stats(bracket(sig_na_fvg(w_), 0.15, 2.5)))
