"""Iter 77 (queue 78) — opex short refinement: entry 09:30 / 09:45 / 10:00 / 13:00, stop k·σ, target r×stop, exit 12:00 / 15:55.
Train 2010–19 → validate 2020–23 → test 2024–26 for the top 3 + base (09:30, k0.4, r2, 15:55)."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
src = open("../longhist/iter30_calendar.py").read(); exec(src[src.index("def cal(days):"):src.index("\nres = []")])
S = build(); R0, X1 = t2m("09:30"), t2m("15:55")
def split(key, msk):
    days, X = S[key]
    if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
    return days, X
def run(days, X, en, k, r, ex):
    o, h, l, c = (X[:, :, i] for i in range(4)); C = cal(days); O = o[:, R0]; t0, te = t2m(en), t2m(ex)
    sig = pd.Series(np.abs(c[:, X1] / O - 1)).rolling(14).mean().shift().values; R = []
    for i in np.nonzero(C["opex"] & np.isfinite(sig))[0]:
        e = o[i, t0]; st = k * sig[i] * O[i]; sl, tp = e + st, e - r * st; v = None
        for j in range(t0, te + 1):
            if h[i, j] >= sl: v = (e - max(o[i, j], sl)); break
            if l[i, j] <= tp: v = (e - tp); break
        if v is None: v = e - c[i, te]
        R.append((v - 2.25 * e / 17000) / st)
    return np.array(R)
TR, VA, TE = split("A", None), split("B", "lt"), split("B", "ge"); rows = []
for en, k, r, ex in itertools.product(("09:30", "09:45", "10:00", "13:00"), (0.25, 0.4, 0.6, 0.8), (1.0, 2.0, 3.0), ("12:00", "15:55")):
    if t2m(ex) <= t2m(en): continue
    R = run(*TR, en, k, r, ex); V = run(*VA, en, k, r, ex)
    rows.append(dict(en=en, k=k, r=r, ex=ex, n=len(R), win=100 * (R > 0).mean(), R=R.mean(), t=R.mean() / R.std() * np.sqrt(len(R)),
                     R_val=V.mean(), t_val=V.mean() / V.std() * np.sqrt(len(V))))
T = pd.DataFrame(rows).sort_values("t", ascending=False); pd.set_option("display.width", 250)
print(T.head(12).round(3).to_string(index=False))
K = T[T.t_val > 1].head(3)
print("\nTEST 2024-26:")
for _, x in pd.concat([K, pd.DataFrame([dict(en="09:30", k=0.4, r=2.0, ex="15:55")])]).iterrows():
    R = run(*TE, x.en, x.k, x.r, x.ex); print(f"  {x.en} k{x.k} r{x.r} exit {x.ex}: n={len(R)} win={100*(R>0).mean():.0f}% R={R.mean():+.3f}")
