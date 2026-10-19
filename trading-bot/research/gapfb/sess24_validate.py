"""Validate on 2020-23: top 5 TRAIN configs (by t) per anchor among 09:30, 10:00, 15:00, 11:30, 03:00."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, run
S = build(); days, X = S["B"]; m = days.year < 2024
T = pd.read_csv("sess24_train.csv", dtype={"T": str}); rows = []
for anc in ("09:30", "10:00", "15:00", "11:30", "03:00"):
    for _, r in T[T["T"] == anc].head(5).iterrows():
        cfg = dict(T=anc, P=int(r.P), m=int(r.m), z=float(r.z), mode=r["mode"], H=int(r.H))
        R, _ = run(days[m], X[m], **cfg)
        rows.append(dict(cfg, t_tr=round(r.t, 2), R_tr=round(r.R, 3), n_val=len(R), win_val=round(100 * (R > 0).mean(), 1),
                         R_val=round(R.mean(), 3), t_val=round(R.mean() / R.std() * np.sqrt(len(R)), 2)))
pd.set_option("display.width", 250); print(pd.DataFrame(rows).to_string(index=False))
