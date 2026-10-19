"""Iter 89 (queue 89) — gap days (|gap| ≥ 0.3 %) where GapFB-C did NOT trigger by 10:30: break of the 12:00–13:29 range at
13:30–14:30, in the gap direction / either direction; stop 2×ATR, 5×ATR trail, exit 15:55."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np
from gapfb2 import arrays
A = arrays()
def go(rows, mode, compress):
    out = []
    for d, g, o, h, l, c, a in rows:
        if abs(g) < 0.003: continue
        gs = 1 if g > 0 else -1; orh, orl = h[:15].max(), l[:15].min(); lvl0 = orh if gs == 1 else orl
        if ((h[15:61] >= lvl0) if gs == 1 else (l[15:61] <= lvl0)).any(): continue     # GapFB triggered → skip
        rh, rl = h[150:240].max(), l[150:240].min()
        if compress and (rh - rl) > 0.5 * (h[:150].max() - l[:150].min()): continue
        bu = np.nonzero(h[240:300] >= rh)[0]; bd = np.nonzero(l[240:300] <= rl)[0]
        tu = bu[0] if len(bu) else 999; td = bd[0] if len(bd) else 999
        if mode == "with": tu, td = (tu, 999) if gs == 1 else (999, td)
        if tu == td: continue
        s, j = (1, 240 + tu) if tu < td else (-1, 240 + td); e = max(rh, o[j]) if s == 1 else min(rl, o[j]); A_ = a[j]; st = 2 * A_; sl = e - s * st; best = e; px = None
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
            best = max(best, h[k]) if s == 1 else min(best, l[k]); sl = max(sl, best - 5 * A_) if s == 1 else min(sl, best + 5 * A_)
        if px is None: px = c[385]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for mode in ("with", "both"):
    for comp in (False, True):
        print(f"lunch break {mode:4s} compress={comp} | " + " | ".join(f"{p}: n={len(R)} R={R.mean():+.3f}" for p, rows in A.items() for R in [go(rows, mode, comp)]), flush=True)
