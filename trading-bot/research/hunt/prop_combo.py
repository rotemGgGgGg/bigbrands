"""LucidFlex 50K lifecycle (eval → funded payouts) for: pre-open fade alone, NA-FVG alone, and both.
Pre-open fade sized by risk: contracts = floor(risk$ / (stop pts × $2)), skip if even 1 MNQ risks > 1.5 × risk$.
Daily P&L is end-of-day (Lucid Flex max loss is end-of-day trailing)."""
import sys; import os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, ".."), os.path.join(H, "../winrate")]
import numpy as np, pandas as pd
from prop_sim2 import lifecycle, evaluate
from prefade import pre_move, trade
import signals as W
from conservative import bracket_c

s, z = pre_move(60)
sig_days = z[z.abs() > 2.0].index
def fade_daily(risk_usd):
    out = {}
    for d in sig_days:
        stop_pts = abs(s[d]) * 1.0
        n = int(risk_usd // (stop_pts * 2))
        if n == 0:
            if stop_pts * 2 > 1.5 * risk_usd: continue
            n = 1
        out[pd.Timestamp(d.date())] = n * 2 * (trade(d, -int(np.sign(s[d])), abs(s[d]), 0.5, 1.0, 780) - 1.0)
    return pd.Series(out)

t = bracket_c(W.sig_na_fvg(), 0.15, 2.0)
na1 = (2 * t.set_index(pd.to_datetime(t.date)).pts)            # $ per MNQ per day (one trade a day)
idx = pd.to_datetime(pd.Index(W.D.days))
rows = []
for name, fr, nq in (("fade $300", 300, 0), ("fade $500", 500, 0), ("fade $700", 700, 0),
                     ("NA-FVG 2 MNQ", 0, 2), ("NA-FVG 3 MNQ", 0, 3),
                     ("fade $500 + NA-FVG 2", 500, 2), ("fade $500 + NA-FVG 3", 500, 3), ("fade $700 + NA-FVG 2", 700, 2)):
    p = pd.Series(0.0, index=idx)
    if fr: p = p.add(fade_daily(fr).reindex(idx).fillna(0), fill_value=0)
    if nq: p = p.add(nq * na1.reindex(idx).fillna(0), fill_value=0)
    pnl = p.values; low = np.minimum(pnl, 0)
    starts = range(0, len(pnl) - 60, 5)
    r = evaluate(pnl, low, starts, keep=1500)
    yrs = p.groupby(p.index.year).sum()
    cs = p.cumsum()
    r.update(name=name, per_year=round(p.sum() / 6.75), worst_day=round(p.min()), maxdd=round((cs - cs.cummax()).min()),
             trade_days_yr=round((p != 0).sum() / 6.75))
    rows.append(r)
pd.set_option("display.width", 250)
print(pd.DataFrame(rows).set_index("name").to_string())

# time to pass the evaluation, fade alone
for fr in (500, 700):
    p = fade_daily(fr).reindex(idx).fillna(0).values
    T = []
    for st in range(0, len(p) - 60, 5):
        bal = peak = 0.0; mll = -2000.0; best = 0.0
        for i in range(st, len(p)):
            bal += p[i]; best = max(best, p[i]); peak = max(peak, bal)
            mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
            if bal <= mll: T.append(("fail", i - st)); break
            if bal >= 3000 and best <= 0.5 * bal: T.append(("pass", i - st)); break
    T = pd.DataFrame(T, columns=["r", "days"])
    ps = T[T.r == "pass"].days
    print(f"fade ${fr}: completed {len(T)}, passed {round(100*(T.r=='pass').mean(),1)}%, trading days to pass median {ps.median():.0f} "
          f"(≈{ps.median()/21:.1f} months), 75th pct {ps.quantile(.75):.0f}")
