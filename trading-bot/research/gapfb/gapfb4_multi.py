"""GapFB-C on other markets (HistData CFDs, NY time): SPXUSD (S&P 500 ≈ ES), XAUUSD (gold ≈ GC), plus NQ.
Same rules as config C; cost 0.013 % of price per round trip (≈ 2.25 NQ pt at 17,000). Periods 2012-19 / 2020-23 / 2024-25.
Portfolio = equal 1 R per market per trade, daily sums → total, max drawdown."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb import prep
from gapfb2 import arrays, trade
from load import frame
CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)
def rows_of(days):
    out = []; prev = None
    for d, g in days:
        o, h, l, c, a = (g[k].values.astype(float) for k in ("open", "high", "low", "close", "atr"))
        if prev is not None: out.append((d, o[0] / prev - 1, o, h, l, c, a))
        prev = c[389]
    return out
M = {"NQ": [r for rows in arrays().values() for r in rows if r[0].year >= 2012]}
for nm, p in (("SPX", "SPXUSD"), ("GOLD", "XAUUSD")): M[nm] = rows_of(prep(frame(p)))
allt = []
for nm, rows in M.items():
    for d, g, o, h, l, c, a in rows:
        r = trade(o, h, l, c, a, g, *CFG)
        if r is not None: allt.append((nm, d, r))
T = pd.DataFrame(allt, columns=["mkt", "day", "R"]); T = T[T.day.dt.year <= 2025]
T["per"] = np.select([T.day.dt.year < 2020, T.day.dt.year < 2024], ["2012-19", "2020-23"], "2024-25")
G = T.groupby(["mkt", "per"]).R.agg(n="count", win=lambda x: round(100 * (x > 0).mean(), 1), R="mean").round(3)
print(G.unstack("per").to_string())
for combo in (["NQ"], ["NQ", "SPX"], ["NQ", "GOLD"], ["NQ", "SPX", "GOLD"]):
    X = T[T.mkt.isin(combo)].groupby("day").R.sum().sort_index(); eq = X.cumsum()
    y = X.groupby(X.index.year).sum()
    print(f"{'+'.join(combo):14s} total={X.sum():+.0f}R maxDD={(eq.cummax()-eq).max():.1f}R return/DD={X.sum()/(eq.cummax()-eq).max():.1f} "
          f"years+ {(y>0).sum()}/{len(y)}")
