"""Replaying his signals on real spot gold, every way they could have filled.

The messages carry a date but no time, so there is no single fill to test.
What there is instead is every minute that day when gold actually traded at
his entry — and the honest thing is to resolve all of them and show the
spread, rather than pick one and call it the answer.

If every fill loses, the conclusion holds whichever minute he sent it. If
some win and some lose, that is the real finding: the signal's outcome
depended on timing he did not publish, which is exactly what a bot cannot
reproduce.

A buy stop is treated as what it is — an order above the market, filled when
price breaks up through the level — not as a limit waiting below.

    python3 signals/spot_replay.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse
import urllib.request

PIP = 0.10

SIGNALS = [
    # date,        kind,       entry,    target,  stop
    ("2026-10-07", "buy",      4084.84, 4118.99, 4071.36),
    ("2026-10-07", "sell",     4112.68, 4088.53, 4121.13),
    ("2026-10-02", "buy stop", 4182.96, 4225.44, 4175.49),
]


def bars_for(day: str, key: str, days_after: int = 2) -> list[tuple[str, float, float]]:
    """The signal's own day, plus the days after it.

    A trade filled near midnight is not unresolved, it is unfinished, and
    cutting the window at midnight would report the truncation as a result.
    """
    end = (dt.date.fromisoformat(day)
           + dt.timedelta(days=days_after)).isoformat()
    params = urllib.parse.urlencode({
        "symbol": "XAU/USD", "interval": "1min",
        "start_date": f"{day} 00:00:00", "end_date": f"{end} 23:59:00",
        "apikey": key, "order": "asc", "outputsize": 5000,
    })
    req = urllib.request.Request(
        f"https://api.twelvedata.com/time_series?{params}",
        headers={"User-Agent": "radar"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("status") == "error":
        raise RuntimeError(data.get("message"))
    return [(v["datetime"], float(v["high"]), float(v["low"]))
            for v in data["values"]]


def resolve_from(i: int, bars: list, side: str, target: float, stop: float):
    """First level touched, walking forward from bar i."""
    for j in range(i, len(bars)):
        _, high, low = bars[j]
        if side == "buy":
            hit_t, hit_s = high >= target, low <= stop
        else:
            hit_t, hit_s = low <= target, high >= stop
        if hit_t and hit_s:
            return "ambiguous", j - i
        if hit_t:
            return "win", j - i
        if hit_s:
            return "loss", j - i
    return "unresolved", None


def main() -> None:
    key = ""
    for line in open("signals/.env", encoding="utf-8"):
        if line.startswith("TWELVEDATA_KEY="):
            key = line.split("=", 1)[1].strip()
    if not key:
        raise SystemExit("no TWELVEDATA_KEY in signals/.env")

    cache: dict[str, list] = {}
    for day, kind, entry, target, stop in SIGNALS:
        if day not in cache:
            cache[day] = bars_for(day, key)
        bars = cache[day]
        side = "sell" if kind == "sell" else "buy"
        risk, reward = abs(entry - stop), abs(target - entry)

        print(f"\n{day}  {kind.upper():<9} entry {entry}  "
              f"TP {target} ({reward / PIP:.0f} pips)  "
              f"SL {stop} ({risk / PIP:.0f} pips)  R:R {reward / risk:.2f}")

        # Every minute the level was actually reachable.
        # Fills are only looked for on the signal's own day; the days after
        # it exist so the trade can finish, not so it can be entered later.
        own_day = [i for i, b in enumerate(bars) if b[0].startswith(day)]
        last_own = own_day[-1] if own_day else len(bars) - 1

        if kind == "buy stop":
            # Filled on a break upward: the previous bar was below the level.
            fills = [i for i in range(1, last_own + 1)
                     if bars[i][1] >= entry > bars[i - 1][1]]
        else:
            fills = [i for i, (_, h, l) in enumerate(bars[:last_own + 1])
                     if l <= entry <= h]

        if not fills:
            lo = min(b[2] for b in bars)
            hi = max(b[1] for b in bars)
            print(f"   never filled; spot ranged {lo:.2f}-{hi:.2f} that day")
            continue

        outcomes = {}
        for i in fills:
            out, mins = resolve_from(i, bars, side, target, stop)
            outcomes.setdefault(out, []).append((bars[i][0][11:16], mins))

        print(f"   {len(fills)} possible fill minutes that day:")
        for out in ("win", "loss", "ambiguous", "unresolved"):
            if out not in outcomes:
                continue
            times = outcomes[out]
            first = ", ".join(t for t, _ in times[:6])
            more = f" (+{len(times) - 6} more)" if len(times) > 6 else ""
            print(f"     {out.upper():<11} {len(times):>4} of {len(fills)}   at {first}{more}")
        wins = len(outcomes.get("win", []))
        losses = len(outcomes.get("loss", []))
        if wins and losses:
            print(f"   -> depended on the minute: {wins} win, {losses} lose. "
                  f"the timing he did not publish decided it.")
        elif wins:
            print(f"   -> won from every fill. the signal stood on its own.")
        elif losses:
            print(f"   -> lost from every fill. no timing would have saved it.")


if __name__ == "__main__":
    main()
