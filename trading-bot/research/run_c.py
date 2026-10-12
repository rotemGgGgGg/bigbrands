import time, json
import numpy as np, pandas as pd
from engine import summarize, S
import strategies_c as C
full = pd.read_pickle(S + "full1m.pkl")
tr_ = pd.concat([full.high - full.low, (full.high - full.close.shift()).abs(), (full.low - full.close.shift()).abs()], axis=1).max(axis=1)
atr20 = tr_.ewm(alpha=1 / 20, adjust=False).mean()
rows = []
for name, f in [("13 London GMM long", lambda: C.london_gmm(full)), ("14 RTH GMM confluence", lambda: C.rth_confluence(full, atr20))]:
    t = time.time(); tr = f(); tr.to_csv(S + "trades_" + name.split()[0] + ".csv", index=False)
    r = summarize(name, tr); r["sec"] = round(time.time() - t); rows.append(r); print(json.dumps(r, default=str), flush=True)
pd.DataFrame(rows).to_csv("results_c.csv", index=False); print("DONE")
