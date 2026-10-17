"""Shared machinery for the influencer study. MNQ 1-minute RTH grid (Databento 2020-01 → 2026-10), 1,660 days.
Global continuous bar series per timeframe (RTH bars concatenated) so indicators carry across days.
Signals are evaluated at a bar CLOSE; market entries fill at the next minute's open; stop/limit entries fill
only when traded (limits: through by 1 tick). Exits walked on 1-minute bars, stop first on ties, flat 15:54.
Costs 2.25 pt per round trip (commission + 1 tick each side + 1 pt stress)."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, ".."), os.path.join(H, "../hunt")]
import numpy as np, pandas as pd
from engine import walk
from feat import load
F, D = load()
N = len(D.days); o, h, l, c, v = D.o, D.h, D.l, D.c, D.v
DAYS = pd.to_datetime(D.days); YR = DAYS.year.values
SIG = F.sig.values; VALID = F.valid.values & ~np.isnan(SIG)
COST, TICK, LAST = 2.25, 0.25, 384
PDH = np.r_[np.nan, h[:-1].max(1)]; PDL = np.r_[np.nan, l[:-1].min(1)]; PDC = np.r_[np.nan, c[:-1, 389]]
okprev = VALID & ~D.roll
DO, DH, DL, DC = o[:, 0], h.max(1), l.min(1), c[:, 389]
RANGE = DH - DL

class G:
    """Global bars of timeframe tf: arrays shaped (N*nb,), plus helpers."""
    def __init__(self, tf):
        self.tf = tf; nb = 390 // tf; self.nb = nb
        self.o = o[:, ::tf][:, :nb].ravel(); self.c = c[:, tf - 1::tf][:, :nb].ravel()
        self.h = h[:, :nb * tf].reshape(N, nb, tf).max(2).ravel(); self.l = l[:, :nb * tf].reshape(N, nb, tf).min(2).ravel()
        self.v = v[:, :nb * tf].reshape(N, nb, tf).sum(2).ravel()
    def day(self, g): return g // self.nb
    def k(self, g): return g % self.nb
    def next_min(self, g): return (self.k(g) + 1) * self.tf          # minute index right after bar g closes

def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().values
def sma(x, n): return pd.Series(x).rolling(n).mean().values
def rsi(x, n):
    d = np.diff(x, prepend=x[0]); up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False).mean(); dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).values
def atr(hh, ll, cc, n):
    pc = np.r_[cc[0], cc[:-1]]; tr = np.maximum(hh - ll, np.maximum(abs(hh - pc), abs(ll - pc)))
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean().values
def adx(hh, ll, cc, n=14):
    up = np.diff(hh, prepend=hh[0]); dn = -np.diff(ll, prepend=ll[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.); ndm = np.where((dn > up) & (dn > 0), dn, 0.)
    a = atr(hh, ll, cc, n); pdi = 100 * pd.Series(pdm).ewm(alpha=1 / n, adjust=False).mean().values / a
    ndi = 100 * pd.Series(ndm).ewm(alpha=1 / n, adjust=False).mean().values / a
    dx = 100 * abs(pdi - ndi) / np.maximum(pdi + ndi, 1e-9)
    return pd.Series(dx).ewm(alpha=1 / n, adjust=False).mean().values, pdi, ndi
def vwap_day(i):
    tp = (h[i] + l[i] + c[i]) / 3; cv = np.cumsum(v[i]); return np.cumsum(tp * v[i]) / np.maximum(cv, 1)

def trade(i, m, side, stop, target=None, entry=None, at_open=True, last=LAST):
    """Enter at minute m (market at open unless `entry` given). Returns (pts_net, risk_pts, exit_minute)."""
    if m > last or not VALID[i]: return None
    e = o[i, m] if entry is None else entry
    if stop is not None and (stop - e) * side >= 0: return None
    px, j, _ = walk(o[i], h[i], l[i], c[i], m, side, e, stop, target, last, at_open=at_open)
    return side * (px - e) - COST, (abs(e - stop) if stop is not None else np.nan), j

def stop_fill(i, m0, m1, level, side):
    """First minute in [m0, m1) where a buy stop (side 1) / sell stop (−1) at `level` fills. Returns (minute, price)."""
    for x in range(m0, min(m1, LAST)):
        if (side == 1 and h[i, x] >= level) or (side == -1 and l[i, x] <= level):
            return x, (max(o[i, x], level) if side == 1 else min(o[i, x], level))
    return None
def limit_fill(i, m0, m1, level, side):
    for x in range(m0, min(m1, LAST)):
        if (side == 1 and l[i, x] <= level - TICK) or (side == -1 and h[i, x] >= level + TICK):
            return x, (min(o[i, x], level) if side == 1 else max(o[i, x], level))
    return None

def summarize(name, who, rows, kind="intraday"):
    if not rows: return dict(influencer=who, strategy=name, n=0, kind=kind)
    df = pd.DataFrame(rows, columns=["i", "pts", "risk"])
    p = df.pts.values; y = YR[df.i.values]; isd = y < 2024; w, lo = p[p > 0], p[p <= 0]
    R = (df.pts / df.risk).values
    return dict(influencer=who, strategy=name, kind=kind, n=len(p), per_yr=round(len(p) / 6.75), win=round(100 * (p > 0).mean(), 1),
                avg_win=round(2 * w.mean()) if len(w) else 0, avg_loss=round(2 * lo.mean()) if len(lo) else 0,
                rr=round(w.mean() / -lo.mean(), 2) if len(w) and len(lo) else np.nan,
                usd=round(2 * p.mean(), 1), usd_IS=round(2 * p[isd].mean(), 1), usd_OOS=round(2 * p[~isd].mean(), 1),
                avgR=round(np.nanmean(R), 3) if np.isfinite(R).any() else np.nan,
                pf=round(w.sum() / -lo.sum(), 2) if lo.sum() < 0 else np.nan,
                yrs_pos=int((pd.Series(p).groupby(y).sum() > 0).sum()),
                t=round(p.mean() / p.std(ddof=1) * np.sqrt(len(p)), 2) if len(p) > 2 else 0)
