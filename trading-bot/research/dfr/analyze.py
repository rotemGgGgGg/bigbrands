"""Every DFR configuration (window × level × upper/lower × fade/break × stop × target × range filter), TRAIN = 2020–2023,
TEST = 2024–2026. Null control: how often does a config look good in TRAIN by chance → check TEST hit rate."""
import numpy as np, pandas as pd
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
T = pd.read_pickle(S + "dfr_trades.pkl"); T["y"] = pd.to_datetime(T.date).dt.year; T["tr"] = T.y < 2024
T["R"] = T.pts / T.risk
keys = ["window", "level", "edge", "play", "stop_R", "target"]
rows = []
for rf in ("all", 0, 1, 2):
    X = T if rf == "all" else T[T.rbucket == rf]
    for k, g in X.groupby(keys):
        a, b = g[g.tr], g[~g.tr]
        if len(a) < 40 or len(b) < 20: continue
        rows.append(dict(zip(keys, k), rfilt=rf, n_tr=len(a), n_te=len(b), win_tr=round(100 * (a.pts > 0).mean(), 1), win_te=round(100 * (b.pts > 0).mean(), 1),
                         R_tr=round(a.R.mean(), 3), R_te=round(b.R.mean(), 3), usd_tr=round(2 * a.pts.mean(), 1), usd_te=round(2 * b.pts.mean(), 1),
                         rr_plan=round((g.reward / g.risk).median(), 2), yrs=int((g.groupby("y").pts.sum() > 0).sum()),
                         t_tr=round(a.R.mean() / a.R.std() * np.sqrt(len(a)), 2), t_te=round(b.R.mean() / b.R.std() * np.sqrt(len(b)), 2)))
R = pd.DataFrame(rows); R.to_csv("dfr_results.csv", index=False)
pd.set_option("display.width", 260); pd.set_option("display.max_rows", 200)
print("configs:", len(R))
print("TRAIN R>0: %d (%.0f%%) | of those TEST R>0: %.0f%%   | base TEST R>0: %.0f%%" % ((R.R_tr > 0).sum(), 100 * (R.R_tr > 0).mean(), 100 * (R[R.R_tr > 0].R_te > 0).mean(), 100 * (R.R_te > 0).mean()))
s = R[R.t_tr > 2.5]; print("TRAIN t>2.5: %d | TEST R>0: %.0f%% | TEST t>2: %d" % (len(s), 100 * (s.R_te > 0).mean(), (s.t_te > 2).sum()))
print("\n— by play/edge (all filters, TRAIN-weighted mean R):"); print(R[R.rfilt == "all"].groupby(["play"])[["R_tr", "R_te"]].mean().round(3))
print("\n— candidates: TRAIN t>2.5 and TEST t>2:"); print(R[(R.t_tr > 2.5) & (R.t_te > 2)].sort_values("t_te", ascending=False).head(25).to_string(index=False))
print("\n— highest TEST win with TRAIN win ≥ 60 and both R > 0 (n_te ≥ 40):")
print(R[(R.win_tr >= 60) & (R.R_tr > 0) & (R.R_te > 0) & (R.n_te >= 40)].sort_values("win_te", ascending=False).head(15).to_string(index=False))
