"""Portfolio of every edge that survived out-of-sample, 1 MNQ each (fade risk-sized), and the LucidFlex lifecycle.
Lesson from practitioners: several small uncorrelated edges beat one 'crazy' strategy."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, ".."), os.path.join(H, "../winrate")]
import numpy as np, pandas as pd
import signals as W
from conservative import bracket_c
from prefade import pre_move, trade
from prop_sim2 import lifecycle, evaluate
idx = pd.to_datetime(pd.Index(W.D.days))
def daily(t): return (2 * t.set_index(pd.to_datetime(t.date)).pts).groupby(level=0).sum().reindex(idx).fillna(0)
comp = {}
comp["NA-FVG"] = daily(bracket_c(W.sig_na_fvg(), 0.15, 2.0))
comp["Afternoon momo"] = daily(W.bracket(W.sig_afternoon(), None, None))
comp["Rebound −1% (to 12:00)"] = daily(W.bracket(W.sig_rebound(), None, None, last=149))
s, z = pre_move(60)
f = {pd.Timestamp(d.date()): 2 * (trade(d, -int(np.sign(s[d])), abs(s[d]), 0.5, 1.0, 780) - 1.0) for d in z[z.abs() > 2].index}
comp["Pre-open fade"] = pd.Series(f).reindex(idx).fillna(0)
P = pd.DataFrame(comp)
isd = P.index.year < 2024
rows = []
for c in P.columns:
    x = P[c][P[c] != 0]
    rows.append(dict(edge=c, trades_yr=round(len(x) / 6.75), win=round(100 * (x > 0).mean()), avg=round(x.mean(), 1),
                     IS=round(P[c][isd][P[c][isd] != 0].mean(), 1), OOS=round(P[c][~isd][P[c][~isd] != 0].mean(), 1),
                     per_yr=round(x.sum() / 6.75), maxdd=round((x.cumsum() - x.cumsum().cummax()).min())))
print(pd.DataFrame(rows).to_string(index=False))
print("\ncorrelation of daily P&L (days where both trade):")
print(P.replace(0, np.nan).corr().round(2).to_string())
tot = P.sum(1)
x = tot[tot != 0]; cs = tot.cumsum()
print(f"\nPORTFOLIO 1 MNQ each: trade days/yr {len(x)/6.75:.0f}, winning days {100*(x>0).mean():.0f}%, $/yr {tot.sum()/6.75:.0f}, "
      f"IS $/yr {tot[isd].sum()/4:.0f}, OOS $/yr {tot[~isd].sum()/2.75:.0f}, maxDD {(cs-cs.cummax()).min():.0f}, worst day {tot.min():.0f}, "
      f"years positive {(tot.groupby(tot.index.year).sum()>0).sum()}/7, monthly positive {100*(tot.resample('ME').sum()>0).mean():.0f}%")
for mult in (1, 2, 3):
    pnl = (mult * tot).values; low = np.minimum(pnl, 0)
    starts = range(0, len(pnl) - 60, 5)
    T = []
    for st in starts:
        bal = peak = best = 0.0; mll = -2000.0
        for i in range(st, len(pnl)):
            bal += pnl[i]; best = max(best, pnl[i]); peak = max(peak, bal); mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
            if bal <= mll: T.append(("fail", i - st)); break
            if bal >= 3000 and best <= 0.5 * bal: T.append(("pass", i - st)); break
    T = pd.DataFrame(T, columns=["r", "d"]); ps = T[T.r == "pass"].d
    ev = evaluate(pnl, low, starts, keep=1500)
    print(f"x{mult} MNQ each: eval pass {100*(T.r=='pass').mean():.0f}%, median {ps.median():.0f} trading days (≈{ps.median()/21:.1f} months), "
          f"payout reached {ev['payout']}%, EV per account ${ev['ev']}")
