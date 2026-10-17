"""Iterations 8–14 (queue items 8–14), each a hypothesis family at planned 1:2+ with ≤ 1 trade/day, TRAIN 2020–23 / TEST 2024–26.
8 CPI/NFP pre-open move (08:30→08:59 or 08:30→09:30) fade/follow   9 leveraged-ETF close flow   10 gap fill
11 failed opening-range breakout   12 1-minute liquidity-spike fade   13 turn-of-month / pre-holiday long   14 Monday vs Friday range."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, ".."), os.path.join(H, "../influencers")]
import numpy as np, pandas as pd, itertools
from lib import o, h, l, c, v, N, SIG, VALID, YR, DAYS, okprev, PDC, PDH, PDL, trade, TICK
from engine import S
rows = []
def rec(it, cfg, R):
    if len(R) < 30: return
    X = pd.DataFrame(R, columns=["i", "R"]).drop_duplicates("i"); tr = YR[X.i] < 2024; w = X.R > 0
    if tr.sum() < 15 or (~tr).sum() < 10: return
    rows.append(dict(iter=it, cfg=cfg, n=len(X), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1),
                     R_tr=round(X.R[tr].mean(), 3), R_te=round(X.R[~tr].mean(), 3),
                     realized=round(X.R[w].mean() / -X.R[~w].mean(), 2) if w.any() and (~w).any() else np.nan))
idx = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(DAYS)}
# ---- 8 CPI / NFP (pre-open from the 24h frame)
CPI = open(os.path.join(H, "cpi_dates.txt")).read().split()
NFP = [d.strftime("%Y-%m-%d") for d in DAYS if d.weekday() == 4 and d.day <= 7]
full = pd.read_pickle(S + "full1m.pkl"); full = full[~full.index.duplicated()]
def px(dstr, hm):
    t = pd.Timestamp(dstr + f" {hm}", tz="America/New_York")
    try: return full.loc[t, "open"]
    except KeyError: return np.nan
for cal, dates in (("CPI", CPI), ("NFP", NFP)):
    for mode, s, rr, endm in itertools.product(("fade", "follow"), (0.5, 1.0), (2.0, 3.0), (59, 179)):
        R = []
        for ds in dates:
            i = idx.get(ds)
            if i is None or not VALID[i]: continue
            p830, p900 = px(ds, "08:30"), px(ds, "09:00")
            mv = (o[i, 0] - p830) if np.isfinite(p830) else np.nan
            if not np.isfinite(mv) or abs(mv) < 5: continue
            side = -int(np.sign(mv)) if mode == "fade" else int(np.sign(mv)); e = o[i, 0]; sp = s * abs(mv)
            r = trade(i, 0, side, e - side * sp, e + side * rr * sp, last=endm)
            if r: R.append((i, r[0] / sp))
        rec(8, f"{cal} 08:30→09:30 {mode} stop{s}×move rr{rr} exit+{endm}", R)
# ---- 9 leveraged-ETF rebalancing: |open→15:30| > k σ → continuation to close
for k, s, rr in itertools.product((1.0, 1.5, 2.0), (0.1, 0.2), (2.0, 3.0)):
    R = []
    for i in range(N):
        if not VALID[i]: continue
        mv = c[i, 359] / o[i, 0] - 1
        if abs(mv) < k * SIG[i]: continue
        side = int(np.sign(mv)); e = o[i, 360]; sp = s * SIG[i] * o[i, 0]; r = trade(i, 360, side, e - side * sp, e + side * rr * sp)
        if r: R.append((i, r[0] / sp))
    rec(9, f"close flow |move|>{k}σ stop{s}σ rr{rr}", R)
# ---- 10 gap fill with ≥1:2 (stop = gap / rr)
for lo_, hi_, rr in itertools.product((0.1, 0.3, 0.6), (0.3, 0.6, 1.5), (2.0, 3.0)):
    if hi_ <= lo_: continue
    R = []
    for i in range(1, N):
        if not okprev[i]: continue
        gap = o[i, 0] - PDC[i]; gs = abs(gap) / (SIG[i] * o[i, 0])
        if not (lo_ <= gs < hi_): continue
        side = -int(np.sign(gap)); e = o[i, 0]; sp = abs(gap) / rr; r = trade(i, 0, side, e - side * sp, PDC[i])
        if r: R.append((i, r[0] / sp))
    rec(10, f"gap fill size {lo_}-{hi_}σ rr{rr}", R)
# ---- 11 failed OR breakout: first 5m close beyond OR(n) then a 5m close back inside → fade to the far side
for orm, rr_min in itertools.product((15, 30, 60), (2.0,)):
    R = []
    for i in range(N):
        if not VALID[i]: continue
        hi, lo = h[i, :orm].max(), l[i, :orm].min(); brk = None
        for m in range(orm + 4, 300, 5):
            if brk is None:
                if c[i, m] > hi: brk = (1, m)
                elif c[i, m] < lo: brk = (-1, m)
                continue
            if (brk[0] == 1 and c[i, m] < hi) or (brk[0] == -1 and c[i, m] > lo):
                side = -brk[0]; ext = h[i, brk[1]:m + 1].max() if side == -1 else l[i, brk[1]:m + 1].min()
                e = o[i, m + 1]; sl = ext + (TICK if side == -1 else -TICK); tgt = lo if side == -1 else hi; risk = abs(e - sl)
                if risk > 1 and abs(tgt - e) >= rr_min * risk:
                    r = trade(i, m + 1, side, sl, tgt)
                    if r: R.append((i, r[0] / risk))
                break
    rec(11, f"failed OR{orm} breakout fade (only trades with ≥1:2 to far side)", R)
# ---- 12 1-minute liquidity spike fade
for k, wick, rr in itertools.product((4, 6, 8), (0.5, 0.65), (2.0, 3.0)):
    R = []
    for i in range(N):
        if not VALID[i]: continue
        rg = h[i] - l[i]; avg = pd.Series(rg).rolling(30).mean().shift().values
        for m in range(31, 370):
            if rg[m] < k * avg[m]: continue
            up = (h[i, m] - max(o[i, m], c[i, m])) / rg[m]; dn = (min(o[i, m], c[i, m]) - l[i, m]) / rg[m]
            if up >= wick: side, sl = -1, h[i, m] + TICK
            elif dn >= wick: side, sl = 1, l[i, m] - TICK
            else: continue
            e = o[i, m + 1]; risk = abs(e - sl)
            if risk > 1 and (sl - e) * side < 0:
                r = trade(i, m + 1, side, sl, e + side * rr * risk)
                if r: R.append((i, r[0] / risk))
            break
    rec(12, f"spike fade k{k} wick{wick} rr{rr}", R)
# ---- 13 turn of month / pre-holiday long intraday
dts = pd.Series(DAYS)
tom = [i for i in range(1, N - 1) if DAYS[i + 1].month != DAYS[i].month or DAYS[i - 1].month != DAYS[i].month]
preh = [i for i in range(N - 1) if (DAYS[i + 1] - DAYS[i]).days > 1 and DAYS[i].weekday() != 4]
for nm, L in (("turn-of-month", tom), ("pre-holiday", preh)):
    for s, rr in itertools.product((0.2, 0.3, 0.5), (2.0, 3.0)):
        R = []
        for i in L:
            if not VALID[i]: continue
            sp = s * SIG[i] * o[i, 0]; e = o[i, 0]; r = trade(i, 0, 1, e - sp, e + rr * sp)
            if r: R.append((i, r[0] / sp))
        rec(13, f"{nm} long stop{s}σ rr{rr}", R)
# ---- 14 Monday: break of Friday's high/low first → continuation / fade at 1:2
for mode, s, rr in itertools.product(("cont", "fade"), (0.2, 0.3), (2.0, 3.0)):
    R = []
    for i in range(1, N):
        if DAYS[i].weekday() != 0 or not okprev[i]: continue
        up = np.nonzero(h[i, :360] > PDH[i])[0]; dn = np.nonzero(l[i, :360] < PDL[i])[0]
        f = min([(up[0], 1) if len(up) else (999, 0), (dn[0], -1) if len(dn) else (999, 0)])
        if f[1] == 0: continue
        side = f[1] if mode == "cont" else -f[1]; m = f[0] + 1; e = o[i, m]; sp = s * SIG[i] * o[i, 0]
        r = trade(i, m, side, e - side * sp, e + side * rr * sp)
        if r: R.append((i, r[0] / sp))
    rec(14, f"Monday Friday-level break {mode} stop{s}σ rr{rr}", R)
out = pd.DataFrame(rows); out.to_csv("iter08_14.csv", index=False); pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 70)
for it in range(8, 15):
    x = out[out.iter == it]
    if x.empty: print(f"iter {it}: no config with enough trades"); continue
    p = ((x.win_tr >= 70) & (x.win_te >= 70) & (x.R_tr > 0) & (x.R_te > 0)).sum()
    b = x.sort_values("win_te", ascending=False).iloc[0]
    print(f"iter {it}: configs {len(x)} PASS {p} | best TEST win {b.win_te}% (TRAIN {b.win_tr}%, R {b.R_tr:+.2f}/{b.R_te:+.2f}, n {b.n}) {b.cfg}")
