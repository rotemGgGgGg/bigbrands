"""Iter 72 (queue 73) — portfolio v2 on real NQ 2010–26: GapFB-score + Pre-Fade + opex-Friday short (+ WVB / OD options)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from portfolio_edges import run, S
from gapfb2 import arrays, trade
from sess24 import t2m
src = open("../longhist/iter30_calendar.py").read(); exec(src[src.index("def cal(days):"):src.index("\nres = []")])
CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0); R0, X1 = t2m("09:30"), t2m("15:55")
rows = []
for key in ("A", "B"):
    days, X = S[key]; res = run(days, X)
    for k, v in res.items(): rows += [(d, k, r) for d, r in v]
    o, h, l, c = (X[:, :, i] for i in range(4)); C = cal(days); O = o[:, R0]
    sig = pd.Series(np.abs(c[:, X1] / O - 1)).rolling(14).mean().shift().values
    for i in np.nonzero(C["opex"] & np.isfinite(sig))[0]:
        e = O[i]; st = 0.4 * sig[i] * e; sl, tp = e + st, e - 2 * st; r = None
        for j in range(R0, X1 + 1):
            if h[i, j] >= sl: r = (e - max(o[i, j], sl) - 2.25 * e / 17000) / st; break
            if l[i, j] <= tp: r = (e - tp - 2.25 * e / 17000) / st; break
        if r is None: r = (e - c[i, X1] - 2.25 * e / 17000) / st
        rows.append((days[i], "OPEX", r))
F = pd.read_csv("features_C.csv", parse_dates=["day"]); F["score"] = (F.yday == 0).astype(int) + F.beyond + F.or_dir; good = set(F[F.score >= 2].day)
for rr in arrays().values():
    for d, g, o_, h_, l_, c_, a in rr:
        r = trade(o_, h_, l_, c_, a, g, *CFG)
        if r is not None: rows.append((d, "GapFB", r)); rows += [(d, "GapFB-score", r)] if d in good else []
T = pd.DataFrame(rows, columns=["day", "edge", "R"]); P = T.pivot_table(index="day", columns="edge", values="R", aggfunc="sum").fillna(0)
print("OPEX corr with others:", P.corr()["OPEX"].round(2).to_dict())
def stats(cols):
    x = P[cols].sum(axis=1); eq = x.cumsum(); y = x.groupby(x.index.year).sum()
    per = {p: x[(x.index.year >= a) & (x.index.year <= b)].sum() / max(1, ((x.index.year >= a) & (x.index.year <= b)).sum()) * 252
           for p, (a, b) in {"10-19": (2010, 2019), "20-23": (2020, 2023), "24-26": (2024, 2026)}.items()}
    print(f"{'+'.join(cols):34s} total={x.sum():+5.0f}R maxDD={(eq.cummax()-eq).max():5.1f}R ret/DD={x.sum()/(eq.cummax()-eq).max():5.1f} "
          f"years+ {(y>0).sum()}/{len(y)} | R/yr " + " ".join(f"{k}:{v:+.0f}" for k, v in per.items()))
for cols in (["OPEX"], ["GapFB-score", "PF"], ["GapFB-score", "PF", "OPEX"], ["GapFB", "PF", "OPEX"], ["GapFB-score", "PF", "OPEX", "WVB"],
             ["GapFB", "PF", "OPEX", "WVB", "OD"]):
    stats(cols)
