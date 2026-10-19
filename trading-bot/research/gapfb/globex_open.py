"""Iter 82 — 'GapFB at the Globex open' (18:00 NY, incl. Sunday): gap = 18:00 open vs the prior 16:59 close (weekday) / Friday
16:59 (Sunday); |gap| ≥ thr; OR = first m minutes from 18:00; stop entry in the gap direction within 60 min; stop 2×ATR, 5×ATR trail;
exit 02:00 (before London) or 09:29. Real NQ 2010–19 / MNQ 2020–23 / 2024–26. Session i = 18:00 (day before) → 16:59."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
S = build()
def run(days, X, thr, m, ex, sunday_only):
    o, h, l, c, a = (X[:, :, i] for i in range(5)); te = t2m(ex); out = []
    for i in range(1, len(days)):
        if sunday_only and days[i].weekday() != 0: continue          # session dated Monday = Sunday-evening open
        gap = o[i, 0] / c[i - 1, t2m("16:59")] - 1
        if abs(gap) < thr: continue
        s = 1 if gap > 0 else -1; orh, orl = h[i, :m].max(), l[i, :m].min(); lvl = orh if s == 1 else orl
        win = (h[i, m:m + 60] >= lvl) if s == 1 else (l[i, m:m + 60] <= lvl)
        if not win.any(): continue
        j = m + np.argmax(win); e = max(lvl, o[i, j]) if s == 1 else min(lvl, o[i, j]); A = a[i, j]
        if not A > 0: continue
        st = 2 * A; sl = e - s * st; best = e; px = None
        for k in range(j, te + 1):
            if (l[i, k] <= sl) if s == 1 else (h[i, k] >= sl): px = sl if k == j else (min(o[i, k], sl) if s == 1 else max(o[i, k], sl)); break
            best = max(best, h[i, k]) if s == 1 else min(best, l[i, k]); sl = max(sl, best - 5 * A) if s == 1 else min(sl, best + 5 * A)
        if px is None: px = c[i, te]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for thr, m, ex, sun in itertools.product((0.001, 0.002, 0.004), (15, 30), ("02:00", "09:29"), (False, True)):
    line = []
    for nm, key, msk in (("2010-19", "A", None), ("2020-23", "B", "lt"), ("2024-26", "B", "ge")):
        days, X = S[key]
        if msk: mm = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[mm], X[mm]
        R = run(days, X, thr, m, ex, sun)
        line.append(f"{nm}: n={len(R):4d} R={R.mean():+.3f}" if len(R) else f"{nm}: -")
    print(f"gap≥{thr*100:.1f}% OR{m} exit {ex} {'Sun' if sun else 'all'} | " + " | ".join(line), flush=True)
