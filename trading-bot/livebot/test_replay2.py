"""Replay check for Pre-Fade and Opex logic: M30 candles built from historical MNQ 1-minute data, evaluated day by day as the
bot would (data up to the decision time only), compared with the research signal days (research/gapfb/portfolio_edges.run)."""
import sys; sys.path[:0] = ["../research/gapfb", "../research", "../research/longhist"]
from datetime import timezone
import numpy as np, pandas as pd
from strategy import Candle, prefade, opex, NY, is_opex
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/full1m.pkl"
f = pd.read_pickle(SP); f = f[~f.index.duplicated()]["2025-06-01":]
m30 = f.resample("30min", label="left", closed="left").agg(dict(open="first", high="max", low="min", close="last")).dropna()
C = [Candle(t.to_pydatetime().astimezone(timezone.utc), r.open, r.high, r.low, r.close) for t, r in m30.iterrows()]
times = np.array([c.t for c in C])
from portfolio_edges import run, S
days, X = S["B"]; res = run(days, X)
pf_days = {d.date(): r for d, r in res["PF"] if d >= pd.Timestamp("2025-07-15")}
bot_pf = set(); bot_opex = set()
for d in sorted(set(m30.index.tz_convert(NY).date)):
    if pd.Timestamp(d) < pd.Timestamp("2025-07-15") or pd.Timestamp(d).weekday() >= 5: continue
    cut = pd.Timestamp(d).tz_localize(NY) + pd.Timedelta(hours=9)
    o, _ = prefade([c for c in C if c.t < cut], d)
    if o: bot_pf.add(d)
    cut2 = pd.Timestamp(d).tz_localize(NY) + pd.Timedelta(hours=9, minutes=30)
    o2, _ = opex([c for c in C if c.t < cut2], d)
    if o2: bot_opex.add(d)
rs = set(pf_days)
print(f"Pre-Fade days: research {len(rs)}, bot {len(bot_pf)}, both {len(rs & bot_pf)} | only research {sorted(rs - bot_pf)} | only bot {sorted(bot_pf - rs)}")
print(f"Opex days (bot): {sorted(bot_opex)}")
