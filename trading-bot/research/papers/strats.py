"""127 classic published strategies, coded with the rules / default parameters printed in the source (no tuning).
Every function takes the data dict D and a lookback scale s (1.0 = published; 0.75 / 1.25 only for the robustness level)
and returns ('d', hold, mode) for the daily engine or ('i', spec) for the intraday engine (see engine.py).
Daily signal rules use the day's RTH close and are executed at the NEXT open ('oo'), never at the close that created them.
Volume-based classics (OBV, MFI, VWAP, Chaikin, Force index, pocket pivot) are not testable: the free data has no volume."""
import numpy as np, pandas as pd

REG = []


def reg(name, src, kind="d", params=True):
    def w(f): REG.append(dict(sid=len(REG) + 1, name=name, src=src, kind=kind, params=params, fn=f)); return f
    return w


# ---------------------------------------------------------------- helpers
S = pd.Series
def L(n, s): return max(2, int(round(n * s)))
def sma(x, n): return S(x).rolling(n).mean().values
def ema(x, n): return S(x).ewm(span=n, adjust=False).mean().values
def rma(x, n): return S(x).ewm(alpha=1.0 / n, adjust=False).mean().values
def hh(x, n): return S(x).rolling(n).max().values
def ll(x, n): return S(x).rolling(n).min().values
def lag(x, k=1):
    y = np.full(len(x), np.nan); y[k:] = x[:-k]; return y
def rsi(c, n):
    d = np.diff(c, prepend=c[0]); u = rma(np.maximum(d, 0), n); v = rma(np.maximum(-d, 0), n)
    return 100 - 100 / (1 + u / np.where(v == 0, 1e-12, v))
def trange(h, l, c):
    pc = lag(c); t = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc))); t[0] = h[0] - l[0]; return t
def atr(h, l, c, n): return rma(trange(h, l, c), n)
def dmi(h, l, c, n):
    up = h - lag(h); dn = lag(l) - l; up[0] = dn[0] = 0
    p = np.where((up > dn) & (up > 0), up, 0.0); m = np.where((dn > up) & (dn > 0), dn, 0.0); t = rma(trange(h, l, c), n)
    pdi = 100 * rma(p, n) / t; mdi = 100 * rma(m, n) / t; dx = 100 * np.abs(pdi - mdi) / np.maximum(pdi + mdi, 1e-12)
    return pdi, mdi, rma(dx, n)
def xo(a, b): return (a > b) & (lag(a) <= lag(b))
def xu(a, b): return (a < b) & (lag(a) >= lag(b))
def nz(x): return np.nan_to_num(np.asarray(x, float)).astype(bool)


def state(entL, exL, entS=None, exS=None):
    """position after the close of each day; entries ignored while already in that direction; exit and flip handled per day."""
    n = len(entL); p = np.zeros(n); cur = 0
    entS = np.zeros(n, bool) if entS is None else entS; exS = np.zeros(n, bool) if exS is None else exS
    for t in range(n):
        if cur == 1 and exL[t]: cur = 0
        elif cur == -1 and exS[t]: cur = 0
        if entL[t] and cur != 1: cur = 1
        elif entS[t] and cur != -1: cur = -1
        p[t] = cur
    return p


def hold_n(sigL, sigS, n):
    """BLL fixed-length: a signal opens a position held n days; signals during a holding period are ignored."""
    p = np.zeros(len(sigL)); t = 0
    while t < len(sigL):
        if sigL[t] or sigS[t]:
            p[t:t + n] = 1 if sigL[t] else -1; t += n
        else: t += 1
    return p


def sig(p):
    """position decided at close t -> held open t+1..open t+2 ('oo' mode index t+1)."""
    return ("d", lag(np.nan_to_num(p)), "oo")


def month_end(D):
    d = D["days"]; m = d.month.values; return np.r_[m[1:] != m[:-1], True]


def monthly(D, f):
    """decision at each month-end close, held for the whole next month."""
    me = month_end(D); p = np.full(len(me), np.nan); p[me] = f[me]; return S(p).ffill().fillna(0).values


def dly(D): return D["do"], D["dh"], D["dl"], D["dc"]


# ================================================================= DAILY: Brock, Lakonishok & LeBaron (1992) J. Finance 47(5)
for (a, b, band) in [(1, 50, 0), (1, 50, .01), (1, 150, 0), (1, 150, .01), (5, 150, 0), (5, 150, .01), (1, 200, 0), (1, 200, .01), (2, 200, 0), (2, 200, .01)]:
    def f(D, s, a=a, b=b, band=band):
        c = D["dc"]; fa = sma(c, a) if a > 1 else c; fb = sma(c, L(b, s))
        return sig(np.where(fa > fb * (1 + band), 1, np.where(fa < fb * (1 - band), -1, 0)))
    reg(f"BLL VMA ({a},{b},{band})", "Brock, Lakonishok & LeBaron 1992, variable-length MA")(f)
for (a, b) in [(1, 50), (1, 150), (5, 150), (1, 200), (2, 200)]:
    def f(D, s, a=a, b=b):
        c = D["dc"]; fa = sma(c, a) if a > 1 else c; fb = sma(c, L(b, s))
        return sig(hold_n(nz(xo(fa, fb)), nz(xu(fa, fb)), 10))
    reg(f"BLL FMA ({a},{b}) 10-day hold", "Brock, Lakonishok & LeBaron 1992, fixed-length MA")(f)
for (b, band) in [(50, 0), (50, .01), (150, 0), (150, .01), (200, 0), (200, .01)]:
    def f(D, s, b=b, band=band):
        c = D["dc"]; mx = lag(hh(c, L(b, s))); mn = lag(ll(c, L(b, s)))
        return sig(hold_n(nz(c > mx * (1 + band)), nz(c < mn * (1 - band)), 10))
    reg(f"BLL TRB ({b},{band}) 10-day hold", "Brock, Lakonishok & LeBaron 1992, trading-range breakout")(f)


# ================================================================= DAILY trend
@reg("Faber 10-month SMA (long/flat)", "Faber 2007, A Quantitative Approach to Tactical Asset Allocation")
def f(D, s):
    c = D["dc"]; me = month_end(D); mc = c[me]; sm = sma(mc, L(10, s)); x = np.full(len(c), np.nan); x[me] = (mc > sm).astype(float)
    return ("d", lag(S(x).ffill().fillna(0).values), "oo")

@reg("Price > 200-day SMA (long/flat)", "Siegel 1998 Stocks for the Long Run; Gartley 1935")
def f(D, s): c = D["dc"]; return sig((c > sma(c, L(200, s))).astype(float))

@reg("Golden cross 50/200 (long/flat)", "classic; Brock et al. 1992 family")
def f(D, s): c = D["dc"]; return sig((sma(c, L(50, s)) > sma(c, L(200, s))).astype(float))

@reg("Golden/death cross 50/200 (long/short)", "classic")
def f(D, s): c = D["dc"]; return sig(np.sign(sma(c, L(50, s)) - sma(c, L(200, s))))

@reg("Turtle System 1 (20/10 Donchian)", "Faith 2007, Way of the Turtle (Dennis & Eckhardt 1983)")
def f(D, s):
    o, h, l, c = dly(D); a, b = L(20, s), L(10, s)
    return sig(state(nz(c > lag(hh(h, a))), nz(c < lag(ll(l, b))), nz(c < lag(ll(l, a))), nz(c > lag(hh(h, b)))))

@reg("Turtle System 2 (55/20 Donchian)", "Faith 2007, Way of the Turtle")
def f(D, s):
    o, h, l, c = dly(D); a, b = L(55, s), L(20, s)
    return sig(state(nz(c > lag(hh(h, a))), nz(c < lag(ll(l, b))), nz(c < lag(ll(l, a))), nz(c > lag(hh(h, b)))))

@reg("Donchian 4-week rule (stop & reverse)", "Donchian 1960, Commodity Year Book; Kaufman, Trading Systems & Methods")
def f(D, s):
    o, h, l, c = dly(D); a = L(20, s); up = nz(c > lag(hh(h, a))); dn = nz(c < lag(ll(l, a)))
    return sig(state(up, dn, dn, up))

for k in (1, 3, 6, 12):
    def f(D, s, k=k):
        c = D["dc"]; return ("d", lag(monthly(D, np.sign(c / lag(c, L(21 * k, s)) - 1))), "oo")
    reg(f"Time-series momentum {k}m (long/short, monthly)", "Moskowitz, Ooi & Pedersen 2012, JFE 104")(f)

@reg("Absolute momentum 12m (long/flat)", "Antonacci 2014, Dual Momentum Investing")
def f(D, s): c = D["dc"]; return ("d", lag(monthly(D, (c / lag(c, L(252, s)) > 1).astype(float))), "oo")

@reg("52-week-high proximity >= 95% (long/flat)", "George & Hwang 2004, J. Finance 59")
def f(D, s): c = D["dc"]; return sig((c >= 0.95 * hh(c, L(252, s))).astype(float))

@reg("Volatility-managed buy & hold (16% target, cap 2x)", "Moreira & Muir 2017, J. Finance 72")
def f(D, s):
    c = D["dc"]; r = np.diff(np.log(c), prepend=np.log(c[0])); v = S(r).rolling(L(21, s)).std().values * np.sqrt(252)
    return sig(np.clip(0.16 / v, 0, 2))

@reg("MACD 12/26/9 signal cross (long/short)", "Appel 1979")
def f(D, s):
    c = D["dc"]; m = ema(c, L(12, s)) - ema(c, L(26, s)); return sig(np.sign(m - ema(m, L(9, s))))

@reg("MACD zero line (long/short)", "Appel 1979")
def f(D, s): c = D["dc"]; return sig(np.sign(ema(c, L(12, s)) - ema(c, L(26, s))))

@reg("RSI(14) 50 cross trend (long/short)", "Wilder 1978, New Concepts in Technical Trading Systems")
def f(D, s): return sig(np.sign(rsi(D["dc"], L(14, s)) - 50))

@reg("Parabolic SAR 0.02/0.2 (stop & reverse)", "Wilder 1978")
def f(D, s):
    o, h, l, c = dly(D); n = len(c); p = np.zeros(n); up = True; af = .02; ep = h[0]; sr = l[0]
    for i in range(1, n):
        sr = sr + af * (ep - sr)
        if up:
            sr = min(sr, l[i - 1], l[max(i - 2, 0)])
            if l[i] < sr: up = False; sr = ep; ep = l[i]; af = .02
            elif h[i] > ep: ep = h[i]; af = min(af + .02, .2)
        else:
            sr = max(sr, h[i - 1], h[max(i - 2, 0)])
            if h[i] > sr: up = True; sr = ep; ep = h[i]; af = .02
            elif l[i] < ep: ep = l[i]; af = min(af + .02, .2)
        p[i] = 1 if up else -1
    return sig(p)

@reg("DMI +DI/-DI with ADX>25", "Wilder 1978")
def f(D, s):
    o, h, l, c = dly(D); pdi, mdi, ax = dmi(h, l, c, L(14, s)); return sig(np.where(ax > 25, np.sign(pdi - mdi), 0))

@reg("Bollinger 20/2 breakout (exit at mid)", "Bollinger 2001, Bollinger on Bollinger Bands")
def f(D, s):
    c = D["dc"]; n = L(20, s); m = sma(c, n); sd = S(c).rolling(n).std(ddof=0).values
    return sig(state(nz(c > m + 2 * sd), nz(c < m), nz(c < m - 2 * sd), nz(c > m)))

@reg("Keltner 10-day channel breakout (stop & reverse)", "Keltner 1960, How to Make Money in Commodities")
def f(D, s):
    o, h, l, c = dly(D); n = L(10, s); mid = sma((h + l + c) / 3, n); b = sma(h - l, n)
    up = nz(c > mid + b); dn = nz(c < mid - b); return sig(state(up, dn, dn, up))

@reg("CCI(20) +/-100 (Lambert)", "Lambert 1980, Commodities magazine")
def f(D, s):
    o, h, l, c = dly(D); n = L(20, s); tp = (h + l + c) / 3; m = sma(tp, n)
    md = S(tp).rolling(n).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True).values; cci = (tp - m) / (0.015 * md)
    return sig(np.where(cci > 100, 1, np.where(cci < -100, -1, 0)))

@reg("ROC(12) zero line (long/short)", "Pring, Technical Analysis Explained")
def f(D, s): c = D["dc"]; return sig(np.sign(c - lag(c, L(12, s))))

@reg("Aroon(25) up/down cross", "Chande 1995")
def f(D, s):
    o, h, l, c = dly(D); n = L(25, s)
    au = S(h).rolling(n + 1).apply(lambda x: x.argmax(), raw=True).values; ad = S(l).rolling(n + 1).apply(lambda x: x.argmin(), raw=True).values
    return sig(np.sign(au - ad))

@reg("KAMA(10) price cross", "Kaufman 1995, Smarter Trading")
def f(D, s):
    c = D["dc"]; n = L(10, s); k = np.full(len(c), np.nan); fs, ss = 2 / 3, 2 / 31
    for i in range(n, len(c)):
        ch = abs(c[i] - c[i - n]); vol = np.abs(np.diff(c[i - n:i + 1])).sum(); er = ch / vol if vol > 0 else 0
        sc = (er * (fs - ss) + ss) ** 2; pv = k[i - 1] if not np.isnan(k[i - 1]) else c[i - 1]; k[i] = pv + sc * (c[i] - pv)
    return sig(np.sign(c - k))

@reg("Triple MA 4-9-18", "Pring / R.C. Allen 1972 'How to Build a Fortune in Commodities'")
def f(D, s):
    c = D["dc"]; a, b, d = sma(c, L(4, s)), sma(c, L(9, s)), sma(c, L(18, s))
    return sig(np.where((a > b) & (b > d), 1, np.where((a < b) & (b < d), -1, 0)))

@reg("Ichimoku cloud + tenkan/kijun", "Hosoda 1969")
def f(D, s):
    o, h, l, c = dly(D); t = (hh(h, L(9, s)) + ll(l, L(9, s))) / 2; k = (hh(h, L(26, s)) + ll(l, L(26, s))) / 2
    A = lag((t + k) / 2, L(26, s)); B = lag((hh(h, L(52, s)) + ll(l, L(52, s))) / 2, L(26, s))
    return sig(np.where((c > np.fmax(A, B)) & (t > k), 1, np.where((c < np.fmin(A, B)) & (t < k), -1, 0)))

@reg("Heikin-Ashi colour", "Valcu 2004, TASC")
def f(D, s):
    o, h, l, c = dly(D); hc = (o + h + l + c) / 4; ho = np.empty(len(c)); ho[0] = (o[0] + c[0]) / 2
    for i in range(1, len(c)): ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    return sig(np.sign(hc - ho))

@reg("Supertrend (10, 3)", "Seban 2009")
def f(D, s):
    o, h, l, c = dly(D); a = atr(h, l, c, L(10, s)); n = len(c); d = np.ones(n); up = np.zeros(n); dn = np.zeros(n)
    for i in range(n):
        m = (h[i] + l[i]) / 2; u, lo = m + 3 * a[i], m - 3 * a[i]
        if i == 0: up[i], dn[i] = u, lo; continue
        dn[i] = lo if (lo > dn[i - 1] or c[i - 1] < dn[i - 1]) else dn[i - 1]
        up[i] = u if (u < up[i - 1] or c[i - 1] > up[i - 1]) else up[i - 1]
        d[i] = (1 if c[i] > up[i] else -1) if d[i - 1] == -1 else (-1 if c[i] < dn[i] else 1)
    return sig(d)

@reg("Elder Impulse (EMA13 & MACD-hist slopes)", "Elder 2002, Come Into My Trading Room")
def f(D, s):
    c = D["dc"]; e = ema(c, L(13, s)); m = ema(c, L(12, s)) - ema(c, L(26, s)); hs = m - ema(m, L(9, s))
    a, b = np.sign(e - lag(e)), np.sign(hs - lag(hs)); return sig(np.where((a > 0) & (b > 0), 1, np.where((a < 0) & (b < 0), -1, 0)))

@reg("Raschke 3-10 oscillator signal cross", "Raschke & Connors 1995, Street Smarts")
def f(D, s):
    c = D["dc"]; m = sma(c, L(3, s)) - sma(c, L(10, s)); return sig(np.sign(m - sma(m, L(16, s))))

@reg("1-day momentum (sign of today)", "Lo & MacKinlay 1988 autocorrelation")
def f(D, s): c = D["dc"]; return sig(np.sign(c - lag(c)))


# ================================================================= DAILY mean reversion
@reg("1-day reversal", "Lehmann 1990 / Jegadeesh 1990 (index version)")
def f(D, s): c = D["dc"]; return sig(-np.sign(c - lag(c)))

@reg("Weekly reversal (Friday, hold a week)", "Lehmann 1990, QJE")
def f(D, s):
    c = D["dc"]; fr = D["days"].weekday.values == 4; x = np.full(len(c), np.nan); x[fr] = -np.sign(c - lag(c, L(5, s)))[fr]
    return ("d", lag(S(x).ffill().fillna(0).values), "oo")

@reg("RSI(14) 30/70 reversal", "Wilder 1978")
def f(D, s):
    r = rsi(D["dc"], L(14, s)); return sig(state(nz(xo(r, np.full_like(r, 30))), nz(r > 70), nz(xu(r, np.full_like(r, 70))), nz(r < 30)))

@reg("Bollinger 20/2 reversion (exit at mid)", "Bollinger 2001")
def f(D, s):
    c = D["dc"]; n = L(20, s); m = sma(c, n); sd = S(c).rolling(n).std(ddof=0).values
    return sig(state(nz(c < m - 2 * sd), nz(c > m), nz(c > m + 2 * sd), nz(c < m)))

@reg("Stochastic 14/3 cross in 20/80 zones", "Lane 1984")
def f(D, s):
    o, h, l, c = dly(D); n = L(14, s); k = 100 * (c - ll(l, n)) / np.maximum(hh(h, n) - ll(l, n), 1e-9); d = sma(k, 3)
    return sig(state(nz(xo(k, d) & (d < 20)), nz(xu(k, d) & (d > 80)), nz(xu(k, d) & (d > 80)), nz(xo(k, d) & (d < 20))))

@reg("Williams %R(14) oversold long (exit -20)", "Williams 1973, How I Made $1,000,000 Trading Commodities")
def f(D, s):
    o, h, l, c = dly(D); n = L(14, s); w = -100 * (hh(h, n) - c) / np.maximum(hh(h, n) - ll(l, n), 1e-9)
    return sig(state(nz(w < -80), nz(w > -20)))

@reg("Williams %R(14) overbought short (exit -80)", "Williams 1973")
def f(D, s):
    o, h, l, c = dly(D); n = L(14, s); w = -100 * (hh(h, n) - c) / np.maximum(hh(h, n) - ll(l, n), 1e-9)
    z = np.zeros(len(c), bool); return sig(state(z, z, nz(w > -20), nz(w < -80)))

def _above(D, s): c = D["dc"]; return c > sma(c, L(200, s)), c < sma(c, L(200, s))

@reg("Connors RSI(2) long (<10, >SMA200, exit >SMA5)", "Connors & Alvarez 2008, Short Term Trading Strategies That Work")
def f(D, s):
    c = D["dc"]; up, _ = _above(D, s); r = rsi(c, 2); return sig(state(nz(up & (r < 10)), nz(c > sma(c, L(5, s)))))

@reg("Connors RSI(2) short (>90, <SMA200, exit <SMA5)", "Connors & Alvarez 2008")
def f(D, s):
    c = D["dc"]; _, dn = _above(D, s); r = rsi(c, 2); z = np.zeros(len(c), bool)
    return sig(state(z, z, nz(dn & (r > 90)), nz(c < sma(c, L(5, s)))))

@reg("Connors Double 7s long", "Connors & Alvarez 2009, High Probability ETF Trading")
def f(D, s):
    c = D["dc"]; up, _ = _above(D, s); n = L(7, s); return sig(state(nz(up & (c <= ll(c, n))), nz(c >= hh(c, n))))

@reg("Connors Double 7s short", "Connors & Alvarez 2009")
def f(D, s):
    c = D["dc"]; _, dn = _above(D, s); n = L(7, s); z = np.zeros(len(c), bool)
    return sig(state(z, z, nz(dn & (c >= hh(c, n))), nz(c <= ll(c, n))))

@reg("Connors 3-day high/low (3 lower highs & lows)", "Connors & Alvarez 2009")
def f(D, s):
    o, h, l, c = dly(D); up, _ = _above(D, s); s5 = sma(c, L(5, s))
    lh = (h < lag(h)) & (lag(h) < lag(h, 2)) & (lag(h, 2) < lag(h, 3)); lo = (l < lag(l)) & (lag(l) < lag(l, 2)) & (lag(l, 2) < lag(l, 3))
    return sig(state(nz(up & (c < s5) & lh & lo), nz(c > s5)))

@reg("Connors cumulative RSI(2) 2-day < 35", "Connors & Alvarez 2009")
def f(D, s):
    c = D["dc"]; up, _ = _above(D, s); r = rsi(c, 2); return sig(state(nz(up & (r + lag(r) < 35)), nz(r > 65)))

@reg("Connors %b (BB 5,1) < 0.2 three days", "Connors & Alvarez 2009")
def f(D, s):
    c = D["dc"]; up, _ = _above(D, s); n = L(5, s); m = sma(c, n); sd = S(c).rolling(n).std(ddof=0).values
    b = (c - (m - sd)) / np.maximum(2 * sd, 1e-9); e = (b < .2) & (lag(b) < .2) & (lag(b, 2) < .2)
    return sig(state(nz(up & e), nz(b > .8)))

@reg("Connors R3 (RSI2 falling 3 days, <10)", "Connors & Alvarez 2009")
def f(D, s):
    c = D["dc"]; up, _ = _above(D, s); r = rsi(c, 2)
    e = up & (r < lag(r)) & (lag(r) < lag(r, 2)) & (lag(r, 2) < 60) & (r < 10); return sig(state(nz(e), nz(r > 70)))

@reg("Connors multiple days down (4 of 5)", "Connors & Alvarez 2009")
def f(D, s):
    c = D["dc"]; up, _ = _above(D, s); s5 = sma(c, L(5, s)); dn = S((c < lag(c)).astype(float)).rolling(5).sum().values
    return sig(state(nz(up & (c < s5) & (dn >= 4)), nz(c > s5)))

@reg("IBS < 0.2 long one day", "Pagonidis 2013, The IBS Effect (NAAIM)")
def f(D, s):
    o, h, l, c = dly(D); i = (c - l) / np.maximum(h - l, 1e-9); return sig((i < .2).astype(float))

@reg("IBS > 0.8 short one day", "Pagonidis 2013")
def f(D, s):
    o, h, l, c = dly(D); i = (c - l) / np.maximum(h - l, 1e-9); return sig(-(i > .8).astype(float))

@reg("Outside day down close -> long next day", "Williams 1999, Long-Term Secrets to Short-Term Trading")
def f(D, s):
    o, h, l, c = dly(D); e = (h > lag(h)) & (l < lag(l)) & (c < lag(l)); return sig(nz(e).astype(float))


# ================================================================= CALENDAR (price-independent, close-to-close)
def _tdom(D):
    d = D["days"]; ym = d.year.values * 12 + d.month.values; first = np.r_[True, ym[1:] != ym[:-1]]
    k = np.zeros(len(d), int); kk = 0
    for i in range(len(d)): kk = 1 if first[i] else kk + 1; k[i] = kk
    last = np.r_[first[1:], True]; return k, last

@reg("Turn of month (-1..+3)", "Ariel 1987, JFE 18", params=False)
def f(D, s): k, last = _tdom(D); return ("d", ((k <= 3) | last).astype(float), "cc")

@reg("Turn of month (-1..+4)", "Lakonishok & Smidt 1988, RFS 1", params=False)
def f(D, s): k, last = _tdom(D); return ("d", ((k <= 4) | last).astype(float), "cc")

@reg("First trading day of month", "Hirsch, Stock Trader's Almanac", params=False)
def f(D, s): k, _ = _tdom(D); return ("d", (k == 1).astype(float), "cc")

@reg("Monday effect (short Monday)", "French 1980, JFE 8", params=False)
def f(D, s): return ("d", -(D["days"].weekday.values == 0).astype(float), "cc")

@reg("Friday long", "French 1980; Gibbons & Hess 1981", params=False)
def f(D, s): return ("d", (D["days"].weekday.values == 4).astype(float), "cc")

@reg("Pre-holiday long", "Ariel 1990, J. Finance 45; Lakonishok & Smidt 1988", params=False)
def f(D, s):
    d = D["days"]; nb = np.r_[np.busday_count(d.values[:-1].astype("datetime64[D]"), d.values[1:].astype("datetime64[D]")), 1]
    return ("d", (nb > 1).astype(float), "cc")

@reg("Halloween / sell in May (long Nov-Apr)", "Bouman & Jacobsen 2002, AER 92", params=False)
def f(D, s): m = D["days"].month.values; return ("d", ((m >= 11) | (m <= 4)).astype(float), "cc")

@reg("January long", "Rozeff & Kinney 1976, JFE 3", params=False)
def f(D, s): return ("d", (D["days"].month.values == 1).astype(float), "cc")

@reg("Santa Claus rally (last 5 Dec + first 2 Jan)", "Hirsch 1972, Stock Trader's Almanac", params=False)
def f(D, s):
    d = D["days"]; k, last = _tdom(D); m = d.month.values; y = d.year.values; x = np.zeros(len(d))
    x[(m == 1) & (k <= 2)] = 1
    for yy in np.unique(y):
        idx = np.nonzero((y == yy) & (m == 12))[0]; x[idx[-5:]] = 1
    return ("d", x, "cc")

def _opex_week(D):
    d = D["days"]; dd = d.day.values; wd = d.weekday.values; fri3 = np.zeros(len(d), bool)
    ym = d.year.values * 12 + d.month.values
    for g in np.unique(ym):
        i = np.nonzero(ym == g)[0]
        for j in i:
            if 15 <= dd[j] + (4 - wd[j]) <= 21: fri3[j] = True    # day falls in the week whose Friday is the 3rd Friday
    return fri3

@reg("Options-expiration week long", "Stivers & Sun 2013 / Hirsch Almanac", params=False)
def f(D, s): return ("d", _opex_week(D).astype(float), "cc")

@reg("Week after options expiration short", "Hirsch, Stock Trader's Almanac", params=False)
def f(D, s):
    w = _opex_week(D); after = np.zeros(len(w)); i = 0
    while i < len(w):
        if w[i] and (i + 1 < len(w)) and not w[i + 1]: after[i + 1:i + 6] = -1; i += 6
        else: i += 1
    return ("d", after, "cc")

@reg("Turnaround Tuesday (long Tue after down Monday)", "Connors & Raschke 1995, Street Smarts")
def f(D, s):
    c = D["dc"]; wd = D["days"].weekday.values; e = (wd == 0) & (c < lag(c)); return sig(nz(e).astype(float))

@reg("Overnight long (close->open)", "Cooper, Cliff & Gulen 2008, 'Return differences between trading and non-trading hours'", params=False)
def f(D, s): return ("d", np.ones(len(D["dc"])), "co")

@reg("Intraday long (open->close)", "Cooper, Cliff & Gulen 2008 (the complementary leg)", params=False)
def f(D, s): return ("d", np.ones(len(D["dc"])), "oc")

@reg("Weekend overnight long (Fri close->Mon open)", "French 1980 weekend effect", params=False)
def f(D, s): return ("d", (D["days"].weekday.values == 0).astype(float), "co")

@reg("Overnight long after a down session (15:50 vs open)", "Branch & Ma 2012; Lou, Polk & Skouras 2019 tug of war", params=False)
def f(D, s):
    e = D["c"][:, 380] < D["do"]; return ("d", lag(e.astype(float)), "co")

@reg("Gap fade (all gaps, open->close)", "Branch & Ma 2012 overnight/intraday reversal", params=False)
def f(D, s): g = D["do"] - lag(D["dc"]); return ("d", -np.sign(np.nan_to_num(g)), "oc")

@reg("Gap continuation >0.5% (open->close)", "classic 'gap and go'", params=False)
def f(D, s):
    g = (D["do"] - lag(D["dc"])) / lag(D["dc"]); return ("d", np.where(np.abs(np.nan_to_num(g)) > .005, np.sign(g), 0), "oc")


# ================================================================= INTRADAY
def blank(D, kind):
    n = len(D["days"]); z = np.full(n, np.nan)
    return dict(dir=np.zeros(n, int), e=np.zeros(n, int), kind=kind, lvlL=z.copy(), lvlS=z.copy(), stopL=z.copy(), stopS=z.copy(),
                tgtL=z.copy(), tgtS=z.copy(), tx=np.full(n, 389))

def oco(D, hi, lo, cond, e=0, stopL=None, stopS=None, tgtL=None, tgtS=None):
    sp = blank(D, 1); ok = nz(cond) & ~np.isnan(hi) & ~np.isnan(lo)
    sp["dir"][ok] = 2; sp["e"][:] = e; sp["lvlL"], sp["lvlS"] = hi, lo
    sp["stopL"] = lo if stopL is None else stopL; sp["stopS"] = hi if stopS is None else stopS
    if tgtL is not None: sp["tgtL"] = tgtL
    if tgtS is not None: sp["tgtS"] = tgtS
    return ("i", sp)

def pdh(D): return lag(D["dh"]), lag(D["dl"]), lag(D["dc"])

@reg("Crabel NR7 breakout (prior H/L, exit close)", "Crabel 1990, Day Trading with Short-Term Price Patterns", "i")
def f(D, s):
    r = D["dh"] - D["dl"]; n = L(7, s); c = lag(r <= ll(r, n)); ph, pl, _ = pdh(D); return oco(D, ph, pl, c)

@reg("Crabel NR4 breakout", "Crabel 1990", "i")
def f(D, s):
    r = D["dh"] - D["dl"]; n = L(4, s); c = lag(r <= ll(r, n)); ph, pl, _ = pdh(D); return oco(D, ph, pl, c)

@reg("Crabel ID/NR4 breakout", "Crabel 1990", "i")
def f(D, s):
    h, l = D["dh"], D["dl"]; r = h - l; c = lag((r <= ll(r, L(4, s))) & (h < lag(h)) & (l > lag(l))); ph, pl, _ = pdh(D)
    return oco(D, ph, pl, c)

@reg("Inside-day breakout", "Bulkowski, Encyclopedia of Chart Patterns; Crabel 1990", "i")
def f(D, s):
    h, l = D["dh"], D["dl"]; c = lag((h < lag(h)) & (l > lag(l))); ph, pl, _ = pdh(D); return oco(D, ph, pl, c)

@reg("Crabel stretch ORB (open +/- 10-day stretch)", "Crabel 1990", "i")
def f(D, s):
    o, h, l = D["do"], D["dh"], D["dl"]; st = lag(sma(np.minimum(h - o, o - l), L(10, s)))
    return oco(D, o + st, o - st, np.ones(len(o), bool))

for nmin in (5, 15, 30, 60):
    def f(D, s, nmin=nmin):
        k = L(nmin, s); hi = D["h"][:, :k].max(1); lo = D["l"][:, :k].min(1); return oco(D, hi, lo, np.ones(len(hi), bool), e=k)
    reg(f"Opening-range breakout {nmin} min (stop other side, exit close)", "Crabel 1990; Holmberg, Lonnbark & Lundstrom 2013 FRL", "i")(f)

@reg("Zarattini-Aziz 5-min ORB, 10R target", "Zarattini & Aziz 2023, 'Can Day Trading Really Be Profitable?' SSRN 4416622", "i")
def f(D, s):
    k = L(5, s); o5 = D["o"][:, 0]; c5 = D["c"][:, k - 1]; hi = D["h"][:, :k].max(1); lo = D["l"][:, :k].min(1)
    sp = blank(D, 0); sp["dir"] = np.sign(c5 - o5).astype(int); sp["e"][:] = k
    sp["stopL"], sp["stopS"] = lo, hi; ent = D["o"][:, k]
    sp["tgtL"] = ent + 10 * (ent - lo); sp["tgtS"] = ent - 10 * (hi - ent); return ("i", sp)

@reg("Zarattini-Barbon-Aziz noise-boundary momentum (simplified static stop)", "Zarattini, Barbon & Aziz 2024, 'Beat the Market' SSRN 4824172", "i")
def f(D, s):
    O, C = D["o"], D["c"]; do, pc = D["do"], lag(D["dc"]); mv = np.abs(C / do[:, None] - 1)
    sg = np.full_like(mv, np.nan); n = L(14, s)
    for i in range(n, len(do)): sg[i] = mv[i - n:i].mean(0)
    ub = np.fmax(do, pc)[:, None] * (1 + sg); lb = np.fmin(do, pc)[:, None] * (1 - sg)
    sp = blank(D, 0); chk = np.arange(29, 360, 30)
    for i in range(n, len(do)):
        for m in chk:
            if C[i, m] > ub[i, m]: sp["dir"][i] = 1; sp["e"][i] = m + 1; sp["stopL"][i] = ub[i, m]; break
            if C[i, m] < lb[i, m]: sp["dir"][i] = -1; sp["e"][i] = m + 1; sp["stopS"][i] = lb[i, m]; break
    return ("i", sp)

@reg("Market intraday momentum: 1st half-hour -> last half-hour", "Gao, Han, Li & Zhou 2018, JFE 129", "i", params=False)
def f(D, s):
    sp = blank(D, 0); r1 = D["c"][:, 29] - lag(D["dc"]); sp["dir"] = np.sign(np.nan_to_num(r1)).astype(int); sp["e"][:] = 360; return ("i", sp)

@reg("Intraday momentum: 1st and 12th half-hour agree", "Gao, Han, Li & Zhou 2018", "i", params=False)
def f(D, s):
    sp = blank(D, 0); r1 = np.sign(np.nan_to_num(D["c"][:, 29] - lag(D["dc"]))); r12 = np.sign(D["c"][:, 359] - D["c"][:, 329])
    sp["dir"] = np.where(r1 == r12, r1, 0).astype(int); sp["e"][:] = 360; return ("i", sp)

@reg("Rest-of-day return -> last half-hour", "Baltussen, Da, Lammers & Martens 2021, JFE 142", "i", params=False)
def f(D, s):
    sp = blank(D, 0); r = D["c"][:, 359] - lag(D["dc"]); sp["dir"] = np.sign(np.nan_to_num(r)).astype(int); sp["e"][:] = 360; return ("i", sp)

@reg("Same half-hour persistence (yesterday's last 30 min)", "Heston, Korajczyk & Sadka 2010, J. Finance 65", "i", params=False)
def f(D, s):
    sp = blank(D, 0); r = lag(D["c"][:, 389] - D["o"][:, 360]); sp["dir"] = np.sign(np.nan_to_num(r)).astype(int); sp["e"][:] = 360; return ("i", sp)

def _piv(D):
    ph, pl, pc = pdh(D); p = (ph + pl + pc) / 3; return p, 2 * p - pl, 2 * p - ph, p + (ph - pl), p - (ph - pl)

@reg("Floor pivot: fade R1 (stop R2, target P)", "classic floor-trader pivots (Person 2004, A Complete Guide to Technical Trading Tactics)", "i", params=False)
def f(D, s):
    p, r1, s1, r2, s2 = _piv(D); sp = blank(D, 2); sp["dir"][~np.isnan(p)] = -1; sp["lvlS"], sp["stopS"], sp["tgtS"] = r1, r2, p; return ("i", sp)

@reg("Floor pivot: fade S1 (stop S2, target P)", "Person 2004", "i", params=False)
def f(D, s):
    p, r1, s1, r2, s2 = _piv(D); sp = blank(D, 2); sp["dir"][~np.isnan(p)] = 1; sp["lvlL"], sp["stopL"], sp["tgtL"] = s1, s2, p; return ("i", sp)

@reg("Floor pivot: R1 breakout (stop P, target R2)", "Person 2004", "i", params=False)
def f(D, s):
    p, r1, s1, r2, s2 = _piv(D); sp = blank(D, 1); sp["dir"][~np.isnan(p)] = 1; sp["lvlL"], sp["stopL"], sp["tgtL"] = r1, p, r2; return ("i", sp)

@reg("Floor pivot: S1 breakdown (stop P, target S2)", "Person 2004", "i", params=False)
def f(D, s):
    p, r1, s1, r2, s2 = _piv(D); sp = blank(D, 1); sp["dir"][~np.isnan(p)] = -1; sp["lvlS"], sp["stopS"], sp["tgtS"] = s1, p, s2; return ("i", sp)

def _cam(D, s=1.0):
    ph, pl, pc = pdh(D); r = (ph - pl) * s; return pc, pc + r * 1.1 / 4, pc - r * 1.1 / 4, pc + r * 1.1 / 2, pc - r * 1.1 / 2

@reg("Camarilla fade H3 (stop H4, target prior close)", "Nick Scott 1989, Camarilla equation", "i")
def f(D, s):
    pc, h3, l3, h4, l4 = _cam(D, s); sp = blank(D, 2); sp["dir"][~np.isnan(pc)] = -1; sp["lvlS"], sp["stopS"], sp["tgtS"] = h3, h4, pc; return ("i", sp)

@reg("Camarilla fade L3 (stop L4, target prior close)", "Nick Scott 1989", "i")
def f(D, s):
    pc, h3, l3, h4, l4 = _cam(D, s); sp = blank(D, 2); sp["dir"][~np.isnan(pc)] = 1; sp["lvlL"], sp["stopL"], sp["tgtL"] = l3, l4, pc; return ("i", sp)

@reg("Camarilla H4/L4 breakout (stop H3/L3, exit close)", "Nick Scott 1989", "i")
def f(D, s):
    pc, h3, l3, h4, l4 = _cam(D, s); return oco(D, h4, l4, ~np.isnan(pc), stopL=h3, stopS=l3)

@reg("Williams volatility breakout (open +/- 0.5 x prior range)", "Williams 1999, Long-Term Secrets to Short-Term Trading", "i", params=False)
def f(D, s):
    ph, pl, _ = pdh(D); o = D["do"]; r = ph - pl; return oco(D, o + .5 * r, o - .5 * r, ~np.isnan(r))

@reg("Williams Oops! long (gap below prior low, buy stop prior low)", "Williams 1979", "i", params=False)
def f(D, s):
    ph, pl, _ = pdh(D); o = D["do"]; sp = blank(D, 1); e = nz(o < pl); sp["dir"][e] = 1; sp["lvlL"] = pl; sp["stopL"] = o - (pl - o); return ("i", sp)

@reg("Williams Oops! short (gap above prior high)", "Williams 1979", "i", params=False)
def f(D, s):
    ph, pl, _ = pdh(D); o = D["do"]; sp = blank(D, 1); e = nz(o > ph); sp["dir"][e] = -1; sp["lvlS"] = ph; sp["stopS"] = o + (o - ph); return ("i", sp)

def _after_break(D, lvl, below):
    """first minute the price trades 1 pt beyond lvl (below=True: under it); entry eligible from the next minute."""
    hit = (D["l"] < lvl[:, None] - 1) if below else (D["h"] > lvl[:, None] + 1)
    a = hit.any(1); m = hit.argmax(1); return a, m

@reg("Raschke 80-20 long", "Raschke & Connors 1995, Street Smarts", "i", params=False)
def f(D, s):
    o, h, l, c = dly(D); r = np.maximum(h - l, 1e-9); setup = lag(((o - l) / r >= .8) & ((c - l) / r <= .2)); ph, pl, _ = pdh(D)
    a, m = _after_break(D, np.nan_to_num(pl), True); sp = blank(D, 1); ok = nz(setup) & a & (m < 388)
    sp["dir"][ok] = 1; sp["e"][ok] = m[ok] + 1; sp["lvlL"] = pl
    sp["stopL"] = np.array([D["l"][i, :m[i] + 1].min() if ok[i] else np.nan for i in range(len(o))]); return ("i", sp)

@reg("Raschke 80-20 short", "Raschke & Connors 1995", "i", params=False)
def f(D, s):
    o, h, l, c = dly(D); r = np.maximum(h - l, 1e-9); setup = lag(((o - l) / r <= .2) & ((c - l) / r >= .8)); ph, pl, _ = pdh(D)
    a, m = _after_break(D, np.nan_to_num(ph), False); sp = blank(D, 1); ok = nz(setup) & a & (m < 388)
    sp["dir"][ok] = -1; sp["e"][ok] = m[ok] + 1; sp["lvlS"] = ph
    sp["stopS"] = np.array([D["h"][i, :m[i] + 1].max() if ok[i] else np.nan for i in range(len(o))]); return ("i", sp)

@reg("Raschke Turtle Soup +1 long", "Raschke & Connors 1995", "i")
def f(D, s):
    o, h, l, c = dly(D); n = L(20, s); prev = lag(ll(l, n)); old = lag(S(l).rolling(n).apply(lambda x: n - 1 - x.argmin(), raw=True).values)
    setup = lag((l < prev) & (c <= prev) & (old >= 3)); lvl = lag(prev); sp = blank(D, 1); ok = nz(setup) & ~np.isnan(lvl)
    sp["dir"][ok] = 1; sp["lvlL"] = lvl; sp["stopL"] = lag(l); return ("i", sp)

@reg("Raschke Turtle Soup +1 short", "Raschke & Connors 1995", "i")
def f(D, s):
    o, h, l, c = dly(D); n = L(20, s); prev = lag(hh(h, n)); old = lag(S(h).rolling(n).apply(lambda x: n - 1 - x.argmax(), raw=True).values)
    setup = lag((h > prev) & (c >= prev) & (old >= 3)); lvl = lag(prev); sp = blank(D, 1); ok = nz(setup) & ~np.isnan(lvl)
    sp["dir"][ok] = -1; sp["lvlS"] = lvl; sp["stopS"] = lag(h); return ("i", sp)

def _lbr(D, s):
    c = D["dc"]; return lag(rsi(c - lag(c), L(3, s)))

@reg("Raschke momentum pinball long (LBR/RSI<30, first-hour high)", "Raschke & Connors 1995", "i")
def f(D, s):
    x = _lbr(D, s); hi = D["h"][:, :60].max(1); lo = D["l"][:, :60].min(1); sp = blank(D, 1); ok = nz(x < 30)
    sp["dir"][ok] = 1; sp["e"][:] = 60; sp["lvlL"], sp["stopL"] = hi, lo; return ("i", sp)

@reg("Raschke momentum pinball short (LBR/RSI>70)", "Raschke & Connors 1995", "i")
def f(D, s):
    x = _lbr(D, s); hi = D["h"][:, :60].max(1); lo = D["l"][:, :60].min(1); sp = blank(D, 1); ok = nz(x > 70)
    sp["dir"][ok] = -1; sp["e"][:] = 60; sp["lvlS"], sp["stopS"] = lo, hi; return ("i", sp)

@reg("Raschke ADX gapper long", "Raschke & Connors 1995", "i")
def f(D, s):
    o, h, l, c = dly(D); pdi, mdi, ax = dmi(h, l, c, L(12, s)); ph, pl, _ = pdh(D)
    ok = nz(lag(ax) > 30) & nz(lag(pdi) > lag(mdi)) & nz(o < pl); sp = blank(D, 1); sp["dir"][ok] = 1; sp["lvlL"] = pl; sp["stopL"] = o - (pl - o); return ("i", sp)

@reg("Raschke ADX gapper short", "Raschke & Connors 1995", "i")
def f(D, s):
    o, h, l, c = dly(D); pdi, mdi, ax = dmi(h, l, c, L(12, s)); ph, pl, _ = pdh(D)
    ok = nz(lag(ax) > 30) & nz(lag(mdi) > lag(pdi)) & nz(o > ph); sp = blank(D, 1); sp["dir"][ok] = -1; sp["lvlS"] = ph; sp["stopS"] = o + (o - ph); return ("i", sp)

@reg("Raschke Holy Grail long (ADX>30, pullback to EMA20)", "Raschke & Connors 1995", "i")
def f(D, s):
    o, h, l, c = dly(D); pdi, mdi, ax = dmi(h, l, c, L(14, s)); e = ema(c, L(20, s))
    st = lag((ax > 30) & (pdi > mdi) & (l <= e)); sp = blank(D, 1); ok = nz(st); sp["dir"][ok] = 1; sp["lvlL"] = lag(h); sp["stopL"] = lag(l); return ("i", sp)

@reg("Raschke Holy Grail short", "Raschke & Connors 1995", "i")
def f(D, s):
    o, h, l, c = dly(D); pdi, mdi, ax = dmi(h, l, c, L(14, s)); e = ema(c, L(20, s))
    st = lag((ax > 30) & (mdi > pdi) & (h >= e)); sp = blank(D, 1); ok = nz(st); sp["dir"][ok] = -1; sp["lvlS"] = lag(l); sp["stopS"] = lag(h); return ("i", sp)

@reg("Gap fill: fade gap >0.15% at open, target prior close, stop 1x gap", "classic gap-fill (Caporale & Plastun 2017 for US indices)", "i", params=False)
def f(D, s):
    o = D["do"]; pc = lag(D["dc"]); g = o - pc; ok = nz(np.abs(g) / pc > .0015); sp = blank(D, 0)
    sp["dir"][ok] = -np.sign(g[ok]).astype(int); sp["tgtL"], sp["tgtS"] = pc, pc; sp["stopL"], sp["stopS"] = o - np.abs(g), o + np.abs(g)
    return ("i", sp)

@reg("Initial-balance (first hour) breakout, stop IB middle", "Dalton 1990, Mind Over Markets (Market Profile)", "i")
def f(D, s):
    k = L(60, s); hi = D["h"][:, :k].max(1); lo = D["l"][:, :k].min(1); mid = (hi + lo) / 2
    return oco(D, hi, lo, np.ones(len(hi), bool), e=k, stopL=mid, stopS=mid)

UNTESTABLE = ["On-Balance Volume (Granville 1963)", "Money Flow Index (Quong & Soudack)", "VWAP reversion / Zarattini VWAP trail",
              "Chaikin oscillator", "Elder force index", "O'Neil pocket pivot", "Pre-FOMC drift (Lucca & Moench 2015) - no reliable FOMC calendar offline"]
