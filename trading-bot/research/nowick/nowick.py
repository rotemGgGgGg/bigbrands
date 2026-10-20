"""'No-wick candle' strategy — 23,760 rule variants (+7,920 placebo variants) on 11 markets, 6 timeframes.
Idea (as told to the user): in a trend, a candle that is all body on the trend side (bullish candle with open = low, or bearish
with open = high) marks a level; when price comes back to it, enter with the trend at 1:1.
Mechanics (long; short mirrored):
  signal  : close > open and lower wick ≤ tol × range (tol 0 = open == low exactly).  placebo: lower wick 20–60 % of range.
  trend   : 0 none | 1 EMA20 rising | 2 close > EMA50 | 3 EMA20 > EMA50 | 4 close > EMA200 (higher-timeframe proxy), at the signal close.
  level   : the candle open (lv=0) or 25 % into the body (lv=0.25).
  entry   : first touch of the level within `expiry` bars; limit fill at min(open, level) (mode 0) or next bar open (mode 1).
  stop    : level − k × ATR14 (k 0.1 / 0.5 / 1.0); target = entry + rr × risk.  Stop-first on shared bars, no target on the fill bar.
  exits   : 1–15 m bars trade inside the market's main session only and are flat at session end; 1 h / 4 h bars use the 24 h
            stream and exit after 120 / 30 bars.  One trade at a time per variant.
Costs per round trip = max(frac × price, minimum) per market (COST below)."""
import os, sys, pickle, itertools, time
import numpy as np, pandas as pd
from numba import njit
from multiprocessing import Pool
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "longhist"))
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
BARS = SP + "nowick_bars/"
SESS = {"NQ": (570, 960), "NSXUSD": (570, 960), "SPXUSD": (570, 960), "GRXEUR": (180, 690), "XAUUSD": (500, 810),
        "XAGUSD": (500, 810), "WTIUSD": (540, 870), "BCOUSD": (540, 870), "USDJPY": None, "UDXUSD": None, "JPXJPY": None}
COST = {"NQ": (1.32e-4, 0.5), "NSXUSD": (1.0e-4, 1.0), "SPXUSD": (1.1e-4, 0.3), "GRXEUR": (1.0e-4, 1.0), "JPXJPY": (2.0e-4, 7.0),
        "XAUUSD": (2.0e-4, 0.2), "XAGUSD": (6.0e-4, 0.02), "WTIUSD": (6.0e-4, 0.03), "BCOUSD": (6.0e-4, 0.03),
        "USDJPY": (1.0e-4, 0.01), "UDXUSD": (2.0e-4, 0.01)}
TFS = (1, 3, 5, 15, 60, 240)
HOLD = {60: 120, 240: 30}
FILT = ("none", "ema20_up", "c>ema50", "ema20>ema50", "c>ema200")
TOLS = (0.0, 0.05, 0.10, "placebo")
LEVELS = (0.0, 0.25)
GRID = dict(entry=((0.0, 0), (0.25, 0), (0.0, 1)), stopk=(0.1, 0.5, 1.0), rr=(1.0, 1.5, 2.0, 3.0), expiry=(10, 50))
YEARS = list(range(2010, 2027))


def minute_frame(mkt):
    if mkt == "NQ":
        f = pd.read_pickle(SP + "nq16.pkl")
    else:
        from load import frame
        f = frame(mkt)
    f = f[["open", "high", "low", "close"]].astype(float)
    return f[f.index.notna()]


def bars(mkt, tf):
    p = f"{BARS}{mkt}_{tf}.pkl"
    if os.path.exists(p): return pd.read_pickle(p)
    f = minute_frame(mkt); m = (f.index.hour * 60 + f.index.minute).values
    s = SESS[mkt]
    if tf in HOLD or s is None:                                   # 24 h trading day 18:00 → 16:59
        day = (f.index + pd.Timedelta(hours=6)).normalize().tz_localize(None); bucket = ((m - 1080) % 1440) // tf
        keep = ((m - 1080) % 1440) < 1380
    else:
        day = f.index.normalize().tz_localize(None); bucket = (m - s[0]) // tf; keep = (m >= s[0]) & (m < s[1])
    f = f[keep]; day = day[keep]; bucket = bucket[keep]
    wk = day.weekday < 5; f = f[wk]; day = day[wk]; bucket = bucket[wk]
    code = day.values.astype("datetime64[D]").astype(np.int64) * 10000 + bucket
    st = np.r_[0, np.flatnonzero(np.diff(code)) + 1]
    o = f.open.values[st]; c = f.close.values[np.r_[st[1:] - 1, len(f) - 1]]
    h = np.maximum.reduceat(f.high.values, st); l = np.minimum.reduceat(f.low.values, st)
    d = day.values[st]
    B = pd.DataFrame(dict(o=o, h=h, l=l, c=c, day=d))
    os.makedirs(BARS, exist_ok=True); B.to_pickle(p); return B


@njit(cache=True)
def sim(o, h, l, c, atr, sess, last, sigL, sigS, lv, mode, expiry, k, rr, hold, cf, cmin, thru=0.0, side=0):
    n = len(o); outi = np.empty(n, np.int64); outr = np.empty(n); nt = 0; i = 0
    while i < n - 2:
        s = 1 if sigL[i] else (-1 if sigS[i] else 0)
        if side != 0 and s != side: s = 0
        if s == 0 or not atr[i] > 0:
            i += 1; continue
        L = o[i] + lv * (c[i] - o[i]); S = L - s * k * atr[i]
        j = -1
        for d in range(1, expiry + 1):
            if i + d >= n: break
            if hold == 0 and sess[i + d] != sess[i]: break
            if (l[i + d] <= L - thru) if s == 1 else (h[i + d] >= L + thru):
                j = i + d; break
        if j < 0:
            i += 1; continue
        if mode == 0:
            e = min(o[j], L) if s == 1 else max(o[j], L); m0 = j
        else:
            if (l[j] <= S) if s == 1 else (h[j] >= S):
                i = j + 1; continue
            if j + 1 >= n or (hold == 0 and sess[j + 1] != sess[i]):
                i = j + 1; continue
            e = o[j + 1]; m0 = j + 1
        risk = s * (e - S)
        if risk <= 0:
            i = j + 1; continue
        T = e + s * rr * risk; px = np.nan; m = m0
        while True:
            if (l[m] <= S) if s == 1 else (h[m] >= S):
                px = min(o[m], S) if s == 1 else max(o[m], S)
                if m == j and mode == 0: px = S
                break
            if not (m == j and mode == 0):
                if (h[m] >= T + thru) if s == 1 else (l[m] <= T - thru):
                    px = max(o[m], T) if s == 1 else min(o[m], T); break
            if (hold == 0 and last[m]) or (hold > 0 and m - m0 >= hold) or m == n - 1:
                px = c[m]; break
            m += 1
        cost = max(cf * e, cmin)
        outi[nt] = m0; outr[nt] = (s * (px - e) - cost) / risk; nt += 1
        i = m + 1
    return outi[:nt], outr[:nt]


def mkbars(m): return [(m, tf, len(bars(m, tf))) for tf in TFS]


def ema(x, n): return pd.Series(x).ewm(span=n, adjust=False).mean().values


def job(args):
    mkt, tf = args
    B = bars(mkt, tf); o, h, l, c = (B[x].values for x in "ohlc"); day = pd.DatetimeIndex(B.day)
    yr = day.year.values; sess = day.values.astype("datetime64[D]").astype(np.int64)
    last = np.r_[sess[1:] != sess[:-1], True]
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc))); atr = pd.Series(tr).rolling(14).mean().values
    e20, e50, e200 = ema(c, 20), ema(c, 50), ema(c, 200); e20p = np.r_[e20[0], e20[:-1]]
    up = [np.ones(len(c), bool), e20 > e20p, c > e50, e20 > e50, c > e200]
    dn = [np.ones(len(c), bool), e20 < e20p, c < e50, e20 < e50, c < e200]
    rng = h - l; lw = np.minimum(o, c) - l; uw = h - np.maximum(o, c); bull = c > o; bear = c < o; eps = 1e-9 * c
    cf, cmin = COST[mkt]; hold = HOLD.get(tf, 0); rows = []
    for tol in TOLS:
        if tol == "placebo":
            sl = bull & (lw >= 0.2 * rng) & (lw <= 0.6 * rng); ss = bear & (uw >= 0.2 * rng) & (uw <= 0.6 * rng)
        else:
            sl = bull & (lw <= tol * rng + eps); ss = bear & (uw <= tol * rng + eps)
        for fi, fn in enumerate(FILT):
            SL, SS = sl & up[fi], ss & dn[fi]
            for (lv, mode), k, rr, ex in itertools.product(*GRID.values()):
                ti, R = sim(o, h, l, c, atr, sess, last, SL, SS, lv, mode, ex, k, rr, hold, cf, cmin)
                y = yr[ti]; row = dict(mkt=mkt, tf=tf, tol=str(tol), filt=fn, level=lv, mode=mode, stopk=k, rr=rr, expiry=ex)
                for nm, msk in (("tr", y <= 2019), ("va", (y >= 2020) & (y <= 2023)), ("te", y >= 2024)):
                    r = R[msk]; nyr = len(np.unique(y[msk])) or 1
                    row[nm + "_n"] = len(r); row[nm + "_yr"] = len(r) / nyr
                    row[nm + "_win"] = 100 * (r > 0).mean() if len(r) else np.nan
                    row[nm + "_R"] = r.mean() if len(r) else np.nan; row[nm + "_tot"] = r.sum()
                    row[nm + "_t"] = r.mean() / r.std() * np.sqrt(len(r)) if len(r) > 2 and r.std() > 0 else np.nan
                    eq = np.cumsum(r); row[nm + "_dd"] = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max() if len(r) else 0
                for Y in YEARS: row[f"y{Y}"] = R[y == Y].sum() if (y == Y).any() else np.nan
                rows.append(row)
    return rows


if __name__ == "__main__":
    t0 = time.time(); jobs = [(m, tf) for tf in TFS for m in SESS]
    if len(sys.argv) > 1 and sys.argv[1] == "bars":
        with Pool(4) as P: print(P.map(mkbars, list(SESS)))
        sys.exit()
    out = []
    with Pool(4) as P:
        for rows in P.imap_unordered(job, jobs):
            out += rows; print(rows[0]["mkt"], rows[0]["tf"], len(out), f"{time.time() - t0:.0f}s", flush=True)
            pd.DataFrame(out).to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "grid.csv.gz"), index=False)
    print("done", len(out))
