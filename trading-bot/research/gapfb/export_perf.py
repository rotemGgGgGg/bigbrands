"""Export daily R per strategy (portfolio of GapFB-score + Pre-Fade + Opex, real NQ 2010–19 + MNQ 2020–26) for the app's
Performance page → trading-bot/app/bridge/static/perf.json. One row per trading day: [date, gapfb, prefade, opex]
(0 = no trade that day; each strategy trades at most once a day, so a non-zero value is one trade's R)."""
import sys, json; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
exec(open("portfolio2.py").read().split("print(\"OPEX corr")[0])
cols = {"GapFB-score": "gapfb", "PF": "prefade", "OPEX": "opex"}
Q = P[list(cols)].rename(columns=cols)
days = sorted(set(d for key in ("A", "B") for d in S[key][0]))
Q = Q.reindex(pd.DatetimeIndex(days)).fillna(0.0)
rows = [[d.strftime("%Y-%m-%d"), round(r.gapfb, 3), round(r.prefade, 3), round(r.opex, 3)] for d, r in Q.iterrows()]
out = {"source": "Backtest: real NQ futures 2010-19 (Databento), MNQ 2020-26; costs 2.25 NQ pt per trade; 1 R = risk per trade.",
       "updated": rows[-1][0], "columns": ["date", "gapfb", "prefade", "opex"], "rows": rows}
p = "../../app/bridge/static/perf.json"; json.dump(out, open(p, "w"), separators=(",", ":"))
x = Q.sum(axis=1); print(len(rows), "days", rows[0][0], "→", rows[-1][0], "| total R", round(x.sum(), 1), "| per strategy", Q.sum().round(1).to_dict())
