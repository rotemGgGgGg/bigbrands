"""Iter 61 (queue 60) — personal-account Monte-Carlo for GapFB-C + score ≥ 2 (with / without add-on): resample 55 trades a year
from the 2010–26 trade list (10,000 years), risk 1 % of equity per R (compounding). Reports % losing years, median / 5th / 95th
percentile yearly return, median and 95th percentile max drawdown within the year."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
from final import day
T = pd.read_csv("features_C.csv", parse_dates=["day"]); T["score"] = (T.yday == 0).astype(int) + T.beyond + T.or_dir
keep = set(T[T.score >= 2].day); A = arrays(); rng = np.random.default_rng(5)
for add in (False, True):
    R = np.array([x[0] for rows in A.values() for d, g, o, h, l, c, a in rows if d in keep and (x := day(o, h, l, c, a, g, 0, add)) is not None])
    for risk in (0.01, 0.02):
        S = rng.choice(R, size=(10000, 55)); eq = np.cumprod(1 + risk * S, axis=1)
        ret = eq[:, -1] - 1; dd = (1 - eq / np.maximum.accumulate(eq, axis=1)).max(1)
        print(f"add-on={add} risk {risk*100:.0f}%/R: losing years {100*(ret<0).mean():4.1f}% | yearly return median {100*np.median(ret):+.0f}% "
              f"p5 {100*np.percentile(ret,5):+.0f}% p95 {100*np.percentile(ret,95):+.0f}% | max DD median {100*np.median(dd):.0f}% p95 {100*np.percentile(dd,95):.0f}%")
