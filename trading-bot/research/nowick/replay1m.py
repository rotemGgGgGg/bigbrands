"""Replay of the best NQ cell with 1-minute resolution: signals and ATR/EMA come from closed 5-minute bars, but the limit fill,
stop and target are walked minute by minute (strict: price must trade 1 tick through the level / target). Removes any
optimism from not knowing the order of high and low inside a 5-minute bar."""
import numpy as np, pandas as pd
from numba import njit
import nowick as N
from robust import prep


@njit(cache=True)
def run1m(o1, h1, l1, c1, s1, last1, end5, sigL, sigS, O5, C5, atr, k, rr, exp1, thru, cf, cmin):
    n5 = len(end5); outt = np.empty(n5, np.int64); outr = np.empty(n5); nt = 0; busy = -1
    for i in range(n5):
        s = 1 if sigL[i] else (-1 if sigS[i] else 0)
        if s == 0 or not atr[i] > 0 or end5[i] <= busy: continue
        L = O5[i]; S = L - s * k * atr[i]; a = end5[i] + 1; j = -1
        for m in range(a, min(a + exp1, len(o1))):
            if s1[m] != s1[end5[i]]: break
            if (l1[m] <= L - thru) if s == 1 else (h1[m] >= L + thru):
                j = m; break
        if j < 0: continue
        e = min(o1[j], L) if s == 1 else max(o1[j], L); risk = s * (e - S)
        if risk <= 0: continue
        T = e + s * rr * risk; m = j
        while True:
            if (l1[m] <= S) if s == 1 else (h1[m] >= S):
                px = S if m == j else (min(o1[m], S) if s == 1 else max(o1[m], S)); break
            if m > j and ((h1[m] >= T + thru) if s == 1 else (l1[m] <= T - thru)):
                px = max(o1[m], T) if s == 1 else min(o1[m], T); break
            if last1[m] or m == len(o1) - 1:
                px = c1[m]; break
            m += 1
        outt[nt] = j; outr[nt] = (s * (px - e) - max(cf * e, cmin)) / risk; nt += 1; busy = m
    return outt[:nt], outr[:nt]


if __name__ == "__main__":
    B1 = N.bars("NQ", 1); B5 = N.bars("NQ", 5)
    d1 = pd.DatetimeIndex(B1.day); s1 = d1.values.astype("datetime64[D]").astype(np.int64); last1 = np.r_[s1[1:] != s1[:-1], True]
    # each 5m bar = 5 consecutive session minutes; map by (day, bucket)
    m1 = np.zeros(len(B1), np.int64); first = np.r_[True, s1[1:] != s1[:-1]]
    idx = np.arange(len(B1)); start = np.maximum.accumulate(np.where(first, idx, 0)); m1 = idx - start
    code1 = s1 * 10000 + m1 // 5
    o5, h5, l5, c5, atr, sess5, last5, up, dn, day5 = prep("NQ", 5)
    # 5m bucket number inside its day
    first5 = np.r_[True, sess5[1:] != sess5[:-1]]; i5 = np.arange(len(o5)); b5 = i5 - np.maximum.accumulate(np.where(first5, i5, 0))
    code5 = sess5 * 10000 + b5
    # last 1m index of every 5m bar
    end5 = np.searchsorted(code1, code5, side="right") - 1
    ok = code1[end5] == code5
    print("5m bars mapped:", ok.mean())
    rng = h5 - l5; lw = np.minimum(o5, c5) - l5; uw = h5 - np.maximum(o5, c5); eps = 1e-9 * c5
    sl = (c5 > o5) & (lw <= 0.1 * rng + eps) & up["c>ema200"] & ok; ss = (c5 < o5) & (uw <= 0.1 * rng + eps) & dn["c>ema200"] & ok
    cf, cmin = N.COST["NQ"]
    rows = []
    for k, rr in ((1.0, 3.0), (1.5, 3.0), (1.0, 2.0), (1.0, 1.0)):
        for cx in (1, 2):
            t, R = run1m(*(B1[x].values for x in "ohlc"), s1, last1, end5, sl, ss, o5, c5, atr, k, rr, 250, 0.25, cf * cx, cmin * cx)
            y = d1[t].year
            T = pd.DataFrame(dict(y=y, R=R)); g = T.groupby("y").R.sum()
            rows.append(dict(stop=k, rr=rr, costx=cx, n=len(R), per_yr=len(R) / len(g), win=100 * (R > 0).mean(), R=R.mean(), tot=R.sum(),
                             yrs_pos=f"{(g > 0).sum()}/{len(g)}", tr=R[y <= 2019].mean(), va=R[(y >= 2020) & (y <= 2023)].mean(), te=R[y >= 2024].mean()))
            if (k, rr, cx) == (1.0, 3.0, 1):
                T.assign(date=d1[t]).to_csv("replay1m_trades.csv", index=False)
                print(T.groupby("y").R.agg(n="size", win=lambda r: 100 * (r > 0).mean(), R="mean", tot="sum").round(3).to_string())
    pd.set_option("display.width", 250); print(pd.DataFrame(rows).round(3).to_string(index=False))
