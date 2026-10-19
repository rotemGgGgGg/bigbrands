"""Iter 64 — gap days with score ≤ 1 (and = 0): trade the 15-min OR break AGAINST the gap (gap-fill side), entry ≤10:30,
stop 2×ATR, target 2× stop (1:2) or 5×ATR trail, exit 15:55."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
A = arrays(); F = pd.read_csv("features_C.csv", parse_dates=["day"])
def score_of(rows):
    out = {}
    for i in range(1, len(rows)):
        d, g, o, h, l, c, a = rows[i]; _, _, po, ph, pl, pc, _ = rows[i - 1]; s = 1 if g > 0 else -1
        out[d] = int(s * (pc[389] - po[0]) <= 0) + int((s == 1 and o[0] > ph.max()) or (s == -1 and o[0] < pl.min())) + int(s * (c[14] - o[0]) > 0)
    return out
def go(rows, maxs, mode):
    sc = score_of(rows); out = []
    for d, g, o, h, l, c, a in rows:
        if abs(g) < 0.003 or sc.get(d, 9) > maxs: continue
        s = -1 if g > 0 else 1; orh, orl = h[:15].max(), l[:15].min(); lvl = orh if s == 1 else orl
        win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
        if not win.any(): continue
        j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st
        tp = e + s * 2 * st if mode == "1:2" else None; best = e; px = None
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
            if k > j and tp is not None and ((h[k] >= tp) if s == 1 else (l[k] <= tp)): px = tp; break
            if tp is None: best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
        if px is None: px = c[385]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for maxs in (0, 1):
    for mode in ("1:2", "trail"):
        line = []
        for per, rows in A.items():
            R = go(rows, maxs, mode); w = R > 0; line.append(f"{per}: n={len(R)} win={100*w.mean():4.1f}% R={R.mean():+.3f}")
        print(f"score<={maxs} against-gap {mode:5s} | " + " | ".join(line), flush=True)
