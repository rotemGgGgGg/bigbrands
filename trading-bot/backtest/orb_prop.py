"""Prop-firm ORB — 15-minute opening range breakout on MNQ 5m, built for a Lucid 50K eval.

Rules (mirrors pine/orb_prop.pine):
  * Opening range = 09:30–09:45 NY (three 5m bars).
  * From the 09:45 bar: stop orders one tick beyond the range, both sides, one cancels the other. Last new entry 11:30.
  * Stop = sl_mult × range from the entry, target = tp_mult × range (default 0.75 / 1.5 → RR 1:2).
  * One trade per day, win or lose. Everything flat at 15:55 NY — nothing is held overnight.
  * Size by dollars: contracts = floor(risk_usd / (stop points × $2)); skip the day if even 1 contract risks more than max_risk_usd.
  * Prop guard: skip a trade whose full loss would breach the $2,000 end-of-day trailing drawdown.
  * Optional breakeven: stop moves to entry once price reaches be_at_r × R in profit (off by default).
Fills follow TradingView's broker emulator: open → nearer extreme → other extreme → close.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass

import pandas as pd

TICK, PT_USD = 0.25, 2.0          # MNQ


@dataclass
class P:
    sl_mult: float = 0.75
    tp_mult: float = 1.5
    risk_usd: float = 250.0
    max_risk_usd: float = 350.0
    brake_at: float = 1e9           # risk halved this far below the high-water mark (off by default, as in Pine)
    dd_limit: float = 2000.0
    dd_guard: bool = True          # skip a trade whose full loss would breach the EOD trailing drawdown
    target: float = 3000.0
    stop_at_target: bool = False   # True = stop once the eval target is reached
    last_entry: int = 11 * 60 + 30
    flat_at: int = 15 * 60 + 55
    be_at_r: float = 0.0           # 0 = off
    cap_pts: float = 0.0           # >0: stop = min(sl_mult × range, cap_pts); target = rr × stop
    rr: float = 2.0


def rt(x):
    return math.floor(x / TICK + 0.5 + 1e-9) * TICK


def path(o, h, l, c):
    return [o, h, l, c] if (h - o) <= (o - l) else [o, l, h, c]


def run(df: pd.DataFrame, p: P = P()):
    trades, eq, hwm, peak_eod = [], 0.0, 0.0, 0.0
    for day, d in df.groupby(df.index.date):
        peak_eod = max(peak_eod, eq)
        if p.stop_at_target and eq >= p.target:
            break
        mins = d.index.hour * 60 + d.index.minute
        orb = d[(mins >= 570) & (mins < 585)]
        if len(orb) < 3:
            continue
        hi, lo = orb.high.max(), orb.low.min()
        rng = hi - lo
        if rng <= 0:
            continue
        stop_pts = p.sl_mult * rng
        tgt_pts = p.tp_mult * rng
        if p.cap_pts > 0 and stop_pts > p.cap_pts:
            stop_pts, tgt_pts = p.cap_pts, p.rr * p.cap_pts
        risk = p.risk_usd / 2 if hwm - eq >= p.brake_at else p.risk_usd
        qty = math.floor(risk / (stop_pts * PT_USD))
        if qty < 1:
            if stop_pts * PT_USD > p.max_risk_usd:
                continue
            qty = 1
        if p.dd_guard and qty * stop_pts * PT_USD >= eq - (peak_eod - p.dd_limit):
            continue
        buy, sell = hi + TICK, lo - TICK
        pos = None
        for t, b in d[mins >= 585].iterrows():
            m = t.hour * 60 + t.minute
            if pos is None:
                if m > p.last_entry:
                    break
                pts = path(b.open, b.high, b.low, b.close)
                # gap through a level at the open fills at the open
                seg = None
                if b.open >= buy:
                    pos, seg = dict(d=1, e=b.open), pts
                elif b.open <= sell:
                    pos, seg = dict(d=-1, e=b.open), pts
                else:
                    cur = b.open
                    for k, nxt in enumerate(pts[1:], 1):
                        if nxt > cur and cur < buy <= nxt:
                            pos, seg = dict(d=1, e=buy), [buy] + pts[k:]; break
                        if nxt < cur and nxt <= sell < cur:
                            pos, seg = dict(d=-1, e=sell), [sell] + pts[k:]; break
                        cur = nxt
                if pos is None:
                    continue
                pos.update(t=t, sl=rt(pos["e"] - pos["d"] * stop_pts), tp=rt(pos["e"] + pos["d"] * tgt_pts), be=False)
                start = pos["e"]
            else:
                seg, start = path(b.open, b.high, b.low, b.close), b.open
            # walk the rest of the bar with the bracket in place
            out = None
            d_ = pos["d"]
            if (start <= pos["sl"]) if d_ == 1 else (start >= pos["sl"]):
                out = ("stop", start)
            elif (start >= pos["tp"]) if d_ == 1 else (start <= pos["tp"]):
                out = ("target", start)
            cur = start
            for nxt in seg[1:]:
                if out:
                    break
                lo_, hi_ = min(cur, nxt), max(cur, nxt)
                hits = [(n, x) for n, x in (("stop", pos["sl"]), ("target", pos["tp"])) if lo_ <= x <= hi_ and x != cur]
                if hits:
                    out = min(hits, key=lambda z: abs(z[1] - cur))
                cur = nxt
            if out is None and p.be_at_r > 0 and not pos["be"]:
                fav = (b.high - pos["e"]) if d_ == 1 else (pos["e"] - b.low)
                if fav >= p.be_at_r * stop_pts:
                    pos["sl"], pos["be"] = pos["e"], True
            if out is None and m + 5 >= p.flat_at:
                out = ("15:55", b.close)
            if out:
                pnl = (out[1] - pos["e"]) * d_ * PT_USD * qty
                eq += pnl
                hwm = max(hwm, eq)
                trades.append(dict(date=day, entry_time=pos["t"], side="LONG" if d_ == 1 else "SHORT", qty=qty, range=rng,
                                   entry=pos["e"], exit=out[0], exit_price=out[1], pnl=pnl, r=pnl / (stop_pts * PT_USD * qty)))
                break
    return pd.DataFrame(trades)


def lucid(tr: pd.DataFrame, target=3000.0, dd=2000.0):
    """Start a fresh 50K eval on every trading day; EOD trailing drawdown from the highest close. → (passed, failed, open)."""
    days = sorted(tr.date.unique())
    daily = tr.groupby("date").pnl.sum()
    res = []
    for s in days:
        bal = peak = 0.0
        outcome = "open"
        for d in [x for x in days if x >= s]:
            bal += daily.get(d, 0.0)
            if bal <= peak - dd:
                outcome = "fail"; break
            if bal >= target:
                outcome = "pass"; break
            peak = max(peak, bal)
        res.append(outcome)
    return pd.Series(res).value_counts().to_dict()


def report(tr: pd.DataFrame, name=""):
    if tr.empty:
        return print(name, "no trades")
    w, l = tr[tr.pnl > 0], tr[tr.pnl <= 0]
    cum = tr.pnl.cumsum()
    dd = (cum - cum.cummax().clip(lower=0)).min()
    s = m = 0
    for x in tr.pnl:
        s = s + 1 if x > 0 else 0
        m = max(m, s)
    best_day = tr.groupby("date").pnl.sum().max()
    print(f"{name:28} n {len(tr):3}  win {100 * len(w) / len(tr):4.1f}%  net ${tr.pnl.sum():8.0f}  avgW ${w.pnl.mean():5.0f}  "
          f"avgL ${-l.pnl.mean():5.0f}  RR {w.pnl.mean() / -l.pnl.mean():4.2f}  maxDD ${dd:6.0f}  winStreak {m}  "
          f"bestDay {100 * best_day / max(tr.pnl.sum(), 1):4.0f}% of net  lucid {lucid(tr)}")


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from sp_v8 import load
    df = load(sys.argv[1] if len(sys.argv) > 1 else None)
    report(run(df), "default 0.75/1.5")
