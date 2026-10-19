"""End-to-end smoke test with a fake broker: runs every bot job on historical days and records the orders it would send."""
from datetime import timezone, date
import pandas as pd
import bot as B
from strategy import Candle, NY
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/full1m.pkl"
f = pd.read_pickle(SP); f = f[~f.index.duplicated()]["2026-07-01":]
m30 = f.resample("30min", label="left", closed="left").agg(dict(open="first", high="max", low="min", close="last")).dropna()
class Fake:
    instrument = "NAS100_USD"; calls = []; now = None
    def _c(self, df): return [Candle(t.to_pydatetime().astimezone(timezone.utc), r.open, r.high, r.low, r.close) for t, r in df[df.index < self.now].iterrows()]
    def candles_m1(self, n=5000): return self._c(f.tail(200000))[-n:]
    def candles(self, g, n=2000): return self._c(m30)[-n:]
    def balance(self): return 100000.0
    def spec(self): return {"minimumTradeSize": "0.1", "tradeUnitsPrecision": "1", "displayPrecision": "1"}
    def units_for_risk(self, r, s): return round(r / s, 1)
    def net_side(self): return 0
    def place_stop_entry(self, *a): self.calls.append(("STOP", a[:3]))
    def market_bracket(self, *a): self.calls.append(("MARKET", a[:3]))
    def close_tagged(self, t): return 0
    def cancel_pending(self): return 0
    def close_position(self): return None
    def closed_trades(self, n): return []
b = B.Bot.__new__(B.Bot); b.cfg = {"environment": "practice"}; b.dry = False; b.risk_pct = 1.0; b.enabled = {}; b.state = {}
b.br = Fake(); b.state_path = B.HERE / "state_test.json"
for d in pd.bdate_range("2026-07-13", "2026-07-24"):
    dd = d.date()
    for hh, mm, fn in ((9, 0, b.job_prefade), (9, 30, b.job_opex), (9, 45, b.job_gapfb)):
        b.br.now = pd.Timestamp(dd).tz_localize(NY) + pd.Timedelta(hours=hh, minutes=mm); fn(dd)
print("orders:", b.br.calls)
