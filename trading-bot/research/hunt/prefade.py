"""Pre-open fade ("news overreaction"): at 09:00 ET, if the move from 09:00−L to 08:59 is more than z standard
deviations (rolling 20 days of that same window, previous days only), fade it.
Entry 09:00 open. Target = retrace a × |pre-move| ; stop = b × |pre-move| beyond entry ; time exit at T_exit.
1-minute walk, stop first on ties, $2.50 / 1.25 pt costs."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd, itertools
from engine import S
COST, TICK = 1.25, 0.25
full = pd.read_pickle(S + "full1m.pkl")
full = full[~full.index.duplicated()]
m = full.index.hour * 60 + full.index.minute
day = full.index.normalize()
DAYS = {}
sel = full[(m >= 300) & (m < 960)]                       # 05:00–15:59 window per day
for d, g in sel.groupby(sel.index.normalize()):
    if d.weekday() >= 5: continue
    gm = (g.index.hour * 60 + g.index.minute).values
    if not ((gm == 540).any()): continue
    DAYS[d] = (gm, g.open.values, g.high.values, g.low.values, g.close.values)
dates = sorted(DAYS)

def pre_move(L):
    mv = {}
    for d in dates:
        gm, o, h, l, c = DAYS[d]
        a = np.nonzero(gm == 540 - L)[0]; b = np.nonzero(gm == 539)[0]
        if len(a) and len(b): mv[d] = c[b[0]] - o[a[0]]
    s = pd.Series(mv)
    ret = s / pd.Series({d: DAYS[d][1][np.nonzero(DAYS[d][0] == 540)[0][0]] for d in s.index})
    z = ret / ret.rolling(20).std().shift()
    return s, z

def trade(d, side, size, a, b, t_exit, entry_min=540):
    gm, o, h, l, c = DAYS[d]
    j0 = np.nonzero(gm >= entry_min)[0]
    if not len(j0): return None
    j0 = j0[0]; e = o[j0]
    tp = e + side * a * size if a else None
    sl = e - side * b * size if b else None
    for j in range(j0, len(gm)):
        if gm[j] >= t_exit: return side * (o[j] - e) - COST
        if sl is not None and ((l[j] <= sl) if side == 1 else (h[j] >= sl)):
            return side * ((min(o[j], sl) if side == 1 else max(o[j], sl)) - e) - COST
        if tp is not None and ((h[j] >= tp + TICK) if side == 1 else (l[j] <= tp - TICK)):
            return side * (tp - e) - COST
    return side * (c[-1] - e) - COST

def stats(x):
    x = pd.Series(x).dropna(); y = x.index.year if hasattr(x.index, "year") else None
    w, lo = x[x > 0], x[x <= 0]
    isd = x.index < pd.Timestamp("2024-01-01", tz=x.index.tz)
    cs = (2 * x).cumsum()
    st = cur = ls = lc = 0
    for v in x:
        cur = cur + 1 if v > 0 else 0; st = max(st, cur); lc = lc + 1 if v <= 0 else 0; ls = max(ls, lc)
    return dict(n=len(x), win=round(100 * (x > 0).mean(), 1), avg=round(2 * x.mean(), 1), avg_w=round(2 * w.mean()) if len(w) else 0,
                avg_l=round(2 * lo.mean()) if len(lo) else 0, IS=round(2 * x[isd].mean(), 1), OOS=round(2 * x[~isd].mean(), 1),
                tot=round(2 * x.sum()), maxdd=round((cs - cs.cummax()).min()), yrs=f"{int((x.groupby(x.index.year).sum() > 0).sum())}/{x.index.year.nunique()}",
                pf=round(w.sum() / -lo.sum(), 2) if len(lo) and lo.sum() < 0 else 99, wst=st, lst=ls)

if __name__ == "__main__":
    rows = []
    for L in (30, 60, 120):
        s, z = pre_move(L)
        for zt in (1.25, 1.5, 2.0):
            sig = z[(z.abs() > zt)].index
            for a, b, te in itertools.product((0.25, 0.5, 0.75, 1.0, None), (0.5, 1.0, 1.5, None), (630, 720, 780, 900)):
                x = {d: trade(d, -int(np.sign(s[d])), abs(s[d]), a, b, te) for d in sig}
                r = stats(pd.Series(x)); r.update(L=L, z=zt, a=a, b=b, te=te); rows.append(r)
        print(L, len(rows), file=sys.stderr, flush=True)
    R = pd.DataFrame(rows); R.to_csv("prefade_grid.csv", index=False)
    pd.set_option("display.width", 250)
    print(R.sort_values("IS", ascending=False).head(40).to_string())
