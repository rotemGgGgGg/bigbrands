"""AVP-zone rule reverse-engineered from allo's screenshots (QQQ Nov 2, GC Nov 1-2, NQ Nov 3, NQ short Nov 5):
  - zones = LVNs (low-volume nodes) of a composite profile of the previous N sessions (computed before the day: no look-ahead)
  - a 5-minute bar coming from above trades into the top of an LVN and closes back above it -> long (mirror: short at the bottom)
  - stop beyond the zone's far edge or the bar's wick, whichever is further, minus 1 tick
  - target: 2R / 3R / 1% / the session's earlier extreme (the 'white line') / hold to 15:55
Volume: HistData has none, so the profile is time-at-price (each 1-minute bar spreads 1 unit over its range) - a TPO proxy.
Test: 2012-19 vs 2020-26, plus the random baseline from allo's own paper: the same rule on zones shifted by a random amount
(same widths), 100 runs. Cost 1.3 bp per trade. NQ = NSXUSD 1-minute, 00:00-16:00 NY."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../spmodel"))
from lbr import days
G = days("NSXUSD"); DL = sorted(G); BP = 1.3; TICK = 0.25


def zones_for(j, nback=5, rowfrac=0.0005, thr=0.35, minrun=3):
    d = DL[j]; px = G[d][0][0]; row = max(TICK, round(px * rowfrac / TICK) * TICK)
    hs = np.concatenate([G[DL[k]][1] for k in range(j - nback, j)]); ls = np.concatenate([G[DL[k]][2] for k in range(j - nback, j)])
    lo0 = ls.min(); n = int((hs.max() - lo0) / row) + 2; prof = np.zeros(n)
    a = ((ls - lo0) / row).astype(int); b = ((hs - lo0) / row).astype(int)
    w = 1.0 / (b - a + 1); np.add.at(prof, a, w); np.add.at(prof, b + 1, -w); prof = np.cumsum(prof)[:n]
    sm = np.convolve(prof, np.ones(3) / 3, mode="same")
    ref = pd.Series(sm).rolling(41, center=True, min_periods=10).max().values
    low = sm < thr * ref; Z = []; k = 0
    while k < n:
        if low[k]:
            e = k
            while e + 1 < n and low[e + 1]: e += 1
            if e - k + 1 >= minrun and k > 3 and e < n - 4: Z.append((lo0 + k * row, lo0 + (e + 1) * row))
            k = e + 1
        else: k += 1
    return Z


ZCACHE = {}
def trades(target="2R", shift=None, rng=None, maxn=1):
    out = {}
    for j in range(6, len(DL)):
        d = DL[j]
        if j not in ZCACHE: ZCACHE[j] = zones_for(j)
        Z = ZCACHE[j]
        if not Z: continue
        if shift is not None:
            Z = [(lo + s * (hi - lo), hi + s * (hi - lo)) for (lo, hi), s in zip(Z, rng.choice([-1, 1], len(Z)) * rng.uniform(1.0, 3.0, len(Z)))]
        o, h, l, c = G[d]; taken = 0
        for i in range(579, 925, 5):                                    # 5-min bars from 09:35 to 15:25
            bh, bl, bc, pc = h[i - 4:i + 1].max(), l[i - 4:i + 1].min(), c[i], c[i - 5]
            sig = None
            for lo, hi in Z:
                if pc > hi and bl <= hi and bc > hi: sig = (1, min(lo, bl) - TICK); break
                if pc < lo and bh >= lo and bc < lo: sig = (-1, max(hi, bh) + TICK); break
            if sig is None: continue
            s, stop = sig; e0 = i + 1; ent = o[e0]; risk = s * (ent - stop)
            if risk <= ent * 0.0003: continue
            if target in ("2R", "3R"): tg = ent + s * float(target[0]) * risk
            elif target == "1%": tg = ent * (1 + s * 0.01)
            elif target == "extreme": tg = h[570:e0].max() if s == 1 else l[570:e0].min()
            else: tg = None
            if tg is not None and s * (tg - ent) <= 0: tg = ent + s * 2 * risk
            hh, ll = h[e0:955], l[e0:955]
            hs_ = np.nonzero(ll <= stop)[0] if s == 1 else np.nonzero(hh >= stop)[0]
            ht = (np.nonzero(hh >= tg)[0] if s == 1 else np.nonzero(ll <= tg)[0]) if tg is not None else np.array([], int)
            ts, tt = (hs_[0] if len(hs_) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
            px = stop if ts <= tt and ts < 10 ** 9 else (tg if tt < 10 ** 9 else c[954])
            out[(d, i)] = (s * (px - ent) - ent * BP / 1e4) / risk
            taken += 1
            if taken >= maxn: break
    s = pd.Series(out, dtype=float)
    if len(s): s.index = pd.DatetimeIndex([k[0] for k in s.index])
    return s


def st(s):
    t = lambda x: x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0
    Y = s.index.year; I, O, L2 = s[Y <= 2019], s[Y >= 2020], s[s.index >= "2024-10-24"]
    return dict(n_yr=len(s) / 14.8, win=100 * (s > 0).mean(), rr=s[s > 0].mean() / -s[s < 0].mean(), IS_R=I.mean(), IS_t=t(I), OOS_R=O.mean(),
                OOS_t=t(O), last2y_R=L2.mean(), pos_yrs=f"{int((s.groupby(Y).sum() > 0).sum())}/15")


if __name__ == "__main__":
    rows = []
    for tg in ("2R", "3R", "1%", "extreme", "eod"):
        s = trades(tg); r = st(s); r["target"] = tg
        rng = np.random.default_rng(42); pl_is, pl_oos = [], []
        for _ in range(100):
            p = trades(tg, shift=True, rng=rng); Y = p.index.year; pl_is.append(p[Y <= 2019].mean()); pl_oos.append(p[Y >= 2020].mean())
        r["p_IS_vs_shifted"] = np.mean(np.array(pl_is) >= r["IS_R"]); r["p_OOS_vs_shifted"] = np.mean(np.array(pl_oos) >= r["OOS_R"])
        r["shifted_median_OOS_R"] = np.median(pl_oos); rows.append(r); print(tg, "done", flush=True)
    T = pd.DataFrame(rows); pd.set_option("display.width", 230); print(T.round(3).to_string(index=False))
    zc = [len(ZCACHE[j]) for j in ZCACHE]; print(f"zones per day: median {np.median(zc):.0f}")
