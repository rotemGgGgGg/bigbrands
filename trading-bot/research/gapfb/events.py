"""Iter 74 — event days vs GapFB-score and Pre-Fade (real NQ): NFP (approx. first Friday of the month, 2010–26), CPI
(quant_loop/cpi_dates.txt, 2020–26), FOMC statement days (quant_loop/iter03_fomc.py list, 2020–26). R on event vs other days."""
import sys, re; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from portfolio_edges import run, S
from gapfb2 import arrays, trade
CFG = (15, "with", 2.0, 0, 5.0, 60, 385, 0.003, 1.0)
cpi = set(pd.to_datetime(open("../quant_loop/cpi_dates.txt").read().split()))
fomc = set(pd.to_datetime(re.search(r'F = """(.*?)"""', open("../quant_loop/iter03_fomc.py").read(), re.S).group(1).split()))
F = pd.read_csv("features_C.csv", parse_dates=["day"]); F["score"] = (F.yday == 0).astype(int) + F.beyond + F.or_dir; good = set(F[F.score >= 2].day)
G = {}
for rr in arrays().values():
    for d, g, o, h, l, c, a in rr:
        r = trade(o, h, l, c, a, g, *CFG)
        if r is not None and d in good: G[d] = r
PF = {}
for key in ("A", "B"):
    days, X = S[key]; PF.update(dict(run(days, X)["PF"]))
nfp = lambda d: d.weekday() == 4 and d.day <= 7
for nm, E in (("GapFB-score", G), ("Pre-Fade", PF)):
    s = pd.Series(E); s.index = pd.DatetimeIndex(s.index)
    for ev, f, start in (("NFP", nfp, 2010), ("CPI", lambda d: d in cpi, 2020), ("FOMC", lambda d: d in fomc, 2020)):
        x = s[s.index.year >= start]; m = np.array([f(d) for d in x.index])
        print(f"{nm:11s} {ev:4s} ({start}+): event n={m.sum():3d} R={x[m].mean():+.3f} | other n={(~m).sum():4d} R={x[~m].mean():+.3f}")
