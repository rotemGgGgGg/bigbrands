"""Replay check: run strategy.evaluate on historical MNQ 1-minute data (as the bot would at 09:45) and compare side / level /
score / skip-reason with the research trade list (research/gapfb/trades_compare.csv). Needs the research pickle (scratchpad)."""
import sys
from datetime import timezone
import pandas as pd
from strategy import Candle, evaluate, NY
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/full1m.pkl"
f = pd.read_pickle(SP); f = f[~f.index.duplicated()]
R = pd.read_csv("../research/gapfb/trades_compare.csv", parse_dates=["date"]).set_index("date")
ok = bad = 0
days = sorted(set(f.index.normalize().tz_localize(None)) & set(R.index))
for d in days:
    end = pd.Timestamp(d).tz_localize(NY) + pd.Timedelta(hours=9, minutes=44)
    win = f.loc[end - pd.Timedelta(days=4):end]
    cs = [Candle(t.to_pydatetime().astimezone(timezone.utc), r.open, r.high, r.low, r.close) for t, r in win.iterrows()]
    sig, why = evaluate(cs, d.date())
    r = R.loc[d]
    exp_trade = r.result != "skipped (score<2)"
    got = sig is not None
    same = (got == exp_trade) and (not got or (sig.side == (1 if r.side == "LONG" else -1) and abs(sig.level - r.order_level) < 0.01))
    ok += same; bad += not same
    if not same and bad <= 10:
        print(d.date(), "research:", r.result, r.side, r.order_level, "score", r.score, "| bot:", why if sig is None else (sig.side, sig.level, sig.score))
print(f"days compared {ok + bad}: match {ok}, mismatch {bad}")
