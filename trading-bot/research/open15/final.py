"""Finalists = top-3 distinct families by 2020-2023 validation t (chosen before looking at the holdout).
Full re-simulation, coin flips (random days / random direction, 500 draws, 2012-2023), 2x costs, per-year $ with 1 MNQ."""
import sys, numpy as np, pandas as pd
import o15 as S
sys.path.insert(0, "../papers"); import engine as E
FIN = [(1, "gap", 0.618, -1, "stp", 89, np.inf, 0.5, ("with", "against", "large")),
       (15, "or", 1.272, 1, "stp", 389, np.inf, 2.0, ("with", "with", "small")),
       (5, "or", 2.618, 1, "stp", 389, 1.0, 3.0, ("any", "with", "small"))]
rng = np.random.default_rng(15); YR = S.YR
for K, a, x, sd, et, tx, st, tg, fl in FIN:
    g = S.group(K, a, x, sd, et, detail=(tx, st, tg)); F = S.filters(K, sd)[:, S.FILT.index(fl)].astype(bool)
    d = g["d"][F[g["d"]]]; net = g["net"][d]; R = g["R"][d]; fp = g["fp"][d]
    cost = S.COST[d]; net2 = net - cost
    T = dict(d=d, dir=np.full(len(d), sd), fm=g["fm"][d], fp=fp, sd=np.full(len(d), np.nan) if np.isinf(st) else st * R,
             td=tg * R, tx=np.full(len(d), tx), net=net)
    m = YR[d] <= 2023; Tm = {k: v[m] for k, v in T.items()}
    _, p_days, p_dir = E.intraday_null(S.D, Tm, np.nonzero(YR <= 2023)[0], 500, rng)
    w = net > 0; print(f"\n{'SHORT' if sd < 0 else 'LONG'} K={K} {a} fib {x} {et} exit={tx} stop={st} tgt={tg} filt={fl}")
    print(f"trades {len(d)} ({len(d)/14.8:.0f}/yr) win {100*w.mean():.1f}% R:R {net[w].mean()/-net[~w].mean():.2f} | "
          f"coin flip p(random days)={p_days:.3f} p(random dir)={p_dir:.3f} | 2x cost total {net2.sum()*2:,.0f}$ vs 1x {net.sum()*2:,.0f}$")
    print(pd.Series(net * 2).groupby(YR[d]).sum().round(0).astype(int).to_dict())
