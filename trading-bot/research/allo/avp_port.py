"""Exact Python port of pine/avp_zones.pine (defaults), to test it on 14 years instead of the few months TradingView loads.
Session = futures day starting 18:00 New York. At each session start: composite profile of the previous 5 sessions' chart
bars (each bar's volume spread evenly over its range, 150 rows), 3-row smoothing, LVN = below 35% of the local peak (+-20 rows),
runs >= 3 rows. Signal on a confirmed bar: close[1] > LVN top, low <= top, close > top -> long (mirror short), one per zone per
side per session, stop = zone far edge or the bar's extreme minus 2 points, target 2R; flat at the next session's open.
Scoreboard identical to the Pine table (no costs), plus a with-costs column (1 NQ point per round trip; DAX 1, gold 0.3).
Volume modes: 'real' (Dukascopy tick volume), 'tpo' (1 per bar), and HistData NSXUSD (no volume -> tpo).
Random baseline: zones shifted by 1-3 zone widths in a random direction (100 runs)."""
import sys, os, math, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi"))
import mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
COST = {"USATECHIDXUSD": 1.0, "NSXUSD": 1.0, "DEUIDXEUR": 1.0, "XAUUSD": 0.3}


def bars(sym, tf):
    f = SP + f"port_{sym}_{tf}.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    if sym == "NSXUSD":
        df = mdata.histdata(sym); df = df[~df.index.duplicated()].sort_index(); df["v"] = 1.0
    else:
        z = np.load(mdata.DK + sym + ".npz"); t = pd.to_datetime(z["t"] * 60, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
        df = pd.DataFrame({k: z[k] for k in "ohlcv"}, index=t); df = df[~df.index.duplicated()].sort_index()
    b = df.resample(f"{tf}min", label="left", closed="left").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum")).dropna()
    b["sess"] = (b.index + pd.Timedelta(hours=6)).normalize()
    pd.to_pickle(b, f); return b


def zones(h, l, v, n_rows=150, thr=0.35, win=20, min_run=3):
    lo, hi = l.min(), h.max(); rowH = (hi - lo) / n_rows
    if rowH <= 0: return []
    a = np.clip(((l - lo) / rowH).astype(int), 0, n_rows - 1); b = np.clip(((h - lo) / rowH).astype(int), 0, n_rows - 1)
    per = v / (b - a + 1); prof = np.zeros(n_rows + 1); np.add.at(prof, a, per); np.add.at(prof, b + 1, -per); prof = np.cumsum(prof)[:n_rows]
    s = prof.copy(); cnt = np.ones(n_rows); s[1:] += prof[:-1]; cnt[1:] += 1; s[:-1] += prof[1:]; cnt[:-1] += 1; sm = s / cnt
    pk = pd.Series(sm).rolling(2 * win + 1, center=True, min_periods=1).max().values
    idx = np.arange(n_rows); low = (sm < thr * pk) & (idx > 3) & (idx < n_rows - 4); Z = []; r = 0
    while r < n_rows:
        if low[r]:
            e = r
            while e + 1 < n_rows and low[e + 1]: e += 1
            if e - r + 1 >= min_run: Z.append((lo + r * rowH, lo + (e + 1) * rowH))
            r = e + 1
        else: r += 1
    return Z


def run(sym, tf, vol="real", n_sess=5, rr=2.0, buf=2.0, stop_mode="zone", shift_rng=None, thr=0.35):
    B = bars(sym, tf); O, Hh, L, C, V = (B[k].values for k in "ohlcv"); S = B.sess.values
    if vol == "tpo": V = np.ones(len(B))
    starts = np.r_[0, np.nonzero(S[1:] != S[:-1])[0] + 1]; ends = np.r_[starts[1:], len(B)]
    res = []; openT = []                                    # trades: (entry, stop, target, dir, entry_time)
    for si in range(len(starts)):
        a, e_ = starts[si], ends[si]
        # flat open trades at this session's first bar open, after checking stop/target on that bar (Pine order)
        if si >= n_sess:
            pa, pb = starts[si - n_sess], starts[si]
            Z = zones(Hh[pa:pb], L[pa:pb], V[pa:pb], thr=thr)
            if shift_rng is not None:
                Z = [(lo + s * (hi - lo), hi + s * (hi - lo)) for (lo, hi), s in zip(Z, shift_rng.choice([-1, 1], len(Z)) * shift_rng.uniform(1.0, 3.0, len(Z)))]
        else: Z = []
        usedL = [False] * len(Z); usedS = [False] * len(Z)
        for i in range(a, e_):
            new = i == a
            keep = []
            for (en, st, tg, d, t0) in openT:
                if (d == 1 and L[i] <= st) or (d == -1 and Hh[i] >= st): res.append((t0, -1.0, en, st))
                elif (d == 1 and Hh[i] >= tg) or (d == -1 and L[i] <= tg): res.append((t0, rr, en, st))
                elif new: res.append((t0, d * (O[i] - en) / abs(en - st), en, st))
                else: keep.append((en, st, tg, d, t0))
            openT = keep
            if i == 0 or not Z: continue
            sig = None
            for k, (bot, top) in enumerate(Z):
                if sig is None and not usedL[k] and C[i - 1] > top and L[i] <= top and C[i] > top:
                    sl = (L[i] if stop_mode == "wick" else min(bot, L[i])) - buf; sig = (1, sl); usedL[k] = True
                if not usedS[k] and C[i - 1] < bot and Hh[i] >= bot and C[i] < bot:
                    ss = (Hh[i] if stop_mode == "wick" else max(top, Hh[i])) + buf
                    usedS[k] = True
                    if sig is None: sig = (-1, ss)
            if sig is not None:
                d, st = sig; en = C[i]; rk = abs(en - st)
                if rk > 0: openT.append((en, st, en + d * rr * rk, d, B.index[i]))
    T = pd.DataFrame(res, columns=["t", "R", "entry", "stop"]).set_index("t").sort_index()
    T["R_cost"] = T.R - COST.get(sym, 1.0) / (T.entry - T.stop).abs()
    return T


def summ(T, col="R"):
    x = T[col]; t = lambda s: s.mean() / s.std() * math.sqrt(len(s)) if len(s) > 2 and s.std() > 0 else 0
    Y = T.index.year; I, Oo = x[Y <= 2019], x[Y >= 2020]; w = (T.R > 0)
    return dict(n=len(x), per_yr=len(x) / max((T.index[-1] - T.index[0]).days / 365.25, 1e-9), win=100 * (T.R >= 1.999).mean(),
                avgR=x.mean(), IS=I.mean(), IS_t=t(I), OOS=Oo.mean(), OOS_t=t(Oo), pos_yrs=f"{int((x.groupby(Y).sum() > 0).sum())}/{Y.nunique()}")


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "DEUIDXEUR"
    for tf in (5, 15):
        T = run(sym, tf); print(sym, tf, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in summ(T).items()})
