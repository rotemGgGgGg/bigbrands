"""LAYERS - 13,271,040 multi-timeframe strategies on NQ (Dukascopy 1-min with volume, 2012-2026, NY time, cost 1 pt round trip).
Every strategy = HTF zone -> touch -> 15-minute confirmation -> 1-minute entry -> stop -> target -> context filters.
 L1 HTF fair-value gap   : timeframe D / 4H / 1H; 3-candle gap (low[i] > high[i-2] or mirror), active after the 3rd candle closes.
 L1 touch                : near edge / 50% (CE) / far edge (full fill), first touch within 30 days.
 L1 mode                 : react (trade away from the zone) / invert (trade through it, the gap failed).
 L2 15m confirmation     : none / close back out of the zone / engulfing / break of structure / displacement candle /
                           15m FVG / sweep-and-reclaim / volume push (8 bars = 2 hours window).
 L3 1m entry             : market / limit at 50% of the confirmation bar / 1m micro break (close > 5-bar high) / limit at zone edge
                           (60-minute window).
 Stop                    : zone far edge -2 / swing since touch -2 / 0.10 x daily ATR / 0.25 x daily ATR. Risk 3 pts .. 1.5 ATR.
 Target                  : 1R / 2R / 3R / 5R / 10R / hold to session close (17:00). Stop first when both in one bar.
 Filters (960)           : gap size >= 0 / .25 / .5 / 1 ATR(tf) x touch age <= 1 / 3 / 10 / 30 days x session all/Asia/London/NY AM/NY PM
                           x daily trend all/with/against x day state all/with today's move/against/expanded (>0.8 ATR).
Base configs 3*3*2*8*4*4*6 = 13,824; x 960 filters = 13,271,040 strategies.
GATES: 2012-17 n>=40, t>=3  ->  2018-21 n>=20, t>=2  ->  2022-26 looked at once.
PLACEBO: the whole factory again with every zone moved 1-3 zone widths up or down at random (same sizes, same times)."""
import os, sys, time, math, numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"; DK = SP + "duka/"
OUT = SP + "layers/"; os.makedirs(OUT, exist_ok=True)
COST = 1.0
TFS = ["D", "4H", "1H"]; TOUCH = ["near", "mid", "far"]; MODE = ["react", "invert"]
CONF = ["none", "reject", "engulf", "bos", "displace", "fvg15", "sweep", "volume"]
ENTRY = ["market", "limit50", "micro_bos", "retest"]; STOP = ["zone", "swing", "0.10atr", "0.25atr"]; TGT = [1, 2, 3, 5, 10, "close"]
NCHUNK = 8 * 4 * 4 * 6; NB = 3 * 3 * 2 * NCHUNK; NCELL = 512

# ---------------------------------------------------------------- data
z = np.load(DK + "USATECHIDXUSD.npz")
Tt = pd.to_datetime(z["t"].astype(np.int64) * 60, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
df = pd.DataFrame({k: z[k].astype(float) for k in "ohlcv"}, index=Tt); df = df[~df.index.duplicated()].sort_index()
df = df[df.index >= "2011-10-01"]
O, H, L, C, V = (df[k].values for k in "ohlcv"); T = df.index; N = len(df); NS = T.values.astype("datetime64[ns]").astype(np.int64)
MIN = (T.hour * 60 + T.minute).values; YEAR = T.year.values
sid = pd.factorize((T + pd.Timedelta(hours=6)).normalize())[0]
sst = np.r_[0, np.nonzero(np.diff(sid))[0] + 1]; sen = np.r_[sst[1:], N]


def sparse(a, fn):
    tab = [a]; k = 1
    while (1 << k) <= len(a):
        p = tab[-1]; h = 1 << (k - 1); tab.append(fn(p[:-h], p[h:])); k += 1
    return tab


MINL = sparse(L, np.minimum); MAXH = sparse(H, np.maximum)


def first_hit(tab, level, start, end, le):
    """smallest j in [start, end) with L[j] <= level (le, min-table) or H[j] >= level (max-table); end if none."""
    pos = start.astype(np.int64).copy()
    for k in range(len(tab) - 1, -1, -1):
        step = 1 << k; ok = pos + step <= end
        if not ok.any(): continue
        v = tab[k][np.where(ok, pos, 0)]
        adv = ok & ((v > level) if le else (v < level))
        pos = np.where(adv, pos + step, pos)
    return pos


def rmq(tab, fn, a, b):
    """fn over [a, b), b > a."""
    n = b - a; k = np.floor(np.log2(np.maximum(n, 1))).astype(int); out = np.empty(len(a))
    for kk in np.unique(k):
        m = k == kk; out[m] = fn(tab[kk][a[m]], tab[kk][b[m] - (1 << kk)])
    return out


srng = np.maximum.reduceat(H, sst) - np.minimum.reduceat(L, sst)
ATRD = pd.Series(srng).rolling(14).mean().shift(1).values
sclose = C[sen - 1]; sma = pd.Series(sclose).rolling(50).mean().values
TREND = np.r_[0, np.sign(sclose - sma)[:-1]]; SOPEN = O[sst]


def bars(key):
    st = np.r_[0, np.nonzero(key[1:] != key[:-1])[0] + 1]; en = np.r_[st[1:], N]
    return dict(st=st, en=en, o=O[st], c=C[en - 1], h=np.maximum.reduceat(H, st), l=np.minimum.reduceat(L, st), v=np.add.reduceat(V, st))


HR = 3600 * 10**9
B15 = bars(NS // (15 * 60 * 10**9)); n15 = len(B15["st"]); M2B15 = np.repeat(np.arange(n15), B15["en"] - B15["st"])
BODY20 = pd.Series(np.abs(B15["c"] - B15["o"])).rolling(20).mean().shift(1).values
VOL20 = pd.Series(B15["v"]).rolling(20).mean().shift(1).values
HTF = {"D": bars(sid), "4H": bars((NS + 6 * HR) // (4 * HR)), "1H": bars(NS // HR)}
D30 = np.searchsorted(NS, NS + 30 * 86400 * 10**9)


def gaps(tf, placebo):
    b = HTF[tf]; h, l = b["h"], b["l"]; atr = pd.Series(h - l).rolling(14).mean().values
    i = np.arange(2, len(h)); bull = l[i] > h[i - 2]; bear = h[i] < l[i - 2]; i = i[bull | bear]; bull = l[i] > h[i - 2]
    lo = np.where(bull, h[i - 2], h[i]); hi = np.where(bull, l[i], l[i - 2]); act = b["en"][i]; size = (hi - lo) / atr[i]
    keep = (act < N - 5) & np.isfinite(size); lo, hi, act, size = lo[keep], hi[keep], act[keep], size[keep]
    if placebo:
        rng = np.random.default_rng(11 + TFS.index(tf)); s = rng.choice([-1, 1], len(lo)) * rng.uniform(1, 3, len(lo)) * (hi - lo)
        lo, hi = lo + s, hi + s
    return lo, hi, act, size


def events(tf, touch, placebo):
    lo, hi, act, size = gaps(tf, placebo); p0 = C[act - 1]; above = p0 > hi; below = p0 < lo; ok = above | below
    lo, hi, act, size, above = lo[ok], hi[ok], act[ok], size[ok], above[ok]
    lev = {"near": np.where(above, hi, lo), "mid": (lo + hi) / 2, "far": np.where(above, lo, hi)}[touch]
    end = D30[act]; j0 = np.empty(len(lo), np.int64)
    j0[above] = first_hit(MINL, lev[above], act[above], end[above], True)
    j0[~above] = first_hit(MAXH, lev[~above], act[~above], end[~above], False)
    ok = (j0 < end) & (j0 < N - 200)
    age = (NS[j0[ok]] - NS[act[ok]]) / 86400e9
    return dict(j0=j0[ok], lo=lo[ok], hi=hi[ok], d=np.where(above[ok], 1, -1), size=size[ok], age=age)


def U(d, o, h, l, c):          # long-space view: for shorts negate and swap high/low
    d = d[:, None]; return d * o, np.where(d > 0, h, -l), np.where(d > 0, l, -h), d * c


def confirmations(E, d):
    j0 = E["j0"]; b0 = M2B15[j0]; idx = np.minimum(b0[:, None] + np.arange(8), n15 - 1); pidx = np.maximum(b0 - 1, 0)
    o, h, l, c = U(d, *(B15[k][idx] for k in "ohlc")); v = B15["v"][idx]
    po, pc = d * B15["o"][pidx], d * B15["c"][pidx]
    ztop = np.where(d > 0, E["hi"], -E["lo"])[:, None]
    up = c > o; prev_c = np.c_[pc, c[:, :-1]]; prev_o = np.c_[po, o[:, :-1]]
    hmax = np.maximum.accumulate(h, 1); lmin = np.minimum.accumulate(l, 1)
    hprev = np.c_[np.full(len(h), np.inf), hmax[:, :-1]]; lprev = np.c_[np.full(len(l), -np.inf), lmin[:, :-1]]
    h2 = np.c_[np.full((len(h), 2), np.inf), h[:, :-2]]
    cond = {"reject": c > ztop,
            "engulf": up & (c >= np.maximum(prev_o, prev_c)) & (o <= np.minimum(prev_o, prev_c)),
            "bos": c > hprev,
            "displace": (c - o) >= 1.5 * BODY20[idx],
            "fvg15": l > h2,
            "sweep": (l < lprev) & up & (c > prev_c),
            "volume": up & (v >= 1.5 * VOL20[idx])}
    out = {"none": (j0 + 1, np.ones(len(j0), bool), (np.where(d > 0, H[j0], -L[j0]) + np.where(d > 0, L[j0], -H[j0])) / 2)}
    for name, m in cond.items():
        has = m.any(1); k = m.argmax(1); r = np.arange(len(k))
        out[name] = (B15["en"][idx[r, k]], has, (h[r, k] + l[r, k]) / 2)
    return out


W = 60


def entries(s, d, mid, ztop):
    s = np.minimum(s, N - W - 8); idx = s[:, None] + np.arange(-5, W + 1)
    o, h, l, c = U(d, O[idx], H[idx], L[idx], C[idx]); r = np.arange(len(s)); res = {}
    res["market"] = (s, o[:, 5], np.ones(len(s), bool))
    for name, lev in (("limit50", mid), ("retest", ztop)):
        m = l[:, 5:5 + W] <= lev[:, None]; has = m.any(1); j = m.argmax(1)
        res[name] = (s + j, np.minimum(lev, o[r, 5 + j]), has)
    hh5 = np.max(np.lib.stride_tricks.sliding_window_view(h, 5, axis=1)[:, :W], axis=2)   # max of the 5 bars before bar j
    m = c[:, 5:5 + W] > hh5; has = m.any(1); j = m.argmax(1)
    res["micro_bos"] = (s + j + 1, o[r, 6 + j], has)
    return res


def run_chunk(tf, touch, placebo):
    E = events(tf, touch, placebo); n_ = np.zeros((2, NCHUNK, NCELL, 3)); s_ = np.zeros_like(n_); q_ = np.zeros_like(n_); ntr = 0
    sb = np.digitize(E["size"], [0.25, 0.5, 1.0]); ab = np.digitize(E["age"], [1, 3, 10])
    for mi, mode in enumerate(MODE):
        d = E["d"] * (1 if mode == "react" else -1); ztop = np.where(d > 0, E["hi"], -E["lo"]); zbot = np.where(d > 0, E["lo"], -E["hi"])
        CF = confirmations(E, d)
        for ci, cname in enumerate(CONF):
            s, has, mid = CF[cname]
            for ei_, ename in enumerate(ENTRY):
                sel = np.nonzero(has)[0]
                if not len(sel): continue
                ei, eU, ok = entries(s[sel], d[sel], mid[sel], ztop[sel])[ename]
                sel, ei, eU = sel[ok], ei[ok], eU[ok]
                dd = d[sel]; si = sid[ei]; atr = ATRD[si]; je = sen[si] - 1
                good = np.isfinite(atr) & (ei <= je) & (YEAR[ei] >= 2012) & (ei > E["j0"][sel])
                sel, ei, eU, dd, si, atr, je = (x[good] for x in (sel, ei, eU, dd, si, atr, je))
                if not len(sel): continue
                j0 = E["j0"][sel]
                swing = np.where(dd > 0, rmq(MINL, np.minimum, j0, ei), -rmq(MAXH, np.maximum, j0, ei))
                e = dd * eU
                # context cell (shared by stops/targets)
                m_ = MIN[ei]; sess = np.where((m_ >= 1080) | (m_ < 120), 0, np.where(m_ < 570, 1, np.where(m_ < 720, 2, 3)))
                tr = (dd * TREND[si] > 0).astype(int); wd = (dd * (e - SOPEN[si]) > 0).astype(int)
                a0 = sst[si]; nonempty = ei > a0
                dr = np.zeros(len(ei)); dr[nonempty] = rmq(MAXH, np.maximum, a0[nonempty], ei[nonempty]) - rmq(MINL, np.minimum, a0[nonempty], ei[nonempty])
                ex = (dr / atr > 0.8).astype(int)
                cell = ((((sb[sel] * 4 + ab[sel]) * 4 + sess) * 2 + tr) * 2 + wd) * 2 + ex
                per = np.where(YEAR[ei] <= 2017, 0, np.where(YEAR[ei] <= 2021, 1, 2))
                for sti, sname in enumerate(STOP):
                    sU = {"zone": zbot[sel] - 2, "swing": swing - 2, "0.10atr": eU - 0.10 * atr, "0.25atr": eU - 0.25 * atr}[sname]
                    risk = eU - sU; v = (risk >= 3) & (risk <= 1.5 * atr)
                    if not v.any(): continue
                    vv = np.nonzero(v)[0]; rk = risk[vv]; dv = dd[vv]; ev = e[vv]; st = dv * sU[vv]; a = ei[vv]; b = je[vv] + 1
                    js = np.empty(len(vv), np.int64); lg = dv > 0
                    js[lg] = first_hit(MINL, st[lg], a[lg], b[lg], True); js[~lg] = first_hit(MAXH, st[~lg], a[~lg], b[~lg], False)
                    hitS = js < b; tout = dv * (C[b - 1] - ev) / rk; cst = COST / rk
                    for ti, tg in enumerate(TGT):
                        if tg == "close": R = np.where(hitS, -1.0, tout) - cst
                        else:
                            lvl = ev + dv * tg * rk; jt = np.empty(len(vv), np.int64)
                            jt[lg] = first_hit(MAXH, lvl[lg], a[lg], b[lg], False); jt[~lg] = first_hit(MINL, lvl[~lg], a[~lg], b[~lg], True)
                            hitT = jt < b; win = hitT & (~hitS | (jt < js)); loss = hitS & ~win
                            R = np.where(win, tg, np.where(loss, -1.0, tout)) - cst
                        lb = ((ci * 4 + ei_) * 4 + sti) * 6 + ti
                        key = (lb * NCELL + cell[vv]) * 3 + per[vv]
                        n_[mi].reshape(-1)[:] += np.bincount(key, minlength=NCHUNK * NCELL * 3)
                        s_[mi].reshape(-1)[:] += np.bincount(key, R, minlength=NCHUNK * NCELL * 3)
                        q_[mi].reshape(-1)[:] += np.bincount(key, R * R, minlength=NCHUNK * NCELL * 3)
                        ntr += len(vv)
    return n_, s_, q_, ntr, len(E["j0"])


if __name__ == "__main__":
    placebo = int(sys.argv[1]); tfs = sys.argv[2].split(",") if len(sys.argv) > 2 else TFS
    for tf in tfs:
        for touch in TOUCH:
            t0 = time.time(); n_, s_, q_, ntr, nev = run_chunk(tf, touch, placebo)
            np.savez_compressed(OUT + f"{'P' if placebo else 'R'}_{tf}_{touch}.npz", n=n_.astype(np.float32), s=s_, q=q_)
            print(f"{'placebo' if placebo else 'real'} {tf} {touch}: events {nev}, trades {ntr}, {time.time()-t0:.0f}s", flush=True)
