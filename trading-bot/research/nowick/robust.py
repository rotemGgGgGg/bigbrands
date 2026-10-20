"""Robustness checks for the best no-wick variants: strict fills (price must trade 1 tick THROUGH the level), long vs short,
double costs, per-year table, neighbours of the chosen cell, and the same rule on the other index markets."""
import sys, itertools
import numpy as np, pandas as pd
import nowick as N

TICK = {"NQ": 0.25, "NSXUSD": 0.25, "SPXUSD": 0.25, "GRXEUR": 0.5, "XAUUSD": 0.1}
_cache = {}


def prep(mkt, tf):
    if (mkt, tf) in _cache: return _cache[(mkt, tf)]
    B = N.bars(mkt, tf); o, h, l, c = (B[x].values for x in "ohlc"); day = pd.DatetimeIndex(B.day)
    sess = day.values.astype("datetime64[D]").astype(np.int64); last = np.r_[sess[1:] != sess[:-1], True]
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc))); atr = pd.Series(tr).rolling(14).mean().values
    e20, e50, e200 = N.ema(c, 20), N.ema(c, 50), N.ema(c, 200); e20p = np.r_[e20[0], e20[:-1]]
    up = dict(zip(N.FILT, [np.ones(len(c), bool), e20 > e20p, c > e50, e20 > e50, c > e200]))
    dn = dict(zip(N.FILT, [np.ones(len(c), bool), e20 < e20p, c < e50, e20 < e50, c < e200]))
    _cache[(mkt, tf)] = (o, h, l, c, atr, sess, last, up, dn, day); return _cache[(mkt, tf)]


def variant(mkt, tf, tol, filt, level, mode, stopk, rr, expiry, thru=0.0, side=0, costx=1.0):
    o, h, l, c, atr, sess, last, up, dn, day = prep(mkt, tf)
    rng = h - l; lw = np.minimum(o, c) - l; uw = h - np.maximum(o, c); eps = 1e-9 * c
    if tol == "placebo":
        sl = (c > o) & (lw >= 0.2 * rng) & (lw <= 0.6 * rng); ss = (c < o) & (uw >= 0.2 * rng) & (uw <= 0.6 * rng)
    else:
        sl = (c > o) & (lw <= float(tol) * rng + eps); ss = (c < o) & (uw <= float(tol) * rng + eps)
    cf, cmin = N.COST[mkt]
    ti, R = N.sim(o, h, l, c, atr, sess, last, sl & up[filt], ss & dn[filt], level, mode, expiry, stopk, rr, N.HOLD.get(tf, 0),
                  cf * costx, cmin * costx, thru, side)
    return pd.DataFrame(dict(date=day[ti], R=R))


def summ(T, label):
    y = T.date.dt.year; out = dict(label=label, n=len(T), per_yr=len(T) / max(y.nunique(), 1), win=100 * (T.R > 0).mean(), R=T.R.mean(),
                                   tot=T.R.sum(), t=T.R.mean() / T.R.std() * np.sqrt(len(T)))
    eq = T.R.cumsum().values; out["dd"] = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    out["yrs_pos"] = f"{(T.groupby(y).R.sum() > 0).sum()}/{y.nunique()}"
    for nm, m in (("tr", y <= 2019), ("va", (y >= 2020) & (y <= 2023)), ("te", y >= 2024)): out[nm + "_R"] = T.R[m].mean()
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    best = dict(mkt="NQ", tf=5, tol="0.1", filt="c>ema200", level=0.0, mode=0, stopk=1.0, rr=3.0, expiry=50)
    rows = []
    for mkt in ("NQ", "NSXUSD", "SPXUSD", "GRXEUR", "XAUUSD"):
        b = dict(best, mkt=mkt); tk = TICK[mkt]
        rows.append(summ(variant(**b), f"{mkt} base"))
        rows.append(summ(variant(**b, thru=tk), f"{mkt} fill needs 1 tick through"))
        rows.append(summ(variant(**b, thru=tk, costx=2), f"{mkt} 1 tick through + 2x costs"))
        rows.append(summ(variant(**b, side=1), f"{mkt} longs only"))
        rows.append(summ(variant(**b, side=-1), f"{mkt} shorts only"))
        rows.append(summ(variant(**dict(b, tol="placebo")), f"{mkt} placebo (normal wick)"))
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    # neighbours of the NQ cell (strict fill)
    nb = []
    for k, vals in dict(tf=(3, 5, 15), stopk=(0.5, 1.0), rr=(2.0, 3.0), expiry=(10, 50), filt=N.FILT, tol=("0.05", "0.1")).items():
        for v in vals:
            b = dict(best, **{k: v}); nb.append(summ(variant(**b, thru=0.25), f"{k}={v}"))
    print("\nNQ neighbours (strict fill):"); print(pd.DataFrame(nb).round(3).to_string(index=False))
    T = variant(**best, thru=0.25); y = T.date.dt.year
    Y = T.groupby(y).R.agg(n="size", win=lambda r: 100 * (r > 0).mean(), R="mean", tot="sum")
    print("\nNQ per year (strict fill):"); print(Y.round(3).to_string())
    T.to_csv("best_trades_NQ.csv", index=False)
