"""Per-year R, longest losing streak, max drawdown (R) for the two leading no-TP configs, 2010-26, 1 trade/day."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb import run, periods
dd = sum(periods().values(), [])
for k, ex, thr in ((3.0, 385, 0.003), (3.0, 150, 0.003), (3.0, 385, 0.005)):
    T = run(dd, thr, 385, ex, 1, k, 1e9); r = T.R.values
    eq = np.cumsum(r); mdd = (np.maximum.accumulate(eq) - eq).max()
    ls = max(len(x) for x in "".join("L" if v <= 0 else "W" for v in r).split("W"))
    y = T.groupby(T.day.dt.year).R.agg(["count", "mean", "sum"]).round(2)
    w = r > 0
    print(f"=== stop {k}×ATR exit {(570+ex)//60}:{(570+ex)%60:02d} gap≥{thr*100:.1f}%: n={len(r)} win={100*w.mean():.1f}% "
          f"rr={r[w].mean()/-r[~w].mean():.2f} avgR={r.mean():+.3f} totalR={r.sum():+.0f} maxDD={mdd:.1f}R longest losing streak={ls}")
    print("   years positive:", (y["sum"] > 0).sum(), "of", len(y), "|", " ".join(f"{i}:{s:+.0f}" for i, s in y["sum"].items()))
    T.to_csv(f"notp_trades_k{k}_ex{ex}_g{thr}.csv", index=False)
