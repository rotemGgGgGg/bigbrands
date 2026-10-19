"""Iter 88 — closing drift (MOC imbalance proxy): at 15:30 (or 15:45), if the move since the 09:30 open is ≥ x·σ (σ = 14-day
mean |open→close|), follow or fade into 15:59; plain hold (σ units) and a 1:2 bracket (stop 0.1σ). Real NQ 2010–19 / MNQ 2020–26."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
S = build(); R0, X1 = t2m("09:30"), t2m("15:59")
def run(days, X, at, x, mode, kind):
    o, h, l, c = (X[:, :, i] for i in range(4)); O = o[:, R0]; t = t2m(at)
    sig = pd.Series(np.abs(c[:, X1] / O - 1)).rolling(14).mean().shift().values; out = []
    for i in range(15, len(days)):
        if not np.isfinite(sig[i]): continue
        sg = sig[i] * O[i]; mv = c[i, t - 1] - O[i]
        if abs(mv) < x * sg: continue
        s = int(np.sign(mv)) * (1 if mode == "follow" else -1); e = o[i, t]
        if kind == "hold": out.append((s * (c[i, X1] - e) - 2.25 * e / 17000) / sg); continue
        st = 0.1 * sg; sl, tp = e - s * st, e + s * 2 * st; px = c[i, X1]
        for k in range(t, X1 + 1):
            if (l[i, k] <= sl) if s == 1 else (h[i, k] >= sl): px = min(o[i, k], sl) if s == 1 else max(o[i, k], sl); break
            if (h[i, k] >= tp) if s == 1 else (l[i, k] <= tp): px = tp; break
        out.append((s * (px - e) - 2.25 * e / 17000) / st)
    return np.array(out)
for at, x, mode, kind in itertools.product(("15:30", "15:45"), (0.5, 1.0, 1.5), ("follow", "fade"), ("hold", "1:2")):
    line = []
    for nm, key, msk in (("2010-19", "A", None), ("2020-23", "B", "lt"), ("2024-26", "B", "ge")):
        days, X = S[key]
        if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
        R = run(days, X, at, x, mode, kind); line.append(f"{nm}: n={len(R)} win={100*(R>0).mean():4.1f}% {R.mean():+.3f}")
    print(f"{at} |mv|≥{x}σ {mode:6s} {kind:4s} | " + " | ".join(line), flush=True)
