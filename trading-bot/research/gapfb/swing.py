"""GapFB-C with overnight holding (personal account): same entry (gap ≥0.3 %, 15-min OR, gap direction, entry ≤10:30, stop 2×ATR,
5×ATR trail). Exit variants: 15:55 same day (base) / next session 09:29 / next session 15:55 / hold while trail not hit up to
N sessions. Uses the 24 h session grid (sess24.pkl): session i = 18:00 (day before) → 16:59; RTH 09:30 = minute 930."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
S = build(); R0 = t2m("09:30")
def go(days, X, exit_mode, max_sess=1):
    o, h, l, c, a = (X[:, :, i] for i in range(5)); out = []
    for i in range(1, len(days) - max_sess):
        pc = c[i - 1, t2m("15:59")]; g = o[i, R0] / pc - 1
        if abs(g) < 0.003: continue
        s = 1 if g > 0 else -1; orh, orl = h[i, R0:R0 + 15].max(), l[i, R0:R0 + 15].min(); lvl = orh if s == 1 else orl
        win = (h[i, R0 + 15:R0 + 61] >= lvl) if s == 1 else (l[i, R0 + 15:R0 + 61] <= lvl)
        if not win.any(): continue
        j = R0 + 15 + np.argmax(win); e = max(orh, o[i, j]) if s == 1 else min(orl, o[i, j]); A = a[i, j]; st = 2 * A; sl = e - s * st; best = e
        # path: rest of today to 15:55, then following sessions per exit mode
        seg = [(i, j, t2m("15:55"))]
        if exit_mode == "next_open": seg.append((i + 1, 0, t2m("09:29")))
        if exit_mode == "next_close": seg.append((i + 1, 0, t2m("15:55")))
        if exit_mode == "trail_n": seg += [(i + k, 0, t2m("15:55")) for k in range(1, max_sess + 1)]
        px = None
        for (d, k0, k1) in seg:
            for k in range(k0, k1 + 1):
                if (l[d, k] <= sl) if s == 1 else (h[d, k] >= sl):
                    px = sl if (d == i and k == j) else (min(o[d, k], sl) if s == 1 else max(o[d, k], sl)); break
                best = max(best, h[d, k]) if s == 1 else min(best, l[d, k]); sl = max(sl, best - 5 * A) if s == 1 else min(sl, best + 5 * A)
            if px is not None: break
        if px is None: d, k1 = seg[-1][0], seg[-1][2]; px = c[d, k1]
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for mode, n in (("same_day", 1), ("next_open", 1), ("next_close", 1), ("trail_n", 3), ("trail_n", 5)):
    line = []
    for nm, (days, X), msk in (("2010-19", S["A"], None), ("2020-23", S["B"], "lt"), ("2024-26", S["B"], "ge")):
        if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
        R = go(days, X, mode, n); w = R > 0
        line.append(f"{nm}: n={len(R)} win={100*w.mean():4.1f}% rr={R[w].mean()/-R[~w].mean():.2f} R={R.mean():+.3f}")
    print(f"{mode}{n if mode=='trail_n' else '':2} | " + " | ".join(line), flush=True)
