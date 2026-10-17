"""Iteration 2 — meta-labelling. Events = entries of the validated edges (Noise-Area break, Williams VB, Afternoon, Rebound,
Pre-Open Fade proxy at 09:45, NA-FVG retrace). Label = 2R-before-1R with stop = s·σ (first passage, costs). Features = the
stage-2 feature row at the event's 5-minute slot (signed by side). HistGradientBoosting fit on 2020–23 events only;
probability threshold fixed on TRAIN quantiles; TEST 2024–26 evaluated once. First event per day only."""
import sys, os, pickle; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, ".."), os.path.join(H, "../hunt"), os.path.join(H, "../winrate"), os.path.join(H, "../influencers")]
import numpy as np, pandas as pd
from core import first_passage, SPLIT, SIG, o
from sklearn.ensemble import HistGradientBoostingClassifier
import signals as W
from lib import okprev, RANGE, DO, stop_fill, N, VALID
ev = []
for i, k0, s, _ in W.sig_na_first(): ev.append((i, k0, s, "NA"))
for i, j, s, lim in W.sig_na_fvg(): ev.append((i, j + 1, s, "NAFVG"))
for i, j, s, _ in W.sig_afternoon(): ev.append((i, j, s, "PM"))
for i, j, s, _ in W.sig_rebound(): ev.append((i, 15, s, "REB"))
for i in range(1, N):
    if not okprev[i]: continue
    r = RANGE[i - 1]; a, b = stop_fill(i, 1, 384, DO[i] + 0.6 * r, 1), stop_fill(i, 1, 384, DO[i] - 0.6 * r, -1)
    f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
    if f: ev.append((i, f[0][0] + 1, f[1], "WVB"))
E = pd.DataFrame(ev, columns=["i", "m", "side", "src"]); E = E[(E.m >= 16) & (E.m <= 330)]
E = E.sort_values(["i", "m"]).groupby("i").head(1).reset_index(drop=True)          # first event per day
X = pickle.load(open(os.path.join(H, "stage2_data.pkl"), "rb"))
X["slot"] = X.m; feats = [x for x in X.columns if x not in ("i", "m", "slot", "side") and not x.startswith("R") and not x.startswith("sp")]
E["slot"] = ((E.m - 1) // 5) * 5; E.loc[E.slot < 15, "slot"] = 15
M = E.merge(X[["i", "slot", "side"] + feats], on=["i", "slot", "side"], how="inner")
M = pd.concat([M, pd.get_dummies(M.src, prefix="src").astype(float)], axis=1); feats2 = feats + [c for c in M.columns if c.startswith("src_")]
print("events", len(M), M.src.value_counts().to_dict())
rows = []
for s in (0.1, 0.2, 0.3, 0.5):
    lab = []
    for r in M.itertuples():
        sp = s * SIG[r.i] * o[r.i, 0]; lab.append(first_passage(r.i, int(r.m), int(r.side), o[r.i, int(r.m)], sp, 2.0)[0])
    M[f"R{s}"] = lab
    y = (M[f"R{s}"] > 0).astype(int); tr = SPLIT[M.i.values] == 0; te = ~tr
    for depth, leaf in ((2, 50), (3, 30), (None, 100)):
        mdl = HistGradientBoostingClassifier(max_depth=depth, min_samples_leaf=leaf, learning_rate=0.05, max_iter=200, random_state=0).fit(M.loc[tr, feats2], y[tr])
        ptr = mdl.predict_proba(M.loc[tr, feats2])[:, 1]; pte = mdl.predict_proba(M.loc[te, feats2])[:, 1]
        for q in (0.0, 0.5, 0.8, 0.9, 0.95):
            th = np.quantile(ptr, q); a = M.loc[te, f"R{s}"].values[pte >= th]
            if len(a) < 15: continue
            w = a > 0
            rows.append(dict(stop_sig=s, depth=depth, leaf=leaf, top_q=q, n_te=len(a), win_te=round(100 * w.mean(), 1), R_te=round(a.mean(), 3),
                             realized=round(a[w].mean() / -a[~w].mean(), 2) if (~w).any() and w.any() else np.nan,
                             base_win_te=round(100 * (M.loc[te, f"R{s}"] > 0).mean(), 1)))
out = pd.DataFrame(rows); out.to_csv("iter02_meta.csv", index=False); pd.set_option("display.width", 200)
print(out.sort_values("win_te", ascending=False).head(15).to_string(index=False))
print("PASS (TEST win ≥ 70, R > 0, n ≥ 30):", int(((out.win_te >= 70) & (out.R_te > 0) & (out.n_te >= 30)).sum()))
