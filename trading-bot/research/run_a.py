import pickle, sys, time, json
import numpy as np, pandas as pd
from engine import Data, summarize, S
import strategies_a as A

try:
    D = pickle.load(open(S + "D.pkl", "rb"))
except Exception:
    D = Data(); pickle.dump(D, open(S + "D.pkl", "wb"))
print(len(D.days), "RTH days", D.days[0], "→", D.days[-1], flush=True)
full = D.full
# 1-min Wilder ATR(14) on the full 24h series (for #11)
tr_ = pd.concat([full.high - full.low, (full.high - full.close.shift()).abs(), (full.low - full.close.shift()).abs()], axis=1).max(axis=1)
atr1 = tr_.ewm(alpha=1 / 14, adjust=False).mean()

tests = [
    ("01 Noise-Area (VWAP entry+trail, code)", lambda: A.noise_area(D, True, True)),
    ("01 Noise-Area (band only, paper base)", lambda: A.noise_area(D, False, False)),
    ("01 Noise-Area (band entry, VWAP trail)", lambda: A.noise_area(D, False, True)),
    ("02 5m ORB first candle 10R", lambda: A.orb5_first_candle(D)),
    ("03 Last-30min rROD", lambda: A.last30(D, "rROD")),
    ("03 Last-30min rONFH", lambda: A.last30(D, "rONFH")),
    ("03 Last-30min both", lambda: A.last30(D, "both")),
    ("04 VWAP trend always-in", lambda: A.vwap_trend(D)),
    ("05 30m ORB hold 1 bar", lambda: A.orb30_time(D, 1)),
    ("05 30m ORB hold 15 bars", lambda: A.orb30_time(D, 15)),
    ("06 Gap fill zone", lambda: A.gap_fill(D)),
    ("11 EMA 9/21 open + VWAP", lambda: A.ema_cross_open(D, full.close, atr1)),
    ("12 IB breakout close-entry", lambda: A.ib_breakout(D, True, True)),
    ("12 IB breakout stop-entry", lambda: A.ib_breakout(D, True, False)),
    ("15 Crabel stretch x1", lambda: A.crabel(D, 1.0)),
    ("15 Crabel stretch x2", lambda: A.crabel(D, 2.0)),
    ("15 Crabel stretch x1 NR4", lambda: A.crabel(D, 1.0, 4)),
    ("15 Crabel stretch x1 NR7", lambda: A.crabel(D, 1.0, 7)),
    ("17 Overnight drift 02-03", lambda: A.overnight_drift(full)),
    ("18 Williams k=0.25", lambda: A.williams(D)),
    ("19 ORB 2TP (15m OR)", lambda: A.orb_2tp(D, 15)),
    ("19 ORB 2TP (30m OR)", lambda: A.orb_2tp(D, 30)),
    ("20 VA 80% rule", lambda: A.va80(D)),
]
only = sys.argv[1:] 
rows = []
for name, f in tests:
    if only and not any(name.startswith(o) for o in only):
        continue
    t = time.time()
    tr = f()
    tr.to_csv(S + "trades_" + name.split()[0] + "_" + str(abs(hash(name)) % 10**6) + ".csv", index=False)
    r = summarize(name, tr); r["sec"] = round(time.time() - t)
    rows.append(r); print(json.dumps(r, default=str), flush=True)
    pd.DataFrame(rows).to_csv("results_a_partial.csv", index=False)
pd.DataFrame(rows).to_csv("results_a.csv", index=False)
print("DONE")
