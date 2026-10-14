"""Robustness for the pre-open fade: roll-day filter, per-year, top-day dependence, side split, cost stress, z neighbourhood."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from prefade import pre_move, trade, stats, S
instr = pd.read_pickle(S + "instr.pkl")
im = instr.index.hour * 60 + instr.index.minute
w = instr[(im >= 360) & (im < 780)]
nun = w.groupby(w.index.normalize()).nunique()
bad = set(nun[nun.iloc[:, 0] > 1].index) if isinstance(nun, pd.DataFrame) else set(nun[nun > 1].index)
print("days with a contract switch 06:00–13:00:", len(bad))
pd.set_option("display.width", 250)
def run(L, zt, a, b, te, extra=0.0, side=None):
    s, z = pre_move(L)
    sig = [d for d in z[(z.abs() > zt)].index if d not in bad]
    x = {}
    for d in sig:
        sd = -int(np.sign(s[d]))
        if side and sd != side: continue
        x[d] = trade(d, sd, abs(s[d]), a, b, te) - extra
    return pd.Series(x)
base = dict(L=60, zt=2.0, a=1.0, b=1.0, te=780)
x = run(**base)
print("BASE", stats(x))
print("by year $:", (2 * x).groupby(x.index.year).agg(["sum", "count"]).round().T.to_string())
print("long only", stats(run(**base, side=1))); print("short only", stats(run(**base, side=-1)))
print("+1 pt extra cost", stats(run(**base, extra=1.0))); print("+3 pt extra cost", stats(run(**base, extra=3.0)))
srt = x.sort_values(ascending=False)
print("total $", round(2 * x.sum()), "without best 5 days", round(2 * srt.iloc[5:].sum()), "median $", round(2 * x.median(), 1))
print("best days", (2 * srt.head(5)).round().to_dict())
rows = []
for L in (45, 60, 90):
    for zt in (1.5, 1.75, 2.0, 2.25, 2.5):
        for a in (0.75, 1.0, 1.25):
            for b in (1.0, 1.5):
                r = stats(run(L, zt, a, b, 780)); r.update(L=L, z=zt, a=a, b=b); rows.append(r)
R = pd.DataFrame(rows); print(R.to_string())
print("share of neighbourhood with IS>0 & OOS>0:", round(((R.IS > 0) & (R.OOS > 0)).mean(), 2))
