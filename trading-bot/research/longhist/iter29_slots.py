"""Iter 29 — minute-of-day seasonality scan: mean signed return of every 5-minute and 15-minute slot 09:30–15:55, conditional on the
day's direction so far (open → slot start up/down) — does any slot have a drift that is the SAME sign and significant in all three
periods? Then the best slots are traded at 1:2 brackets (stop 0.1σ)."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
from load import frame, RTH
from engine import walk
exec(open("iter26_web.py").read().split("res = []")[0])
rows = []
for per, o, h, l, c, dow in grids():
    N = len(o); mv = np.abs(c[:, 389] / o[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
    for L_, s0 in itertools.product((5, 15), range(5, 385, 5)):
        if s0 + L_ > 389: continue
        r = (c[:, s0 + L_ - 1] - o[:, s0]) / (sig * o[:, 0]); dirn = np.sign(c[:, s0 - 1] - o[:, 0])
        for cond, m in (("all", np.isfinite(r)), ("day_up", np.isfinite(r) & (dirn > 0)), ("day_dn", np.isfinite(r) & (dirn < 0))):
            x = r[m]; rows.append(dict(per=per, slot=f"{9 + (30 + s0) // 60:02d}:{(30 + s0) % 60:02d}", L=L_, cond=cond, mean=x.mean(), t=x.mean() / x.std() * np.sqrt(len(x))))
T = pd.DataFrame(rows); P = T.pivot_table(index=["slot", "L", "cond"], columns="per", values="t")
same = P[(np.sign(P).nunique(axis=1) == 1)]; same = same.assign(min_abs_t=same.abs().min(axis=1)).sort_values("min_abs_t", ascending=False)
pd.set_option("display.width", 200); print("slots tested", len(P), "| same sign in all 3 periods:", len(same)); print(same.head(15).round(2).to_string())
T.to_csv("iter29_slots.csv", index=False)
