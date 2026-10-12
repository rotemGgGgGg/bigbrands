"""30-minute ORB + 2-minute 20 EMA pullback (flexingjoetrades, Instagram reel Ddzb26MRUqs).

Rules shown in the video:
  * Opening range = high/low of 09:30–10:00 NY.
  * Wait for a 10-minute candle to CLOSE outside the range (first one decides the side).
  * Switch to 2-minute, 20 EMA. Enter on the first interaction with the EMA (limit at the EMA).
Not shown (he gates it behind "comment VIDEO"): stop, target, cut-off. Those are parameters here:
  * stop_mode "pts": fixed points;  "rng": k × range;  "mid": the middle of the range.
  * target = rr × stop.  One trade per day.  No new entry after last_entry; flat at flat_at.
Fills on 1-minute bars. Limit = EMA of the last completed 2-minute bar. A bar that hits both stop and
target counts as a loss; a stop hit inside the fill bar counts as a loss.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

PT_USD = 2.0                      # MNQ $ per point
COST_USD = 1.5 + 0.5              # round-trip commission + 1 tick slippage on the exit, per contract


@dataclass
class P:
    stop_mode: str = "pts"        # pts | rng | mid
    stop: float = 20.0            # points (pts) or × range (rng)
    rr: float = 1.0
    last_entry: int = 12 * 60     # minutes after midnight NY
    flat_at: int = 15 * 60 + 55
    both_sides: bool = True       # the video shows a long; shorts mirror it


def prep(df1: pd.DataFrame) -> pd.DataFrame:
    """1-minute bars (index = bar open, NY tz) + EMA20 of the last *completed* 2-minute bar."""
    c2 = df1["close"].resample("2min", label="left", closed="left").last().dropna()
    ema = c2.ewm(span=20, adjust=False).mean()
    # a 2-min bar opened at t completes at t+2min → usable from t+2min on
    ema.index = ema.index + pd.Timedelta(minutes=2)
    d = df1.copy()
    d["ema"] = ema.reindex(d.index, method="ffill")
    return d


def run(d: pd.DataFrame, p: P = P()) -> pd.DataFrame:
    out = []
    mins = d.index.hour * 60 + d.index.minute
    d = d.assign(m=mins, day=d.index.date)
    for day, g in d.groupby("day"):
        if g.index[0].weekday() >= 5:
            continue
        orw = g[(g.m >= 570) & (g.m < 600)]
        if len(orw) < 25:
            continue
        hi, lo = orw.high.max(), orw.low.min()
        rng = hi - lo
        if rng <= 0:
            continue
        # 10-min candles from 10:00
        s = g[(g.m >= 600) & (g.m < p.last_entry)]
        if s.empty:
            continue
        c10 = s["close"].resample("10min", label="left", closed="left").last().dropna()
        side, armed_at = 0, None
        for t, c in c10.items():
            if c > hi:
                side, armed_at = 1, t + pd.Timedelta(minutes=10)
                break
            if c < lo and p.both_sides:
                side, armed_at = -1, t + pd.Timedelta(minutes=10)
                break
        if not side:
            continue
        w = g[(g.index >= armed_at) & (g.m <= p.flat_at)]
        pos = None
        for t, b in w.iterrows():
            if pos is None:
                if b.m >= p.last_entry:
                    break
                lim = b.ema
                if np.isnan(lim):
                    continue
                touched = b.low <= lim if side == 1 else b.high >= lim
                if not touched:
                    continue
                e = min(b.open, lim) if side == 1 else max(b.open, lim)
                if p.stop_mode == "pts":
                    sd = p.stop
                elif p.stop_mode == "rng":
                    sd = p.stop * rng
                else:                                   # mid of the range
                    sd = (e - (hi + lo) / 2) * side
                if sd <= 1:
                    continue                            # entry already beyond the stop level — skip day
                stp, tgt = e - side * sd, e + side * sd * p.rr
                pos = dict(t=t, e=e, sd=sd, stp=stp, tgt=tgt)
                # same bar: stop counts, target does not (unknown order)
                if (b.low <= stp) if side == 1 else (b.high >= stp):
                    out.append(dict(date=day, t=t, side=side, rng=rng, sd=sd, res="stop", r=-1.0))
                    break
                continue
            hit_s = b.low <= pos["stp"] if side == 1 else b.high >= pos["stp"]
            hit_t = b.high >= pos["tgt"] if side == 1 else b.low <= pos["tgt"]
            if hit_s:
                out.append(dict(date=day, t=pos["t"], side=side, rng=rng, sd=pos["sd"], res="stop", r=-1.0))
                break
            if hit_t:
                out.append(dict(date=day, t=pos["t"], side=side, rng=rng, sd=pos["sd"], res="target", r=p.rr))
                break
            if b.m >= p.flat_at:
                r = (b.close - pos["e"]) * side / pos["sd"]
                out.append(dict(date=day, t=pos["t"], side=side, rng=rng, sd=pos["sd"], res="time", r=r))
                break
    tr = pd.DataFrame(out)
    if not tr.empty:
        tr["cost_r"] = COST_USD / (tr.sd * PT_USD)     # costs per 1 contract, in R
        tr["r_net"] = tr.r - tr.cost_r
    return tr


def streaks(x):
    best = cur = 0
    for v in x:
        cur = cur + 1 if v > 0 else 0
        best = max(best, cur)
    return best


def lucid(tr: pd.DataFrame, risk=250.0, target=3000.0, dd=2000.0):
    """Start a 50K eval on every trading day; $risk per trade; EOD trailing drawdown. → pass %, n."""
    daily = (tr.r_net * risk).groupby(tr.date).sum()
    days = list(daily.index)
    res = []
    for i in range(len(days)):
        bal = peak = 0.0
        out = None
        for d in days[i:]:
            bal += daily[d]
            if bal <= peak - dd:
                out = "fail"; break
            if bal >= target:
                out = "pass"; break
            peak = max(peak, bal)
        if out:
            res.append(out)
    return 100 * res.count("pass") / max(len(res), 1), len(res)


def summary(tr: pd.DataFrame) -> dict:
    y = tr.date.astype(str).str[:4]
    by = tr.groupby(y).r_net.sum()
    cum = tr.r_net.cumsum()
    return dict(n=len(tr), win=100 * (tr.r > 0).mean(), avg=tr.r_net.mean(), tot=tr.r_net.sum(),
                dd=(cum - cum.cummax()).min(), streak=streaks(tr.r), yrs_pos=int((by > 0).sum()), yrs=len(by),
                by=by.round(1).to_dict(), lucid=lucid(tr)[0])


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from data import load_file
    raw = pd.read_csv(sys.argv[1], usecols=["ts_event", "open", "high", "low", "close", "volume", "symbol"])
    raw["ts"] = pd.to_datetime(raw.ts_event, utc=True).dt.tz_convert("America/New_York")
    df1 = raw.set_index("ts")[["open", "high", "low", "close", "volume"]].sort_index()
    df1 = df1[~df1.index.duplicated()]
    d = prep(df1)
    print(f"{d.index[0]} → {d.index[-1]}  {len(d):,} 1-min bars")
    for tr_, name in [(run(d, P(stop_mode="mid", rr=1.0)), "stop range-mid rr1")]:
        print(name, summary(tr_))
