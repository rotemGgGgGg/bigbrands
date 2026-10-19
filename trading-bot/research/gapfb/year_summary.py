"""Per-year results of the final NQ portfolio (GapFB-score + Pre-Fade + Opex short), real NQ 2010–19 + MNQ 2020–26.
Writes year_summary.csv and prints the tables used in trading-bot/RESULTS_BY_YEAR.md."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
exec(open("portfolio2.py").read().split("print(\"OPEX corr")[0])          # builds T (day, edge, R) and P (daily pivot)
E = {"GapFB-score": "GapFB", "PF": "PreFade", "OPEX": "Opex"}
T = T[T.edge.isin(E)].copy(); T["edge"] = T.edge.map(E); T["yr"] = pd.DatetimeIndex(T.day).year
def stats(R):
    R = np.asarray(R); w = R > 0
    return len(R), 100 * w.mean(), (R[w].mean() / -R[~w].mean()) if w.any() and (~w).any() else np.nan, R.sum()
print("== per strategy (2010–2026)")
for e, g in T.groupby("edge"):
    n, win, rr, tot = stats(g.R); yrs = g.yr.nunique()
    print(f"{e}: n={n} win={win:.0f}% R:R=1:{rr:.2f} trades/yr={n/16.3:.0f} totalR={tot:+.0f}")
rows = []
for y, g in T.groupby("yr"):
    n, win, rr, tot = stats(g.R)
    rows.append(dict(year=y, GapFB=g[g.edge == "GapFB"].R.sum(), PreFade=g[g.edge == "PreFade"].R.sum(), Opex=g[g.edge == "Opex"].R.sum(),
                     trades=n, win=win, rr=rr, total_R=tot, pct_1=tot, usd_500=tot * 5, usd_10k=tot * 100))
Y = pd.DataFrame(rows).round(1); Y.to_csv("year_summary.csv", index=False); print(Y.to_string(index=False))
x = T.groupby("day").R.sum().sort_index(); eq = x.cumsum()
ls = max(len(s) for s in "".join("L" if v <= 0 else "W" for v in T.sort_values("day").R).split("W"))
n, win, rr, tot = stats(T.R)
print(f"ALL: trades {n} win {win:.0f}% R:R 1:{rr:.2f} total {tot:+.0f}R maxDD {(eq.cummax()-eq).max():.1f}R years+ {(Y.total_R>0).sum()}/{len(Y)} streak {ls}")
