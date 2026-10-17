import sys, time, traceback; sys.path.insert(0, ".")
import pandas as pd
from strategies import ROSTER, NOT_TESTABLE, summarize
rows = []
for who, name, fn, kind in ROSTER:
    t = time.time()
    try: r = summarize(name, who, fn(), kind)
    except Exception as e: traceback.print_exc(); r = dict(influencer=who, strategy=name, n=0, kind=kind, error=str(e)[:80])
    rows.append(r); print(f"{who:28s} {name:32s} n={r.get('n')} win={r.get('win')} $={r.get('usd')} IS={r.get('usd_IS')} OOS={r.get('usd_OOS')} yrs={r.get('yrs_pos')} ({time.time()-t:.0f}s)", flush=True)
for who, name, why in NOT_TESTABLE: rows.append(dict(influencer=who, strategy=name, kind="not testable", note=why))
pd.DataFrame(rows).to_csv("results.csv", index=False)
