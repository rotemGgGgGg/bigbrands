"""Same FRAMA/CPMA entries, exits that a bot can actually get. Gross vs net, by cost level."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "..")
from engine import S, IS_END
from frama_bt import signals

full = pd.read_pickle(S + "full1m.pkl")
b = full.resample("15min", label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
sig, _, _ = signals(b)
t1 = full.index; o1, h1, l1, c1 = (full[k].values for k in ("open", "high", "low", "close"))
m1 = (t1.hour * 60 + t1.minute).values
T = t1.values

def sim(tp=10.0, trail=0.5, sl=100.0, fixed=False, rth=False):
    out = []
    idx = np.where(sig != 0)[0]
    for n, i in enumerate(idx):
        if i + 1 >= len(b): break
        st = b.index[i + 1]
        if rth and not (570 <= st.hour * 60 + st.minute < 945): continue
        j = np.searchsorted(T, st.to_datetime64())
        if j >= len(T): break
        side = sig[i]; e = o1[j]
        act = b.close.values[i] + side * tp
        stop = (b.low.values[i] - sl) if side == 1 else (b.high.values[i] + sl)
        nxt = idx[n + 1] + 1 if n + 1 < len(idx) else None
        lim = np.searchsorted(T, b.index[nxt].to_datetime64()) if nxt is not None and nxt < len(b) else len(T) - 1
        active, best, px = False, None, None
        for x in range(j, lim):
            if rth and m1[x] >= 955: px = c1[x]; break
            if side == 1:
                if l1[x] <= stop and not active: px = min(o1[x], stop); break
                if fixed and h1[x] >= act and x > j: px = act; break
                if active and l1[x] <= best - trail: px = min(o1[x], best - trail); break
                if not fixed and not active and h1[x] >= act:
                    active, best = True, act
                    if c1[x] <= act - trail: px = act - trail; break
                    continue
                if active: best = max(best, h1[x])
            else:
                if h1[x] >= stop and not active: px = max(o1[x], stop); break
                if fixed and l1[x] <= act and x > j: px = act; break
                if active and h1[x] >= best + trail: px = max(o1[x], best + trail); break
                if not fixed and not active and l1[x] <= act:
                    active, best = True, act
                    if c1[x] >= act + trail: px = act + trail; break
                    continue
                if active: best = min(best, l1[x])
        if px is None: px = o1[lim]
        out.append((t1[j], (px - e) * side))
    d = pd.DataFrame(out, columns=["t", "pts"])
    return d

rows = []
for name, kw in [("original: +10 then trail 0.5", {}), ("original, RTH only", dict(rth=True)),
                 ("trail 5 after +10", dict(trail=5)), ("trail 10 after +10", dict(trail=10)),
                 ("fixed TP 10 / SL 100", dict(fixed=True)), ("fixed TP 20 / SL 100", dict(fixed=True, tp=20)),
                 ("fixed TP 10, RTH only", dict(fixed=True, rth=True)), ("trail 5 after +10, RTH only", dict(trail=5, rth=True))]:
    d = sim(**kw); g = d.pts
    yrs = d.t.dt.year
    row = dict(variant=name, trades=len(d), per_day=round(len(d) / 1700, 1), win=round(100 * (g > 0).mean(), 1),
               gross_pts=round(g.mean(), 2), gross_usd_total=round(2 * g.sum()))
    for label, cost in (("$1.00 (comm only, no slip)", 0.5), ("$2.50 (comm+1 tick)", 1.25), ("$3.50 (comm+2 ticks)", 1.75)):
        row["net " + label] = round(2 * (g - cost).sum())
    row["IS_gross"] = round(g[d.t < IS_END].mean(), 2); row["OOS_gross"] = round(g[d.t >= IS_END].mean(), 2)
    row["yrs+ @2.50"] = f"{int(((g - 1.25).groupby(yrs).sum() > 0).sum())}/{yrs.nunique()}"
    rows.append(row); print(row, flush=True)
pd.DataFrame(rows).to_csv("frama_variants.csv", index=False)
