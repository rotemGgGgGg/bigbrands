"""Opening-window search (user request): setups that form in the first K minutes after 09:30 (K = 1,2,3,5,10,15) on the
1-minute chart, using free tools - Fibonacci levels of an anchor range - with every combination of entry level, order type,
stop, target, exit time and three filters. 12.4M variants.

Anchor ranges (low=0, high=1): opening range of the first K minutes, previous RTH day, pre-market 04:00-09:29, open vs prior close.
Entry  : Fib level x in LEVELS, limit (fade/retrace) or stop (breakout) order, long or short, eligible from minute K until 10:30.
Stop   : fill -/+ s x range (s in STOPS, inf = none). Target: fill +/- t x range. Exit by 10:00 / 10:30 / 11:00 / 12:00 / 16:00.
Filters: opening-range candle with/against the trade, gap with/against, opening range smaller/larger than its prior-20-day median.
Fills  : limits need 1 tick through, stop entries fill at the worse of level/open, stop wins a stop+target tie, a stop already
         beyond the fill exits at the fill. Costs 2.25 pt x price/17000 per round trip.
Funnel : select on 2012-2019 only, 2020-2023 validation, 2024-2026-10 holdout looked at once, coin flips + 2x costs on finalists."""
import sys, os, time, itertools, pickle, math
import numpy as np, pandas as pd
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "papers")); import pdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/open15/"
KS = (1, 2, 3, 5, 10, 15); ANCH = ("or", "pd", "pm", "gap")
LEVELS = (-1.618, -1.0, -0.618, -0.272, 0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0, 2.618)
STOPS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, np.inf); TGTS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0)
TXS = (29, 59, 89, 149, 389); LAST_ENTRY = 60; TICK = 0.25
FILT = list(itertools.product(("any", "with", "against"), ("any", "with", "against"), ("any", "small", "large")))
D = pdata.load(); O, H, L, C = D["o"], D["h"], D["l"], D["c"]; N = len(D["dc"]); MM = np.arange(390)
YR = D["days"].year.values; YI = YR - 2012; NY = YI.max() + 1
PC = np.r_[np.nan, D["dc"][:-1]]; COST = 2.25 * D["do"] / 17000
TR, VA, HO = YR <= 2019, (YR >= 2020) & (YR <= 2023), YR >= 2024


def anchor(K, a):
    if a == "or": hi, lo = H[:, :K].max(1), L[:, :K].min(1)
    elif a == "pd": hi, lo = np.r_[np.nan, D["dh"][:-1]], np.r_[np.nan, D["dl"][:-1]]
    elif a == "pm": hi, lo = D["pmh"], D["pml"]
    else: hi, lo = np.fmax(D["do"], PC), np.fmin(D["do"], PC)
    return hi, lo


def filters(K, sd):
    ordir = np.sign(C[:, K - 1] - O[:, 0]) * sd; gp = np.sign(D["do"] - PC) * sd
    orr = H[:, :K].max(1) - L[:, :K].min(1); med = pd.Series(orr).rolling(20).median().shift(1).values
    F = np.zeros((N, len(FILT)))
    for j, (a, b, c) in enumerate(FILT):
        m = np.ones(N, bool)
        if a != "any": m &= (ordir > 0) if a == "with" else (ordir < 0)
        if b != "any": m &= (gp > 0) if b == "with" else (gp < 0)
        if c != "any": m &= (orr < med) if c == "small" else (orr > med)
        F[:, j] = m
    return F


def first(mask): return np.where(mask.any(1), mask.argmax(1), 9999)


def group(K, a, x, sd, et, detail=None):
    """all stop x target x exit combos for one (K, anchor, level, side, order type). Returns P (N x combos) of net pts."""
    hi, lo = anchor(K, a); R = hi - lo; ok = np.isfinite(R) & (R > 0); lvl = lo + x * R
    lv = np.where(ok, lvl, np.nan)[:, None]; el = (MM[None] >= K) & (MM[None] <= LAST_ENTRY)
    if et == "lim": hit = (L <= lv - TICK) if sd > 0 else (H >= lv + TICK)
    else: hit = (H >= lv) if sd > 0 else (L <= lv)
    fm = first(el & hit); tr = (fm < 9999) & ok; r = np.arange(N); om = O[r, np.minimum(fm, 389)]
    if et == "lim": fp = np.minimum(lvl, om) if sd > 0 else np.maximum(lvl, om)
    else: fp = np.maximum(lvl, om) if sd > 0 else np.minimum(lvl, om)
    after = MM[None] >= fm[:, None]; after2 = MM[None] > fm[:, None]
    MS, SPX, MT, TP = [], [], [], []
    for s in STOPS:
        if np.isinf(s): MS.append(np.full(N, 9999)); SPX.append(np.zeros(N)); continue
        st = fp - sd * s * R; m = first(after & ((L <= st[:, None]) if sd > 0 else (H >= st[:, None]))); ox = O[r, np.minimum(m, 389)]
        px = np.where(m > fm, np.minimum(st, ox) if sd > 0 else np.maximum(st, ox), np.minimum(st, fp) if sd > 0 else np.maximum(st, fp))
        MS.append(m); SPX.append(px)
    for t in TGTS:
        tg = fp + sd * t * R; MT.append(first(after2 & ((H >= tg[:, None] + TICK) if sd > 0 else (L <= tg[:, None] - TICK)))); TP.append(tg)
    cols = []; keys = []
    for tx in TXS:
        live = tr & (fm <= tx); cx = C[:, tx]
        for i, s in enumerate(STOPS):
            for j, t in enumerate(TGTS):
                ms, mt = MS[i], MT[j]; xp = np.where((ms <= tx) & (ms <= mt), SPX[i], np.where(mt <= tx, TP[j], cx))
                cols.append(np.where(live, sd * (xp - fp) - COST, 0.0)); keys.append((tx, s, t))
                if detail is not None and detail == (tx, s, t):
                    return dict(d=np.nonzero(live)[0], fm=fm, fp=fp, R=R, xp=xp, net=cols[-1])
    return np.array(cols).T, keys


def work(arg):
    K, a, x, sd, et = arg; P, keys = group(K, a, x, sd, et); F = filters(K, sd)
    Y = np.eye(NY)[YI]; Z = (F[:, :, None] * Y[:, None, :]).reshape(N, -1)
    S3 = np.stack([TR, VA, HO], 1).astype(float); Z3 = (F[:, :, None] * S3[:, None, :]).reshape(N, -1)
    nz = (P != 0).astype(float)
    sy = (P.T @ Z).reshape(len(keys), len(FILT), NY); ny = (nz.T @ Z).reshape(len(keys), len(FILT), NY)
    sq = ((P * P).T @ Z3).reshape(len(keys), len(FILT), 3); wn = ((P > 0).astype(float).T @ Z3).reshape(len(keys), len(FILT), 3)
    n_tr = ny[:, :, :8].sum(2); s_tr = sy[:, :, :8].sum(2); mu = s_tr / np.maximum(n_tr, 1)
    var = sq[:, :, 0] / np.maximum(n_tr, 1) - mu ** 2; t = np.where(n_tr >= 150, mu / np.sqrt(np.maximum(var, 1e-12)) * np.sqrt(n_tr), 0)
    hist = np.histogram(t[n_tr >= 150], bins=np.arange(-30, 30.5, 0.5))[0]
    rows = []
    for ci, fi in zip(*np.nonzero(t >= 3.0)):
        tx, s, tg = keys[ci]
        rows.append(dict(K=K, anchor=a, level=x, side=sd, order=et, exit=tx, stop=s, tgt=tg, filt="/".join(FILT[fi]), t_tr=t[ci, fi],
                         **{f"y{2012 + k}": sy[ci, fi, k] for k in range(NY)}, **{f"n{2012 + k}": ny[ci, fi, k] for k in range(NY)},
                         sq_va=sq[ci, fi, 1], sq_ho=sq[ci, fi, 2], w_tr=wn[ci, fi, 0], w_va=wn[ci, fi, 1], w_ho=wn[ci, fi, 2]))
    best = np.unravel_index(np.argmax(t), t.shape)
    return rows, hist, int((n_tr >= 150).sum()), P.shape[1] * len(FILT), (float(t[best]), arg, keys[best[0]], FILT[best[1]])


if __name__ == "__main__":
    os.makedirs(SP, exist_ok=True)
    jobs = list(itertools.product(KS, ANCH, LEVELS, (1, -1), ("lim", "stp")))
    t0 = time.time(); rows = []; hist = 0; nvalid = 0; ntot = 0; bests = []
    with Pool(4) as pool:
        for i, (r, h, nv, nt, b) in enumerate(pool.imap_unordered(work, jobs, chunksize=2)):
            rows += r; hist = hist + h; nvalid += nv; ntot += nt; bests.append(b)
            if i % 40 == 0: print(f"{i}/{len(jobs)} groups, {ntot:,} variants, {len(rows)} with train t>=3, {time.time() - t0:.0f}s", flush=True)
    pickle.dump(dict(rows=rows, hist=hist, nvalid=nvalid, ntot=ntot, bests=bests), open(SP + "search.pkl", "wb"))
    print(f"done: {ntot:,} variants ({nvalid:,} with >=150 train trades), {len(rows)} with train t>=3, {time.time() - t0:.0f}s")
