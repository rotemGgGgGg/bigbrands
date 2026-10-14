import sys, pickle, numpy as np, pandas as pd
from core import SPLIT, DAYS
from sklearn.ensemble import HistGradientBoostingClassifier
df = pickle.load(open("stage2_data.pkl", "rb")); df["split"] = SPLIT[df.i.values]
feats = [x for x in df.columns if x not in ("i", "m", "split") and not x.startswith("R") and not x.startswith("sp")]
tr, va = df.split == 0, df.split == 1
for k, lr, depth, leaf, q in ((0.2, 0.1, 4, 1000, 0.997), (0.2, 0.1, 4, 1000, 0.999), (0.3, 0.03, None, 500, 0.99)):
    y = (df[f"R{k}"] > 0).astype(int)
    mdl = HistGradientBoostingClassifier(learning_rate=lr, max_depth=depth, min_samples_leaf=leaf, max_iter=300, early_stopping=True,
                                         validation_fraction=0.15, random_state=0).fit(df.loc[tr, feats], y[tr])
    thr = np.quantile(mdl.predict_proba(df.loc[tr, feats])[:, 1], q)
    sel = df[va].copy(); sel["p"] = mdl.predict_proba(sel[feats])[:, 1]; sel = sel[sel.p >= thr]
    sel["date"] = DAYS[sel.i.values].date; sel["R"] = sel[f"R{k}"]
    print(f"\n== stop {k}σ top {q}: trades {len(sel)}, distinct days {sel.date.nunique()}")
    print("per day:", sel.groupby("date").agg(n=("R", "size"), R=("R", "mean"), side=("side", "mean"), m0=("m", "min"), m1=("m", "max")).to_string())
    one = sel.sort_values("p", ascending=False).groupby("date").head(1)
    print("ONE trade per day (highest p):", len(one), "win", round(100 * (one.R > 0).mean(), 1), "avgR", round(one.R.mean(), 3),
          "target hits (R>1.5)", int((one.R > 1.5).sum()))
