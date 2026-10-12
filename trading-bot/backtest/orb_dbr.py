"""Pre-market range "double break" reversal (DayTradingRauf, Instagram reel DeT6YMHNNVv).

What the video says:
  * Range = high/low of 08:12–09:12 NY (a pre-market range into the open). MNQ 5-minute chart.
  * Wait for the high OR the low to be taken first, then look for the reversal.
  * His stat (edgeful, NQ, Mondays, 52 days): 73% of days break BOTH sides of the range during the day.
  * Chart: short after the high is swept; entry as a 5-minute candle closes back under the range high;
    stop loss above the sweep's high. Fib extensions −0.25/−0.5/−1/−1.5 drawn on the range.
Not said (gated behind "comment TIME"): exact entry trigger and target. Parameters here:
  * trigger: first 5-min candle that closes back inside the range (bearish for a short / bullish for a long).
  * stop = sweep extreme + buf points.  target: "opp" = other side of the range (the double break),
    "mid" = middle of the range, "rr" = rr × risk.
One trade per day, only on the side swept FIRST. Fills on 1-min bars; stop and target in one bar = stop.
"""
from __future__ import annotations

import pandas as pd

PT_USD = 2.0
COST_USD = 2.0                    # commission + 1 tick slippage, round trip, per MNQ contract


def load_1m(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path, usecols=["ts_event", "open", "high", "low", "close"])
    raw["ts"] = pd.to_datetime(raw.ts_event, utc=True).dt.tz_convert("America/New_York")
    d = raw.set_index("ts")[["open", "high", "low", "close"]].sort_index()
    d = d[~d.index.duplicated()]
    m = d.index.hour * 60 + d.index.minute
    return d[(m >= 8 * 60) & (m <= 16 * 60)]


def double_break_rate(d: pd.DataFrame, r0=8 * 60 + 12, r1=9 * 60 + 12, end=18 * 60) -> dict:
    """Check his 73% claim: share of days that trade through both the range high and low after r1."""
    m = d.index.hour * 60 + d.index.minute
    d = d.assign(m=m, day=d.index.date)
    c = dict(both=0, up=0, down=0, none=0)
    for _, g in d.groupby("day"):
        rg = g[(g.m >= r0) & (g.m < r1)]
        if len(rg) < 50:
            continue
        hi, lo = rg.high.max(), rg.low.min()
        a = g[(g.m >= r1) & (g.m < end)]
        u, dn = (a.high > hi).any(), (a.low < lo).any()
        c["both" if u and dn else "up" if u else "down" if dn else "none"] += 1
    n = sum(c.values())
    return {k: round(100 * v / n, 1) for k, v in c.items()} | {"days": n}


def run(d: pd.DataFrame, target="opp", rr=1.0, buf=1.0, last_entry=11 * 60, flat_at=15 * 60 + 55,
        r0=8 * 60 + 12, r1=9 * 60 + 12, max_risk_frac=10.0) -> pd.DataFrame:
    m = d.index.hour * 60 + d.index.minute
    d = d.assign(m=m, day=d.index.date)
    out = []
    for day, g in d.groupby("day"):
        rg = g[(g.m >= r0) & (g.m < r1)]
        if len(rg) < 50 or g.index[0].weekday() >= 5:
            continue
        hi, lo = rg.high.max(), rg.low.min()
        rng = hi - lo
        a = g[(g.m >= r1) & (g.m <= flat_at)]
        # first side taken
        up, dn = a[a.high > hi], a[a.low < lo]
        tu = up.index[0] if len(up) else None
        td = dn.index[0] if len(dn) else None
        if tu is None and td is None:
            continue
        side = -1 if (td is None or (tu is not None and tu < td)) else 1     # high swept first → short
        tb = tu if side == -1 else td
        if tu is not None and td is not None and tu == td:
            continue                                                        # both in one minute: skip
        # 5-minute candles after the break
        post = a[a.index >= tb.floor("5min")]
        c5 = post.resample("5min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        ext = None
        entry = None
        for t, b in c5.iterrows():
            if t.hour * 60 + t.minute >= last_entry:
                break
            ext = b.high if ext is None and side == -1 else b.low if ext is None else \
                max(ext, b.high) if side == -1 else min(ext, b.low)
            back = (b.close < hi and b.close < b.open) if side == -1 else (b.close > lo and b.close > b.open)
            if back:
                entry = (t + pd.Timedelta(minutes=5), b.close)
                break
        if entry is None:
            continue
        te, e = entry
        stp = ext + buf if side == -1 else ext - buf
        risk = abs(e - stp)
        if risk <= 0 or risk > max_risk_frac * rng:
            continue
        if target == "opp":
            tgt = lo if side == -1 else hi
        elif target == "mid":
            tgt = (hi + lo) / 2
        else:
            tgt = e + side * rr * risk
        reward = (tgt - e) * side
        if reward <= 0:
            continue
        res, r = None, None
        for t, b in a[a.index >= te].iterrows():
            hs = b.high >= stp if side == -1 else b.low <= stp
            ht = b.low <= tgt if side == -1 else b.high >= tgt
            if hs:
                res, r = "stop", -1.0; break
            if ht:
                res, r = "target", reward / risk; break
            if b.m >= flat_at:
                res, r = "time", (b.close - e) * side / risk; break
        if res is None:
            continue
        out.append(dict(date=day, t=te, side=side, rng=rng, risk=risk, rr=reward / risk, res=res, r=r))
    tr = pd.DataFrame(out)
    if not tr.empty:
        tr["r_net"] = tr.r - COST_USD / (tr.risk * PT_USD)
    return tr
