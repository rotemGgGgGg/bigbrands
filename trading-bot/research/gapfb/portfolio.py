"""Iter 69 — NQ multi-edge portfolio on real data 2010–26: GapFB-C (score ≥ 2 and plain), Pre-Open Fade, Williams VB, open-drive.
1 R risk per trade per edge; daily sums; correlation of daily R; total, max DD, years positive, per period."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from portfolio_edges import run, S
from gapfb2 import arrays, trade
CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)
rows = []
for key in ("A", "B"):
    days, X = S[key]; res = run(days, X)
    for k, v in res.items(): rows += [(d, k, r) for d, r in v]
F = pd.read_csv("features_C.csv", parse_dates=["day"]); F["score"] = (F.yday == 0).astype(int) + F.beyond + F.or_dir; good = set(F[F.score >= 2].day)
for rr in arrays().values():
    for d, g, o, h, l, c, a in rr:
        r = trade(o, h, l, c, a, g, *CFG)
        if r is not None: rows.append((d, "GapFB", r)); rows += [(d, "GapFB-score", r)] if d in good else []
T = pd.DataFrame(rows, columns=["day", "edge", "R"]); P = T.pivot_table(index="day", columns="edge", values="R", aggfunc="sum").fillna(0)
print("daily-R correlation:\n", P.corr().round(2).to_string())
def stats(cols):
    x = P[cols].sum(1); eq = x.cumsum(); y = x.groupby(x.index.year).sum()
    per = {p: x[(x.index.year >= a) & (x.index.year <= b)].sum() / max(1, ((x.index.year >= a) & (x.index.year <= b)).sum()) * 252
           for p, (a, b) in {"10-19": (2010, 2019), "20-23": (2020, 2023), "24-26": (2024, 2026)}.items()}
    print(f"{'+'.join(cols):40s} total={x.sum():+5.0f}R maxDD={(eq.cummax()-eq).max():5.1f}R ret/DD={x.sum()/(eq.cummax()-eq).max():5.1f} "
          f"years+ {(y>0).sum()}/{len(y)} | R/yr " + " ".join(f"{k}:{v:+.0f}" for k, v in per.items()))
for cols in (["GapFB"], ["GapFB-score"], ["PF"], ["WVB"], ["OD"], ["GapFB", "PF"], ["GapFB-score", "PF"], ["GapFB", "PF", "WVB"],
             ["GapFB", "PF", "WVB", "OD"], ["GapFB-score", "PF", "WVB", "OD"]):
    stats(cols)
