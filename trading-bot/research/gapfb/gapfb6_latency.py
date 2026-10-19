"""GapFB-C execution sensitivity: entry delayed by L minutes after the OR break (market at that bar's open) and extra
slippage x pt per round trip. NQ, three periods."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
A = arrays()
def tr(o, h, l, c, a, gap, L, slip):
    if abs(gap) < 0.003: return None
    orh, orl = h[:15].max(), l[:15].min(); s = 1 if gap > 0 else -1; lvl = orh if s == 1 else orl
    hit = np.nonzero((h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl))[0]
    if not len(hit): return None
    j = hit[0] + 15
    if L == 0: e = max(orh, o[j]) if s == 1 else min(orl, o[j]); j0 = j
    else: j0 = j + L; e = o[j0]
    st = 2 * a[j0]; sl = e - s * st; best = e
    for k in range(j0, 386):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if (k == j0 and L == 0) else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
        best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * a[j0]) if s == 1 else min(sl, best + 5 * a[j0])
    else: px = c[385]
    return (s * (px - e) - (2.25 + slip) * e / 17000) / st
for L, slip in ((0, 0), (1, 0), (2, 0), (3, 0), (0, 2), (0, 4), (1, 2)):
    out = []
    for per, rows in A.items():
        R = np.array([r for d, g, o, h, l, c, a in rows if (r := tr(o, h, l, c, a, g, L, slip)) is not None]); w = R > 0
        out.append(f"{per}: win={100*w.mean():4.1f}% rr={R[w].mean()/-R[~w].mean():.2f} R={R.mean():+.3f}")
    print(f"delay {L} min, extra slip {slip} pt | " + " | ".join(out))
