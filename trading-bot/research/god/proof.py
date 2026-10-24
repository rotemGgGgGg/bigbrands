"""Proof pack for the final 'God' portfolio (picked by portfolio.py under STRESS = strict fills + 2x costs):
  NW30598 (w 0.5R) + GFB1906 (w 0.5R) + PF306 (w 2R) + OPX37 (w 2R).
Outputs: per-period / per-year results (nominal and stressed costs), NW 1-minute replay, random-entry and placebo controls,
Deflated Sharpe Ratio over every variant tried, bootstrap drawdown."""
import os, sys, pickle
os.environ["STRESS"] = "1"
import numpy as np, pandas as pd
from scipy.stats import norm, skew, kurtosis
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import components as K
import nowick as N
from numba import njit
W = dict(NW=0.5, GFB=0.5, PF=2.0, OPX=2.0)
NW_ID, GFB_ID, PF_ID, OPX_ID = 30598, 1906, 306, 37


def trades(cx, thru):
    """trade lists (date, R) for the four components at the given cost multiplier / fill strictness."""
    K.CX, K.THRU = cx, thru
    out = {}
    cfg = K.NW_CFGS[NW_ID]; A = K.nw_arrays(cfg["tf"]); w0, w1 = cfg["win"]; wm = (A["mins"] >= w0) & (A["mins"] < w1)
    sl = A["bull"] & (A["lw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["up"][cfg["filt"]] & wm
    ss = A["bear"] & (A["uw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["dn"][cfg["filt"]] & wm
    cf, cmin = N.COST["NQ"]
    ti, R = N.sim(A["o"], A["h"], A["l"], A["c"], A["atr"], A["sess"], A["last"], sl, ss, 0.0, 0, cfg["expiry"], cfg["stopk"], cfg["rr"], 0,
                  cf * cx, cmin * cx, thru, cfg["side"])
    out["NW"] = pd.DataFrame(dict(date=pd.DatetimeIndex(A["day"][ti]), R=R))
    from sess24 import t2m
    d, g, O, H, L, C, AA, score = K.gfb_arrays(); c = K.GFB_CFGS[GFB_ID]
    ii, R = K.gfb_sim(g, O, H, L, C, AA, score, c["orm"], c["stopk"], c["trail"], c["be"], c["cut"], c["gmin"], c["smin"], cx)
    out["GFB"] = pd.DataFrame(dict(date=d[ii], R=R))
    d, X = K.x24(); import itertools
    c = [dict(zip(K.PFG, v)) for v in itertools.product(*K.PFG.values())][PF_ID]; t0 = t2m(c["w0"])
    pre = X[:, t2m("08:59"), 3] / X[:, t0, 0] - 1; sd = pd.Series(pre).rolling(20).std().shift().values
    ii, R = K.pf_sim(X, sd, t0, t2m("08:59"), t2m("09:00"), c["z"], c["tp"], c["sl"], t2m(c["ex"]) - 1, cx)
    out["PF"] = pd.DataFrame(dict(date=d[ii], R=R))
    c = [dict(zip(K.OPXG, v)) for v in itertools.product(*K.OPXG.values())][OPX_ID]
    opex = np.array([(x.weekday() == 4) and (15 <= x.day <= 21) for x in d])
    sig = pd.Series(np.abs(X[:, t2m("15:55"), 3] / X[:, t2m("09:30"), 0] - 1)).rolling(14).mean().shift().values
    ii, R = K.opx_sim(X, opex, sig, t2m(c["te"]), c["sl"], c["tpm"], t2m(c["ex"]) - 1, cx)
    out["OPX"] = pd.DataFrame(dict(date=d[ii], R=R))
    return out


def daily(T):
    s = sum((W[c] * T[c].groupby("date").R.sum()).reindex(sorted(set().union(*[set(v.date) for v in T.values()]))).fillna(0) for c in T)
    return s.sort_index()


def pstats(x, n_tr=None):
    x = x[x.index.weekday < 5]; eq = x.cumsum(); dd = (eq.cummax() - eq).max(); y = x.groupby(x.index.year).sum()
    return dict(R_yr=x.mean() * 252, sharpe=x.mean() / x.std() * np.sqrt(252), maxDD=dd, yrs_pos=f"{(y > 0).sum()}/{len(y)}", worst_yr=y.min())


def comp_table(T):
    rows = []
    for c, t in T.items():
        y = t.date.dt.year
        for nm, m in (("2010-19", y <= 2019), ("2020-23", (y >= 2020) & (y <= 2023)), ("2024-26", y >= 2024), ("all", y > 0)):
            r = t.R[m]; rows.append(dict(comp=c, period=nm, n=len(r), per_yr=len(r) / max(y[m].nunique(), 1), win=100 * (r > 0).mean(),
                                         avgW=r[r > 0].mean(), avgL=r[r <= 0].mean(), R=r.mean(), tot=r.sum()))
    return pd.DataFrame(rows)


def random_control(seeds=30):
    """NW exits/filters kept, but the no-wick signal replaced by random bars from the same window (same count)."""
    cfg = K.NW_CFGS[NW_ID]; A = K.nw_arrays(cfg["tf"]); w0, w1 = cfg["win"]; wm = (A["mins"] >= w0) & (A["mins"] < w1)
    real = A["bull"] & (A["lw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["up"][cfg["filt"]] & wm
    pool = np.nonzero(A["bull"] & A["up"][cfg["filt"]] & wm)[0]; cf, cmin = N.COST["NQ"]; res = []
    for sd in range(seeds):
        rs = np.random.default_rng(sd); m = np.zeros(len(real), bool); m[rs.choice(pool, real.sum(), replace=False)] = True
        ti, R = N.sim(A["o"], A["h"], A["l"], A["c"], A["atr"], A["sess"], A["last"], m, np.zeros(len(m), bool), 0.0, 0, cfg["expiry"],
                      cfg["stopk"], cfg["rr"], 0, cf * 2, cmin * 2, 0.25, 1)
        res.append(R.mean())
    return np.array(res)


@njit(cache=True)
def run1m(o1, h1, l1, c1, s1, last1, end_, sigL, O_, atr, k, rr, exp1, thru, cf, cmin):
    n = len(end_); outt = np.empty(n, np.int64); outr = np.empty(n); nt = 0; busy = -1
    for i in range(n):
        if not sigL[i] or not atr[i] > 0 or end_[i] <= busy: continue
        L = O_[i]; S = L - k * atr[i]; a = end_[i] + 1; j = -1
        for m in range(a, min(a + exp1, len(o1))):
            if s1[m] != s1[end_[i]]: break
            if l1[m] <= L - thru:
                j = m; break
        if j < 0: continue
        e = min(o1[j], L); risk = e - S
        if risk <= 0: continue
        T = e + rr * risk; m = j
        while True:
            if l1[m] <= S:
                px = S if m == j else min(o1[m], S); break
            if m > j and h1[m] >= T + thru:
                px = max(o1[m], T); break
            if last1[m] or m == len(o1) - 1:
                px = c1[m]; break
            m += 1
        outt[nt] = j; outr[nt] = (px - e - max(cf * e, cmin)) / risk; nt += 1; busy = m
    return outt[:nt], outr[:nt]


def replay_1m():
    cfg = K.NW_CFGS[NW_ID]; tf = cfg["tf"]
    B1 = N.bars("NQ", 1); d1 = pd.DatetimeIndex(B1.day); s1 = d1.values.astype("datetime64[D]").astype(np.int64)
    last1 = np.r_[s1[1:] != s1[:-1], True]; first = np.r_[True, s1[1:] != s1[:-1]]; idx = np.arange(len(B1))
    m1 = idx - np.maximum.accumulate(np.where(first, idx, 0)); code1 = s1 * 10000 + m1 // tf
    A = K.nw_arrays(tf); first3 = np.r_[True, A["sess"][1:] != A["sess"][:-1]]; i3 = np.arange(len(A["o"]))
    code3 = A["sess"] * 10000 + (i3 - np.maximum.accumulate(np.where(first3, i3, 0)))
    end_ = np.searchsorted(code1, code3, side="right") - 1; ok = code1[end_] == code3
    w0, w1 = cfg["win"]; wm = (A["mins"] >= w0) & (A["mins"] < w1)
    sl = A["bull"] & (A["lw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["up"][cfg["filt"]] & wm & ok
    cf, cmin = N.COST["NQ"]; out = {}
    for cx in (1, 2):
        t, R = run1m(*(B1[x].values for x in "ohlc"), s1, last1, end_, sl, A["o"], A["atr"], cfg["stopk"], cfg["rr"], cfg["expiry"] * tf,
                     0.25, cf * cx, cmin * cx)
        out[cx] = pd.DataFrame(dict(date=d1[t], R=R))
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 250); res = {}
    Tn = trades(1.0, 0.0); Ts = trades(2.0, 0.25)
    for nm, T in (("nominal", Tn), ("stress (strict fill + 2x cost)", Ts)):
        print(f"\n=== {nm} — components"); print(comp_table(T).round(3).to_string(index=False))
        x = daily(T)
        print("portfolio:", {p: {k: (round(v, 2) if isinstance(v, float) else v) for k, v in pstats(x[(x.index.year >= a) & (x.index.year <= b)]).items()}
                             for p, (a, b) in {"2010-19": (2010, 2019), "2020-23": (2020, 2023), "2024-26": (2024, 2026), "all": (2010, 2026)}.items()})
        print("per year R:", x.groupby(x.index.year).sum().round(1).to_dict())
        res[nm] = x
    pickle.dump(dict(Tn=Tn, Ts=Ts, xn=res["nominal"], xs=res["stress (strict fill + 2x cost)"]), open(K.SP + "proof.pkl", "wb"))
    # controls
    rc = random_control(); real = Ts["NW"].R.mean()
    print(f"\nNW random-entry control (strict+2x): mean {rc.mean():+.3f}R, max of 30 seeds {rc.max():+.3f}R  vs real {real:+.3f}R")
    rp = replay_1m()
    for cx, t in rp.items():
        y = t.date.dt.year; print(f"NW 1-min replay cost x{cx}: n={len(t)} R={t.R.mean():+.3f} yrs+ {(t.groupby(y).R.sum() > 0).sum()}/{y.nunique()} "
                                  f"tr {t.R[y <= 2019].mean():+.3f} va {t.R[(y >= 2020) & (y <= 2023)].mean():+.3f} te {t.R[y >= 2024].mean():+.3f}")
    # Deflated Sharpe on TRAIN, number of trials = everything tried in this project stage
    P = pd.read_csv(K.SP + "portfolios.csv.gz", usecols=["sh_tr"]); n_trials = 2 * 128358 + 2 * 581931
    x = res["stress (strict fill + 2x cost)"]; xt = x[x.index.year <= 2019]; xt = xt[xt.index.weekday < 5]
    sr = xt.mean() / xt.std(); v = (P.sh_tr / np.sqrt(252)).var(); g = 0.5772156649
    e_max = np.sqrt(v) * ((1 - g) * norm.ppf(1 - 1 / n_trials) + g * norm.ppf(1 - 1 / (n_trials * np.e)))
    dsr = norm.cdf((sr - e_max) * np.sqrt(len(xt) - 1) / np.sqrt(1 - skew(xt) * sr + (kurtosis(xt, fisher=False) - 1) / 4 * sr ** 2))
    xte = x[x.index.year >= 2024]; xte = xte[xte.index.weekday < 5]; t_te = xte.mean() / xte.std() * np.sqrt(len(xte))
    print(f"\nDeflated Sharpe (train, {n_trials:,} trials): SR/day {sr:.3f} vs expected max under null {e_max:.3f} -> DSR = {dsr:.6f}")
    print(f"TEST 2024-26 (never used for selection): daily t-stat {t_te:.2f}, p ≈ {2 * (1 - norm.cdf(abs(t_te))):.2e}")
    # bootstrap drawdown (stress)
    xa = x[x.index.weekday < 5].values; rs = np.random.default_rng(0); dds = []
    for _ in range(2000):
        s = rs.choice(xa, len(xa)); eq = np.cumsum(s); dds.append((np.maximum.accumulate(eq) - eq).max())
    print(f"bootstrap max DD (stress, 16y, 2000 paths): median {np.median(dds):.1f}R, 95% {np.percentile(dds, 95):.1f}R, 99% {np.percentile(dds, 99):.1f}R")
