"""GapFB bot — rules reconstructed from its public Discord alerts (Jul 2026) and verified against Databento MNQ:
 gap = 09:30 open vs prior 15:59 close, |gap| ≥ 0.3 %  (qualifying alerts from 0.33 %; −0.26 % and −0.02 % days had no alert)
 OR  = 09:30–09:34 high / low (matches the alerts to 1–2 ticks); armed at 09:35
 entry: buy stop at OR high, sell stop at OR low; stop = 2 × ATR(14, 1-minute) at the fill, target = 2 × stop distance (2:1)
 up to 2 trades a day ("Trade # 1 of 2", "# 2 of 2"); after a trade closes both sides are live again.
Unknown and tested as variants: gap threshold, entry cut-off, time exit. Costs 2.25 pt per round trip (scaled by price/17000
for older data). Fills: stop entry at max(level, bar open); in the entry bar only the stop is checked; stop first on ties."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
def prep(f):
    f = f[f.index.notna()][["open", "high", "low", "close"]].copy()
    pc = f.close.shift(); tr = pd.concat([f.high - f.low, (f.high - pc).abs(), (f.low - pc).abs()], axis=1).max(axis=1)
    f["atr"] = tr.rolling(14).mean().shift()          # ATR known at the open of each bar (previous 14 closed bars)
    m = f.index.hour * 60 + f.index.minute
    r = f[(m >= 570) & (m < 960)]; days = []
    for d, g in r.groupby(r.index.date):
        if len(g) < 360 or pd.Timestamp(d).weekday() >= 5: continue
        g = g.set_index(g.index.hour * 60 + g.index.minute - 570).reindex(range(390))
        g["close"] = g.close.ffill().bfill()
        for k in ("open", "high", "low"): g[k] = g[k].fillna(g.close)
        g["atr"] = g.atr.ffill().bfill(); days.append((pd.Timestamp(d), g))
    return days
def run(days, thr=0.003, cut=389, tlast=389, max_tr=2, sl_atr=2.0, rr=2.0):
    out = []; prev = None
    for d, g in days:
        o, h, l, c, a = (g[k].values for k in ("open", "high", "low", "close", "atr"))
        if prev is None: prev = c[389]; continue
        gap = o[0] / prev - 1; prev = c[389]
        if abs(gap) < thr: continue
        orh, orl = h[:5].max(), l[:5].min(); cost = 2.25 * o[0] / 17000; m = 5; n = 0
        while n < max_tr and m <= cut:
            hu = np.nonzero(h[m:cut + 1] >= orh)[0]; hd = np.nonzero(l[m:cut + 1] <= orl)[0]
            tu = hu[0] + m if len(hu) else 999; td = hd[0] + m if len(hd) else 999
            if tu == td == 999: break
            s, j = (1, tu) if tu < td else (-1, td)
            if tu == td: break                                   # both in one bar: ambiguous, skip
            e = max(orh, o[j]) if s == 1 else min(orl, o[j]); st = sl_atr * a[j]
            sl, tp = e - s * st, e + s * rr * st; px = None
            for k in range(j, tlast + 1):
                if (l[k] <= sl) if s == 1 else (h[k] >= sl): px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
                if k > j and ((h[k] >= tp) if s == 1 else (l[k] <= tp)): px = tp; break
            if px is None: px, k = c[tlast], tlast
            out.append(dict(day=d, n=n + 1, side=s, R=(s * (px - e) - cost) / st, pts=s * (px - e) - cost, gap=gap))
            n += 1; m = k + 1
    return pd.DataFrame(out)
def summ(T, label):
    if not len(T): return
    w = T.R > 0; yrs = (T.day.max() - T.day.min()).days / 365.25
    print(f"{label:38s} n={len(T):5d} ({len(T)/max(yrs,0.1):5.0f}/yr) win={100*w.mean():5.1f}%  avgR={T.R.mean():+.3f}  "
          f"avgWin={T.R[w].mean():.2f}R avgLoss={T.R[~w].mean():.2f}R")
if __name__ == "__main__":
    from load import frame
    sets = {"MNQ 2020-23": None, "MNQ 2024-26": None}
    full = pd.read_pickle(SP + "full1m.pkl"); D = prep(full)
    sets["MNQ 2020-23"] = [x for x in D if x[0].year < 2024]; sets["MNQ 2024-26"] = [x for x in D if x[0].year >= 2024]
    N = frame("NSXUSD"); sets["NSX CFD 2012-19"] = prep(N[:"2019-12-31"])
    for nm, dd in sets.items():
        print("==", nm)
        for thr, cut, tlast in itertools.product((0.003, 0.005), (389, 150), (389, 150)):
            T = run(dd, thr, cut, tlast); summ(T, f"gap≥{thr*100:.1f}% cut{cut} exit{tlast}")
        T = run(dd); summ(T[T.n == 1], "  base: trade #1 only"); summ(T[T.n == 2], "  base: trade #2 only")
        T.to_csv(f"trades_{nm.split()[0]}_{nm.split()[-1]}.csv", index=False)

def periods():
    """2010-19 from the user's Databento NQ 1-minute file (front month by prior-session volume), 2020-23 / 2024-26 MNQ."""
    nq = pd.read_pickle(SP + "nq16.pkl"); D = prep(full := pd.read_pickle(SP + "full1m.pkl"))
    return {"2010-19": prep(nq[:"2019-12-31"]), "2020-23": [x for x in D if x[0].year < 2024], "2024-26": [x for x in D if x[0].year >= 2024]}
