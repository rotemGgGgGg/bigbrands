"""Iteration 5 — volatility-regime conditioning of the validated edges at planned 1:2. Regimes from information known before the
entry: yesterday's range vs its 20-day mean (vol_ratio), overnight range vs typical (on_range/rsig), 5-day trend sign, VIX-free.
For each edge × regime bucket (TRAIN tertiles) × stop size: 1:2 bracket, one trade per day."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, ".."), os.path.join(H, "../hunt"), os.path.join(H, "../winrate"), os.path.join(H, "../influencers")]
import numpy as np, pandas as pd, itertools
from lib import o, N, SIG, VALID, YR, okprev, RANGE, DO, stop_fill, trade, F
import signals as W
ev = {"NA": [(i, k0, s) for i, k0, s, _ in W.sig_na_first()], "PM": [(i, j, s) for i, j, s, _ in W.sig_afternoon()],
      "REB": [(i, 1, s) for i, j, s, _ in W.sig_rebound()], "NAFVG": [(i, j + 1, s) for i, j, s, _ in W.sig_na_fvg()]}
wv = []
for i in range(1, N):
    if not okprev[i]: continue
    r = RANGE[i - 1]; a, b = stop_fill(i, 1, 384, DO[i] + 0.6 * r, 1), stop_fill(i, 1, 384, DO[i] - 0.6 * r, -1)
    f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
    if f: wv.append((i, f[0][0] + 1, f[1]))
ev["WVB"] = wv
reg = {"vol_ratio": F.vol_ratio.values, "on_rel": (F.on_range / F.rsig).values, "trend_aligned": None}
tr_mask = YR < 2024
rows = []
for (name, E), s in itertools.product(ev.items(), (0.15, 0.25, 0.4, 0.6)):
    res = []
    for i, m, side in E:
        if m > 380 or not VALID[i]: continue
        sp = s * SIG[i] * o[i, 0]; e = o[i, m]; r = trade(i, m, side, e - side * sp, e + side * 2 * sp)
        if r: res.append((i, side, r[0] / sp))
    X = pd.DataFrame(res, columns=["i", "side", "R"]).drop_duplicates("i")
    for rn, arr in reg.items():
        if rn == "trend_aligned":
            key = (np.sign(F.ret5.values[X.i]) == X.side).astype(int); buckets = {"aligned": key == 1, "against": key == 0}
        else:
            vals = arr[X.i]; q = np.nanquantile(arr[tr_mask], [1 / 3, 2 / 3])
            buckets = {"low": vals < q[0], "mid": (vals >= q[0]) & (vals < q[1]), "high": vals >= q[1]}
        for bn, bm in buckets.items():
            Y = X[np.asarray(bm)]
            if len(Y) < 40: continue
            tr = YR[Y.i] < 2024; w = Y.R > 0
            rows.append(dict(edge=name, stop_sig=s, regime=rn, bucket=bn, n=len(Y), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1),
                             R_tr=round(Y.R[tr].mean(), 3), R_te=round(Y.R[~tr].mean(), 3)))
out = pd.DataFrame(rows); out.to_csv("iter05_regime.csv", index=False); pd.set_option("display.width", 200)
print(out.sort_values("win_tr", ascending=False).head(12).to_string(index=False))
print("configs", len(out), "| PASS:", int(((out.win_tr >= 70) & (out.win_te >= 70) & (out.R_tr > 0) & (out.R_te > 0)).sum()))
