"""REVERSAL-DAY MOMENTUM (RDM) - the family both theory factories converged on, made tradeable.
Signal at 09:45 NY: today = sign(09:45 price - 09:00 open), yesterday = sign(yesterday's RTH close - RTH open).
If they disagree -> trade in today's direction from 09:45, flat at 15:55.
Stops (choose on 2012-19): none / k x ATR (0.5, 0.75, 1.0) / structural (back through the 09:00 open +- 0.1 ATR) /
trailing 0.75 ATR. Regime: all days vs high-volatility days only (ATR above its 60-day median).
Sizing for a 50K prop account: fixed $ risk per trade -> MNQ contracts = risk / (stop distance x $2), at least 1.
Prop rules: $3,000 target, $2,000 EOD trailing drawdown (locks at +$100), best day <= 50% of profit, then a $1,500 payout.
Cost: 1.3 bp of price per trade (CFD-level; real MNQ is cheaper)."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../spmodel"))
from lbr import days
BP = 1.3; G = days("NSXUSD"); DL = sorted(G)
RNG = pd.Series({d: G[d][1][570:960].max() - G[d][2][570:960].min() for d in DL}); ATR = RNG.rolling(14).mean().shift(1); ATRM = ATR.rolling(60).median()


def trades(stop, regime):
    out = []
    for j in range(1, len(DL)):
        d = DL[j]; A = ATR.get(d)
        if not np.isfinite(A): continue
        if regime == "high vol" and not (A > ATRM.get(d, np.inf)): continue
        o, h, l, c = G[d]; po, ph, pl, pc = G[DL[j - 1]]
        yd = np.sign(pc[959] - po[570]); td = np.sign(o[585] - o[540])
        if yd == 0 or td == 0 or yd == td: continue
        s = td; e = o[585]
        if stop == "none": sl = e - s * 1.5 * A
        elif stop.startswith("atr"): sl = e - s * float(stop[3:]) * A
        elif stop == "struct": sl = o[540] - s * 0.1 * A
        else: sl = e - s * 0.75 * A                                      # trail start
        risk = s * (e - sl)
        if risk <= e * 0.0005: continue
        hh, ll, cc = h[585:955], l[585:955], c[585:955]
        if stop == "trail":
            best = np.maximum.accumulate(hh) if s == 1 else np.minimum.accumulate(ll); lvl = best - s * 0.75 * A
            lvl = np.r_[sl, lvl[:-1]]; hit = np.nonzero(ll <= lvl)[0] if s == 1 else np.nonzero(hh >= lvl)[0]
            px = lvl[hit[0]] if len(hit) else cc[-1]
        else:
            hit = np.nonzero(ll <= sl)[0] if s == 1 else np.nonzero(hh >= sl)[0]
            px = sl if (len(hit) and stop != "none") else cc[-1]
        out.append(dict(day=d, side=s, entry=e, risk_pts=risk, pts=s * (px - e) - e * BP / 1e4))
    T = pd.DataFrame(out).set_index("day"); T["R"] = T.pts / T.risk_pts; return T


def prop(T, risk_usd):
    pnl = []
    for _, r in T.iterrows():
        n = max(1, int(risk_usd // (r.risk_pts * 2))); pnl.append(n * r.pts * 2)
    pnl = pd.Series(pnl, index=T.index); x = pnl[pnl.index.year >= 2020].values; res = []
    for st in range(0, len(x) - 40, 10):
        bal = peak = best = 0.0; floor = -2000.0; ph = None
        for i in range(st, len(x)):
            bal += x[i]; best = max(best, x[i]); peak = max(peak, bal); floor = 100.0 if peak >= 2100 else max(floor, peak - 2000)
            if bal <= floor: res.append(("fail", None)); break
            if ph is None and bal >= 3000 and best <= .5 * bal: ph = i; bal = peak = best = 0.0; floor = -2000.0; continue
            if ph is not None and bal >= 1500: res.append(("payout", i - st)); break
        else: res.append(("open", None))
    R = pd.DataFrame(res, columns=["r", "n"]); pv = R[R.r == "payout"]
    return f"payout {100*len(pv)/len(R):.0f}% fail {100*(R.r=='fail').mean():.0f}% (median {pv.n.median():.0f} trades to payout) | $/yr per {risk_usd}$-risk unit: {pnl[pnl.index.year>=2020].sum()/6.8:,.0f}"


if __name__ == "__main__":
    t = lambda x: x.mean() / x.std() * math.sqrt(len(x)); rows = []
    for stop, reg in itertools.product(("none", "atr0.5", "atr0.75", "atr1.0", "struct", "trail"), ("all", "high vol")):
        T = trades(stop, reg); Y = T.index.year; I, O, L2 = T[Y <= 2019], T[Y >= 2020], T[T.index >= "2024-10-24"]
        rows.append(dict(stop=stop, regime=reg, per_yr=len(T) / 14.8, win=100 * (T.R > 0).mean(), rr=T.R[T.R > 0].mean() / -T.R[T.R < 0].mean(),
                         IS_R=I.R.mean(), IS_t=t(I.R), OOS_R=O.R.mean(), OOS_t=t(O.R), last2y_R=L2.R.mean(), pos_yrs=f"{(T.R.groupby(Y).sum()>0).sum()}/15",
                         avg_risk_pts=T.risk_pts.mean()))
    S = pd.DataFrame(rows).sort_values("IS_t", ascending=False); pd.set_option("display.width", 220); print(S.round(3).to_string(index=False))
    b = S.iloc[0]; T = trades(b["stop"], b["regime"]); print(f"\nPICK (best 2012-19): stop {b['stop']} | {b['regime']}")
    print("per year R:", T.R.groupby(T.index.year).sum().round(1).to_dict())
    for risk in (200, 300, 400): print(f"prop 50K, ${risk} risk/trade:", prop(T, risk))
