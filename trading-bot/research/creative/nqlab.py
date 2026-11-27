"""NQ LAB - theory first, then test. Families (each written with its story before running):
F1 RDM SURFACE   : yesterday's traders are trapped when today reverses early; the bigger both moves, the more fuel.
                   Map E[09:45->15:55 | today z, yesterday z] in tertiles (thresholds from 2012-19).
F2 TRAPPED NIGHT : RTH first 15/30 min reverses the overnight move -> overnight positions liquidate all day -> follow RTH.
F3 TWO-DAY TRAP  : two same-colour days, then today reverses early -> more trapped inventory than after one day.
F4 EXHAUSTION    : an early run > k ATR by 10:00 has used its fuel -> fade 10:00-12:00 (vs continuation control).
F5 WEEKLY DRIFT  : Thursday/Friday, price vs the week's open at 09:45 -> weekly positioning finishes in that direction.
F6 EARLY EXTREME : day's RTH low (high) printed 09:30-10:00 and price above (below) the open at 10:30 -> trend day.
F7 TURNAROUND TUE: Monday down -> Tuesday up (classic), and the mirror.
F8 SMALL GAP FILL: gap 0.1-0.4 ATR -> fade at 09:30 to yesterday's close, stop 1 gap beyond, flat 12:00.
Every series in bp per trade net of 1.3 bp. Gate: 2012-19 t>=2.5 and 2020-26 same sign t>=1.5. Survivors -> NQ book with RDM."""
import os as _os; DATA = _os.path.join(_os.path.expanduser(_os.environ.get("EDGE_DATA", "~/edge-data")), "")  # raw data + caches (set EDGE_DATA to move it)
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../spmodel"))
from lbr import days
BP = 1.3; G = days("NSXUSD"); DL = sorted(G); SP = DATA
RNG = pd.Series({d: G[d][1][570:960].max() - G[d][2][570:960].min() for d in DL}); ATR = RNG.rolling(14).mean().shift(1)
def r(d, e, x, s): o, h, l, c = G[d]; return s * (c[x - 1] / o[e] - 1) * 1e4 - BP
def tt(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0


def base():
    rows = []
    for j in range(2, len(DL)):
        d = DL[j]; A = ATR.get(d)
        if not np.isfinite(A): continue
        o, h, l, c = G[d]; p = G[DL[j - 1]]; p2 = G[DL[j - 2]]
        rows.append(dict(d=d, A=A, yd=p[3][959] - p[0][570], y2=p2[3][959] - p2[0][570], pc=p[3][959], td=o[585] - o[540],
                         on=o[569] - p[3][959], f15=c[584] - o[570], f30=c[599] - o[570], wd=d.weekday()))
    return pd.DataFrame(rows).set_index("d")


B = base(); S = {}
def add(name, d, v): S.setdefault(name, {})[d] = v

# F1 surface
dis = B[np.sign(B.td) != np.sign(B.yd)]; zt, zy = (dis.td / dis.A).abs(), (dis.yd / dis.A).abs()
qt, qy = zt[dis.index.year <= 2019].quantile([1 / 3, 2 / 3]).values, zy[dis.index.year <= 2019].quantile([1 / 3, 2 / 3]).values
for d, row in dis.iterrows():
    bt = int(np.searchsorted(qt, abs(row.td) / row.A)); by = int(np.searchsorted(qy, abs(row.yd) / row.A))
    add(f"F1 RDM today-tercile {bt} x yday-tercile {by}", d, r(d, 585, 955, np.sign(row.td)))
agr = B[np.sign(B.td) == np.sign(B.yd)]
for d, row in agr.iterrows(): add("F1 control: today AGREES with yesterday, follow today", d, r(d, 585, 955, np.sign(row.td)))
for d, row in B.iterrows():
    o, h, l, c = G[d]
    # F2
    for k, col, e in (("15", "f15", 585), ("30", "f30", 600)):
        if np.sign(row[col]) and np.sign(row[col]) != np.sign(row.on): add(f"F2 first {k} min reverses overnight -> follow to 15:55", d, r(d, e, 955, np.sign(row[col])))
    # F3
    if np.sign(row.yd) == np.sign(row.y2) and np.sign(row.td) and np.sign(row.td) != np.sign(row.yd): add("F3 two same days, today reverses -> follow", d, r(d, 585, 955, np.sign(row.td)))
    if np.sign(row.yd) != np.sign(row.y2) and np.sign(row.td) and np.sign(row.td) != np.sign(row.yd): add("F3 control: mixed days, today reverses -> follow", d, r(d, 585, 955, np.sign(row.td)))
    # F4
    run = (o[600] - o[570]) / row.A
    for k in (0.5, 0.8):
        if abs(run) > k:
            add(f"F4 run>{k}ATR by 10:00 -> fade 10-12", d, r(d, 600, 720, -np.sign(run)))
            add(f"F4 control run>{k}ATR -> continue to 15:55", d, r(d, 600, 955, np.sign(run)))
    # F6
    lo_t, hi_t = np.argmin(l[570:630]), np.argmax(h[570:630])
    dayl, dayh = l[570:630].min(), h[570:630].max()
    if lo_t < 30 and o[630] > o[570] and l[600:630].min() > dayl: add("F6 early low + above open at 10:30 -> long to 15:55", d, r(d, 630, 955, 1))
    if hi_t < 30 and o[630] < o[570] and h[600:630].max() < dayh: add("F6 early low + above open at 10:30 -> long to 15:55", d, r(d, 630, 955, -1))
    # F7
    if row.wd == 1:
        add("F7 Tuesday: opposite of Monday, 09:30-15:55", d, r(d, 570, 955, -np.sign(row.yd)))
    # F8
    gap = o[570] - row.pc; g = abs(gap) / row.A
    if 0.1 < g < 0.4:
        s = -np.sign(gap); ent = o[570]; tg = row.pc; sl = ent - s * abs(gap)
        hh, ll = h[570:720], l[570:720]
        hs = np.nonzero(ll <= sl)[0] if s == 1 else np.nonzero(hh >= sl)[0]; ht = np.nonzero(hh >= tg)[0] if s == 1 else np.nonzero(ll <= tg)[0]
        ts, tg_ = (hs[0] if len(hs) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
        px = sl if ts <= tg_ and ts < 10 ** 9 else (tg if tg_ < 10 ** 9 else c[719]); add("F8 small gap fill by 12:00", d, s * (px / ent - 1) * 1e4 - BP)
# F5 weekly
wk_open = {}
for d in DL: wk_open.setdefault(d - pd.Timedelta(days=d.weekday()), G[d][0][0])
for d, row in B.iterrows():
    if row.wd in (3, 4):
        wo = wk_open[d - pd.Timedelta(days=d.weekday())]; s = np.sign(G[d][0][585] - wo)
        if s: add("F5 Thu/Fri follow price vs week open, 09:45-15:55", d, r(d, 585, 955, s))
# RDM reference
for d, row in B.iterrows():
    if np.sign(row.td) and np.sign(row.td) != np.sign(row.yd): add("RDM (reference)", d, r(d, 585, 955, np.sign(row.td)))

if __name__ == "__main__":
    rows = []
    for k, v in S.items():
        s = pd.Series(v).sort_index(); Y = s.index.year; I, O, L2 = s[Y <= 2019], s[Y >= 2020], s[s.index >= "2024-10-24"]
        if len(s) < 40: continue
        rows.append(dict(family=k, per_yr=len(s) / 14.8, win=100 * (s > 0).mean(), rr=s[s > 0].mean() / -s[s < 0].mean(), IS_bp=I.mean(), IS_t=tt(I),
                         OOS_bp=O.mean(), OOS_t=tt(O), last2y=L2.mean(), pos_yrs=f"{int((s.groupby(Y).sum() > 0).sum())}/15",
                         PASS=bool(tt(I) >= 2.5 and np.sign(O.mean()) == np.sign(I.mean()) and abs(tt(O)) >= 1.5)))
    T = pd.DataFrame(rows).sort_values("IS_t", ascending=False); pd.set_option("display.width", 240); pd.set_option("display.max_colwidth", 70)
    print(T.round(2).to_string(index=False)); pd.to_pickle(S, SP + "nqlab_series.pkl")
