"""Iteration 1 — edge stacking. For each day collect the directional calls (and the minute they become known) of the validated
edges; trade when ≥ k calls agree, entering at the minute the k-th agreeing call appears; 1:2 bracket with stop = s × daily σ."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, ".."), os.path.join(H, "../hunt"), os.path.join(H, "../winrate"), os.path.join(H, "../influencers")]
import numpy as np, pandas as pd, itertools
from lib import o, h, l, c, N, SIG, VALID, YR, okprev, DO, RANGE, stop_fill, trade, DAYS
import signals as W
from prefade import pre_move
calls = {i: [] for i in range(N)}                       # (minute known, side, name)
for i, k0, s, _ in W.sig_na_first(): calls[i].append((k0, s, "NA"))
for i, j, s, _ in W.sig_afternoon(): calls[i].append((j, s, "PM"))
for i, j, s, _ in W.sig_rebound(): calls[i].append((0, s, "REB"))
for i in range(1, N):                                    # Williams VB first trigger
    if not okprev[i]: continue
    r = RANGE[i - 1]; a, b = stop_fill(i, 1, 384, DO[i] + 0.6 * r, 1), stop_fill(i, 1, 384, DO[i] - 0.6 * r, -1)
    f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
    if f: calls[i].append((f[0][0] + 1, f[1], "WVB"))
s_, z_ = pre_move(60); dmap = {d: i for i, d in enumerate(pd.to_datetime(DAYS).date)}
for d in z_[z_.abs() > 1.5].index:
    i = dmap.get(d.date())
    if i is not None: calls[i].append((0, -int(np.sign(s_[d])), "PF"))
rows = []
for kmin, stop_s, rr in itertools.product((2, 3), (0.1, 0.2, 0.3, 0.5), (2.0, 2.5, 3.0)):
    R = []
    for i in range(N):
        if not VALID[i] or len(calls[i]) < kmin: continue
        cs = sorted(calls[i]); trig = None
        for t in range(len(cs)):
            for side in (1, -1):
                agree = [x for x in cs[:t + 1] if x[1] == side]
                if len(agree) >= kmin and not any(x[1] == -side for x in cs[:t + 1]): trig = (cs[t][0], side); break
            if trig: break
        if not trig or trig[0] > 380: continue
        m, side = trig; e = o[i, m]; sp = stop_s * SIG[i] * o[i, 0]
        r = trade(i, m, side, e - side * sp, e + side * rr * sp)
        if r: R.append((i, r[0] / sp, r[0]))
    if not R: continue
    X = pd.DataFrame(R, columns=["i", "R", "pts"]); tr = YR[X.i] < 2024
    w = X.R > 0
    rows.append(dict(k=kmin, stop_sig=stop_s, rr=rr, n=len(X), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1),
                     R_tr=round(X.R[tr].mean(), 3), R_te=round(X.R[~tr].mean(), 3),
                     realized=round(X.R[w].mean() / -X.R[~w].mean(), 2) if (~w).any() else np.nan))
out = pd.DataFrame(rows); out.to_csv("iter01_stack.csv", index=False); pd.set_option("display.width", 200); print(out.to_string(index=False))
print("PASS (win_tr≥70 & win_te≥70 & rr≥2 & R>0 both):", int(((out.win_tr >= 70) & (out.win_te >= 70) & (out.R_tr > 0) & (out.R_te > 0)).sum()))
