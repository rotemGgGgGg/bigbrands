"""Iteration 6 — intraday volatility contraction: the last n 5-minute bars are all inside a range narrower than q × the day's
average 5m range (NR-n squeeze) → stop orders at both ends; stop = other end; target 2–3 R.
Iteration 7 — overnight inventory: opening position vs overnight range + gap → first-hour continuation or reversal with 1:2."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, "../influencers")]
import numpy as np, pandas as pd, itertools
from lib import o, h, l, c, N, SIG, VALID, YR, F, stop_fill, trade, G, TICK
g = G(5); rows = []
for n, q, rr in itertools.product((3, 4, 6, 8), (0.3, 0.5, 0.7), (2.0, 3.0)):
    R = []
    for i in range(N):
        if not VALID[i]: continue
        avg = (g.h[i * 78:(i + 1) * 78] - g.l[i * 78:(i + 1) * 78])
        for k in range(max(n, 6), 70):
            gi = i * 78 + k; seg = slice(gi - n + 1, gi + 1); hi, lo = g.h[seg].max(), g.l[seg].min()
            if hi - lo < q * avg[:k].mean() * n ** 0.5 and hi - lo > 2:
                m = g.next_min(gi); a, b = stop_fill(i, m, m + 60, hi + TICK, 1), stop_fill(i, m, m + 60, lo - TICK, -1)
                f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
                if f:
                    (mm, px), s = f; stp = lo - TICK if s == 1 else hi + TICK; rk = abs(px - stp)
                    r = trade(i, mm, s, stp, px + s * rr * rk, entry=px, at_open=False)
                    if r: R.append((i, r[0] / rk))
                break
    if len(R) < 40: continue
    X = pd.DataFrame(R, columns=["i", "R"]); tr = YR[X.i] < 2024; w = X.R > 0
    rows.append(dict(iter=6, cfg=f"NR{n} q{q}", rr=rr, n=len(X), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1), R_tr=round(X.R[tr].mean(), 3), R_te=round(X.R[~tr].mean(), 3)))
on_pos, gap = F.on_pos.values, F.gap.values
for zone, mode, s, rr in itertools.product(("above_on", "below_on", "inside_on"), ("cont", "rev"), (0.15, 0.3), (2.0, 3.0)):
    R = []
    for i in range(1, N):
        if not VALID[i] or np.isnan(on_pos[i]): continue
        z = "above_on" if on_pos[i] > 1 else "below_on" if on_pos[i] < 0 else "inside_on"
        if z != zone: continue
        side = int(np.sign(gap[i])) if zone == "inside_on" else (1 if zone == "above_on" else -1)
        if side == 0 or np.isnan(gap[i]): continue
        if mode == "rev": side = -side
        sp = s * SIG[i] * o[i, 0]; e = o[i, 0]; r = trade(i, 0, side, e - side * sp, e + side * rr * sp, last=60)
        if r: R.append((i, r[0] / sp))
    if len(R) < 40: continue
    X = pd.DataFrame(R, columns=["i", "R"]); tr = YR[X.i] < 2024; w = X.R > 0
    rows.append(dict(iter=7, cfg=f"{zone} {mode} stop{s}", rr=rr, n=len(X), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1), R_tr=round(X.R[tr].mean(), 3), R_te=round(X.R[~tr].mean(), 3)))
out = pd.DataFrame(rows); out.to_csv("iter06_07.csv", index=False); pd.set_option("display.width", 200)
for it in (6, 7):
    x = out[out.iter == it]; print(f"iter {it}: configs {len(x)} PASS {int(((x.win_tr>=70)&(x.win_te>=70)&(x.R_tr>0)&(x.R_te>0)).sum())}"); print(x.sort_values("win_tr", ascending=False).head(6).to_string(index=False))
