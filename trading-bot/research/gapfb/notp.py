"""Variant described by the user (from the author's YouTube video): same GapFB entries, stop k×ATR(14, 1-min) at the fill,
NO take-profit, exit at a fixed clock time (or at the stop). Three periods. Reports win rate, avg win / avg loss (R:R), avg R."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb import prep, run, SP, periods
from load import frame
sets = periods()
rows = []
for (nm, dd), k, ex, mt in itertools.product(sets.items(), (1.0, 2.0, 3.0), (60, 90, 150, 270, 385), (1, 2)):
    T = run(dd, 0.003, 385, ex, mt, k, 1e9)
    if not len(T): continue
    w = T.R > 0; yrs = (T.day.max() - T.day.min()).days / 365.25
    rows.append(dict(per=nm, sl_atr=k, exit=f"{(570+ex)//60}:{(570+ex)%60:02d}", max_tr=mt, n_yr=round(len(T) / yrs),
                     win=round(100 * w.mean(), 1), rr=round(T.R[w].mean() / -T.R[~w].mean(), 2), R=round(T.R.mean(), 3)))
X = pd.DataFrame(rows); X.to_csv("notp_results.csv", index=False)
P = X.pivot_table(index=["sl_atr", "exit", "max_tr"], columns="per", values=["win", "rr", "R"])
P["minR"] = P["R"].min(axis=1); pd.set_option("display.width", 250)
print(P.sort_values("minR", ascending=False).round(2).to_string())
