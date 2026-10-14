import numpy as np, pandas as pd
from signals import *
from deep import stats
def bracket_c(sigs, a, b, last=384, tick=0.25):
    rows = []
    for i, j, s, lim in sigs:
        if np.isnan(day_sig[i]) or j > last: continue
        h, l, o, c = D.h[i], D.l[i], D.o[i], D.c[i]
        # entry only if price trades THROUGH the limit by one tick
        if not ((l[j] <= lim - tick) if s == 1 else (h[j] >= lim + tick)):
            j2 = next((x for x in range(j + 1, last) if ((l[x] <= lim - tick) if s == 1 else (h[x] >= lim + tick))), None)
            if j2 is None: continue
            j = j2
        e = lim; sc = day_sig[i] * e
        tp, sl = e + s * a * sc, e - s * b * sc
        px = None
        for x in range(j, last + 1):
            if (l[x] <= sl) if s == 1 else (h[x] >= sl): px = min(o[x], sl) if (x > j and s == 1) else (max(o[x], sl) if x > j else sl); break
            if x > j and ((h[x] >= tp + tick) if s == 1 else (l[x] <= tp - tick)): px = tp; break
        if px is None: px = c[last]
        rows.append((D.days[i], (px - e) * s - COST_PTS))
    return pd.DataFrame(rows, columns=["date", "pts"])
sg = sig_na_fvg()
for a, b in ((0.15, 2.0), (0.15, 2.5), (0.125, 2.0), (0.175, 2.0), (0.2, 2.0)):
    print(a, b, stats(bracket_c(sg, a, b)))
