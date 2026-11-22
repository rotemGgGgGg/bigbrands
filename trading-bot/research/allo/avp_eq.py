"""THE AVP EQUATION - meta-labelling (Lopez de Prado): the AVP signal decides WHERE, a linear equation decides WHETHER.
Every signal of the exact Pine port (NQ, real Dukascopy volume, 5-minute) gets 9 features known at the signal bar:
  x1 side            +1 long / -1 short
  x2 zone width      (top-bottom) / ATR14 of sessions
  x3 emptiness       1 - LVN mean volume / local peak   (how empty the node is)
  x4 risk            |entry - stop| / ATR
  x5 trend           side x sign(close - 50-session average close)
  x6 day move        side x (close - session open) / ATR        (with or against today's move)
  x7 bar volume      signal bar volume / average of the last 20 bars
  x8 New York        1 if 09:30-16:00 NY
  x9 London          1 if 02:00-09:30 NY
Label = R per trade after costs (1 NQ point round trip). Equation fitted by ridge regression on 2012-19 ONLY (standardised x).
Rule: take the signal when E[R] > 0 (and a stricter 'top 30% of 2012-19 predictions' cut). Judged once on 2020-26.
Random check: the same equation with its coefficients' signs/feature mapping shuffled (permute predictions within 2020-26, 1,000x)."""
import sys, os, math, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import avp_port as P
FEAT = ["side", "zone_width", "emptiness", "risk", "trend", "day_move", "bar_volume", "NY", "London"]


def zones_d(h, l, v, n_rows=150, thr=0.35, win=20, min_run=3):
    lo, hi = l.min(), h.max(); rowH = (hi - lo) / n_rows
    if rowH <= 0: return []
    a = np.clip(((l - lo) / rowH).astype(int), 0, n_rows - 1); b = np.clip(((h - lo) / rowH).astype(int), 0, n_rows - 1)
    per = v / (b - a + 1); prof = np.zeros(n_rows + 1); np.add.at(prof, a, per); np.add.at(prof, b + 1, -per); prof = np.cumsum(prof)[:n_rows]
    s = prof.copy(); cnt = np.ones(n_rows); s[1:] += prof[:-1]; cnt[1:] += 1; s[:-1] += prof[1:]; cnt[:-1] += 1; sm = s / cnt
    pk = pd.Series(sm).rolling(2 * win + 1, center=True, min_periods=1).max().values
    idx = np.arange(n_rows); low = (sm < thr * pk) & (idx > 3) & (idx < n_rows - 4); Z = []; r = 0
    while r < n_rows:
        if low[r]:
            e = r
            while e + 1 < n_rows and low[e + 1]: e += 1
            if e - r + 1 >= min_run: Z.append((lo + r * rowH, lo + (e + 1) * rowH, 1 - sm[r:e + 1].mean() / max(pk[r:e + 1].mean(), 1e-12)))
            r = e + 1
        else: r += 1
    return Z


def collect(sym="USATECHIDXUSD", tf=5, rr=2.0, buf=2.0, n_sess=5):
    B = P.bars(sym, tf); O, Hh, L, C, V = (B[k].values for k in "ohlcv"); S = B.sess.values; T = B.index
    starts = np.r_[0, np.nonzero(S[1:] != S[:-1])[0] + 1]; ends = np.r_[starts[1:], len(B)]
    srange = np.array([Hh[a:b].max() - L[a:b].min() for a, b in zip(starts, ends)]); sclose = np.array([C[b - 1] for b in ends])
    atr = pd.Series(srange).rolling(14).mean().shift(1).values; sma = pd.Series(sclose).rolling(50).mean().shift(1).values
    v20 = pd.Series(V).rolling(20).mean().shift(1).values; mins = T.hour * 60 + T.minute
    res = []; openT = []
    for si in range(len(starts)):
        a, e_ = starts[si], ends[si]
        Z = zones_d(Hh[starts[si - n_sess]:a], L[starts[si - n_sess]:a], V[starts[si - n_sess]:a]) if si >= n_sess else []
        usedL = [False] * len(Z); usedS = [False] * len(Z)
        for i in range(a, e_):
            keep = []
            for tr in openT:
                en, st, tg, d = tr["entry"], tr["stop"], tr["tgt"], tr["side"]
                if (d == 1 and L[i] <= st) or (d == -1 and Hh[i] >= st): tr["R"] = -1.0
                elif (d == 1 and Hh[i] >= tg) or (d == -1 and L[i] <= tg): tr["R"] = rr
                elif i == a: tr["R"] = d * (O[i] - en) / abs(en - st)
                else: keep.append(tr); continue
                res.append(tr)
            openT = keep
            if i == 0 or not Z or not np.isfinite(atr[si]) or not np.isfinite(sma[si]): continue
            sig = None
            for k, (bot, top, emp) in enumerate(Z):
                if sig is None and not usedL[k] and C[i - 1] > top and L[i] <= top and C[i] > top:
                    sig = (1, min(bot, L[i]) - buf, bot, top, emp); usedL[k] = True
                if not usedS[k] and C[i - 1] < bot and Hh[i] >= bot and C[i] < bot:
                    usedS[k] = True
                    if sig is None: sig = (-1, max(top, Hh[i]) + buf, bot, top, emp)
            if sig is None: continue
            d, st, bot, top, emp = sig; en = C[i]; rk = abs(en - st); A = atr[si]
            if rk <= 0: continue
            m = mins[i]
            openT.append(dict(t=T[i], entry=en, stop=st, tgt=en + d * rr * rk, side=d, zone_width=(top - bot) / A, emptiness=emp, risk=rk / A,
                              trend=d * np.sign(en - sma[si]), day_move=d * (en - O[a]) / A, bar_volume=V[i] / v20[i] if v20[i] > 0 else 1.0,
                              NY=float(570 <= m < 960), London=float(120 <= m < 570)))
    D = pd.DataFrame(res).set_index("t").sort_index(); D["R_cost"] = D.R - P.COST[sym] / (D.entry - D.stop).abs()
    return D


def tst(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0


if __name__ == "__main__":
    D = collect(); Y = D.index.year; I, O = D[Y <= 2019], D[Y >= 2020]
    X = I[FEAT].values; mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1
    Z = (X - mu) / sd; y = I.R_cost.values; lam = 50.0
    A = np.c_[np.ones(len(Z)), Z]; beta = np.linalg.solve(A.T @ A + lam * np.diag([0] + [1] * len(FEAT)), A.T @ y)
    def pred(df): return np.c_[np.ones(len(df)), (df[FEAT].values - mu) / sd] @ beta
    pI, pO = pred(I), pred(O); cut = np.quantile(pI, 0.70)
    print(f"signals: 2012-19 {len(I)}, 2020-26 {len(O)} | all signals after costs: IS {I.R_cost.mean():+.3f}R, OOS {O.R_cost.mean():+.3f}R")
    print("\nEQUATION (standardised inputs z = (x - mean_2012-19) / sd_2012-19):")
    print(f"  E[R] = {beta[0]:+.4f}" + "".join(f" {b:+.4f}*z({f})" for b, f in zip(beta[1:], FEAT)))
    print("  in raw units: E[R] = " + f"{beta[0] - np.sum(beta[1:] * mu / sd):+.4f}" + "".join(f" {b / s:+.4f}*{f}" for b, s, f in zip(beta[1:], sd, FEAT)))
    for lab, ci, co in (("E[R] > 0", 0.0, 0.0), ("top 30% of 2012-19 predictions", cut, cut)):
        si, so = I.R_cost[pI > ci], O.R_cost[pO > co]
        rng = np.random.default_rng(1); nul = np.array([O.R_cost.values[rng.permutation(len(O))[:len(so)]].mean() for _ in range(1000)])
        yy = so.groupby(so.index.year).sum()
        print(f"\nRULE take if {lab}: 2012-19 {len(si)/8:.0f}/yr avg {si.mean():+.3f}R (t {tst(si):.2f}) | 2020-26 {len(so)/6.85:.0f}/yr avg {so.mean():+.3f}R (t {tst(so):.2f}), "
              f"win {100*(O.R[pO>co]>=1.999).mean():.1f}%, positive years {int((yy>0).sum())}/{len(yy)} | random same-size picks: p={np.mean(nul >= so.mean()):.3f}")
        print("  2020-26 by year R:", yy.round(1).to_dict())
    D.to_pickle("/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/avp_eq_data.pkl")
