"""LONDON BREAK & RETEST - a new strategy built from the SP-model autopsy: S1 (reversal after a sweep) loses, S2 (continuation
after the level breaks) is the only part that holds, and only with the trend.
Rules (NY time):
  trend   : yesterday's close vs its 50-day average -> longs only above, shorts only below ('filter off' = both, as control)
  levels  : London high / low = 00:00-06:00 range
  setup   : between 09:30 and the cutoff, a 5-minute close beyond the London level on the trend side
  entry   : 'retest' = limit at the level after the break (until the cutoff); 'break' = at the next minute's open
  stop    : back inside the range by k x London range (k = 0.25 / 0.5), measured from the level
  target  : 2R, or hold to 15:55 ('eod')
  one trade per day; a break on the wrong side first does not block the trade side.
Data: HistData 1-minute (NQ = NSXUSD, S&P = SPXUSD). Cost 1.3 bp per trade. Choose on 2012-19; check 2020-26, S&P, last 2 years."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi"))
import mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"; BP = 1.3


def days(sym):
    f = SP + f"lbr_{sym}.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    df = mdata.histdata(sym); df = df[~df.index.duplicated()].sort_index(); m = df.index.hour * 60 + df.index.minute
    d = df.index.normalize(); sel = m < 960; x = df[sel]; mm = m[sel]; dd = d[sel]; G = {}
    for day, idx in pd.Series(np.arange(len(x)), index=dd).groupby(level=0):
        if day.weekday() >= 5: continue
        g = x.iloc[idx.values].set_index(mm[idx.values]).reindex(range(960))
        if g.c.iloc[:360].notna().sum() < 300 or g.c.iloc[570:960].notna().sum() < 330: continue
        g["c"] = g.c.ffill().bfill()
        for k in "ohl": g[k] = g[k].fillna(g.c)
        G[day] = g[list("ohlc")].values.T
    pd.to_pickle(G, f); return G


def run(sym, entry, k, tgt, cutoff, use_trend):
    G = days(sym); D = mdata.load(sym); dc = pd.Series(D["dc"], index=D["days"]); up = (dc > dc.rolling(50).mean()).shift(1)
    out = {}
    for day in sorted(G):
        u = up.get(day)
        if u is None or pd.isna(u): continue
        o, h, l, c = G[day]; LH, LL = h[:360].max(), l[:360].min(); R = LH - LL
        if R <= 0: continue
        sides = [1 if u else -1] if use_trend else [1, -1]
        best = None
        for s in sides:
            lvl = LH if s == 1 else LL
            for i in range(574, cutoff, 5):                                # 5-minute closes at 09:34, 09:39, ...
                if (c[i] > lvl) if s == 1 else (c[i] < lvl):
                    if best is None or i < best[1]: best = (s, i, lvl)
                    break
        if best is None: continue
        s, i, lvl = best; stop = lvl - s * k * R
        if entry == "break":
            e0 = i + 1; ent = o[e0]
        else:
            seg = l[i + 1:cutoff] if s == 1 else h[i + 1:cutoff]
            hit = np.nonzero(seg <= lvl)[0] if s == 1 else np.nonzero(seg >= lvl)[0]
            if not len(hit): continue
            e0 = i + 1 + hit[0]; ent = min(lvl, o[e0]) if s == 1 else max(lvl, o[e0])
        risk = s * (ent - stop)
        if risk <= 0: continue
        tg = ent + s * 2 * risk if tgt == "2R" else None
        hh, ll = h[e0:955], l[e0:955]
        hs = np.nonzero(ll <= stop)[0] if s == 1 else np.nonzero(hh >= stop)[0]
        ht = (np.nonzero(hh >= tg)[0] if s == 1 else np.nonzero(ll <= tg)[0]) if tg is not None else np.array([], int)
        ts, tt = (hs[0] if len(hs) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
        px = stop if ts <= tt and ts < 10 ** 9 else (tg if tt < 10 ** 9 else c[954])
        cost = ent * BP / 1e4
        out[day] = (s * (px - ent) - cost) / risk
    return pd.Series(out, dtype=float)


def st(s):
    if len(s) < 5: return dict(n=len(s))
    w, l = s[s > 0], s[s < 0]; t = s.mean() / s.std() * math.sqrt(len(s))
    return dict(n_yr=round(len(s) / max((s.index[-1] - s.index[0]).days / 365.25, 1e-9), 1), win=round(100 * (s > 0).mean(), 1),
                rr=round(w.mean() / -l.mean(), 2), avgR=round(s.mean(), 3), t=round(t, 2), totR=round(s.sum(), 1))


if __name__ == "__main__":
    pd.set_option("display.width", 230); rows = []
    grid = list(itertools.product(("retest", "break"), (0.25, 0.5), ("2R", "eod"), (660, 720), (True, False)))
    for entry, k, tgt, cut, tr in grid:
        s = run("NSXUSD", entry, k, tgt, cut, tr); Y = s.index.year
        a, b = st(s[Y <= 2019]), st(s[Y >= 2020])
        rows.append(dict(entry=entry, k=k, tgt=tgt, cutoff=f"{cut//60}:00", trend=tr, n_yr=st(s)["n_yr"], win=st(s)["win"], rr=st(s)["rr"],
                         IS_R=a["avgR"], IS_t=a["t"], OOS_R=b["avgR"], OOS_t=b["t"], pos_yrs=int((s.groupby(Y).sum() > 0).sum())))
    T = pd.DataFrame(rows).sort_values("IS_t", ascending=False); T.to_csv(SP + "lbr_grid.csv", index=False)
    print("===== NQ, all 32 variants, sorted by 2012-19 t\n", T.to_string(index=False))
    print("\ntrend filter ON vs OFF (mean over variants):", T.groupby("trend")[["IS_R", "OOS_R"]].mean().round(3).to_dict())
    best = T[T.trend].iloc[0]; args = (best.entry, best.k, best.tgt, int(best.cutoff.split(":")[0]) * 60, True)
    print(f"\n===== PICK (best 2012-19 with trend): {args}")
    for sym in ("NSXUSD", "SPXUSD"):
        s = run(sym, *args); Y = s.index.year
        print(f"{sym}: all {st(s)} \n   2012-19 {st(s[Y<=2019])}\n   2020-26 {st(s[Y>=2020])}\n   last 2y {st(s[s.index>='2024-10-24'])}")
        print("   by year R:", s.groupby(Y).sum().round(1).to_dict())
