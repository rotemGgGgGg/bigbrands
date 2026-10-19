"""Opex-Friday short at 09:30 (iter 30) on REAL NQ 2010–19 + MNQ 2020–26: stop k·σ, target 2k·σ, exit 15:55; placebo = other Fridays."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
exec(open("../longhist/iter30_calendar.py").read().split("\nres = []")[0].split("exec(open(")[0])
src = open("../longhist/iter30_calendar.py").read(); exec(src[src.index("def cal(days):"):src.index("\nres = []")])
S = build(); R0, X1 = t2m("09:30"), t2m("15:55")
for nm, key, msk in (("2010-19", "A", None), ("2020-23", "B", "lt"), ("2024-26", "B", "ge")):
    days, X = S[key]
    if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
    o, h, l, c = (X[:, :, i] for i in range(4)); C = cal(days); O = o[:, R0]
    sig = pd.Series(np.abs(c[:, X1] / O - 1)).rolling(14).mean().shift().values
    for k in (0.25, 0.4):
        def r(i):
            e = O[i]; st = k * sig[i] * e; sl, tp = e + st, e - 2 * st
            for j in range(R0, X1 + 1):
                if h[i, j] >= sl: return (e - max(o[i, j], sl) - 2.25 * e / 17000) / st
                if l[i, j] <= tp: return (e - tp - 2.25 * e / 17000) / st
            return (e - c[i, X1] - 2.25 * e / 17000) / st
        ok = np.isfinite(sig); op = [r(i) for i in np.nonzero(C["opex"] & ok)[0]]
        fr = [r(i) for i in np.nonzero((days.weekday == 4) & ~C["opex"] & ok)[0]]
        print(f"{nm} k{k}: opex n={len(op)} win={100*np.mean(np.array(op)>0):.0f}% R={np.mean(op):+.3f} | other Fridays R={np.mean(fr):+.3f}", flush=True)
