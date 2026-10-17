"""Iteration 3 — FOMC days (statement 14:00 ET; dates from federalreserve.gov, 2020 regular meetings added).
(a) pre-FOMC drift (Lucca & Moench): long 09:30 → 14:00 with 1:2 brackets;  (b) 14:00 spike: follow / fade the 14:00–14:0x move,
entering at 14:0x, stop = s × |spike|, target 2–3 × stop, exit 15:55;  (c) press-conference reversal at 14:30–15:00."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, "../influencers")]
import numpy as np, pandas as pd, itertools
from lib import o, h, l, c, N, SIG, VALID, YR, DAYS, trade
F = """2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16 2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28
2021-09-22 2021-11-03 2021-12-15 2022-01-26 2022-03-16 2022-05-04 2022-06-15 2022-07-27 2022-09-21 2022-11-02 2022-12-14 2023-02-01
2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13 2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31
2024-09-18 2024-11-07 2024-12-18 2025-01-29 2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10 2026-01-28
2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16""".split()
idx = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(DAYS)}
FD = [idx[d] for d in F if d in idx and VALID[idx[d]]]
print("FOMC days in data:", len(FD))
rows = []
def rec(name, cfg, R):
    if len(R) < 15: return
    R = pd.DataFrame(R, columns=["i", "R"]); tr = YR[R.i] < 2024; w = R.R > 0
    rows.append(dict(play=name, **cfg, n=len(R), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1),
                     R_tr=round(R.R[tr].mean(), 3), R_te=round(R.R[~tr].mean(), 3)))
for s, rr in itertools.product((0.2, 0.3, 0.5, 1.0), (2.0, 3.0)):
    R = []
    for i in FD:
        sp = s * SIG[i] * o[i, 0]; e = o[i, 0]; r = trade(i, 0, 1, e - sp, e + rr * sp, last=269)
        if r: R.append((i, r[0] / sp))
    rec("pre-FOMC drift long 09:30→14:00", dict(stop=f"{s}σ", rr=rr, win_min="-"), R)
for wm, s, rr, mode in itertools.product((5, 10, 15, 30), (0.5, 1.0, 1.5), (2.0, 3.0), ("follow", "fade")):
    R = []
    for i in FD:
        mv = c[i, 270 + wm - 1] - o[i, 270]
        if abs(mv) < 2: continue
        side = int(np.sign(mv)) * (1 if mode == "follow" else -1); m = 270 + wm; e = o[i, m]; sp = s * abs(mv)
        r = trade(i, m, side, e - side * sp, e + side * rr * sp)
        if r: R.append((i, r[0] / sp))
    rec(f"14:00 spike {mode}", dict(stop=f"{s}×spike", rr=rr, win_min=wm), R)
for s, rr in itertools.product((0.5, 1.0), (2.0, 3.0)):
    R = []
    for i in FD:
        mv = c[i, 299] - o[i, 270]; side = -int(np.sign(mv)); m = 300; e = o[i, m]; sp = s * max(abs(mv), 2)
        r = trade(i, m, side, e - side * sp, e + side * rr * sp)
        if r: R.append((i, r[0] / sp))
    rec("presser reversal (fade 14:00–14:30 at 14:30)", dict(stop=f"{s}×move", rr=rr, win_min=30), R)
out = pd.DataFrame(rows); out.to_csv("iter03_fomc.csv", index=False); pd.set_option("display.width", 200)
print(out.sort_values("R_tr", ascending=False).head(15).to_string(index=False))
print("PASS:", int(((out.win_tr >= 70) & (out.win_te >= 70) & (out.R_tr > 0) & (out.R_te > 0)).sum()))
