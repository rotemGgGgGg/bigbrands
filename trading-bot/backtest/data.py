"""Load intraday bars from a local file and turn them into 5-minute bars in New York time.

Supported files (detected automatically):
  * NinjaTrader 8 minute export (.txt, no header):   20240102 093100;16850.25;16852;16849.5;16851.75;312
      NinjaTrader stamps each bar with its CLOSE time, in the time zone set in NinjaTrader
      (Tools → Options → General → Time zone). Pass that zone with --tz (default America/New_York).
  * TradingView "Export chart data" CSV: time,open,high,low,close,Volume  (time = bar OPEN, unix seconds or ISO)
  * Any CSV with a header: datetime (or date + time), open, high, low, close, volume  (bar OPEN time)

1-minute (or 2-, 3-minute) bars are combined into 5-minute bars: open of the first, highest high,
lowest low, close of the last, summed volume. Bars are aligned to :00, :05, :10 … NY time.
"""
from __future__ import annotations

import pandas as pd

TZ_NY = "America/New_York"


def _read_ninjatrader(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", header=None, names=["ts", "open", "high", "low", "close", "volume"],
                     dtype={"ts": str})
    df.index = pd.to_datetime(df.pop("ts"), format="%Y%m%d %H%M%S")
    return df


def _read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {c: c.strip().lower() for c in df.columns}
    df = df.rename(columns=cols)
    if "datetime" in df.columns:
        ts = df.pop("datetime")
    elif "time" in df.columns and "date" in df.columns:
        ts = df.pop("date").astype(str) + " " + df.pop("time").astype(str)
    elif "time" in df.columns:
        ts = df.pop("time")
    elif "date" in df.columns:
        ts = df.pop("date")
    else:
        ts = df.pop(df.columns[0])
    if pd.api.types.is_numeric_dtype(ts):
        idx = pd.to_datetime(ts, unit="s", utc=True)            # TradingView unix seconds
    else:
        idx = pd.to_datetime(ts, utc=False, format="mixed")
    df.index = pd.DatetimeIndex(idx)
    return df[["open", "high", "low", "close", "volume"]]


def detect_format(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        first = fh.readline()
    if ";" in first and first[:8].isdigit():
        return "ninjatrader"
    return "csv"


def load_file(path: str, tz: str = TZ_NY, stamp: str = "auto") -> pd.DataFrame:
    """Return 5-minute OHLCV bars indexed by bar OPEN time in New York time.

    tz:    time zone of naive timestamps in the file (ignored when the file carries offsets / UTC).
    stamp: "open" or "close" — which end of the bar the file's timestamp marks.
           "auto" = close for NinjaTrader exports, open for everything else.
    """
    fmt = detect_format(path)
    df = _read_ninjatrader(path) if fmt == "ninjatrader" else _read_csv(path)
    if stamp == "auto":
        stamp = "close" if fmt == "ninjatrader" else "open"
    df = df.apply(pd.to_numeric, errors="coerce").dropna(subset=["open", "high", "low", "close"])
    df["volume"] = df["volume"].fillna(0)
    idx = df.index
    idx = idx.tz_localize(tz, ambiguous="infer", nonexistent="shift_forward") if idx.tz is None else idx
    df.index = idx.tz_convert(TZ_NY)
    df = df[~df.index.duplicated(keep="last")].sort_index()

    step = df.index.to_series().diff().dropna()
    base = step[step > pd.Timedelta(0)].mode()
    bar = base.iloc[0] if len(base) else pd.Timedelta(minutes=5)
    if stamp == "close":
        df.index = df.index - bar                               # move to bar OPEN time
    if bar > pd.Timedelta(minutes=5) or pd.Timedelta(minutes=5) % bar != pd.Timedelta(0):
        raise ValueError(f"bars are {bar}; need 1, 2, 3 or 5-minute bars")
    if bar < pd.Timedelta(minutes=5):
        df = df.resample("5min", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna(subset=["open"])
    return df[["open", "high", "low", "close", "volume"]]
