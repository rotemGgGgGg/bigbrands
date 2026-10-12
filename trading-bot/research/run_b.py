import pickle, sys, time, json
import numpy as np, pandas as pd
from engine import summarize, S
import strategies_b as B
full = pd.read_pickle(S + "full1m.pkl")
tr_ = pd.concat([full.high - full.low, (full.high - full.close.shift()).abs(), (full.low - full.close.shift()).abs()], axis=1).max(axis=1)
atr14 = tr_.ewm(alpha=1 / 14, adjust=False).mean().values
atr20 = tr_.ewm(alpha=1 / 20, adjust=False).mean().values
tests = [
    ("07 Asia/London sweep + FVG", lambda: B.sweep_fvg(full)),
    ("08 Silver Bullet AM", lambda: B.silver_bullet(full, atr20)),
    ("10 HTF sweep & reclaim", lambda: B.htf_sweep(full, atr14)),
]
rows = []
for name, f in tests:
    if sys.argv[1:] and not any(name.startswith(a) for a in sys.argv[1:]):
        continue
    t = time.time(); tr = f()
    tr.to_csv(S + "trades_" + name.split()[0] + ".csv", index=False)
    r = summarize(name, tr); r["sec"] = round(time.time() - t); rows.append(r)
    print(json.dumps(r, default=str), flush=True)
    pd.DataFrame(rows).to_csv("results_b_partial.csv", index=False)
pd.DataFrame(rows).to_csv("results_b.csv", index=False); print("DONE")
