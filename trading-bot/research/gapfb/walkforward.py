"""Iter 81 (queue 83) — walk-forward GapFB score: for each 2-year window from 2012, fit the logistic on ALL earlier trades only
(features_C.csv features, standardised on that history), keep days whose probability ≥ the median of the training scores,
evaluate on the window. Compared with: all trades, and the fixed 3-point rule (score ≥ 2)."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
T = pd.read_csv("features_C.csv", parse_dates=["day"]).dropna().sort_values("day")
T = pd.concat([T, pd.get_dummies(T.dow, prefix="d").astype(float)], axis=1)
F = ["gap_sig", "beyond", "trend", "yday", "or_dir", "or_loc_s", "or_w", "vix"] + [c for c in T if c.startswith("d_")]
T["pts"] = (T.yday == 0).astype(int) + T.beyond + T.or_dir; T["yr"] = T.day.dt.year
rows = []
for y0 in range(2012, 2027, 2):
    tr, te = T[T.yr < y0], T[(T.yr >= y0) & (T.yr < y0 + 2)]
    if not len(te): continue
    mu, sd = tr[F].mean(), tr[F].std() + 1e-9
    m = LogisticRegression(C=0.3, max_iter=2000).fit(((tr[F] - mu) / sd).values, (tr.R > 0).astype(int))
    p_tr = m.predict_proba(((tr[F] - mu) / sd).values)[:, 1]; p_te = m.predict_proba(((te[F] - mu) / sd).values)[:, 1]
    keep = te[p_te >= np.median(p_tr)]
    rows.append(dict(window=f"{y0}-{min(y0+1, 2026)}", n_all=len(te), R_all=te.R.mean(), n_wf=len(keep), R_wf=keep.R.mean(),
                     n_pts=(te.pts >= 2).sum(), R_pts=te[te.pts >= 2].R.mean()))
X = pd.DataFrame(rows); print(X.round(3).to_string(index=False))
for c in ("all", "wf", "pts"):
    n = X[f"n_{c}"]; print(f"{c:3s}: trade-weighted mean R = {(X[f'R_{c}'] * n).sum() / n.sum():+.3f}, windows positive {(X[f'R_{c}'] > 0).sum()}/{len(X)}")
