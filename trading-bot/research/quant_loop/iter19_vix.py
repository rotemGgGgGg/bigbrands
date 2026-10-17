"""Iteration 19 — VIX / 10-year-yield regime (FRED, previous day's close only) as a filter for the validated edges at 1:2."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, ".."), os.path.join(H, "../hunt"), os.path.join(H, "../winrate"), os.path.join(H, "../influencers")]
import numpy as np, pandas as pd, itertools
from lib import o, N, SIG, VALID, YR, okprev, RANGE, DO, stop_fill, trade, DAYS
import signals as W
vix = pd.read_csv("vix.csv", index_col=0, parse_dates=True).iloc[:, 0].apply(pd.to_numeric, errors="coerce")
y10 = pd.read_csv("dgs10.csv", index_col=0, parse_dates=True).iloc[:, 0].apply(pd.to_numeric, errors="coerce")
dd = pd.DatetimeIndex(DAYS)
vprev = vix.shift(1).reindex(dd, method="ffill").values                     # yesterday's close
vchg = (vix / vix.shift(1) - 1).shift(1).reindex(dd, method="ffill").values
ychg = (y10 - y10.shift(1)).shift(1).reindex(dd, method="ffill").values
ev = {"NA": [(i, k0, s) for i, k0, s, _ in W.sig_na_first()], "NAFVG": [(i, j + 1, s) for i, j, s, _ in W.sig_na_fvg()],
      "PM": [(i, j, s) for i, j, s, _ in W.sig_afternoon()], "REB": [(i, 1, s) for i, j, s, _ in W.sig_rebound()]}
wv = []
for i in range(1, N):
    if not okprev[i]: continue
    r = RANGE[i - 1]; a, b = stop_fill(i, 1, 384, DO[i] + 0.6 * r, 1), stop_fill(i, 1, 384, DO[i] - 0.6 * r, -1)
    f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
    if f: wv.append((i, f[0][0] + 1, f[1]))
ev["WVB"] = wv
tr_all = YR < 2024
filters = {"vix<15": vprev < 15, "vix15-20": (vprev >= 15) & (vprev < 20), "vix20-30": (vprev >= 20) & (vprev < 30), "vix>30": vprev >= 30,
           "vix up>5%": vchg > 0.05, "vix down>5%": vchg < -0.05, "10y up>5bp": ychg > 0.05, "10y down>5bp": ychg < -0.05}
rows = []
for (name, E), s in itertools.product(ev.items(), (0.15, 0.25, 0.4)):
    res = {}
    for i, m, side in E:
        if m > 380 or not VALID[i] or i in res: continue
        sp = s * SIG[i] * o[i, 0]; e = o[i, m]; r = trade(i, m, side, e - side * sp, e + side * 2 * sp)
        if r: res[i] = (side, r[0] / sp)
    X = pd.DataFrame([(i, a, b) for i, (a, b) in res.items()], columns=["i", "side", "R"])
    for fn, fm in filters.items():
        for sd in ("both", "long", "short"):
            Y = X[fm[X.i.values] & ((X.side == 1) if sd == "long" else (X.side == -1) if sd == "short" else True)]
            if len(Y) < 40: continue
            tr = YR[Y.i] < 2024; w = Y.R > 0
            if tr.sum() < 15 or (~tr).sum() < 10: continue
            rows.append(dict(edge=name, stop=s, filt=fn, side=sd, n=len(Y), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1),
                             R_tr=round(Y.R[tr].mean(), 3), R_te=round(Y.R[~tr].mean(), 3)))
out = pd.DataFrame(rows); out.to_csv("iter19_vix.csv", index=False); pd.set_option("display.width", 200)
print(out.sort_values("win_te", ascending=False).head(10).to_string(index=False))
print("configs", len(out), "PASS", int(((out.win_tr >= 70) & (out.win_te >= 70) & (out.R_tr > 0) & (out.R_te > 0)).sum()))
