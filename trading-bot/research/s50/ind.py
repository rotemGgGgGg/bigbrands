"""Indicator helpers matching TradingView ta.* definitions (numpy / pandas / numba)."""
import numpy as np, pandas as pd
from numba import njit


def S(x): return pd.Series(x)
def ema(x, n): return S(x).ewm(span=n, adjust=False).mean().values
def sma(x, n): return S(x).rolling(n).mean().values
def rma(x, n): return S(x).ewm(alpha=1.0 / n, adjust=False).mean().values
def stdev(x, n): return S(x).rolling(n).std(ddof=0).values
def highest(x, n): return S(x).rolling(n).max().values
def lowest(x, n): return S(x).rolling(n).min().values
def ssum(x, n): return S(x).rolling(n).sum().values
def shift(x, k=1):
    y = np.empty_like(x, dtype=float); y[:k] = np.nan; y[k:] = x[:-k]; return y
def xover(a, b):
    a = np.asarray(a, float); b = np.broadcast_to(np.asarray(b, float), a.shape)
    return (a > b) & (shift(a) <= shift(b))
def xunder(a, b):
    a = np.asarray(a, float); b = np.broadcast_to(np.asarray(b, float), a.shape)
    return (a < b) & (shift(a) >= shift(b))


def tr(h, l, c):
    pc = shift(c); x = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))); x[0] = h[0] - l[0]; return x
def atr(h, l, c, n=14): return rma(tr(h, l, c), n)


def rsi(c, n):
    d = np.diff(c, prepend=c[0]); up = rma(np.maximum(d, 0), n); dn = rma(np.maximum(-d, 0), n)
    return np.where(dn == 0, 100.0, 100 - 100 / (1 + up / np.where(dn == 0, 1, dn)))


def stoch(c, h, l, n):
    hh, ll = highest(h, n), lowest(l, n); return 100 * (c - ll) / np.where(hh - ll == 0, np.nan, hh - ll)


def wma(x, n):
    w = np.arange(1, n + 1, dtype=float); out = np.full(len(x), np.nan)
    if len(x) >= n: out[n - 1:] = np.convolve(np.nan_to_num(x), w[::-1], "valid") / w.sum()
    return out
def hma(x, n): return wma(2 * wma(x, max(n // 2, 1)) - wma(x, n), max(int(np.sqrt(n)), 1))


@njit(cache=True)
def meandev(x, ma, n):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        s = 0.0
        for j in range(i - n + 1, i + 1): s += abs(x[j] - ma[i])
        out[i] = s / n
    return out
def cci(src, n):
    m = sma(src, n); return (src - m) / (0.015 * meandev(src, np.nan_to_num(m), n))


@njit(cache=True)
def linreg(y, n):
    out = np.full(len(y), np.nan); xs = np.arange(n) * 1.0; xm = xs.mean(); sxx = ((xs - xm) ** 2).sum()
    for i in range(n - 1, len(y)):
        seg = y[i - n + 1:i + 1]; ym = seg.mean(); b = ((xs - xm) * (seg - ym)).sum() / sxx; out[i] = ym + b * (n - 1 - xm)
    return out


@njit(cache=True)
def supertrend_dir(h, l, c, a, factor):
    n = len(c); d = np.ones(n); up = np.zeros(n); dn = np.zeros(n)
    for i in range(n):
        hl2 = (h[i] + l[i]) / 2; u = hl2 + factor * a[i]; lo = hl2 - factor * a[i]
        if i == 0: up[i] = u; dn[i] = lo; d[i] = 1; continue
        dn[i] = lo if (lo > dn[i - 1] or c[i - 1] < dn[i - 1]) else dn[i - 1]
        up[i] = u if (u < up[i - 1] or c[i - 1] > up[i - 1]) else up[i - 1]
        if d[i - 1] == 1:           # TV: direction 1 = downtrend, -1 = uptrend
            d[i] = -1 if c[i] > up[i] else 1
        else:
            d[i] = 1 if c[i] < dn[i] else -1
    return d


@njit(cache=True)
def sar(h, l, start, inc, mx):
    n = len(h); out = np.full(n, np.nan); up = True; af = start; ep = h[0]; s = l[0]
    for i in range(1, n):
        s = s + af * (ep - s)
        if up:
            s = min(s, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < s: up = False; s = ep; ep = l[i]; af = start
            elif h[i] > ep: ep = h[i]; af = min(af + inc, mx)
        else:
            s = max(s, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > s: up = True; s = ep; ep = h[i]; af = start
            elif l[i] < ep: ep = l[i]; af = min(af + inc, mx)
        out[i] = s
    return out


@njit(cache=True)
def kama(c, n):
    out = np.full(len(c), np.nan); fsc = 2.0 / 3; ssc = 2.0 / 31
    for i in range(n, len(c)):
        ch = abs(c[i] - c[i - n]); vol = 0.0
        for j in range(i - n + 1, i + 1): vol += abs(c[j] - c[j - 1])
        er = ch / vol if vol > 0 else 0.0; sc = (er * (fsc - ssc) + ssc) ** 2
        prev = out[i - 1] if not np.isnan(out[i - 1]) else c[i - 1]
        out[i] = prev + sc * (c[i] - prev)
    return out


@njit(cache=True)
def pivots(x, left, right, high):
    """value of a pivot confirmed at bar i (pivot at i-right), else nan."""
    n = len(x); out = np.full(n, np.nan)
    for i in range(left + right, n):
        p = i - right; v = x[p]; ok = True
        for j in range(p - left, p + right + 1):
            if j == p: continue
            if (x[j] >= v) if high else (x[j] <= v): ok = False; break
        if ok: out[i] = v
    return out


def ffill(x): return S(x).ffill().values


def prev_valuewhen(x):
    """valuewhen(not na(x), x, 1): the pivot before the latest one, known at bar i."""
    last = np.full(len(x), np.nan); prev = np.full(len(x), np.nan); a = np.nan; b = np.nan
    for i in range(len(x)):
        if not np.isnan(x[i]): b = a; a = x[i]
        last[i] = a; prev[i] = b
    return last, prev


@njit(cache=True)
def bars_since_extreme(x, n, high):
    out = np.full(len(x), np.nan)
    for i in range(n, len(x)):
        k = 0; v = x[i]
        for j in range(i, i - n - 1, -1):
            if (x[j] > v) if high else (x[j] < v): v = x[j]; k = i - j
        out[i] = k
    return out


@njit(cache=True)
def heikin(o, h, l, c):
    n = len(c); hc = (o + h + l + c) / 4; ho = np.empty(n); ho[0] = (o[0] + c[0]) / 2
    for i in range(1, n): ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    return ho, hc


def session_vwap(h, l, c, v, day):
    src = (h + l + c) / 3; g = pd.Series(day)
    pv = pd.Series(src * v).groupby(g).cumsum().values; vv = pd.Series(v).groupby(g).cumsum().values
    return pv / np.where(vv == 0, np.nan, vv)


def dmi(h, l, c, n, sm):
    up = h - shift(h); dn = shift(l) - l
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    t = rma(tr(h, l, c), n); pdi = 100 * rma(pdm, n) / t; mdi = 100 * rma(mdm, n) / t
    dx = 100 * np.abs(pdi - mdi) / np.where(pdi + mdi == 0, 1, pdi + mdi); return pdi, mdi, rma(dx, sm)


def mfi(h, l, c, v, n):
    src = (h + l + c) / 3; ch = np.diff(src, prepend=src[0]); mf = src * v
    pos = ssum(np.where(ch > 0, mf, 0.0), n); neg = ssum(np.where(ch < 0, mf, 0.0), n)
    return 100 - 100 / (1 + pos / np.where(neg == 0, np.nan, neg))


def ultosc(h, l, c, a, b, cc):
    pc = shift(c); bp = c - np.fmin(l, pc); t = np.fmax(h, pc) - np.fmin(l, pc)
    av = lambda n: ssum(bp, n) / ssum(t, n)
    return 100 * (4 * av(a) + 2 * av(b) + av(cc)) / 7
