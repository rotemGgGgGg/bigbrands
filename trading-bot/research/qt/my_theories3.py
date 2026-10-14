"""Round 3: 'inter-day reversal' turned into intraday trades (prop-legal, flat by 16:00)."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S, COST_PTS, IS_END
f = pd.read_pickle(S + "full1m.pkl"); m = f.index.hour * 60 + f.index.minute
r = f[(m >= 570) & (m < 960)]
g = r.groupby(r.index.date)
d = g.agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
d["c1200"] = r[(r.index.hour == 11) & (r.index.minute == 59)].groupby(r[(r.index.hour == 11) & (r.index.minute == 59)].index.date).close.last()
d["c1030"] = r[(r.index.hour == 10) & (r.index.minute == 29)].groupby(r[(r.index.hour == 10) & (r.index.minute == 29)].index.date).close.last()
d.index = pd.to_datetime(d.index); d = d[d.index.weekday < 5]
d["pc"], d["pl"], d["ph"], d["ppl"], d["pph"] = d.c.shift(), d.l.shift(), d.h.shift(), d.l.shift(2), d.h.shift(2)
d["ret_prev"] = d.pc / d.c.shift(2) - 1
rows = []
def ev(name, mask, side, exitcol):
    p = ((d[exitcol] - d.o) * side - COST_PTS)[mask].dropna(); y = p.index
    rows.append(dict(rule=name, exit=exitcol, n=len(p), win=round(100 * (p > 0).mean(), 1), avg_usd=round(2 * p.mean(), 1),
                     IS=round(2 * p[y < IS_END].mean(), 1), OOS=round(2 * p[y >= IS_END].mean(), 1),
                     yrs=f"{int((p.groupby(y.year).sum() > 0).sum())}/{y.year.nunique()}"))
ALL = pd.Series(True, index=d.index)
for ex in ("c1030", "c1200", "c"):
    ev("baseline: long every day 09:30→", ALL, 1, ex)
    ev("prev day closed below its prior-day low → long", d.pc < d.ppl, 1, ex)
    ev("prev day closed above its prior-day high → short", d.pc > d.pph, -1, ex)
    ev("prev day fell >1% → long", d.ret_prev < -0.01, 1, ex)
    ev("prev day fell >2% → long", d.ret_prev < -0.02, 1, ex)
    ev("prev day rose >1% → short", d.ret_prev > 0.01, -1, ex)
    ev("gap down >0.5% at open → long", d.o / d.pc - 1 < -0.005, 1, ex)
    ev("gap up >0.5% at open → short", d.o / d.pc - 1 > 0.005, -1, ex)
out = pd.DataFrame(rows); out.to_csv("my_theories_round3.csv", index=False)
print(out.to_string(index=False))
