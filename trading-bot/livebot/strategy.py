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


# ---------------------------------------------------------------- Pre-Open Fade and Opex short (STRATEGY_NQ.md §2, §3)
# Both use 30-minute candles (bar open time): 08:00 and 08:30 bars give the 08:00→08:59 move, 09:30 and 15:30 bars give
# the RTH open→close used for σ.

@dataclass
class MarketOrder:
    name: str            # "prefade" / "opex"
    side: int
    stop_distance: float
    target_distance: float
    exit_hhmm: tuple[int, int]
    info: str


def _bars_by_day(c30: list[Candle]) -> dict[date, dict[int, Candle]]:
    out: dict[date, dict[int, Candle]] = {}
    for c in c30:
        out.setdefault(c.t.astimezone(NY).date(), {})[_ny_minute(c)] = c
    return out


def prefade(c30: list[Candle], today: date, z_min: float = 2.0) -> tuple[MarketOrder | None, str]:
    days = _bars_by_day(c30)
    moves = []
    for d in sorted(days):
        b = days[d]
        if 480 in b and 510 in b:
            moves.append((d, b[480].o, b[510].c))
    if not moves or moves[-1][0] != today:
        return None, "no 08:00–08:59 bars today"
    hist = [c / o - 1 for d, o, c in moves[:-1]][-20:]
    if len(hist) < 20:
        return None, "less than 20 days of history"
    mean = sum(hist) / len(hist); sd = (sum((x - mean) ** 2 for x in hist) / (len(hist) - 1)) ** 0.5
    _, o8, c859 = moves[-1]; ret = c859 / o8 - 1
    z = ret / sd if sd > 0 else 0.0
    if abs(z) <= z_min:
        return None, f"pre-open move z {z:+.2f} (needs |z| > {z_min})"
    size = abs(c859 - o8)
    return MarketOrder("prefade", -1 if ret > 0 else 1, size, 0.5 * size, (13, 0),
                       f"move {c859 - o8:+.2f} pts z {z:+.2f}"), "armed"


def is_opex(d: date) -> bool:
    return d.weekday() == 4 and 15 <= d.day <= 21


def opex(c30: list[Candle], today: date, k: float = 0.4, rr: float = 2.0) -> tuple[MarketOrder | None, str]:
    if not is_opex(today):
        return None, "not the monthly opex Friday"
    days = _bars_by_day(c30)
    hist = [abs(b[930].c / b[570].o - 1) for d, b in sorted(days.items()) if d < today and 570 in b and 930 in b][-14:]
    if len(hist) < 14:
        return None, "less than 14 days of history"
    last_close = c30[-1].c
    sigma_pts = sum(hist) / 14 * last_close
    return MarketOrder("opex", -1, k * sigma_pts, rr * k * sigma_pts, (15, 55), f"σ {sigma_pts:.1f} pts"), "armed"
