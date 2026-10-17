"""Iteration 20 — liquidity 'magnets' at 1:2: when price is d away from an untouched reference level (PDH, PDL, PDC, ONH, ONL,
round 100 / 500, weekly open), trade TOWARD it; target = the level, stop = d/2 (planned 1:2). Also the reverse (rejection: fade
from just before the level with target 2× stop). First trigger per day per level family, 10:00–15:00."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, "../influencers")]
import numpy as np, pandas as pd, itertools
from lib import o, h, l, c, N, SIG, VALID, YR, okprev, PDH, PDL, PDC, F, DAYS, trade
wk_open = np.full(N, np.nan); cur = np.nan
for i in range(N):
    if i == 0 or DAYS[i].weekday() < DAYS[i - 1].weekday(): cur = o[i, 0]
    wk_open[i] = cur
def levels(i, px):
    L = {"PDH": PDH[i], "PDL": PDL[i], "PDC": PDC[i], "ONH": F.onh.values[i], "ONL": F.onl.values[i], "WKO": wk_open[i]}
    L["R100"] = np.round(px / 100) * 100; L["R500"] = np.round(px / 500) * 500
    return L
rows = []
for fam, dmin, dmax, mode in itertools.product(("PDH", "PDL", "PDC", "ONH", "ONL", "WKO", "R100", "R500"), (0.1, 0.2, 0.3), (0.3, 0.5, 0.8), ("toward", "reject")):
    if dmax <= dmin: continue
    R = []
    for i in range(1, N):
        if not okprev[i]: continue
        sg = SIG[i] * o[i, 0]
        for m in range(30, 330, 5):
            px = c[i, m - 1]; lv = levels(i, px)[fam]
            if not np.isfinite(lv): break
            touched = (h[i, :m].max() >= lv) and (l[i, :m].min() <= lv)
            if touched and fam not in ("R100", "R500"): break
            d = lv - px; ad = abs(d) / sg
            if not (dmin <= ad < dmax): continue
            side = int(np.sign(d)) if mode == "toward" else -int(np.sign(d)); e = o[i, m]
            if mode == "toward": stop = e - side * abs(d) / 2; tgt = lv
            else: stop = lv + np.sign(d) * 0.25 * abs(d); tgt = e + side * 2 * abs(stop - e)
            risk = abs(e - stop)
            if risk < 2 or (tgt - e) * side <= 0: break
            r = trade(i, m, side, stop, tgt)
            if r: R.append((i, r[0] / risk))
            break
    if len(R) < 40: continue
    X = pd.DataFrame(R, columns=["i", "R"]); tr = YR[X.i] < 2024; w = X.R > 0
    rows.append(dict(level=fam, d=f"{dmin}-{dmax}σ", mode=mode, n=len(X), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1),
                     R_tr=round(X.R[tr].mean(), 3), R_te=round(X.R[~tr].mean(), 3)))
out = pd.DataFrame(rows); out.to_csv("iter20_magnet.csv", index=False); pd.set_option("display.width", 200)
print(out.sort_values("win_te", ascending=False).head(10).to_string(index=False))
print("configs", len(out), "PASS", int(((out.win_tr >= 70) & (out.win_te >= 70) & (out.R_tr > 0) & (out.R_te > 0)).sum()))
