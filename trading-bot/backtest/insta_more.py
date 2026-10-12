"""Two more Instagram systems, tested on MNQ 1-minute data (Databento 2020–2026).

FCR — "first candle rule" (Avid Trader, reel DeKU6nVPwBc):
  * Range = high/low of the first 5-minute candle (09:30–09:35 NY).
  * 1-minute chart: wait for a breakout (1-min close outside the range).
  * Wait for the pullback that retests the broken level, then an engulfing candle in the breakout direction
    (closing back beyond the level). Enter at its close.
  * Stop one tick beyond the candle that retested the level. Target fixed 3:1.

EMA9 + VWAP (FiFi Trades, reel DeZPxc6g3wI):
  * Enter when a full-body candle closes over VWAP (long) / under VWAP (short). Shown on a 3-minute chart.
  * Exit when a candle closes back under the 9 EMA (long) / over it (short). No stop shown.
"""
from __future__ import annotations

import pandas as pd

TICK, PT_USD, COST_USD = 0.25, 2.0, 2.0


def fcr(d: pd.DataFrame, rr=3.0, last_entry=11 * 60, flat_at=15 * 60 + 55, need_engulf=True) -> pd.DataFrame:
    m = d.index.hour * 60 + d.index.minute
    d = d.assign(m=m, day=d.index.date)
    out = []
    for day, g in d.groupby("day"):
        fc = g[(g.m >= 570) & (g.m < 575)]
        if len(fc) < 5:
            continue
        hi, lo = fc.high.max(), fc.low.min()
        a = g[(g.m >= 575) & (g.m <= flat_at)]
        o, h, l, c, mm = a.open.values, a.high.values, a.low.values, a.close.values, a.m.values
        side, i_brk = 0, None
        for i in range(len(a)):
            if mm[i] >= last_entry:
                break
            if c[i] > hi:
                side, i_brk = 1, i; break
            if c[i] < lo:
                side, i_brk = -1, i; break
        if not side:
            continue
        lvl = hi if side == 1 else lo
        far = lo if side == 1 else hi
        i_ret, ext, entry = None, None, None
        for i in range(i_brk + 1, len(a)):
            if mm[i] >= last_entry:
                break
            if (c[i] < far) if side == 1 else (c[i] > far):
                break                                   # closed through the other side: idea dead
            touched = l[i] <= lvl if side == 1 else h[i] >= lvl
            if i_ret is None:
                if touched:
                    i_ret, ext = i, (l[i] if side == 1 else h[i])
                continue
            ext = min(ext, l[i]) if side == 1 else max(ext, h[i])
            bull = c[i] > o[i] and c[i] >= o[i - 1] and o[i] <= c[i - 1] and c[i - 1] < o[i - 1]
            bear = c[i] < o[i] and c[i] <= o[i - 1] and o[i] >= c[i - 1] and c[i - 1] > o[i - 1]
            conf = (bull if side == 1 else bear) if need_engulf else (c[i] > o[i] if side == 1 else c[i] < o[i])
            if conf and ((c[i] > lvl) if side == 1 else (c[i] < lvl)):
                entry = i; break
        if entry is None:
            continue
        e = c[entry]
        stp = ext - TICK if side == 1 else ext + TICK
        risk = (e - stp) * side
        if risk <= 0:
            continue
        tgt = e + side * rr * risk
        res = None
        for j in range(entry + 1, len(a)):
            if (l[j] <= stp) if side == 1 else (h[j] >= stp):
                res = ("stop", -1.0); break
            if (h[j] >= tgt) if side == 1 else (l[j] <= tgt):
                res = ("target", rr); break
            if mm[j] >= flat_at:
                res = ("time", (c[j] - e) * side / risk); break
        if res:
            out.append(dict(date=day, t=a.index[entry], side=side, risk=risk, res=res[0], r=res[1]))
    tr = pd.DataFrame(out)
    if not tr.empty:
        tr["r_net"] = tr.r - COST_USD / (tr.risk * PT_USD)
        tr["usd"] = tr.r * tr.risk * PT_USD - COST_USD
    return tr


def ema_vwap(d: pd.DataFrame, tf="3min", body=0.6, last_entry=15 * 60 + 30, flat_at=15 * 60 + 55,
             both_sides=True) -> pd.DataFrame:
    """Session VWAP from 09:30, EMA9 on tf bars, many trades a day. Result in points and $ per MNQ."""
    m = d.index.hour * 60 + d.index.minute
    rth = d[(m >= 570) & (m < 960)]
    b = rth.resample(tf, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    b["day"] = b.index.date
    tp = (b.high + b.low + b.close) / 3
    b["vwap"] = (tp * b.volume).groupby(b.day).cumsum() / b.volume.groupby(b.day).cumsum()
    b["ema"] = b.close.ewm(span=9, adjust=False).mean()
    b["m"] = b.index.hour * 60 + b.index.minute
    out = []
    for day, g in b.groupby("day"):
        o, h, l, c, v, e9, mm = (g[k].values for k in ("open", "high", "low", "close", "vwap", "ema", "m"))
        pos = None
        for i in range(1, len(g)):
            end = mm[i] + int(tf[:-3])
            if pos:
                s = pos["side"]
                if ((c[i] < e9[i]) if s == 1 else (c[i] > e9[i])) or end >= flat_at:
                    pts = (c[i] - pos["e"]) * s
                    out.append(dict(date=day, t=pos["t"], side=s, pts=pts, mae=pos["mae"]))
                    pos = None
                else:
                    pos["mae"] = min(pos["mae"], (l[i] - pos["e"]) if s == 1 else (pos["e"] - h[i]))
                continue
            if end > last_entry:
                continue
            full = abs(c[i] - o[i]) >= body * (h[i] - l[i]) and h[i] > l[i]
            up = full and c[i] > o[i] and c[i] > v[i] and c[i - 1] <= v[i - 1]
            dn = full and c[i] < o[i] and c[i] < v[i] and c[i - 1] >= v[i - 1] and both_sides
            if up or dn:
                pos = dict(side=1 if up else -1, e=c[i], t=g.index[i], mae=0.0)
    tr = pd.DataFrame(out)
    if not tr.empty:
        tr["usd"] = tr.pts * PT_USD - COST_USD
    return tr
