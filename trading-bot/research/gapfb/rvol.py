"""Iter 78 (queue 79) — volume filters for GapFB-C (real NQ 2010–19 user file, MNQ 2020–26; volume of the traded contract):
RVOL15 = volume 09:30–09:44 / mean of the same window over the previous 20 sessions; PRE = volume 08:00–09:29 / its 20-day mean.
Bucketed R of GapFB-C trades per period (features_C.csv trades)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
def vols(f):
    m = f.index.hour * 60 + f.index.minute; d = f.index.normalize().tz_localize(None)
    v15 = f.volume[(m >= 570) & (m < 585)].groupby(d[(m >= 570) & (m < 585)]).sum()
    pre = f.volume[(m >= 480) & (m < 570)].groupby(d[(m >= 480) & (m < 570)]).sum()
    return pd.DataFrame(dict(rvol=v15 / v15.rolling(20).mean().shift(), pre=pre / pre.rolling(20).mean().shift()))
V = pd.concat([vols(pd.read_pickle(SP + "nq16.pkl")[:"2019-12-31"]), vols(pd.read_pickle(SP + "full1m.pkl"))])
T = pd.read_csv("features_C.csv", parse_dates=["day"]).join(V, on="day")
for col in ("rvol", "pre"):
    T["b"] = pd.qcut(T[col], 4)
    print(f"\n## {col}"); print(T.groupby(["b", "per"], observed=True).R.agg(["count", "mean"]).unstack("per").round(3).to_string())
