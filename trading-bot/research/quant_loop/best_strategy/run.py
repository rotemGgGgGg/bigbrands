"""Reproduce the PROVISIONAL best candidate: Pre-Open Fade at planned 1:2. Walk-forward by year (fixed rules — nothing is
refit, the rule has no fitted parameters beyond the 20-day z), bootstrap CIs, cost stress, parameter neighbourhood.
Run:  python trading-bot/research/quant_loop/best_strategy/run.py   (needs scratchpad full1m.pkl, see research_state.md)"""
import sys, os, json
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, "../../hunt"), os.path.join(H, "../..")]
import numpy as np, pandas as pd
from prefade import pre_move, trade
cfg = json.load(open(os.path.join(H, "config.json")))
rng = np.random.default_rng(42)
def run(zt, a, b, extra=1.0, L=60):
    s, z = pre_move(L); out = {}
    for d in z[z.abs() > zt].index:
        out[d] = (trade(d, -int(np.sign(s[d])), abs(s[d]), a, b, 780) - extra) / (b * abs(s[d]))
    return pd.Series(out)
R = run(cfg["z_threshold"], cfg["target_x_move"], cfg["stop_x_move"])
def summ(x):
    w, lo = x[x > 0], x[x <= 0]
    bs = np.array([rng.choice(x.values, len(x)).mean() for _ in range(5000)])
    bw = np.array([(rng.choice(x.values, len(x)) > 0).mean() for _ in range(5000)])
    return dict(n=len(x), win=round(100 * (x > 0).mean(), 1), win_ci95=(round(100 * np.quantile(bw, .025), 1), round(100 * np.quantile(bw, .975), 1)),
                avg_win_R=round(w.mean(), 2), avg_loss_R=round(lo.mean(), 2), realized_rr=round(w.mean() / -lo.mean(), 2),
                exp_R=round(x.mean(), 3), exp_ci95=(round(np.quantile(bs, .025), 3), round(np.quantile(bs, .975), 3)),
                pf=round(w.sum() / -lo.sum(), 2), maxdd_R=round((x.cumsum() - x.cumsum().cummax()).min(), 2),
                max_consec_losses=int(max((len(list(g)) for k, g in __import__("itertools").groupby(x.values <= 0) if k), default=0)))
print("ALL:", summ(R))
for y, x in R.groupby(R.index.year): print(" year", y, {k: v for k, v in summ(x).items() if k in ("n", "win", "realized_rr", "exp_R")})
tz = R.index.tz
for nm, m in (("TRAIN 2020-23", R.index < pd.Timestamp("2024-01-01", tz=tz)),
              ("VAL 2024-25H1", (R.index >= pd.Timestamp("2024-01-01", tz=tz)) & (R.index < pd.Timestamp("2025-07-01", tz=tz))),
              ("TEST 2025H2-26", R.index >= pd.Timestamp("2025-07-01", tz=tz))): print(nm, summ(R[m]))
print("direction long :", summ(R[[pre_move(60)[0][d] < 0 for d in R.index]]))
print("direction short:", summ(R[[pre_move(60)[0][d] > 0 for d in R.index]]))
for ex in (0.0, 2.0, 4.0): print(f"extra cost {ex} pt:", {k: v for k, v in summ(run(2.5, 1.0, 0.5, ex)).items() if k in ("win", "exp_R")})
print("neighbourhood (z, tp, sl=tp/2):")
for zt in (2.0, 2.25, 2.5, 2.75, 3.0):
    for a in (0.75, 1.0, 1.25):
        x = run(zt, a, a / 2); print(f"  z{zt} tp{a}: n {len(x)} win {100*(x>0).mean():.1f} exp {x.mean():+.3f}R")
