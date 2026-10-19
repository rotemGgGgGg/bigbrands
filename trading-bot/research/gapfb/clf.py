"""Iter 59 (queue 61b) — which GapFB-C days work? Logistic regression / shallow trees on features known at 09:45
(features_C.csv: gap size in σ, outside-yesterday flag, 20-day trend agreement, yesterday's candle, first-15-min direction,
OR close location, OR width/ATR, weekday, VIX). Train 2010-19 → choose probability cut on train → validate 2020-23 → TEST once."""
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingRegressor
T = pd.read_csv("features_C.csv", parse_dates=["day"]).dropna()
F = ["gap_sig", "beyond", "trend", "yday", "or_dir", "or_loc_s", "or_w", "vix"]
T = pd.concat([T, pd.get_dummies(T.dow, prefix="d").astype(float)], axis=1); F += [c for c in T if c.startswith("d_")]
tr, va, te = (T[T.per == p] for p in ("2010-19", "2020-23", "2024-26"))
mu, sd = tr[F].mean(), tr[F].std() + 1e-9
def X(d): return ((d[F] - mu) / sd).values
for name, model, kind in (("logit", LogisticRegression(C=0.3, max_iter=2000), "p"),
                          ("gbr", GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.03, subsample=0.7, random_state=1), "r")):
    if kind == "p": model.fit(X(tr), (tr.R > 0).astype(int)); score = lambda d: model.predict_proba(X(d))[:, 1]
    else: model.fit(X(tr), tr.R.clip(-1.5, 6)); score = lambda d: model.predict(X(d))
    for q in (0.0, 0.3, 0.5):
        cut = np.quantile(score(tr), q)
        out = []
        for nm, d in (("train", tr), ("val", va), ("TEST", te)):
            k = d[score(d) >= cut]; out.append(f"{nm}: n={len(k)} R={k.R.mean():+.3f}")
        print(f"{name} keep top {100*(1-q):.0f}% | " + " | ".join(out), flush=True)
