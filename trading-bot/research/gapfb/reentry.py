"""Iter 60 (queue 61a) — re-entry after a GapFB-C stop-out: if the base trade is stopped before 12:00, re-enter in the gap
direction on the first 1-minute close back beyond the session average price (typical-price mean since 09:30 — volume is not
in the cached arrays) or back beyond the OR level; stop 2×ATR + 5×ATR trail, exit 15:55. Reported per re-entry (R units)."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from gapfb2 import arrays
A = arrays()
def walk(o, h, l, c, s, j, A_, e):
    st = 2 * A_; sl = e - s * st; best = e
    for k in range(j, 386):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl): return (min(o[k], sl) if s == 1 else max(o[k], sl)) if k > j else sl, k, st
        best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
    return c[385], 385, st
def go(rows, trig):
    out = []
    for d, g, o, h, l, c, a in rows:
        if abs(g) < 0.003: continue
        s = 1 if g > 0 else -1; orh, orl = h[:15].max(), l[:15].min(); lvl = orh if s == 1 else orl
        win = (h[15:61] >= lvl) if s == 1 else (l[15:61] <= lvl)
        if not win.any(): continue
        j = 15 + np.argmax(win); e = max(lvl, o[j]) if s == 1 else min(lvl, o[j])
        px, k, st = walk(o, h, l, c, s, j, a[j], e)
        if s * (px - e) >= 0 or k >= 150: continue                    # only stop-outs before 12:00
        tp = (h + l + c) / 3; avg = np.cumsum(tp) / np.arange(1, 391)
        ref = avg if trig == "avg" else np.full(390, lvl)
        cond = (c[k + 1:150] > ref[k + 1:150]) if s == 1 else (c[k + 1:150] < ref[k + 1:150])
        if not cond.any(): continue
        m = k + 2 + np.argmax(cond)
        if m >= 386: continue
        e2 = o[m]; px2, _, st2 = walk(o, h, l, c, s, m, a[m], e2)
        out.append((s * (px2 - e2) - 2.25 * e2 / 17000) / st2)
    return np.array(out)
for trig in ("avg", "or"):
    line = []
    for per, rows in A.items():
        R = go(rows, trig); w = R > 0; line.append(f"{per}: n={len(R)} win={100*w.mean():4.1f}% R={R.mean():+.3f}")
    print(f"re-entry on {trig:3s} | " + " | ".join(line), flush=True)
