"""Robustness of the add-on: EMA length 10/20/50, arm at +1R; combined daily R (base + add-on, 1 unit risk each), max DD."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
import addon
from gapfb2 import arrays
A = arrays()
orig = addon.ema
for n in (10, 20, 50):
    addon.ema = (lambda x, _n, n=n: orig(x, n))
    line = []; allb = []; allc = []
    for nm, rows in A.items():
        b, ad = addon.go(rows, 1.0)
        line.append(f"{nm}: addon n={len(ad)} R={ad.mean():+.3f}")
        allb += list(b); allc.append(b.sum() + ad.sum())
    print(f"EMA{n} | " + " | ".join(line), flush=True)
# combined equity for EMA20
addon.ema = orig; tot_b = tot_c = 0
for nm, rows in A.items():
    b, ad = addon.go(rows, 1.0); print(f"{nm}: base total {b.sum():+.0f}R  base+addon total {b.sum()+ad.sum():+.0f}R  (addon risk units {len(ad)})")
