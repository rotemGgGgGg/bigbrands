import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, ".."), os.path.join(H, "../winrate")]
import numpy as np, pandas as pd
import signals as W
from conservative import bracket_c
from prefade import pre_move, trade
s, z = pre_move(60)
E = {"NA-FVG": 2 * bracket_c(W.sig_na_fvg(), 0.15, 2.0).pts,
     "Pre-open fade": pd.Series([2 * (trade(d, -int(np.sign(s[d])), abs(s[d]), 0.5, 1.0, 780) - 1.0) for d in z[z.abs() > 2].index]),
     "Afternoon": 2 * W.bracket(W.sig_afternoon(), None, None).pts,
     "Rebound": 2 * W.bracket(W.sig_rebound(), None, None, last=149).pts}
E["ALL (per trade)"] = pd.concat(E.values(), ignore_index=True)
for k, x in E.items():
    w, l = x[x > 0], x[x <= 0]
    print(f"{k:16s} win {100*(x>0).mean():.0f}%  avg win ${w.mean():.0f}  avg loss ${l.mean():.0f}  RR 1:{w.mean()/-l.mean():.2f}  PF {w.sum()/-l.sum():.2f}  breakeven win {100/(1+w.mean()/-l.mean()):.0f}%")
