"""Robustness of the best no-TP variants: gap threshold neighbourhood + placebo on NON-gap days (|gap| < 0.3 %)."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb import run, periods
sets = periods()
for k, ex in ((3.0, 150), (3.0, 385), (2.0, 385), (2.0, 150)):
    print(f"--- stop {k}×ATR, exit {(570+ex)//60}:{(570+ex)%60:02d}, 1 trade/day")
    for thr in (0.0, 0.002, 0.003, 0.005, 0.01, "nogap"):
        line = []
        for nm, dd in sets.items():
            T = run(dd, 0.0 if thr == "nogap" else thr, 385, ex, 1, k, 1e9)
            if thr == "nogap": T = T[T.gap.abs() < 0.003]
            w = T.R > 0; line.append(f"{nm}: n={len(T):4d} win={100*w.mean():4.1f}% rr={T.R[w].mean()/-T.R[~w].mean():.2f} R={T.R.mean():+.3f}")
        print(f"gap {'<0.3% (placebo)' if thr=='nogap' else '≥%.1f%%' % (thr*100):16s}", " | ".join(line), flush=True)
