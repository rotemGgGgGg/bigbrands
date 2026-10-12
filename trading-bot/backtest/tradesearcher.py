"""Two TradeSearcher strategies re-built and tested on MNQ (Databento 1-minute, 2020–2026).

Exits are simulated on 1-minute bars, so no "both stop and target inside one big bar" guessing.

A) "2x take profit, move stop loss to entry" (fpsd4ve) — 1-hour bars.
   Long: bar low < lower Bollinger(20, 2) and Stoch(14,3,3) %K crosses above %D, %K < 25.  Short mirrors (>75).
   Enter next bar open. SL = s, TP1 = s, TP2 = 2.5 s (their 200 / 200 / 500 ticks on RTY ≈ 0.9 % / 0.9 % / 2.25 %).
   Half off at TP1, stop → entry.  One position at a time.
B) "I11L - Reversal Trading Ideas by Larry Connors" — 5-minute bars, long only.
   Buy when the close is the lowest close of the last 7 bars (add-ons: lowest of 7×(n+1) bars AND 1 % below the
   average entry).  Sell everything when RSI(2) > 70.  No stop.  Optional filter close > SMA(55).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PT_USD, COST_USD = 2.0, 2.0       # MNQ: $ per point; commission + 1 tick slippage per contract round trip


def bars(d1: pd.DataFrame, tf: str) -> pd.DataFrame:
    return d1.resample(tf, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()


def _mins(idx):
    return idx.hour * 60 + idx.minute


def two_tp(d1: pd.DataFrame, s=0.009, tp2_mult=2.5, kmax=25, intraday=False) -> pd.DataFrame:
    h = bars(d1, "60min")
    mid = h.close.rolling(20).mean()
    sd = h.close.rolling(20).std(ddof=0)
    lo_bb, up_bb = mid - 2 * sd, mid + 2 * sd
    ll, hh = h.low.rolling(14).min(), h.high.rolling(14).max()
    k = (100 * (h.close - ll) / (hh - ll)).rolling(3).mean()
    dd = k.rolling(3).mean()
    up_x = (k > dd) & (k.shift() <= dd.shift())
    dn_x = (k < dd) & (k.shift() >= dd.shift())
    sig = pd.Series(0, index=h.index)
    sig[(h.low < lo_bb) & up_x & (k < kmax)] = 1
    sig[(h.high > up_bb) & dn_x & (k > 100 - kmax)] = -1
    t1 = d1.index.values
    o1, hi1, lo1, c1 = (d1[c].values for c in ("open", "high", "low", "close"))
    m1 = _mins(d1.index)
    out, free_at = [], np.datetime64("1970-01-01T00:00")
    for t, sgn in sig[sig != 0].items():
        start = t + pd.Timedelta(hours=1)                     # next bar open
        if intraday:
            mm = start.hour * 60 + start.minute
            if mm < 570 or mm > 15 * 60:
                continue
        i = np.searchsorted(t1, start.to_datetime64())
        if i >= len(t1) or t1[i] < free_at:
            continue
        e = o1[i]
        sl, tp1, tp2 = e * (1 - sgn * s), e * (1 + sgn * s), e * (1 + sgn * tp2_mult * s)
        half1 = None
        pnl = None
        j = i
        while j < len(t1):
            if intraday and m1[j] >= 15 * 60 + 55:
                rest = (c1[j] - e) * sgn
                pnl = (half1 if half1 is not None else rest) * 0.5 + rest * 0.5
                break
            hit_sl = lo1[j] <= sl if sgn == 1 else hi1[j] >= sl
            if hit_sl:
                rest = (sl - e) * sgn
                pnl = (half1 if half1 is not None else rest) * 0.5 + rest * 0.5
                break
            if half1 is None and (hi1[j] >= tp1 if sgn == 1 else lo1[j] <= tp1):
                half1 = (tp1 - e) * sgn
                sl = e                                       # stop to entry (from the next minute on)
            if half1 is not None and (hi1[j] >= tp2 if sgn == 1 else lo1[j] <= tp2):
                pnl = half1 * 0.5 + (tp2 - e) * sgn * 0.5
                break
            j += 1
        if pnl is None:
            break
        free_at = t1[j]
        out.append(dict(date=pd.Timestamp(t1[i]).date(), side=sgn, pts=pnl, bars=j - i, risk=e * s))
    tr = pd.DataFrame(out)
    if not tr.empty:
        tr["usd"] = tr.pts * PT_USD - COST_USD
    return tr


def connors(d1: pd.DataFrame, tf="5min", lb=7, avg_drop=0.01, rsi_exit=70, sma_filter=False, max_units=5,
            intraday=True) -> pd.DataFrame:
    b = bars(d1, tf)
    if intraday:
        m = _mins(b.index)
        b = b[(m >= 570) & (m < 960)]
    c = b.close
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    rsi = (100 - 100 / (1 + up / dn)).values
    sma = c.rolling(55).mean().values
    cv, ov = c.values, b.open.values
    mm = _mins(b.index)
    day = b.index.date
    out, pos = [], []
    for i in range(7 * (max_units + 1), len(b) - 1):
        last_bar_of_day = intraday and (day[i + 1] != day[i])
        if pos and (rsi[i] > rsi_exit or last_bar_of_day):
            ex = cv[i] if last_bar_of_day else ov[i + 1]
            for e in pos:
                out.append(dict(date=day[i], pts=ex - e, units=len(pos)))
            pos = []
            continue
        if last_bar_of_day or (intraday and mm[i] >= 15 * 60 + 45):
            continue
        n = len(pos)
        if n >= max_units:
            continue
        win = lb * (n + 1)
        if cv[i] > cv[i - win + 1:i + 1].min():
            continue
        if n and cv[i] > np.mean(pos) * (1 - avg_drop):
            continue
        if sma_filter and not cv[i] > sma[i]:
            continue
        pos.append(ov[i + 1])
    tr = pd.DataFrame(out)
    if not tr.empty:
        tr["usd"] = tr.pts * PT_USD - COST_USD
    return tr


def report(tr: pd.DataFrame, name: str) -> dict:
    y = tr.date.astype(str).str[:4]
    s = tr.usd
    cum = s.cumsum()
    best = cur = 0
    for v in s:
        cur = cur + 1 if v > 0 else 0
        best = max(best, cur)
    r = dict(name=name, n=len(tr), win=round(100 * (s > 0).mean(), 1), avg_usd=round(s.mean(), 1),
             tot_usd=round(s.sum()), dd_usd=round((cum - cum.cummax()).min()), streak=best,
             yrs_pos=f"{int((s.groupby(y).sum() > 0).sum())}/{y.nunique()}",
             IS=round(s[y < "2024"].mean(), 1), OOS=round(s[y >= "2024"].mean(), 1))
    print(r, flush=True)
    return r
