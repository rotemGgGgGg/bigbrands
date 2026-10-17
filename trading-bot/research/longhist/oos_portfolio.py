"""Iter 21 — the remaining portfolio edges on TRUE out-of-sample 2012–2019 (HistData NSXUSD RTH grid, cost scaled to price):
Noise-Area first break (hold to close), NA-FVG 92 % variant (TP 0.10σ / SL 1.5σ, conservative fills), Afternoon momentum 15:00,
Rebound after a −1 % day (09:30→12:00, and the 95 % calm/0.075σ variant). Same rules as research/winrate/signals.py."""
import sys; sys.path.insert(0, "."); sys.path.insert(0, "..")
import numpy as np, pandas as pd
from load import frame, RTH
from engine import walk
f = frame("NSXUSD"); f = f[f.index.notna()][:"2019-12-31"]; D = RTH(f); N = len(D.days)
o, h, l, c = D.o, D.h, D.l, D.c; yrs = np.array([d.year for d in D.days])
cost = lambda e: 2.25 * e / 17000; TICK = 0.25
move = np.abs(c / o[:, :1] - 1); day_sig = pd.Series(move[:, 389]).rolling(14).mean().shift().values
pc = np.r_[np.nan, c[:-1, 389]]; ppc = np.r_[np.nan, np.nan, c[:-2, 389]]
gapd = np.r_[99, np.diff(pd.to_datetime(D.days).values).astype("timedelta64[D]").astype(int)]; valid = gapd <= 4
rng_prev = pd.Series(h.max(1) - l.min(1)); rsig = (rng_prev / o[:, 0]).rolling(14).mean().shift().values
vol_ratio = (rng_prev / o[:, 0]).shift().values / rsig
def report(name, p, unit="pts"):
    p = pd.Series(p); w = p[p > 0]; lo = p[p <= 0]; y = p.index.map(lambda i: yrs[i])
    print(f"{name}: n {len(p)} ({len(p)/8:.0f}/yr) win {100*(p>0).mean():.1f}% RR {w.mean()/-lo.mean():.2f} "
          f"mean {p.mean():+.3f} {unit} t {p.mean()/p.std()*np.sqrt(len(p)):.2f} years+ {(p.groupby(y).sum()>0).sum()}/8")
marks = [29 + 30 * j for j in range(12)]
na = []
for i in range(14, N):
    if not valid[i] or np.isnan(pc[i]): continue
    sig = move[i - 14:i].mean(0); o0 = o[i, 0]; ub, lb = max(o0, pc[i]) * (1 + sig), min(o0, pc[i]) * (1 - sig)
    for k in marks:
        if c[i, k] > ub[k] or c[i, k] < lb[k]: na.append((i, k + 1, 1 if c[i, k] > ub[k] else -1)); break
R = {}
for i, k, s in na:
    e = o[i, k]; R[i] = (s * (c[i, 384] - e) - cost(e)) / (day_sig[i] * e) if np.isfinite(day_sig[i]) else np.nan
report("Noise-Area first break → close (in σ units)", {k: v for k, v in R.items() if np.isfinite(v)}, "σ")
R = {}
for i, k0, s in na:
    if np.isnan(day_sig[i]): continue
    gap = None; hh, ll = h[i], l[i]
    for j in range(k0 + 2, min(k0 + 60, 388)):
        if gap is None:
            if s == 1 and hh[j - 2] < ll[j]: gap = ll[j]
            if s == -1 and ll[j - 2] > hh[j]: gap = hh[j]
            continue
        if (ll[j] <= gap - TICK) if s == 1 else (hh[j] >= gap + TICK):
            sc = day_sig[i] * gap; px, _, _ = walk(o[i], h[i], l[i], c[i], j, s, gap, gap - s * 1.5 * sc, gap + s * 0.10 * sc, 384, at_open=False)
            R[i] = (s * (px - gap) - cost(gap)) / sc; break
report("NA-FVG 92% variant (TP 0.10σ / SL 1.5σ, in σ units)", R, "σ")
r = c[:, 329] / pc - 1; sd = pd.Series(r).rolling(20).std().shift().values; R = {}
for i in range(N):
    if valid[i] and np.isfinite(sd[i]) and abs(r[i]) > sd[i] and np.isfinite(day_sig[i]):
        s = 1 if r[i] > 0 else -1; e = o[i, 330]; R[i] = (s * (c[i, 384] - e) - cost(e)) / (day_sig[i] * e)
report("Afternoon momentum 15:00 → close (σ units)", R, "σ")
rp = pc / ppc - 1; R = {}; R2 = {}
for i in range(2, N):
    if not (valid[i] and valid[i - 1] and rp[i] < -0.01 and np.isfinite(day_sig[i])): continue
    e = o[i, 0]; R[i] = (c[i, 149] - e - cost(e)) / (day_sig[i] * e)
    if vol_ratio[i] < 1.2:
        lv = o[i, 1] - 0.05 * day_sig[i] * o[i, 0]
        jj = next((x for x in range(1, 384) if l[i, x] <= lv - TICK), None)
        if jj is not None:
            sc = day_sig[i] * o[i, 0]; px, _, _ = walk(o[i], h[i], l[i], c[i], jj, 1, lv, lv - 1.5 * sc, lv + 0.075 * sc, 384, at_open=False)
            R2[i] = (px - lv - cost(lv)) / sc
report("Rebound after −1% day 09:30→12:00 (σ units)", R, "σ")
report("Rebound 95% variant (calm, TP 0.075σ / SL 1.5σ)", R2, "σ")
