"""Iter 84 (queue 85) — non-gap days (|gap| < 0.3 %): fade the first 15-min OR break (limit at the OR edge, fill needs 1 tick
through, until 11:00); stop k×ATR beyond, target = OR midpoint or r×stop; exit 15:55."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np
from gapfb2 import arrays
A = arrays()
def go(rows, k, tgt):
    out = []
    for d, g, o, h, l, c, a in rows:
        if abs(g) >= 0.003: continue
        orh, orl = h[:15].max(), l[:15].min(); mid = (orh + orl) / 2; tick = o[0] / 17000 * 0.25
        bu = np.nonzero(h[15:91] >= orh + tick)[0]; bd = np.nonzero(l[15:91] <= orl - tick)[0]
        tu = bu[0] if len(bu) else 999; td = bd[0] if len(bd) else 999
        if tu == td: continue
        s, j, e = (-1, 15 + tu, orh) if tu < td else (1, 15 + td, orl)
        A_ = a[j]; st = k * A_; sl = e - s * st
        tp = mid if tgt == "mid" else e + s * tgt * st
        if s * (tp - e) <= 0: continue
        px = None
        for m in range(j, 386):
            if (l[m] <= sl) if s == 1 else (h[m] >= sl): px = sl if m == j else (min(o[m], sl) if s == 1 else max(o[m], sl)); break
            if m > j and ((h[m] >= tp) if s == 1 else (l[m] <= tp)): px = tp; break
        if px is None: px = c[385]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for k, tgt in itertools.product((1.0, 2.0, 3.0), ("mid", 1.0, 2.0)):
    line = []
    for per, rows in A.items():
        R = go(rows, k, tgt); line.append(f"{per}: n={len(R)} win={100*(R>0).mean():4.1f}% R={R.mean():+.3f}")
    print(f"fade OR break nogap stop{k}ATR tgt {tgt} | " + " | ".join(line), flush=True)
