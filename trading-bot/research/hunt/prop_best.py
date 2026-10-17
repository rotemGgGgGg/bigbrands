"""Which combination + size passes LucidFlex 50K (target $3K, $2K EOD trailing, 50 % consistency) fastest, with a high pass rate?
Components = daily $ per 1 MNQ (costs incl. +1 pt stress where the source script uses it)."""
import sys, os, itertools; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, ".."), os.path.join(H, "../winrate")]
import numpy as np, pandas as pd
import signals as W
from hiwin import run as hw, volr
from prefade import pre_move, trade
from prop_sim2 import evaluate
idx = pd.to_datetime(pd.Index(W.D.days))
def daily(t):
    return (2 * t.pts.groupby([pd.Timestamp(W.D.days[i]) for i in t.i]).sum()).reindex(idx).fillna(0)
C = {}
C["NAFVG92"] = daily(hw(W.sig_na_fvg(), 0.10, 1.5, "mkt"))
C["Rebound95"] = daily(hw([x for x in W.sig_rebound() if volr[x[0]] < 1.2], 0.075, 1.5, "pull"))
C["Afternoon"] = daily(hw(W.sig_afternoon(), 99, None, "mkt"))          # no target, hold to 15:54
s, z = pre_move(60)
C["PreFade"] = pd.Series({pd.Timestamp(d.date()): 2 * (trade(d, -int(np.sign(s[d])), abs(s[d]), 0.5, 1.0, 780) - 1.0) for d in z[z.abs() > 2].index}).reindex(idx).fillna(0)
def pass_stats(p):
    T = []
    for st in range(0, len(p) - 60, 3):
        bal = peak = best = 0.0; mll = -2000.0
        for i in range(st, len(p)):
            bal += p[i]; best = max(best, p[i]); peak = max(peak, bal); mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
            if bal <= mll: T.append((0, i - st)); break
            if bal >= 3000 and best <= 0.5 * bal: T.append((1, i - st)); break
    if not T: return 0.0, np.nan, np.nan
    T = np.array(T); ok = T[:, 0] == 1
    return 100 * ok.mean(), np.median(T[ok, 1]) if ok.any() else np.nan, np.median(T[~ok, 1]) if (~ok).any() else np.nan
rows = []
names = list(C)
for k in range(1, 5):
    for combo in itertools.combinations(names, k):
        for q in itertools.product((1, 2, 3, 4), repeat=k):
            if max(q) > 4: continue
            p = sum(q[j] * C[c] for j, c in enumerate(combo)).values
            pr, dmed, fmed = pass_stats(p)
            try: ev = evaluate(p, np.minimum(p, 0), range(0, len(p) - 60, 5), keep=1500)
            except ValueError: ev = dict(payout=np.nan, ev=np.nan)
            rows.append(dict(combo=" + ".join(f"{c}×{q[j]}" for j, c in enumerate(combo)), pass_pct=round(pr, 1), days_to_pass=dmed,
                             months=round(dmed / 21, 1) if dmed == dmed else np.nan, payout_pct=ev["payout"], ev_per_acct=ev["ev"],
                             yr_usd=round(p.sum() / 6.75), worst_day=round(p.min())))
R = pd.DataFrame(rows); R.to_csv("prop_best.csv", index=False)
pd.set_option("display.width", 220)
print("pass ≥ 80 %, fastest:"); print(R[R.pass_pct >= 80].sort_values("days_to_pass").head(10).to_string(index=False))
print("\npass ≥ 70 %, fastest:"); print(R[R.pass_pct >= 70].sort_values("days_to_pass").head(8).to_string(index=False))
print("\nbest EV per account:"); print(R.sort_values("ev_per_acct", ascending=False).head(8).to_string(index=False))
