"""Step 2 of the funnel: top 300 TRAIN configs by t-stat → VALIDATE 2020-23. Keep those with t_val > 1.5; rank by min(R_train, R_val)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays, evaluate, GRID
A = arrays(); T = pd.read_csv("train_grid.csv").sort_values("t", ascending=False).head(300)
keys = list(GRID); rows = []
for _, r in T.iterrows():
    cfg = tuple(r[k] if k != "stop" else (r[k] if r[k] == "or" else float(r[k])) for k in keys)
    cfg = tuple(int(x) if k in ("orm", "cut", "ex") else x for k, x in zip(keys, cfg))
    R = evaluate(A["2020-23"], cfg); w = R > 0
    rows.append(dict(**{k: v for k, v in zip(keys, cfg)}, R_tr=r.R, t_tr=r.t, win_tr=r.win, n_val=len(R), win_val=100 * w.mean(),
                     rr_val=R[w].mean() / -R[~w].mean(), R_val=R.mean(), t_val=R.mean() / R.std() * np.sqrt(len(R))))
V = pd.DataFrame(rows); V["minR"] = V[["R_tr", "R_val"]].min(axis=1); V.to_csv("validate.csv", index=False)
K = V[V.t_val > 1.5].sort_values("minR", ascending=False)
pd.set_option("display.width", 250); print(len(K), "of 300 pass validation (t_val>1.5)"); print(K.head(25).round(3).to_string(index=False))
