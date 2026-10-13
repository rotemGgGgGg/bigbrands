"""Gold prices by the minute, from whatever is reachable without an account.

Two sources, because the better one needs a key and the other needs nothing:

  * Twelve Data gives spot XAU/USD, which is what the sender quotes. Used
    when TWELVEDATA_KEY is set.
  * Yahoo gives the front gold future, GC=F, with no key at all. It trades at
    a premium to spot that moves slowly, so its LEVELS are wrong for this
    purpose while its MOVEMENT is very close. Used as a fallback, and the
    caller is told which it got, because a thirteen dollar stop is smaller
    than the premium and nothing here should quietly pretend otherwise.

Both return the same thing: one row per minute with a high and a low, which
is all that is needed to ask whether a level was touched.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass

UA = {"User-Agent": "Mozilla/5.0"}


@dataclass
class Bar:
    ts: int          # unix seconds, start of the minute
    high: float
    low: float


@dataclass
class Series:
    bars: list[Bar]
    source: str      # "spot" or "futures"
    symbol: str

    @property
    def is_spot(self) -> bool:
        return self.source == "spot"


def _get(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def from_twelvedata(key: str, minutes: int = 390) -> Series:
    params = urllib.parse.urlencode({
        "symbol": "XAU/USD", "interval": "1min",
        "outputsize": min(minutes, 5000), "apikey": key, "order": "asc",
    })
    data = _get(f"https://api.twelvedata.com/time_series?{params}")
    if data.get("status") == "error":
        raise RuntimeError(f"twelvedata: {data.get('message', 'unknown error')}")
    import datetime
    bars = []
    for row in data.get("values", []):
        # Twelve Data timestamps are exchange-local without an offset, which
        # is fine here: only ordering and spacing are used, never the clock.
        dt = datetime.datetime.fromisoformat(row["datetime"])
        bars.append(Bar(int(dt.replace(tzinfo=datetime.timezone.utc).timestamp()),
                        float(row["high"]), float(row["low"])))
    return Series(bars, "spot", "XAU/USD")


def from_yahoo(range_: str = "1d", interval: str = "1m") -> Series:
    # Yahoo refuses one-minute bars beyond a week, so a longer reach has to
    # trade resolution for it: two minutes back to early September, five back
    # to August. A coarser bar makes an ambiguous outcome more likely, never
    # a wrong one, because the ambiguity is reported rather than resolved.
    data = _get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F"
                f"?interval={interval}&range={range_}")
    result = (data.get("chart") or {}).get("result")
    if not result:
        raise RuntimeError(f"yahoo: {(data.get('chart') or {}).get('error')}")
    result = result[0]
    stamps = result.get("timestamp") or []
    quote = result["indicators"]["quote"][0]
    bars = [Bar(t, h, l) for t, h, l in
            zip(stamps, quote["high"], quote["low"]) if h is not None and l is not None]
    return Series(bars, "futures", f"GC=F {interval}")


def load(minutes: int = 390) -> Series:
    key = os.environ.get("TWELVEDATA_KEY", "").strip()
    if key:
        return from_twelvedata(key, minutes)
    return from_yahoo()
