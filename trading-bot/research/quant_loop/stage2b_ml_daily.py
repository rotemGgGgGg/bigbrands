"""Stage 2b: same ML, but honest unit = one trade per day (the day's highest-probability entry), so a single trend day
cannot fake a high win rate. Threshold fixed on TRAIN daily-max scores. Also excludes absolute-volatility features
in a variant (so the model cannot just pick crash days)."""
import pickle, numpy as np, pandas as pd, itertools
from core import SPLIT, metrics, Logger
from sklearn.ensemble import HistGradientBoostingClassifier
df = pickle.load(open("stage2_data.pkl", "rb")); df["split"] = SPLIT[df.i.values]
ALL = [x for x in df.columns if x not in ("i", "m", "split") and not x.startswith("R") and not x.startswith("sp")]
NOVOL = [x for x in ALL if x not in ("sig", "rv30", "rng", "va_w", "on_range", "vol_ratio")]
L = Logger("stage2b"); rows = []
for k, fs_name, (lr, depth, leaf) in itertools.product((0.1, 0.2, 0.3), ("all", "novol"),
                                                      ((0.05, 3, 200), (0.05, 6, 200), (0.03, None, 500), (0.1, 4, 1000), (0.05, 2, 2000))):
    fs = ALL if fs_name == "all" else NOVOL
    y = (df[f"R{k}"] > 0).astype(int); tr = df.split == 0
    mdl = HistGradientBoostingClassifier(learning_rate=lr, max_depth=depth, min_samples_leaf=leaf, max_iter=300, early_stopping=True,
                                         validation_fraction=0.15, random_state=0).fit(df.loc[tr, fs], y[tr])
    d = df[["i", "split", f"R{k}", f"sp{k}"]].copy(); d["p"] = mdl.predict_proba(df[fs])[:, 1]
    best = d.loc[d.groupby("i").p.idxmax()]                       # one entry per day
    for q in (0.5, 0.8, 0.9, 0.95, 0.98):
        thr = best[best.split == 0].p.quantile(q)
        for sp_name, s in (("train", 0), ("val", 1)):
            b = best[(best.split == s) & (best.p >= thr)]
            m = metrics(b[f"R{k}"].values, b[f"sp{k}"].values)
            cfg = dict(stop_sig=k, feats=fs_name, lr=lr, depth=depth, leaf=leaf, top_q_daily=q, rr=2.0, unit="1/day")
            st = ("val_pass" if s == 1 and m.get("n", 0) >= 30 and m["win"] >= 70 and m["exp_R"] > 0 else ("val_fail" if s == 1 else "train"))
            L.log("ml_hgb_daily", cfg, sp_name, m, st)
            if s == 1: rows.append(dict(cfg, **{x: m.get(x) for x in ("n", "win", "realized_rr", "exp_R", "ci_win_lo", "ci_win_hi", "t")}))
L.close()
R = pd.DataFrame(rows); R.to_csv("stage2b_summary.csv", index=False)
pd.set_option("display.width", 250)
print("configs:", len(R) * 2, "| VAL pass:", ((R.win >= 70) & (R.n >= 30) & (R.exp_R > 0)).sum())
print(R.sort_values("exp_R", ascending=False).head(15).to_string())
print("\nbest win with n>=30:"); print(R[R.n >= 30].sort_values("win", ascending=False).head(8).to_string())
