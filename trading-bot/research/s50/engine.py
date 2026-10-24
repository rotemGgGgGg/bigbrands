"""Generic bar backtester for the Pine templates (numba).
Signal on bar i close → market entry at bar i+1 open (+ slippage). Stop = entry ∓ sl×ATR(14)[i], target = entry ± tp×ATR[i].
Stop checked from the entry bar on (target only from the next bar — Pine places the exit after the fill); stop first when both
are touched in one bar; one position at a time. Sessions: 0 = 24 h (hold until stop/target, flat before a contract roll),
1 = RTH (entries 09:30-15:30, flat at the 16:00 close), 2 = AM (entries 09:30-11:30, flat 16:00).
Costs per round trip in NQ points: 2.25 × price/17000 — the research standard, scaled with price so every year is comparable
(≈ 3.3 pt ≈ $6.6 per MNQ at 25,000; real MNQ commission + 1 tick slippage ≈ $2.5); cx multiplies it (2 = stress). Results in R = net points / stop distance."""
import numpy as np
from numba import njit


@njit(cache=True)
def sim(o, h, l, c, a, mod, roll, sigL, sigS, sl, tp, side, sess, cx):
    n = len(c); oi = np.empty(n, np.int64); ox = np.empty(n, np.int64); orr = np.empty(n); osd = np.empty(n, np.int64); nt = 0
    i = 0
    while i < n - 2:
        s = 1 if sigL[i] else (-1 if sigS[i] else 0)
        if s == 0 or (side != 0 and s != side) or not a[i] > 0:
            i += 1; continue
        j = i + 1
        if roll[j]:
            i += 1; continue
        mj = mod[j]
        if sess == 1 and not (mj >= 570 and mj <= 930):
            i += 1; continue
        if sess == 2 and not (mj >= 570 and mj <= 690):
            i += 1; continue
        e = o[j]; st = sl * a[i]; S = e - s * st; T = e + s * tp * a[i]; px = np.nan; k = j
        while True:
            if (l[k] <= S) if s == 1 else (h[k] >= S):
                px = (min(o[k], S) if s == 1 else max(o[k], S)) if k > j else S; break
            if k > j and ((h[k] >= T) if s == 1 else (l[k] <= T)):
                px = max(o[k], T) if s == 1 else min(o[k], T); break
            if k + 1 >= n:
                px = c[k]; break
            if roll[k + 1]:
                px = c[k]; break
            if sess != 0 and mod[k] < 960 and (mod[k + 1] >= 960 or mod[k + 1] < mod[k]):
                px = c[k]; break
            k += 1
        cost = cx * 2.25 * e / 17000.0
        oi[nt] = j; ox[nt] = k; orr[nt] = (s * (px - e) - cost) / st; osd[nt] = s; nt += 1
        i = k + 1
    return oi[:nt], ox[:nt], orr[:nt], osd[:nt]
