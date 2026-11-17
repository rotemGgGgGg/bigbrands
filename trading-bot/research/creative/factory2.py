"""THEORY FACTORY v2 - wider grammar: multi-day memory, higher-timeframe opens, regime filters, scheduled-flow days.
Theory = 1-2 signed conditions (mirror long/short) x ONE regime filter (or none) x entry/exit x orientation.
New signed conditions (on top of factory.py's 78): day-before-yesterday direction, yesterday close location (top/bottom
quarter of its range), yesterday's high after its low, overnight return, first 5 minutes, price vs yesterday high/low at
09:45 / 10:30, price vs the week's first open and the month's first open.
Regime filters: none, low / high volatility (ATR vs its 60-day median), small / big London range, Monday, Friday, big gap
(> 0.3 ATR), Gotobi day, FOMC day, first 5 / last 3 trading days of the month, day after a shock (yesterday range > 1.5 ATR).
Same gates: 2012-17 t>=3 & n>=60 -> 2018-21 t>=2 same sign -> 2022-26 once; placebo = shuffled day labels."""
import sys, os, math, itertools, time, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "../macro")); sys.path.insert(0, os.path.join(H, "../gotobi"))
import factory as F1
from factory import G, D, PREVD, ND, Y, BP, SP
import fomc


def more_features():
    F, names, times = [], [], []
    def add(n, t, v): F.append(np.array(v, np.int8)); names.append(n); times.append(t)
    Dl = sorted(G); idx = {d: i for i, d in enumerate(Dl)}
    def prev(d, k): i = idx[d] - k; return Dl[i] if i >= 0 else None
    yd, y2, clv, hl, onr, f5, wk, mo = ([] for _ in range(8))
    vs_yh = {585: [], 630: []}
    for d in D:
        o, h, l, c = G[d]; p1 = prev(d, 1); p2 = prev(d, 2)
        po, ph, pl, pc = G[p1]
        y2.append(0 if p2 is None else int(np.sign(G[p2][3][959] - G[p2][0][570])))
        rH, rL = ph[570:960].max(), pl[570:960].min(); q = (pc[959] - rL) / (rH - rL) if rH > rL else .5
        clv.append(1 if q > .75 else (-1 if q < .25 else 0))
        hl.append(1 if np.argmax(ph[570:960]) > np.argmin(pl[570:960]) else -1)
        onr.append(int(np.sign(o[569] - pc[959])))
        f5.append(int(np.sign(c[574] - o[570])))
        for T in vs_yh:
            vs_yh[T].append(1 if o[T] > ph.max() else (-1 if o[T] < pl.min() else 0))
        w0 = d - pd.Timedelta(days=d.weekday()); wd = [x for x in Dl if w0 <= x <= d][0]
        wk.append(int(np.sign(o[585] - G[wd][0][0])))
        m0 = [x for x in Dl if x.year == d.year and x.month == d.month][0]
        mo.append(int(np.sign(o[585] - G[m0][0][0])))
    add("day-before-yesterday direction", 0, y2); add("yesterday close location (top/bottom quarter)", 0, clv)
    add("yesterday high came after its low", 0, hl); add("overnight return", 570, onr); add("first 5 minutes", 575, f5)
    for T, v in vs_yh.items(): add(f"price@{T//60}:{T%60:02d} beyond yesterday high(+)/low(-)", T, v)
    add("price@9:45 vs week open", 585, wk); add("price@9:45 vs month open", 585, mo)
    return F, names, times


def regimes():
    rng = pd.Series({d: G[d][1][570:960].max() - G[d][2][570:960].min() for d in sorted(G)}); atr = rng.rolling(14).mean().shift(1)
    lr = pd.Series({d: G[d][1][:360].max() - G[d][2][:360].min() for d in sorted(G)}); med = lambda s: s.rolling(60).median().shift(1)
    a, am, l_, lm = (atr.reindex(D).values, med(atr).reindex(D).values, lr.reindex(D).values, med(lr).reindex(D).values)
    gap = np.array([abs(G[d][0][570] - G[PREVD[d]][3][959]) for d in D]); prevr = rng.shift(1).reindex(D).values
    sys.path.insert(0, os.path.join(H, "../gotobi")); from gotobi import trade_days; got = set(trade_days(y0=2012, y1=2026))
    fo = set(fomc.dates()); per = pd.DatetimeIndex(D).to_period("M"); rk = pd.Series(1, index=D).groupby(per).cumsum().values
    rk_end = pd.Series(1, index=D)[::-1].groupby(per[::-1]).cumsum()[::-1].values; wd = np.array([d.weekday() for d in D])
    R = {"none": np.ones(ND, bool), "low vol": a < am, "high vol": a > am, "small London": l_ < 0.7 * lm, "big London": l_ > 1.3 * lm,
         "Monday": wd == 0, "Friday": wd == 4, "big gap": gap > 0.3 * a, "Gotobi day": np.array([d in got for d in D]),
         "FOMC day": np.array([d in fo for d in D]), "first 5 days of month": rk <= 5, "last 3 days of month": rk_end <= 3,
         "day after shock": prevr > 1.5 * a}
    return {k: np.nan_to_num(v).astype(bool) for k, v in R.items()}


def scan(F, names, ftime, R, rlab, et, REG, tag):
    P = [(Y <= 2017), (Y >= 2018) & (Y <= 2021), (Y >= 2022)]; keep = []; total = 0; nF = len(F)
    for rname, rm in REG.items():
        Pm = [p & rm for p in P]; RP = [(R * m).T for m in Pm]; R2P = [((R ** 2) * m).T for m in Pm]; ONE = [m.astype(float) for m in Pm]
        def evaluate(S, combos, tmax):
            nonlocal total
            A = np.abs(S).astype(float); Sf = S.astype(float); cnt = [A @ o for o in ONE]; sm = [Sf @ rp for rp in RP]; sq = [A @ r2 for r2 in R2P]
            valid = tmax[:, None] <= et[None, :]; total += int(valid.sum()) * 2
            for orient in (1, -1):
                out = []
                for k in range(3):
                    n = cnt[k][:, None]; s = orient * sm[k] - BP * n; q = sq[k] - 2 * BP * orient * sm[k] + BP ** 2 * n
                    mu = np.where(n > 0, s / np.maximum(n, 1), 0); var = np.where(n > 1, q / np.maximum(n, 1) - mu ** 2, 0)
                    out.append((n, mu, np.where(var > 0, mu / np.sqrt(np.maximum(var, 1e-12)) * np.sqrt(np.maximum(n, 1)), 0)))
                (n0, m0, t0), (n1, m1, t1), (n2, m2, t2) = out
                ok = valid & (n0 >= 60) & (t0 >= 3) & (t1 >= 2) & (m1 > 0)
                for a, b in zip(*np.nonzero(ok)):
                    keep.append(dict(theory=" & ".join(names[x] for x in combos[a]), regime=rname, trade=rlab[b], orient="with" if orient == 1 else "against",
                                     n_yr=(n0[a, 0] + n1[a, 0] + n2[a, 0]) / 14.8, disc_bp=m0[a, b], disc_t=t0[a, b], val_bp=m1[a, b], val_t=t1[a, b],
                                     final_bp=m2[a, b], final_t=t2[a, b], final_n=int(n2[a, 0])))
        evaluate(F, [(i,) for i in range(nF)], ftime)
        for i in range(nF - 1):
            S = F[i][None, :] * (F[i][None, :] == F[i + 1:]); evaluate(S, [(i, j) for j in range(i + 1, nF)], np.maximum(ftime[i], ftime[i + 1:]))
    K = pd.DataFrame(keep); print(f"[{tag}] theories tested: {total:,} | survived discovery+validation: {len(K)}", flush=True); return K


if __name__ == "__main__":
    for i, d in enumerate(D): F1.PREV_OPEN[i] = G[PREVD[d]][0][570]
    Fa, na, ta = F1.features(); Fb, nb, tb = more_features(); R, rlab, et = F1.rets(); REG = regimes()
    F = np.vstack([Fa, np.stack(Fb)]); names = na + nb; ftime = np.r_[ta, tb]
    print(f"{len(F)} signed conditions x {len(REG)} regimes x {len(rlab)} entry/exit", flush=True)
    t0 = time.time(); K = scan(F, names, ftime, R, rlab, et, REG, "REAL")
    rng = np.random.default_rng(11); Fs = np.stack([f[rng.permutation(ND)] for f in F]); Kp = scan(Fs, names, ftime, R, rlab, et, REG, "PLACEBO")
    print(f"{time.time()-t0:.0f}s"); K.to_csv(SP + "factory2_real.csv", index=False); Kp.to_csv(SP + "factory2_placebo.csv", index=False)
    for lab, X in (("REAL", K), ("PLACEBO", Kp)):
        if len(X): print(f"{lab}: survivors {len(X)}, 2022-26 positive {int((X.final_bp>0).sum())}, final t>=2 {int((X.final_t>=2).sum())}, median final {X.final_bp.median():.2f}bp")
    if len(K):
        K["family"] = K.theory.str.replace(r"@\d+:\d+", "@T", regex=True) + " | " + K.regime + " | " + K.orient
        fam = K.groupby("family").agg(n=("final_bp", "size"), final_pos=("final_bp", lambda s: (s > 0).mean()), final_bp=("final_bp", "median"),
                                      final_t=("final_t", "median"), disc_t=("disc_t", "median"), n_yr=("n_yr", "median")).sort_values(["final_t"], ascending=False)
        pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 110)
        print("\nFAMILIES (median over members):\n", fam.head(40).round(2).to_string())
