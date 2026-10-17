"""Policy search: random policies scored on attempts STARTING in 2020–23 (selection) and checked on starts in 2024–26."""
import sys, os, itertools, json; H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import numpy as np, pandas as pd
from ledger import load
from sim import Book, score
L = load(); B = Book(L)
yrs = pd.DatetimeIndex(B.days).year
st_tr = [k for k in range(0, len(B.days) - 60, 4) if yrs[k] < 2024]; st_te = [k for k in range(0, len(B.days) - 60, 4) if yrs[k] >= 2024]
EDGES = ["WVB", "NA", "PF", "PM", "FVG"]
rng = np.random.default_rng(int(sys.argv[1])); n = int(sys.argv[2]); rows = []
for _ in range(n):
    k = rng.integers(1, 6); edges = sorted(rng.choice(EDGES, k, replace=False).tolist())
    pol = dict(edges=edges, base=int(rng.choice([1, 2, 3, 4, 5, 6, 8, 10])), press_at=rng.choice([None, 500, 1000, 1500]),
               mult=float(rng.choice([0.5, 1.5, 2.0])), cap=rng.choice([None, 600, 900, 1200, 1500]), stop=rng.choice([None, 400, 700, 1000]),
               max_trades=int(rng.choice([1, 2, 3, 5])))
    pol["press_at"] = None if pol["press_at"] is None else int(pol["press_at"]); pol["cap"] = None if pol["cap"] is None else int(pol["cap"]); pol["stop"] = None if pol["stop"] is None else int(pol["stop"])
    a = score(B, pol, st_tr)
    if a is None: continue
    b = score(B, pol, st_te) or {}
    rows.append(dict(policy=json.dumps(pol), **{f"tr_{x}": v for x, v in a.items()}, **{f"te_{x}": v for x, v in b.items()}))
pd.DataFrame(rows).to_csv(os.path.join(H, f"search_{sys.argv[1]}.csv"), index=False); print("done", len(rows))
