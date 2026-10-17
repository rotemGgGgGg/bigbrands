"""Iter 34 — Osler (2003, J. Finance 'Currency orders and exchange rate dynamics'): take-profit orders cluster AT round numbers
(→ reversals on touch), stop-loss orders cluster just BEYOND them (→ acceleration once crossed). Applied to NQ 100- and 50-point
levels, three periods, planned 1:2. Window 09:45–15:00, the first round level touched after 09:45 (excluding one that contains the
09:45 price within 0.05σ). FADE: limit at the level (fill needs trade-through by 1 tick-equivalent), stop k·σ beyond, target 2k·σ.
BREAK: stop entry at level + 0.05σ in the crossing direction, stop k·σ back, target 2k·σ. Exit 15:59. One trade per day."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
exec(open("iter26_web.py").read().split("\nres = []")[0])
res = []
for per, o, h, l, c, dow in grids():
    N = len(o); O = o[:, 0]; C = c[:, 389]
    sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    for step, k, mode in itertools.product((100, 50, 25), (0.1, 0.15, 0.25), ("fade", "break")):
        R = []
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            sg = sig[i] * O[i]; tick = O[i] / 17000 * 0.25; p0 = c[i, 14]
            up = np.ceil(p0 / step) * step; dn = np.floor(p0 / step) * step
            if up - p0 < 0.05 * sg: up += step
            if p0 - dn < 0.05 * sg: dn -= step
            hu = np.nonzero(h[i, 15:330] >= up)[0]; hd = np.nonzero(l[i, 15:330] <= dn)[0]
            tu = hu[0] + 15 if len(hu) else 999; td = hd[0] + 15 if len(hd) else 999
            if tu == td == 999 or tu == td: continue
            lvl, dirn, m = (up, 1, tu) if tu < td else (dn, -1, td)     # dirn = direction of approach
            if mode == "fade":
                s = -dirn; e = lvl
                if not (dirn == 1 and h[i, m] >= lvl + tick or dirn == -1 and l[i, m] <= lvl - tick):
                    nx = np.nonzero((h[i, m + 1:389] >= lvl + tick) if dirn == 1 else (l[i, m + 1:389] <= lvl - tick))[0]
                    if not len(nx): continue
                    m = m + 1 + nx[0]
                st = k * sg; px, _, _ = walk(o[i], h[i], l[i], c[i], m, s, e, e - s * st, e + s * 2 * st, 389, at_open=False)
            else:
                s = dirn; e = lvl + s * 0.05 * sg
                hit = np.nonzero((h[i, m:389] >= e) if s == 1 else (l[i, m:389] <= e))[0]
                if not len(hit): continue
                m = m + hit[0]; e = max(e, o[i, m]) if s == 1 else min(e, o[i, m])
                st = k * sg; px, _, _ = walk(o[i], h[i], l[i], c[i], m, s, e, e - s * st, e + s * 2 * st, 389, at_open=False)
            R.append((s * (px - e) - 2.25 * e / 17000) / st)
        R = np.array(R)
        if len(R) < 15: continue
        res.append(dict(per=per, rule=f"{mode} {step}pt k{k}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(res); T.to_csv("iter34_round.csv", index=False)
W = T.pivot_table(index="rule", columns="per", values=["win", "R", "n"]); W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
pd.set_option("display.width", 250); print(W.sort_values("minR", ascending=False).round(3).to_string())
