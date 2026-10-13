"""Replaying the sender's real signals against real gold minutes.

The messages carry a date but not a time of day, so the entry moment has to
be found rather than read: the first minute the price actually traded at the
stated entry is taken as the fill, and the trade is resolved from there. That
is generous to the sender — it assumes a perfect fill at his exact number,
which is the best case rather than the likely one.

What is being tested is not whether he is a good trader. It is whether
following his messages mechanically, which is what a bot would do, produces
the results he publishes. Those are different questions, and only the second
one matters before any money is attached.

    python3 signals/replay.py
"""
from __future__ import annotations

import datetime as dt

from paper import resolve
from prices import from_yahoo, Series

# Transcribed from the channel. Dates are as posted; the times are unknown.
SIGNALS = [
    # date,       side,   entry,    target,   stop,     label
    ("2026-10-07", "buy", 4084.84, 4118.99, 4071.36, "[5m]"),
    ("2026-10-07", "sell", 4112.68, 4088.53, 4121.13, "[3m]"),
    ("2026-10-02", "buy", 4182.96, 4225.44, 4175.49, "[1m] buy stop"),
]

# What he published, for comparison. Gold convention: 1 pip = $0.10.
PIP = 0.10
CLAIMS = {
    "2026-10-12": [120, 140, -29, 110],
    "2026-10-08": [60, 70, 70, 140],
}


def day_bars(series: Series, day: str) -> list:
    start = dt.datetime.fromisoformat(day).replace(tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    lo, hi = int(start.timestamp()), int(end.timestamp())
    return [b for b in series.bars if lo <= b.ts < hi]


def main() -> None:
    # 2-minute bars reach back to early September, which covers every signal
    # here; one-minute only reaches a week.
    series = from_yahoo(range_="60d", interval="2m")
    print(f"{series.symbol} ({series.source}): {len(series.bars)} bars, "
          f"{dt.datetime.utcfromtimestamp(series.bars[0].ts):%Y-%m-%d} onward\n")

    print("=== his published numbers, converted to dollars ===")
    for day, pips in CLAIMS.items():
        moves = [p * PIP for p in pips]
        print(f"  {day}: " + ", ".join(f"{m:+.2f}$" for m in moves)
              + f"   (total {sum(moves):+.2f}$)")
    print("  his stops are $7.47-$13.48 away; his targets $24.15-$42.48")
    print("  so neither his wins nor his losses are his own levels being hit\n")

    print("=== his signals, replayed ===")
    for day, side, entry, target, stop, label in SIGNALS:
        bars = day_bars(series, day)
        if not bars:
            print(f"  {day} {side:<4} -> no price data for that day")
            continue
        lo = min(b.low for b in bars)
        hi = max(b.high for b in bars)

        # Find the first bar whose range contains his entry: the fill.
        fill = next((b for b in bars if b.low <= entry <= b.high), None)
        if fill is None:
            print(f"  {day} {side:<4} entry {entry} -> NEVER TRADED. "
                  f"that day ranged {lo:.2f}-{hi:.2f}")
            continue

        window = Series([b for b in series.bars if b.ts >= fill.ts],
                        series.source, series.symbol)
        r = resolve(side, entry, stop, target, fill.ts, window)
        risk = abs(entry - stop)
        reward = abs(target - entry)
        when = dt.datetime.utcfromtimestamp(fill.ts).strftime("%H:%M")
        print(f"  {day} {side:<4} entry {entry} filled {when}Z  "
              f"risk ${risk:.2f} reward ${reward:.2f} (R:R {reward / risk:.2f})")
        took = f"after {r.minutes} min" if r.minutes is not None else ""
        print(f"        -> {r.outcome.upper()} {took} {r.note}")


if __name__ == "__main__":
    main()
