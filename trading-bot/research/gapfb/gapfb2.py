"""GapFB improvement search with a strict funnel: choose on TRAIN 2010-19, confirm on VALIDATE 2020-23, look at TEST 2024-26 once.
Knobs: opening-range length, direction vs the gap (both / with gap = gap-and-go / against = gap-fill), stop (k×ATR or the
other side of the OR, capped), break-even / ATR trailing after +x R, entry cut-off, exit time, gap band. 1 trade a day."""
import sys, itertools, pickle, os; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb import periods, SP
CACHE = SP + "gapfb_days.pkl"
def arrays():
    if os.path.exists(CACHE): return pickle.load(open(CACHE, "rb"))
    out = {}
    for nm, dd in periods().items():
        prev = None; rows = []
        for d, g in dd:
            o, h, l, c, a = (g[k].values.astype(float) for k in ("open", "high", "low", "close", "atr"))
            if prev is not None: rows.append((d, o[0] / prev - 1, o, h, l, c, a))
            prev = c[389]
        out[nm] = rows
    pickle.dump(out, open(CACHE, "wb")); return out
def trade(o, h, l, c, a, gap, orm, direction, stop, be, trail, cut, ex, gmin, gmax):
    if not (gmin <= abs(gap) < gmax): return None
    orh, orl = h[:orm].max(), l[:orm].min()
    hu = np.nonzero(h[orm:cut + 1] >= orh)[0]; hd = np.nonzero(l[orm:cut + 1] <= orl)[0]
    tu = hu[0] + orm if len(hu) else 9999; td = hd[0] + orm if len(hd) else 9999
    gs = 1 if gap > 0 else -1
    if direction == "with": td = 9999 if gs == 1 else td; tu = 9999 if gs == -1 else tu
    if direction == "against": tu = 9999 if gs == 1 else tu; td = 9999 if gs == -1 else td
    if tu == td: return None
    s, j = (1, tu) if tu < td else (-1, td)
    e = max(orh, o[j]) if s == 1 else min(orl, o[j]); A = a[j]
    if stop == "or": st = min(orh - orl, 4 * A)
    else: st = stop * A
    if st <= 0: return None
    sl = e - s * st; best = e
    for k in range(j, ex + 1):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl):
            px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
        best = max(best, h[k]) if s == 1 else min(best, l[k])
        if be and s * (best - e) >= be * st: sl = max(sl, e) if s == 1 else min(sl, e)
        if trail: sl = max(sl, best - trail * A) if s == 1 else min(sl, best + trail * A)
    else: px = c[ex]
    return (s * (px - e) - 2.25 * e / 17000) / st
def evaluate(rows, cfg):
    R = [r for d, g, o, h, l, c, a in rows if (r := trade(o, h, l, c, a, g, *cfg)) is not None]
    return np.array(R)
GRID = dict(orm=(1, 5, 15), direction=("both", "with", "against"), stop=(2.0, 3.0, 4.0, "or"), be=(0, 1.0, 2.0), trail=(0, 3.0, 5.0),
            cut=(60, 389), ex=(150, 270, 385), gmin=(0.003, 0.005), gmax=(0.02, 1.0))
if __name__ == "__main__":
    A = arrays(); keys = list(GRID); res = []
    for vals in itertools.product(*GRID.values()):
        cfg = vals; R = evaluate(A["2010-19"], cfg)
        if len(R) < 300: continue
        w = R > 0; res.append(dict(zip(keys, vals), n=len(R), win=100 * w.mean(), rr=R[w].mean() / -R[~w].mean(), R=R.mean(),
                                   t=R.mean() / R.std() * np.sqrt(len(R))))
    T = pd.DataFrame(res).sort_values("R", ascending=False); T.to_csv("train_grid.csv", index=False)
    pd.set_option("display.width", 250); print(len(T), "configs"); print(T.head(25).round(3).to_string(index=False))
