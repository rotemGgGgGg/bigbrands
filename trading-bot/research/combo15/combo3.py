"""Round 3 - no picking at all: every strategy with positive alpha on 2012-2019 (24 of 192), equal risk, beta-hedged.
Out-of-sample significance on 2020-2026, a placebo (the same procedure with eligibility drawn at random), and a prop-firm simulation
(50K eval: $3,000 target, $2,000 end-of-day trailing drawdown locking at +$100, best day <= 50 % of profit; then funded until the
first $1,500 payout) started every 5th trading day of 2020-2026."""
import sys, os, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../papers"))
import numpy as np, pandas as pd
import pdata, combo2 as C
P, Y, BH, S = C.P, C.Y, C.BH, C.S; O = Y >= 2020; RNG = np.random.default_rng(7)


def build(cols):
    sd = {c: P[c][S][P[c][S] != 0].std() for c in cols}; ref = 30.0                                  # 30 pts of daily stdev per strategy
    W = pd.DataFrame({c: P[c] * ref / sd[c] for c in cols}).sum(1); b = np.cov(W[S], BH[S])[0, 1] / BH[S].var()
    return W, W - b * BH, b


def prop(pnl, starts):
    res = []
    for st in starts:
        bal = peak = best = 0.0; floor = -2000.0; ph = None
        for i in range(st, len(pnl)):
            bal += pnl[i]; best = max(best, pnl[i]); peak = max(peak, bal); floor = 100.0 if peak >= 2100 else max(floor, peak - 2000)
            if bal <= floor: res.append(("fail", i - st, None)); break
            if ph is None and bal >= 3000 and best <= .5 * bal: ph = i; bal = peak = best = 0.0; floor = -2000.0; continue
            if ph is not None and bal >= 1500: res.append(("payout", ph - st, i - st)); break
        else: res.append(("open", None, None))
    return pd.DataFrame(res, columns=["r", "d_pass", "d_payout"])


if __name__ == "__main__":
    beta = {c: np.cov(P[c][S], BH[S])[0, 1] / BH[S].var() for c in P.columns}; el = []
    for c in P.columns:
        if (P[c][S] != 0).sum() < 80: continue
        a = (P[c] - beta[c] * BH)[S]; t = a.mean() / a.std() * math.sqrt(len(a))
        if t >= 1.0 and (a.groupby(a.index.year).sum() > 0).sum() >= 5: el.append(c)
    raw, hed, b = build(el); h = hed[O]; t = h.mean() / h.std() * math.sqrt(len(h))
    print(f"ALL {len(el)} alpha-eligible, equal risk: beta {b:.2f}; hedged 2020-26 Sharpe {C.sh(h):.2f}, t = {t:.2f}")
    for nm, x in (("raw", raw), ("hedged", hed)):
        for pn, m in (("2012-19 (select)", S), ("2020-22", C.V), ("2023-26", C.F)): print(f"  {nm:6s} {pn:17s}", C.stats(x, m))
    pl = []
    for _ in range(300):                                   # placebo: 24 strategies drawn at random from the whole pool
        k = list(RNG.choice(P.columns, size=len(el), replace=False)); _, hh, _ = build(k); pl.append(C.sh(hh[O]))
    print(f"placebo (random {len(el)} of all 192): 2020-26 hedged Sharpe median {np.median(pl):.2f}, 95th pct {np.percentile(pl, 95):.2f} -> ours beats {100*np.mean(np.array(pl) < C.sh(h)):.0f}%")
    print("hedged per-year $:", (2 * hed.groupby(Y).sum()).round(0).astype(int).to_dict())
    days = np.nonzero(O)[0]; starts = days[:-60:5]
    for scale in (0.05, 0.1, 0.2):
        T = prop((2 * scale * raw).values, starts); pv = T[T.r == "payout"]
        print(f"prop 50K, raw portfolio x{scale} (~{scale*30*len(el)/30:.1f} MNQ-equivalent risk units): payout {100*len(pv)/len(T):.0f}%, "
              f"fail {100*(T.r=='fail').mean():.0f}%, median days to pass {pv.d_pass.median():.0f}, to payout {pv.d_payout.median():.0f}")
