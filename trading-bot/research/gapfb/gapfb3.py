"""Iter: filters known BEFORE entry on top of config C (15-min OR, gap direction, stop 2×ATR, 5×ATR trail, entry ≤10:30,
exit 15:55, gap ≥0.3 %). Builds a trade table with features; buckets are judged on TRAIN 2010-19 and VALIDATE 2020-23
separately (TEST 2024-26 not used here)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays, trade
A = arrays(); CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)
V = pd.read_csv("../quant_loop/vix.csv"); V.columns = ["date", "vix"]; V["date"] = pd.to_datetime(V.date)
V = V.set_index("date").vix.apply(pd.to_numeric, errors="coerce").dropna()
rows = []
for per, days in A.items():
    C = np.array([x[5][389] for x in days]); O = np.array([x[2][0] for x in days]); H = np.array([x[3].max() for x in days]); L = np.array([x[4].min() for x in days])
    rng = pd.Series((H - L) / O).rolling(14).mean().shift().values; sma20 = pd.Series(C).rolling(20).mean().values
    for i, (d, g, o, h, l, c, a) in enumerate(days):
        r = trade(o, h, l, c, a, g, *CFG)
        if r is None or i < 21: continue
        s = 1 if g > 0 else -1
        vix = V[:d - pd.Timedelta(days=1)].iloc[-1] if len(V[:d - pd.Timedelta(days=1)]) else np.nan
        orh, orl = h[:15].max(), l[:15].min()
        rows.append(dict(per=per, day=d, R=r, side=s,
            gap_sig=abs(g) / rng[i],                                       # gap in units of the 14-day mean daily range
            beyond=int((s == 1 and o[0] > H[i - 1]) or (s == -1 and o[0] < L[i - 1])),   # opens outside yesterday's range
            trend=int(s * (C[i - 1] - sma20[i - 1]) > 0),                  # gap direction agrees with 20-day trend
            yday=int(s * (C[i - 1] - O[i - 1]) > 0),                       # yesterday's candle in gap direction
            or_dir=int(s * (c[14] - o[0]) > 0),                            # first 15 min close in gap direction
            or_loc=(c[14] - orl) / (orh - orl) if orh > orl else 0.5,      # where the 15-min close sits in the OR (long sense)
            or_w=(orh - orl) / a[14], dow=d.weekday(), vix=vix))
T = pd.DataFrame(rows); T["or_loc_s"] = np.where(T.side == 1, T.or_loc, 1 - T.or_loc); T.to_csv("features_C.csv", index=False)
def show(col, bins=None):
    x = pd.qcut(T[col], bins, duplicates="drop") if bins else T[col]
    G = T[T.per != "2024-26"].groupby([x, "per"]).R.agg(["count", "mean"]).unstack("per").round(3)
    print(f"\n## {col}"); print(G.to_string())
print("baseline", T[T.per != "2024-26"].groupby("per").R.agg(["count", "mean"]).round(3).to_dict())
for col, b in (("gap_sig", 4), ("beyond", None), ("trend", None), ("yday", None), ("or_dir", None), ("or_loc_s", 4), ("or_w", 4), ("dow", None), ("vix", 4)):
    show(col, b)
