"""Fastest way through a LucidFlex 50K evaluation: +$3,000 before the $2,000 end-of-day trailing loss, 50 % consistency
(best day ≤ 50 % of total profit). An evaluation is a barrier problem; the right score is the EXPECTED COST AND TIME UNTIL THE
FIRST PASS including failed attempts: E[cost] = fee / P(pass), E[days] = (1−P)/P · E[days to fail] + E[days to pass].
Approaches (MNQ 1-minute 2020-01 → 2026-10, costs 2.25 pt per MNQ round trip):
  A coin flip at 09:30 with a $ bracket (zero-edge baseline) · B Williams volatility breakout (only edge that stayed ≥ 0 pre-2020)
  C Noise-Area break · D the 3-edge portfolio — each at several sizes, with a daily profit cap so one day never exceeds the
  consistency limit."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, "../influencers"), os.path.join(H, ".."), os.path.join(H, "../winrate"), os.path.join(H, "../hunt")]
import numpy as np, pandas as pd, itertools
from lib import o, h, l, c, N, SIG, VALID, okprev, RANGE, DO, stop_fill, trade, DAYS
FEE = 150.0
def pass_stats(p, cap=None):
    """p: daily $ series (np.array). cap: if set, a day's profit is capped (the trader stops once up `cap` that day — approximated
    by min(day, cap), which is optimistic only for days that later reversed; days are single-trade here so it is exact)."""
    if cap is not None: p = np.minimum(p, cap)
    out = []
    for st in range(0, len(p) - 40, 2):
        bal = peak = best = 0.0; mll = -2000.0
        for k in range(st, len(p)):
            bal += p[k]; best = max(best, p[k]); peak = max(peak, bal); mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
            if bal <= mll: out.append((0, k - st + 1)); break
            if bal >= 3000 and best <= 0.5 * bal: out.append((1, k - st + 1)); break
    a = np.array(out); P = a[:, 0].mean(); dp = a[a[:, 0] == 1, 1].mean() if P > 0 else np.nan; df = a[a[:, 0] == 0, 1].mean() if P < 1 else 0
    Ed = (1 - P) / P * df + dp if P > 0 else np.inf
    return dict(pass_pct=round(100 * P, 1), days_pass=round(dp, 1), days_fail=round(df, 1), exp_days_to_pass=round(Ed, 1), exp_cost=round(FEE / P) if P > 0 else np.inf)
rows = []
# ---- A: coin flip at 09:30 (several seeds), bracket in points per MNQ with q contracts
rng = np.random.default_rng(0)
for stop_pts, tgt_pts, q in itertools.product((20, 40, 75), (30, 60, 120), (5, 10, 20)):
    if tgt_pts * 2 * q > 1500 or stop_pts * 2 * q > 1900: continue
    res = []
    for seed in range(3):
        sides = np.random.default_rng(seed).choice([-1, 1], N); p = np.zeros(N)
        for i in range(N):
            if not VALID[i]: continue
            e = o[i, 0]; r = trade(i, 0, sides[i], e - sides[i] * stop_pts, e + sides[i] * tgt_pts)
            if r: p[i] = q * 2 * r[0]
        res.append(pass_stats(p))
    rows.append(dict(approach="A coin flip", cfg=f"stop {stop_pts} / tgt {tgt_pts} pts × {q} MNQ", **{k: round(np.mean([x[k] for x in res]), 1) for k in res[0]}))
# ---- B: Williams VB, C: Noise-Area first break (hold to close), with sizes
import signals as W
wvb = np.zeros(N)
for i in range(1, N):
    if not okprev[i]: continue
    r_ = RANGE[i - 1]; a, b = stop_fill(i, 1, 384, DO[i] + 0.6 * r_, 1), stop_fill(i, 1, 384, DO[i] - 0.6 * r_, -1)
    f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
    if f: (m, px), s = f; t = trade(i, m, s, px - s * 0.5 * r_, None, entry=px, at_open=False); wvb[i] = 2 * t[0] if t else 0
na = np.zeros(N)
for i, k0, s, _ in W.sig_na_first():
    t = trade(i, k0, s, None, None); na[i] = 2 * t[0] if t else 0
for name, p1 in (("B Williams VB", wvb), ("C Noise-Area break", na), ("D WVB + NA", wvb + na)):
    for q, cap in itertools.product((1, 2, 3, 5, 8, 10), (None, 1500)):
        rows.append(dict(approach=name, cfg=f"{q} MNQ cap {cap}", **pass_stats(q * p1, cap)))
R = pd.DataFrame(rows); R.to_csv("fastpass.csv", index=False); pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
print(R.sort_values("exp_days_to_pass").head(25).to_string(index=False))
print("\ncheapest expected cost:"); print(R.sort_values("exp_cost").head(10).to_string(index=False))
