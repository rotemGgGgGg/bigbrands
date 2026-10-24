"""Clock-aligned NQ bars with volume from the user's Databento NQ 1-minute file (front month by volume), 2010-06 → 2026-07.
24 h stream (trading day 18:00 → 16:59 NY). Each bar carries: trading-day id, NY minute of day of its start, roll flag
(front-month symbol changed on this bar → indicators/positions must not bridge it)."""
import os
import numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
OUT = SP + "s50_bars/"


def build(tf):
    p = f"{OUT}NQ_{tf}.pkl"
    if os.path.exists(p): return pd.read_pickle(p)
    f = pd.read_pickle(SP + "nq16.pkl"); f = f[f.index.notna()]
    m = (f.index.hour * 60 + f.index.minute).values
    day = (f.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    s18 = (m - 1080) % 1440; keep = (s18 < 1380) & (day.weekday < 5)
    f = f[keep]; day = day[keep]; s18 = s18[keep]
    code = day.values.astype("datetime64[D]").astype(np.int64) * 10000 + s18 // tf
    st = np.r_[0, np.flatnonzero(np.diff(code)) + 1]; en = np.r_[st[1:] - 1, len(f) - 1]
    B = pd.DataFrame(dict(o=f.open.values[st], h=np.maximum.reduceat(f.high.values, st), l=np.minimum.reduceat(f.low.values, st),
                          c=f.close.values[en], v=np.add.reduceat(f.volume.values.astype(float), st),
                          sym=f.symbol.values[en], day=day.values[st], mod=(s18[st] // tf * tf + 1080) % 1440))
    B["roll"] = np.r_[False, B.sym.values[1:] != B.sym.values[:-1]]
    os.makedirs(OUT, exist_ok=True); B.to_pickle(p); return B


if __name__ == "__main__":
    for tf in (5, 15, 60):
        B = build(tf); print(tf, len(B), B.day.iloc[0], B.day.iloc[-1], "rolls", B.roll.sum())
