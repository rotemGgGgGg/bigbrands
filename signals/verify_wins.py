"""Did the wins he showcases actually happen?

The free channel reposts signals from the paid one after they have already
paid out: each signal arrives in the same second as its "TP SMASHED" post.
That makes these messages useless for a win rate — only winners are
reposted — but it makes them a clean test of something else: whether the
wins are real.

For each one, the day before the post is searched for a moment when price
reached his entry, and from each such moment it is checked whether his
target was reached before his stop, and before the post went up. If one
exists, the win happened as described. If none does, it did not.

    python3 signals/verify_wins.py signals.txt
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request

LOOKBACK_H = 24


def key() -> str:
    for line in open("/home/user/bigbrands/signals/.env", encoding="utf-8"):
        if line.startswith("TWELVEDATA_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no key")


_last = [0.0]


def bars(start: dt.datetime, end: dt.datetime, k: str):
    wait = 8.0 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    p = urllib.parse.urlencode({
        "symbol": "XAU/USD", "interval": "1min", "timezone": "UTC",
        "start_date": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_date": end.strftime("%Y-%m-%d %H:%M:%S"),
        "apikey": k, "order": "asc", "outputsize": 5000})
    req = urllib.request.Request(f"https://api.twelvedata.com/time_series?{p}",
                                 headers={"User-Agent": "radar"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    _last[0] = time.time()
    if d.get("status") == "error":
        raise RuntimeError(d.get("message"))
    return [(dt.datetime.fromisoformat(v["datetime"]), float(v["high"]), float(v["low"]))
            for v in d["values"]]


def check(series, side, order, entry, tp, sl):
    """First fill that reaches the target before the stop, or why not."""
    fills = 0
    for i in range(1, len(series)):
        _, h, l = series[i]
        _, ph, pl = series[i - 1]
        if order == "stop":
            hit = (side == "buy" and h >= entry > ph) or (side == "sell" and l <= entry < pl)
        else:
            hit = l <= entry <= h
        if not hit:
            continue
        fills += 1
        for j in range(i, len(series)):
            _, hh, ll = series[j]
            t = hh >= tp if side == "buy" else ll <= tp
            s = ll <= sl if side == "buy" else hh >= sl
            if t and s:
                break                      # both in one minute: not proof either way
            if t:
                return "REAL", series[i][0], series[j][0]
            if s:
                break
    return ("NO FILL" if fills == 0 else "NOT FOUND"), None, None


def main(path: str) -> None:
    k = key()
    tally = {}
    for line in open(path, encoding="utf-8"):
        ts, kind, entry, tp, sl, claimed = line.strip().split("|")
        posted = dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).replace(tzinfo=None)
        side = "sell" if kind.startswith("sell") else "buy"
        order = "stop" if "stop" in kind else "market"
        entry, tp, sl = float(entry), float(tp), float(sl)
        try:
            s = bars(posted - dt.timedelta(hours=LOOKBACK_H), posted, k)
        except Exception as e:
            print(f"{posted:%m-%d %H:%M}  data error: {e}")
            continue
        verdict, filled, hit = check(s, side, order, entry, tp, sl)
        tally[verdict] = tally.get(verdict, 0) + 1
        extra = ""
        if verdict == "REAL":
            extra = (f"filled {filled:%H:%M}, TP {hit:%H:%M}, "
                     f"posted {(posted - hit).total_seconds() / 60:.0f} min after TP")
        print(f"{posted:%m-%d %H:%M}  {kind:<9} {entry:<9} claims +{claimed:<4} -> {verdict:<9} {extra}")
    print("\n" + "  ".join(f"{k}: {v}" for k, v in tally.items()))


if __name__ == "__main__":
    main(sys.argv[1])
