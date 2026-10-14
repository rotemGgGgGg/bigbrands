"""Pre-open dip: NQ falls hard into 09:00 ET (typically the 08:30 data release) → buy 09:00, hold.
Compare with the unconditional 09:00 long (drift control) and the mirror (rally → short)."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S
full = pd.read_pickle(S + "full1m.pkl")
d = full.index.normalize()
def at(hm):
    x = full[(full.index.hour * 60 + full.index.minute) == hm]
    return x.set_axis(x.index.normalize())
o900, c829 = at(540).open, at(539).close
res = {}
for L in (30, 60, 120, 240):
    base = at(540 - L).open
    mv = (c829 / base - 1).dropna()
    z = mv / mv.rolling(20).std().shift()
    for H in (30, 60, 120, 240, 420):
        ex = at(540 + H - 1).close
        r = (ex - o900).reindex(z.index)
        res[(L, H)] = (z, r)
COST = 1.25
rows = []
for (L, H), (z, r) in res.items():
    y = r.index.year
    for name, m, sd in (("all long", z.notna(), 1), ("dip z<-1.5 long", z < -1.5, 1), ("dip z<-2 long", z < -2, 1),
                        ("rally z>1.5 short", z > 1.5, -1), ("rally z>2 short", z > 2, -1)):
        x = (r[m] * sd - COST).dropna(); isd = x.index.year < 2024
        rows.append(dict(L=L, H=H, rule=name, n=len(x), win=round(100 * (x > 0).mean()), avg=round(2 * x.mean(), 1),
                         IS=round(2 * x[isd].mean(), 1), OOS=round(2 * x[~isd].mean(), 1),
                         yrs=int((x.groupby(x.index.year).sum() > 0).sum())))
pd.set_option("display.width", 200)
print(pd.DataFrame(rows).to_string())
