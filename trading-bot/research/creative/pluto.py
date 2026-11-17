"""THE PLUTO SEQUENCE (invented, written down before testing) - time and price both cut in fours, aligned at three scales.
Long (short = mirror), NY time:
  C1 at 09:00 price below the daily true open (00:00 open)
  C2 at 09:00 price below the session true open (07:30 open = start of Q2 of the 06:00-12:00 session)
  C3 at 09:00 price in the lower half of yesterday's (00:00-16:00) range
  C4 manipulation: Q2 (07:30-09:00) swept Q1's (06:00-07:30) low
  C5 micro: at 09:45 (Q3 of the 09:00-10:30 quarter) price below the micro true open (09:22:30 ~ the 09:22 bar open)
Entry 09:45 open. Stop below the Q2 manipulation low. Exits: 2R / opposite liquidity (Q1-Q2 high) / time (12:00).
Variants: full (C1-C5), no micro (C1-C4), no sweep (C1-C3 + C5), x 3 exits. Cost 1.3 bp. Choose 2012-19, check 2020-26 + S&P."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../spmodel"))
from lbr import days
BP = 1.3


def run(sym, use, exit_):
    G = days(sym); D = sorted(G); out = {}
    for j in range(1, len(D)):
        d, pd_ = D[j], D[j - 1]
        o, h, l, c = G[d]; po, ph, pl, pc = G[pd_]
        yH, yL = ph.max(), pl.min(); mid = (yH + yL) / 2
        p9 = o[540]; dTO, sTO, mTO = o[0], o[450], o[562]; e = o[585]
        q1h, q1l = h[360:450].max(), l[360:450].min(); q2h, q2l = h[450:540].max(), l[450:540].min()
        for s in (1, -1):
            c1 = p9 < dTO if s == 1 else p9 > dTO
            c2 = p9 < sTO if s == 1 else p9 > sTO
            c3 = p9 < mid if s == 1 else p9 > mid
            c4 = q2l < q1l if s == 1 else q2h > q1h
            c5 = e < mTO if s == 1 else e > mTO
            need = {"full": (c1, c2, c3, c4, c5), "no micro": (c1, c2, c3, c4), "no sweep": (c1, c2, c3, c5)}[use]
            if not all(need): continue
            stop = (min(q2l, l[540:585].min()) if s == 1 else max(q2h, h[540:585].max())) - s * 0.25
            risk = s * (e - stop)
            if risk < e * 0.0015: continue                                  # stop at least ~0.15% away (else costs dominate)
            tg = {"2R": e + s * 2 * risk, "liquidity": max(q1h, q2h) if s == 1 else min(q1l, q2l), "12:00": None}[exit_]
            if tg is not None and s * (tg - e) <= 0: tg = e + s * risk
            hh, ll = h[585:720], l[585:720]
            hs = np.nonzero(ll <= stop)[0] if s == 1 else np.nonzero(hh >= stop)[0]
            ht = (np.nonzero(hh >= tg)[0] if s == 1 else np.nonzero(ll <= tg)[0]) if tg is not None else np.array([], int)
            ts, tt = (hs[0] if len(hs) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
            px = stop if ts <= tt and ts < 10 ** 9 else (tg if tt < 10 ** 9 else c[719])
            out[d] = (s * (px - e) - e * BP / 1e4) / risk
            break
    return pd.Series(out, dtype=float)


def st(s):
    if len(s) < 5: return {"n": len(s)}
    t = lambda x: x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0
    Y = s.index.year; I, O, L2 = s[Y <= 2019], s[Y >= 2020], s[s.index >= "2024-10-24"]
    return dict(per_yr=round(len(s) / 14.8, 1), win=round(100 * (s > 0).mean(), 1), rr=round(s[s > 0].mean() / -s[s < 0].mean(), 2),
                IS_R=round(I.mean(), 3), IS_t=round(t(I), 2), OOS_R=round(O.mean(), 3), OOS_t=round(t(O), 2),
                last2y_R=round(L2.mean(), 3), last2y_n=len(L2), pos_yrs=f"{int((s.groupby(Y).sum() > 0).sum())}/15")


if __name__ == "__main__":
    rows = []
    for sym in ("NSXUSD", "SPXUSD"):
        for use, ex in itertools.product(("full", "no micro", "no sweep"), ("2R", "liquidity", "12:00")):
            r = st(run(sym, use, ex)); r.update(market=sym, version=use, exit=ex); rows.append(r)
    T = pd.DataFrame(rows); pd.set_option("display.width", 230)
    print(T[["market", "version", "exit", "per_yr", "win", "rr", "IS_R", "IS_t", "OOS_R", "OOS_t", "last2y_R", "last2y_n", "pos_yrs"]].to_string(index=False))
