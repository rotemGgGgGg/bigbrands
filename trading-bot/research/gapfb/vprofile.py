"""Iter 79 (queue 80) — prior-day RTH volume profile (real volume; bins = 0.02 % of price) vs the 09:30 open on GapFB-C days:
loc = open relative to yesterday's value area (70 %) in the gap direction: 'beyond VA', 'inside VA'; and |open − POC| in ATR-day units.
Bucketed GapFB-C R per period."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
def prof(f):
    m = f.index.hour * 60 + f.index.minute; r = f[(m >= 570) & (m < 960)]; out = {}
    for d, g in r.groupby(r.index.normalize().tz_localize(None)):
        b = g.close.iloc[0] * 0.0002; px = np.round(g.close.values / b) * b; vol = pd.Series(g.volume.values).groupby(px).sum().sort_index()
        poc = vol.idxmax(); tot = vol.sum(); P = vol.index.values; V = vol.values; i = np.argmax(V); lo = hi = i; acc = V[i]
        while acc < 0.7 * tot and (lo > 0 or hi < len(V) - 1):
            up = V[hi + 1] if hi < len(V) - 1 else -1; dn = V[lo - 1] if lo > 0 else -1
            if up >= dn: hi += 1; acc += up
            else: lo -= 1; acc += dn
        out[d] = (poc, P[lo], P[hi], g.high.max() - g.low.min())
    return out
PR = {**prof(pd.read_pickle(SP + "nq16.pkl")[:"2019-12-31"]), **prof(pd.read_pickle(SP + "full1m.pkl"))}
days = sorted(PR); prev = {days[i]: PR[days[i - 1]] for i in range(1, len(days))}
T = pd.read_csv("features_C.csv", parse_dates=["day"])
rows = []
for _, t in T.iterrows():
    if t.day not in prev: continue
    poc, val, vah, rng = prev[t.day]
    # open price is not in features_C → reconstruct from gap sign + 'beyond' is RTH range; use the cached RTH arrays instead
    rows.append((t.day, poc, val, vah, rng))
P = pd.DataFrame(rows, columns=["day", "poc", "val", "vah", "rng"])
from gapfb2 import arrays
op = {d: o[0] for rr in arrays().values() for d, g, o, h, l, c, a in rr}
T = T.merge(P, on="day"); T["open"] = T.day.map(op)
T["beyondVA"] = np.where(T.side == 1, T.open > T.vah, T.open < T.val).astype(int)
T["pocdist"] = (T.side * (T.open - T.poc)) / T.rng
print(T.groupby(["beyondVA", "per"]).R.agg(["count", "mean"]).unstack("per").round(3).to_string())
T["b"] = pd.qcut(T.pocdist, 4); print(T.groupby(["b", "per"], observed=True).R.agg(["count", "mean"]).unstack("per").round(3).to_string())
