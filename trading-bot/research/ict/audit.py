"""Look-ahead audit for engine.run: for random configurations and random cut minutes, scramble every bar AFTER the cut and
re-run. Every trade whose ENTRY happened at or before the cut must be identical (entry minute, side, risk), because those
decisions may only depend on bars that had already closed. Also checks that entries never happen outside the window."""
import numpy as np
import ict_data as data, ict_engine as E
from ict_space import sample, COST_PTS, SLIP_PTS

D = data.load(); X, LV, E2 = D["X"], D["LV"], D["ema200"]; prev = np.r_[False, (D["days"][1:] - D["days"][:-1]).days <= 4]
rng = np.random.default_rng(7); bad = 0; checked = 0
for it in range(20000):
    if checked >= 2000: break
    P = sample(rng); d = int(rng.integers(1, len(X) - 1))
    a = E.run(X, LV, E2, prev, P, d, d + 1)
    if len(a[0]) == 0: continue
    cut = int(rng.integers(int(P[E.WS]), int(P[E.TEXIT]) + 1))
    X2 = X.copy(); noise = rng.normal(0, 20, size=(1380 - cut - 1, 1))
    X2[d, cut + 1:, :4] = X2[d, cut + 1:, :4] + noise          # scramble the future (all four prices shift together)
    X2[d, cut + 1:, 1] = X2[d, cut + 1:, :4].max(1); X2[d, cut + 1:, 2] = X2[d, cut + 1:, :4].min(1)
    LV2 = LV.copy(); LV2[d] = data.day_levels(X2, d, prev[d])
    b = E.run(X2, LV2, E2, prev, P, d, d + 1)
    A = [(t, s, round(r, 6)) for t, s, r in zip(a[1], a[2], a[4]) if t <= cut]
    B = [(t, s, round(r, 6)) for t, s, r in zip(b[1], b[2], b[4]) if t <= cut]
    checked += 1
    if A != B: bad += 1; print("MISMATCH", it, d, cut, A, B, P)
    if any(t < P[E.WS] for t in a[1]): bad += 1; print("ENTRY BEFORE WINDOW", P)
print(f"audit: {checked} day-configs checked, {bad} violations")
