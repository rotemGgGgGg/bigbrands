"""GapFB-NQ signal logic, broker-independent (rules: trading-bot/STRATEGY_NQ.md §1, research: research/gapfb).

Input: 1-minute candles (time in UTC, o/h/l/c) covering at least the previous RTH session and today 09:30–09:44 New York.
Output at 09:45 NY: either None (no trade today, with the reason) or a Signal with side, stop-entry level, ATR and the
quality score."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
GAP_MIN = 0.003          # |gap| ≥ 0.3 %
MIN_SCORE = 2            # quality score ≥ 2 of 3
SL_ATR = 2.0             # initial stop = 2 × ATR
TRAIL_ATR = 5.0          # trailing stop = 5 × ATR from the best price


@dataclass
class Candle:
    t: datetime          # bar open, timezone-aware
    o: float
    h: float
    l: float
    c: float


@dataclass
class Signal:
    day: date
    side: int            # +1 long (buy stop at OR high), −1 short (sell stop at OR low)
    level: float         # stop-entry price
    atr: float
    gap: float
    score: int
    or_high: float
    or_low: float

    @property
    def stop_distance(self) -> float:
        return SL_ATR * self.atr

    @property
    def trail_distance(self) -> float:
        return TRAIL_ATR * self.atr


def _ny_minute(c: Candle) -> int:
    t = c.t.astimezone(NY)
    return t.hour * 60 + t.minute


def evaluate(candles: list[Candle], today: date) -> tuple[Signal | None, str]:
    """Decide today's GapFB trade. `candles` sorted by time, complete bars only, up to and including 09:44 NY."""
    by_day: dict[date, list[Candle]] = {}
    for c in candles:
        by_day.setdefault(c.t.astimezone(NY).date(), []).append(c)
    rth = lambda d: [c for c in by_day.get(d, []) if 570 <= _ny_minute(c) < 960]
    today_rth = rth(today)
    or_bars = [c for c in today_rth if _ny_minute(c) < 585]
    if not or_bars or _ny_minute(or_bars[0]) != 570:
        return None, "no 09:30 bar today (holiday / data gap)"
    if len(or_bars) < 13:
        return None, f"opening range incomplete ({len(or_bars)} of 15 bars)"
    prev_days = sorted(d for d in by_day if d < today and rth(d))
    if not prev_days:
        return None, "no previous RTH session in the data"
    y = rth(prev_days[-1])
    y_close_bar = [c for c in y if _ny_minute(c) == 959] or [y[-1]]
    y_open, y_close = y[0].o, y_close_bar[0].c
    y_high, y_low = max(c.h for c in y), min(c.l for c in y)

    d_open = or_bars[0].o
    gap = d_open / y_close - 1
    if abs(gap) < GAP_MIN:
        return None, f"gap {gap * 100:+.2f}% below {GAP_MIN * 100:.1f}%"
    s = 1 if gap > 0 else -1
    or_high, or_low = max(c.h for c in or_bars), min(c.l for c in or_bars)
    close_944 = or_bars[-1].c
    score = int(s * (y_close - y_open) <= 0) \
        + int((s == 1 and d_open > y_high) or (s == -1 and d_open < y_low)) \
        + int(s * (close_944 - d_open) > 0)
    if score < MIN_SCORE:
        return None, f"quality score {score} < {MIN_SCORE}"

    # ATR(14): simple mean of the true range of the last 14 closed 1-minute bars (as researched)
    last = candles[-15:]
    if len(last) < 15:
        return None, "not enough bars for ATR"
    trs = [max(b.h - b.l, abs(b.h - a.c), abs(b.l - a.c)) for a, b in zip(last[:-1], last[1:])]
    atr = sum(trs) / len(trs)
    if atr <= 0:
        return None, "ATR is zero"
    level = or_high if s == 1 else or_low
    return Signal(today, s, level, atr, gap, score, or_high, or_low), "armed"
