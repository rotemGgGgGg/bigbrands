"""The 50 Pine templates (pine/*.pine) as numpy signal functions. Each returns (long, short, uses_trend, trend_len):
raw entry signals WITHOUT the template's trend-EMA filter, whether the template applies it, and its EMA length.
`m` scales the strategy's main lookback(s) (0.5 / 1 / 2 = faster / template / slower). Signals are evaluated on the bar
close and entered at the next bar's open by the engine (TradingView default).
Deliberate deviations from the templates, all documented in RESEARCH.md:
  #24/#25 gap = 09:30 open vs prior 16:00 close (the template's daily-session gap on CME is the 17:00→18:00 halt gap);
  #34 standard Aroon (the template formula exceeds 100); #50 higher timeframe = 15 m on 5 m charts, else 4× the chart."""
import numpy as np, pandas as pd
from ind import *


def L_(x, m): return max(2, int(round(x * m)))


def gen(B, sid, m):
    o, h, l, c, v = B["o"], B["h"], B["l"], B["c"], B["v"]; A = B["atr"]; mod = B["mod"]; day = B["day"]
    T = True; F = False
    if sid == 1:
        r = rsi(c, L_(2, m)); return xover(r, 10), xunder(r, 90), T, 200
    if sid == 2:
        n = L_(20, m); b = sma(c, n); d = stdev(c, n) * 2.2; return xover(c, b - d), xunder(c, b + d), T, 150
    if sid == 3:
        vw = B["vwap"]; return xover(c, vw), xunder(c, vw), T, 100
    if sid == 4:
        f, s = ema(c, L_(20, m)), ema(c, L_(50, m)); t = ema(c, L_(200, m))
        return (f > s) & (s > t) & (l <= f) & (c > f) & (c > o), (f < s) & (s < t) & (h >= f) & (c < f) & (c < o), F, 200
    if sid == 5:
        d = supertrend_dir(h, l, c, atr(h, l, c, L_(14, m)), 3.0); ch = d - shift(d); return ch < 0, ch > 0, T, 100
    if sid == 6:
        n = L_(20, m); b = ema(c, n); w = atr(h, l, c, 14) * 1.8; return xover(c, b - w), xunder(c, b + w), T, 200
    if sid == 7:
        r = rsi(c, L_(14, m)); f, s = ema(c, L_(12, m)), ema(c, L_(26, m)); mac = f - s; sig = ema(mac, 9)
        return xover(r, 50) & (mac > sig), xunder(r, 50) & (mac < sig), T, 100
    if sid in (8, 21):
        key = pd.Series(day) if sid == 8 else pd.Series(pd.DatetimeIndex(day).to_period("W-FRI").start_time)
        g = pd.DataFrame(dict(k=key, h=h, l=l)).groupby("k").agg(h=("h", "max"), l=("l", "min"))
        prev = g.shift(); ph = key.map(prev.h).values; pl = key.map(prev.l).values
        return (l < pl) & (c > pl), (h > ph) & (c < ph), F, 100
    if sid == 22:
        key = pd.Series(pd.DatetimeIndex(day).to_period("W-FRI").start_time)
        g = pd.DataFrame(dict(k=key, h=h, l=l)).groupby("k").agg(h=("h", "max"), l=("l", "min"))
        prev = g.shift(); ph = key.map(prev.h).values; pl = key.map(prev.l).values
        return xover(c, ph), xunder(c, pl), F, 100
    if sid in (9, 23):
        r0, r1, t0, t1 = (570, 585, 585, 720) if sid == 9 else (570, 630, 630, 720)
        if sid == 9 and m != 1: r1 = t0 = 570 + L_(15, m)
        if sid == 23 and m != 1: r1 = t0 = 570 + L_(60, m)
        return orb(h, l, c, mod, day.astype("datetime64[D]").astype(np.int64), r0, r1, t0, t1, sid == 9) + (F, 100)
    if sid == 10:
        n = L_(20, m); ph, pl = shift(highest(h, n)), shift(lowest(l, n)); return (l < pl) & (c > pl), (h > ph) & (c < ph), T, 100
    if sid == 11:
        k = sma(stoch(c, h, l, L_(14, m)), 3); d = sma(k, 3); return xover(k, d) & (k < 25), xunder(k, d) & (k > 75), T, 100
    if sid == 12:
        x = cci((h + l + c) / 3, L_(20, m)); return xover(x, 0), xunder(x, 0), T, 100
    if sid == 13:
        p, q, adx = dmi(h, l, c, L_(14, m), 14); return xover(p, q) & (adx > 20), xover(q, p) & (adx > 20), F, 100
    if sid == 14:
        n = L_(20, m); return xover(c, shift(highest(h, n))), xunder(c, shift(lowest(l, n))), F, 100
    if sid == 15:
        n = L_(20, m); bw = stdev(c, n) * 2.0; kw = atr(h, l, c, n) * 1.5; sq = bw < kw
        mom = linreg(np.nan_to_num(c - ((highest(h, n) + lowest(l, n)) / 2 + sma(c, n)) / 2), n)
        rel = shift(sq.astype(float)) == 1; rel &= ~sq; return rel & (mom > 0), rel & (mom < 0), F, 100
    if sid == 16:
        s = sar(h, l, 0.02 * m, 0.02 * m, 0.2); return xover(c, s), xunder(c, s), T, 100
    if sid == 17:
        ho, hc = heikin(o, h, l, c); up = hc > ho; return up & ~shift(up.astype(float)).astype(bool), ~up & (shift(up.astype(float)) == 1), T, 100
    if sid == 18:
        ins = (h < shift(h)) & (l > shift(l)); pi = shift(ins.astype(float)) == 1
        return pi & (c > shift(h)), pi & (c < shift(l)), T, L_(100, m)
    if sid == 19:
        bull = (c > o) & (shift(c) < shift(o)) & (c >= shift(o)) & (o <= shift(c))
        bear = (c < o) & (shift(c) > shift(o)) & (c <= shift(o)) & (o >= shift(c)); return bull, bear, T, L_(100, m)
    if sid == 20:
        k = L_(3, m); ph = ffill(pivots(h, k, k, True)); pl = ffill(pivots(l, k, k, False)); return xover(c, ph), xunder(c, pl), F, 100
    if sid in (24, 25):
        d = day.astype("datetime64[D]").astype(np.int64); dO, pc = rth_open_prevclose(o, c, mod, d)
        rth = (mod >= 570) & (mod < 960); gap = (dO - pc) / pc * 100; th = 0.25 * m
        if sid == 24: return rth & (gap < -th) & (c > dO), rth & (gap > th) & (c < dO), F, 100
        return rth & (gap > th) & (c > dO), rth & (gap < -th) & (c < dO), T, 100
    if sid == 26:
        n = L_(20, m); mid = ema(c, n); w = atr(h, l, c, n) * 1.5; return xover(c, mid + w), xunder(c, mid - w), F, 100
    if sid == 27:
        k = kama(c, L_(20, m)); return xover(c, k) & (k > shift(k)), xunder(c, k) & (k < shift(k)), F, 100
    if sid == 28:
        f, s = hma(c, L_(16, m)), hma(c, L_(48, m)); return xover(f, s), xunder(f, s), F, 100
    if sid == 29:
        a, b = L_(12, m), L_(26, m); ea, eb = ema(c, a), ema(c, b); f = 2 * ea - ema(ea, a); s = 2 * eb - ema(eb, b)
        return xover(f, s), xunder(f, s), F, 100
    if sid == 30:
        a, b, cc_ = ema(c, L_(9, m)), ema(c, L_(21, m)), ema(c, L_(50, m))
        return (a > b) & (b > cc_) & (shift(a) <= shift(b)), (a < b) & (b < cc_) & (shift(a) >= shift(b)), F, 100
    if sid == 31:
        x = mfi(h, l, c, v, L_(14, m)); return xover(x, 20), xunder(x, 80), T, 100
    if sid == 32:
        n = L_(20, m); mult = np.where(h != l, ((c - l) - (h - c)) / np.where(h != l, h - l, 1), 0.0)
        x = ssum(mult * v, n) / ssum(v, n); return xover(x, 0), xunder(x, 0), T, 100
    if sid == 33:
        ob = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v); ma = sma(ob, L_(20, m)); return xover(ob, ma), xunder(ob, ma), T, 100
    if sid == 34:
        n = L_(25, m); up = 100 * (n - bars_since_extreme(h, n, True)) / n; dn = 100 * (n - bars_since_extreme(l, n, False)) / n
        return xover(up, dn) & (up > 70), xover(dn, up) & (dn > 70), F, 100
    if sid == 35:
        n = L_(14, m); hh, ll = highest(h, n), lowest(l, n); w = -100 * (hh - c) / np.where(hh - ll == 0, np.nan, hh - ll)
        return xover(w, -80), xunder(w, -20), T, 100
    if sid == 36:
        u = ultosc(h, l, c, L_(7, m), L_(14, m), L_(28, m)); return xover(u, 50), xunder(u, 50), T, 100
    if sid == 37:
        r = rsi(c, L_(14, m)); k = sma(stoch(r, r, r, L_(14, m)), 3); d = sma(k, 3)
        return xover(k, d) & (k < 20), xunder(k, d) & (k > 80), T, 100
    if sid == 38:
        n = L_(10, m); x = c - shift(c, n); return xover(x, 0), xunder(x, 0), T, 100
    if sid == 39:
        n = L_(12, m); x = 100 * (c - shift(c, n)) / shift(c, n); return xover(x, 0), xunder(x, 0), T, 100
    if sid == 40:
        f, s = ema(c, L_(12, m)), ema(c, L_(26, m)); mac = f - s; hist = mac - ema(mac, L_(9, m)); return xover(hist, 0), xunder(hist, 0), T, 100
    if sid == 41:
        vw = B["vwap"]; sd = stdev(c - vw, L_(50, m)); return xover(c, vw - 2 * sd), xunder(c, vw + 2 * sd), F, 100
    if sid == 42:
        vw = B["vwap"]; return (c > vw) & (l <= vw) & (c > o), (c < vw) & (h >= vw) & (c < o), T, L_(100, m)
    if sid == 43:
        k = L_(5, m); r = rsi(c, 14)
        plp = pivots(l, k, k, False); php = pivots(h, k, k, True); plr = pivots(r, k, k, False); phr = pivots(r, k, k, True)
        _, pL = prev_valuewhen(plp); _, pLr = prev_valuewhen(plr); _, pH = prev_valuewhen(php); _, pHr = prev_valuewhen(phr)
        bull = ~np.isnan(plp) & ~np.isnan(pL) & (plp < pL) & (plr > pLr); bear = ~np.isnan(php) & ~np.isnan(pH) & (php > pH) & (phr < pHr)
        return bull, bear, T, 100
    if sid == 44:
        bull = (shift(c, 2) < shift(o, 2)) & (shift(c) < shift(c, 2)) & (c > shift(h)) & (c > o)
        bear = (shift(c, 2) > shift(o, 2)) & (shift(c) > shift(c, 2)) & (c < shift(l)) & (c < o); return bull, bear, T, L_(100, m)
    if sid == 45:
        e = ema(c, L_(100, m))
        lo = (c > e) & (shift(c) > shift(e)) & (shift(c, 2) > shift(c)) & (shift(l) <= shift(l, 2)) & (c > shift(h))
        sh = (c < e) & (shift(c) < shift(e)) & (shift(c, 2) < shift(c)) & (shift(h) >= shift(h, 2)) & (c < shift(l)); return lo, sh, F, 100
    if sid == 46:
        ex = (h - l) > sma(h - l, L_(20, m)) * 1.5; return ex & (c > shift(h)), ex & (c < shift(l)), T, 100
    if sid == 47:
        n = L_(20, m); rn = highest(h, n) - lowest(l, n); comp = rn < sma(rn, n) * 0.7; pc_ = shift(comp.astype(float)) == 1
        return pc_ & (c > shift(highest(h, n))), pc_ & (c < shift(lowest(l, n))), F, 100
    if sid == 48:
        hv = A > sma(A, L_(20, m)) * 1.2; return hv & (c > shift(h)), hv & (c < shift(l)), T, 100
    if sid == 49:
        e = ema(c, L_(100, m)); ins = (mod >= 585) & (mod < 720); return ins & xover(c, e) & (c > shift(c)), ins & xunder(c, e) & (c < shift(c)), F, 100
    if sid == 50:
        e = ema(c, L_(100, m)); he = B["htf_ema50"]; return (c > he) & xover(c, e), (c < he) & xunder(c, e), F, 100
    raise ValueError(sid)


from numba import njit


@njit(cache=True)
def orb(h, l, c, mod, day, r0, r1, t0, t1, retest):
    n = len(c); L = np.zeros(n, np.bool_); Sx = np.zeros(n, np.bool_); cur = -1; rh = np.nan; rl = np.nan; ready = False; bu = False; bd = False
    for i in range(n):
        if day[i] != cur: cur = day[i]; rh = np.nan; rl = np.nan; ready = False; bu = False; bd = False
        if mod[i] >= r0 and mod[i] < r1:
            rh = h[i] if np.isnan(rh) else max(rh, h[i]); rl = l[i] if np.isnan(rl) else min(rl, l[i])
        elif mod[i] >= r1 and not np.isnan(rh): ready = True
        intr = mod[i] >= t0 and mod[i] < t1
        if not (ready and intr): continue
        if retest:
            if c[i] > rh: bu = True
            if c[i] < rl: bd = True
            if bu and l[i] <= rh and c[i] > rh: L[i] = True; bu = False
            if bd and h[i] >= rl and c[i] < rl: Sx[i] = True; bd = False
        else:
            if c[i] > rh and i > 0 and c[i - 1] <= rh: L[i] = True
            if c[i] < rl and i > 0 and c[i - 1] >= rl: Sx[i] = True
    return L, Sx


@njit(cache=True)
def rth_open_prevclose(o, c, mod, day):
    n = len(c); dO = np.full(n, np.nan); pc = np.full(n, np.nan); cur = -1; op = np.nan; lastc = np.nan; prevc = np.nan
    for i in range(n):
        if day[i] != cur: cur = day[i]; prevc = lastc; op = np.nan
        if mod[i] == 570 or (np.isnan(op) and mod[i] > 570 and mod[i] < 960): op = o[i]
        if mod[i] < 960 and mod[i] >= 570: lastc = c[i]
        dO[i] = op; pc[i] = prevc
    return dO, pc


def prepare(Bdf, tf):
    B = {k: Bdf[k].values.astype(float) for k in "ohlcv"}
    B["mod"] = Bdf["mod"].values.astype(np.int64); B["day"] = Bdf["day"].values; B["roll"] = Bdf["roll"].values
    B["atr"] = atr(B["h"], B["l"], B["c"], 14)
    B["vwap"] = session_vwap(B["h"], B["l"], B["c"], B["v"], B["day"])
    htf = 15 if tf == 5 else 4 * tf; k = htf // tf
    d = B["day"].astype("datetime64[D]").astype(np.int64); grp = d * 10000 + ((B["mod"] - 1080) % 1440) // htf
    last = np.r_[grp[1:] != grp[:-1], True]; cl = np.where(last, B["c"], np.nan)
    he = pd.Series(cl).dropna().ewm(span=50, adjust=False).mean().reindex(range(len(cl))).values
    B["htf_ema50"] = shift(ffill(he))       # value of the last COMPLETED higher-timeframe bar (no look-ahead)
    return B


def signals(B, sid, m, trend_mode):
    """trend_mode 0 = as template, 1 = toggled (filter removed if the template has it, added if it doesn't)."""
    Lg, Sg, uses, tl = gen(B, sid, m)
    Lg = np.nan_to_num(np.asarray(Lg, float)).astype(bool); Sg = np.nan_to_num(np.asarray(Sg, float)).astype(bool)
    if uses != bool(trend_mode):
        e = ema(B["c"], tl); Lg &= B["c"] > e; Sg &= B["c"] < e
    return Lg, Sg
