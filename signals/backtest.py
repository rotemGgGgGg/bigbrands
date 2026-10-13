"""Every signal from the channel export, against real spot gold, at the
minute it was sent.

The export carries each message's exact timestamp, which removes the guess
the earlier replay had to make. What remains is how the order is filled, and
that is reported two ways rather than one:

  * BOT — what this bot actually does: a market order the moment the message
    arrives, with his stop and target as absolute prices. Whatever gold is
    doing that minute is the fill, not the number in his message.
  * HIS PRICE — a fill at exactly his stated entry, if price reaches it
    within an hour. The most generous reading of the signal.

A buy stop or sell stop only fills when price breaks through the level, and
is treated as such in both.

His own results posts are read too, and the totals he published for each
day are set beside what his signals produced on that same day, so the two
can be compared like for like.

    python3 signals/backtest.py export.txt
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

from parse import parse

PIP = 0.10
FILL_WAIT_MIN = 60
HOLD_DAYS = 3


def env_key() -> str:
    for line in open("/home/user/bigbrands/signals/.env", encoding="utf-8"):
        if line.startswith("TWELVEDATA_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no TWELVEDATA_KEY")


_cache: dict[str, list] = {}
_last_call = [0.0]


def bars_from(day: str, key: str) -> list[tuple[int, float, float, float]]:
    """One-minute spot bars from the start of `day` for HOLD_DAYS, in UTC.

    The free tier allows eight calls a minute, so calls are spaced and every
    window is cached: signals on the same day share one download.
    """
    if day in _cache:
        return _cache[day]
    wait = 8.0 - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    end = (dt.date.fromisoformat(day) + dt.timedelta(days=HOLD_DAYS)).isoformat()
    params = urllib.parse.urlencode({
        "symbol": "XAU/USD", "interval": "1min", "timezone": "UTC",
        "start_date": f"{day} 00:00:00", "end_date": f"{end} 00:00:00",
        "apikey": key, "order": "asc", "outputsize": 5000})
    req = urllib.request.Request(f"https://api.twelvedata.com/time_series?{params}",
                                 headers={"User-Agent": "radar"})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.load(r)
    _last_call[0] = time.time()
    if data.get("status") == "error":
        raise RuntimeError(data.get("message"))
    out = []
    for v in data["values"]:
        t = dt.datetime.fromisoformat(v["datetime"]).replace(tzinfo=dt.timezone.utc)
        out.append((int(t.timestamp()), float(v["open"]), float(v["high"]), float(v["low"])))
    _cache[day] = out
    return out


def first_level(bars, i, side, target, stop):
    """Which of target or stop is touched first from bar i on."""
    for j in range(i, len(bars)):
        _, _, high, low = bars[j]
        if side == "buy":
            t, s = high >= target, low <= stop
        else:
            t, s = low <= target, high >= stop
        if t and s:
            return "ambiguous", j
        if t:
            return "win", j
        if s:
            return "loss", j
    return "open", None


def find_fill(bars, start, sig, mode):
    """Index and price of the fill, or (None, reason)."""
    if mode == "bot" and sig.order == "market":
        return start, bars[start][1]               # the next minute's open
    limit = start + FILL_WAIT_MIN
    for j in range(start, min(limit, len(bars))):
        _, _, high, low = bars[j]
        prev_high = bars[j - 1][2] if j else high
        prev_low = bars[j - 1][3] if j else low
        if sig.order == "stop":
            broke = (sig.side == "buy" and high >= sig.entry > prev_high) or \
                    (sig.side == "sell" and low <= sig.entry < prev_low)
            if broke:
                return j, sig.entry
        elif low <= sig.entry <= high:
            return j, sig.entry
    return None, "entry not reached within an hour"


def pips_for(side, entry, exit_price):
    move = exit_price - entry if side == "buy" else entry - exit_price
    return move / PIP


def main(path: str) -> None:
    key = env_key()
    rows = []
    for line in open(path, encoding="utf-8-sig"):
        line = line.strip()
        if "|" not in line:
            continue
        ts, text = line.split("|", 1)
        rows.append((int(ts), text.replace(" / ", "\n")))

    signals = [(ts, parse(t), t) for ts, t in rows if "Stop Loss" in t]
    results = [(ts, t) for ts, t in rows if "PIPS" in t.upper() and "Stop Loss" not in t]
    print(f"{len(signals)} signals, {len(results)} results posts\n")

    per_day = defaultdict(lambda: {"bot": 0.0, "his": 0.0, "n": 0})
    tally = {"bot": defaultdict(int), "his": defaultdict(int)}
    refused = 0

    for ts, sig, raw in signals:
        if not sig.tradeable:
            refused += 1
            print(f"  REFUSED {dt.datetime.utcfromtimestamp(ts):%m-%d %H:%M}  {'; '.join(sig.problems)}")
            continue
        day = dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        try:
            bars = bars_from(day, key)
        except Exception as e:
            print(f"  NO DATA {day}: {e}")
            continue
        start = next((i for i, b in enumerate(bars) if b[0] >= ts - ts % 60 + 60), None)
        if start is None:
            continue
        line = f"  {dt.datetime.utcfromtimestamp(ts):%m-%d %H:%M}Z {sig.side.upper():<4}{sig.order:<7}"
        per_day[day]["n"] += 1
        for mode in ("bot", "his"):
            i, px = find_fill(bars, start, sig, mode)
            if i is None:
                tally[mode]["unfilled"] += 1
                line += f" | {mode}: unfilled"
                continue
            out, j = first_level(bars, i, sig.side, sig.targets[0], sig.stop)
            tally[mode][out] += 1
            if out == "win":
                p = pips_for(sig.side, px, sig.targets[0])
            elif out == "loss":
                p = pips_for(sig.side, px, sig.stop)
            else:
                p = 0.0
            per_day[day][mode] += p
            line += f" | {mode}: {out} {p:+.0f}"
        print(line)

    print(f"\n{refused} refused by the parser\n")
    for mode, label in (("bot", "BOT (market order on arrival)"),
                        ("his", "HIS PRICE (fill at his exact entry)")):
        t = tally[mode]
        settled = t["win"] + t["loss"]
        rate = 100 * t["win"] / settled if settled else 0
        print(f"{label}")
        print(f"  win {t['win']}  loss {t['loss']}  ambiguous {t['ambiguous']}  "
              f"open {t['open']}  unfilled {t['unfilled']}   win rate {rate:.1f}%")
        total = sum(d[mode] for d in per_day.values())
        print(f"  total {total:+.0f} pips\n")

    claimed = {}
    for ts, text in results:
        day = dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        nums = [int(n.replace("+", "")) for n in re.findall(r"([+-]\d+)\s*PIPS", text, re.I)]
        if "TOTAL" in text.upper() and "TODAY" in text.upper() and nums:
            claimed[day] = nums[-1]
    if claimed:
        print("his published day totals vs his own signals that day (bot / his price):")
        for day in sorted(claimed):
            d = per_day.get(day)
            got = f"{d['bot']:+.0f} / {d['his']:+.0f}  from {d['n']} signals" if d else "no signals in the export that day"
            print(f"  {day}  he says {claimed[day]:+d}   measured {got}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
