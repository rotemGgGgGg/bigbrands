"""Three strategies shown in a sales video, rebuilt from the screenshots and tested on our own data 2012-2026.
  LB  USDJPY London breakout: Asian range (London 00:00-AE), stop orders above/below it from 08:00 London, stop inside range,
      optional target, flat at a fixed afternoon time. 'Needs a real range' = min/max range filter vs its 20-day average.
  GF  Gold front-runner: stop order just before yesterday's high/low (front-run by f x ATR), stop s x ATR (optionally trailing),
      quick target t x ATR, flat at window end. One trade a day (first trigger).
  NM  NQ NY opening momentum: 10-min RTH bars, RSI(14) extreme inside the first hour -> enter next bar open in that direction,
      skip if price stretched too far from the day's open; exit when RSI fades back through a level, stop optional, flat by close.
Every variant is reported in R (risk units) or bp, net of costs. Grid judged on 2012-19 only; 2020-26 is out of sample.
The video's own period (2021-2026) is reported separately so its claim can be compared."""
import sys, os, math, itertools, pickle
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi"))
import numpy as np, pandas as pd, mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/vidstrats/"; os.makedirs(SP, exist_ok=True)


def frame(sym, tz):
    if sym in ("NSXUSD", "SPXUSD"): df = mdata.histdata(sym)
    else:
        z = np.load(mdata.DK + sym + ".npz"); t = pd.to_datetime(z["t"] * 60, unit="s", utc=True).tz_convert(tz).tz_localize(None)
        df = pd.DataFrame({k: z[k] for k in "ohlc"}, index=t)
    df = df.sort_index(); return df[~df.index.duplicated()]


def days_grid(df, start_min, n_min):
    """per calendar day arrays of n_min minutes starting at start_min (local), forward-filled; skip thin days"""
    m = df.index.hour * 60 + df.index.minute; d = df.index.normalize()
    sel = (m >= start_min) & (m < start_min + n_min); x = df[sel]; mm = (m[sel] - start_min).values; dd = d[sel]
    out = {}
    for day, idx in pd.Series(np.arange(len(x)), index=dd).groupby(level=0):
        if day.weekday() >= 5 or len(idx) < n_min * .6: continue
        g = x.iloc[idx.values].set_index(mm[idx.values]).reindex(range(n_min)); g["c"] = g.c.ffill().bfill()
        for k in "ohl": g[k] = g[k].fillna(g.c)
        out[day] = (g.o.values, g.h.values, g.l.values, g.c.values)
    return out


def first(mask):
    i = np.argmax(mask); return i if mask[i] else -1


def trade(o, h, l, c, i0, side, entry, stop, tgt, trail=None):
    """from minute i0 (fill at entry), first of stop/target (stop wins ties), else exit at last close. trail = distance or None"""
    hh, ll = h[i0:], l[i0:]
    if trail is not None:
        if side > 0: stp = np.maximum(stop, np.maximum.accumulate(np.r_[entry, hh[:-1]]) - trail)
        else: stp = np.minimum(stop, np.minimum.accumulate(np.r_[entry, ll[:-1]]) + trail)
    else: stp = np.full(len(hh), stop)
    if side > 0: ts = first(ll <= stp); tt = first(hh >= tgt) if tgt is not None else -1
    else: ts = first(hh >= stp); tt = first(ll <= tgt) if tgt is not None else -1
    if ts >= 0 and (tt < 0 or ts <= tt): return side * (stp[ts] - entry)
    if tt >= 0: return side * (tgt - entry)
    return side * (c[-1] - entry)


# ---------------- LB: USDJPY London breakout ----------------
def LB(sym="USDJPY"):
    f = SP + "LB_days.pkl"
    if os.path.exists(f): G = pickle.load(open(f, "rb"))
    else: G = days_grid(frame(sym, "Europe/London"), 0, 18 * 60); pickle.dump(G, open(f, "wb"))
    bp = mdata.MK[sym][2]; days = sorted(G); res = {}
    asian_rng = pd.Series({d: G[d][1][:7 * 60].max() - G[d][2][:7 * 60].min() for d in days})
    avg = asian_rng.rolling(20).mean().shift(1)
    grid = itertools.product((7, 8), ("long", "both"), (0.0, 0.1), ("mid", "far"), (None, 1.0, 2.0), (13, 16, 17), ("none", "min", "minmax"))
    for AE, dirn, buf, stp, tgtR, X, filt in grid:
        out = {}
        for d in days:
            o, h, l, c = G[d]; ah, al = h[:AE * 60].max(), l[:AE * 60].min(); r = ah - al
            a = avg.get(d, np.nan)
            if not (r > 0) or not np.isfinite(a): continue
            if filt in ("min", "minmax") and r < .5 * a: continue
            if filt == "minmax" and r > 1.5 * a: continue
            e0, e1 = 8 * 60, 12 * 60; up, dn = ah + buf * r, al - buf * r
            iu = first(h[e0:e1] >= up); idn = first(l[e0:e1] <= dn) if dirn == "both" else -1
            if iu < 0 and idn < 0: continue
            if iu >= 0 and (idn < 0 or iu <= idn): side, i0, ent = 1, e0 + iu, max(up, o[e0 + iu])
            else: side, i0, ent = -1, e0 + idn, min(dn, o[e0 + idn])
            sl = (ah + al) / 2 if stp == "mid" else (al if side > 0 else ah)
            risk = abs(ent - sl); cost = ent * bp / 1e4
            if risk < 3 * cost: continue
            tg = ent + side * tgtR * risk if tgtR else None
            pnl = trade(o[:X * 60], h[:X * 60], l[:X * 60], c[:X * 60], i0, side, ent, sl, tg)
            out[d] = (pnl - cost) / risk
        res[(AE, dirn, buf, stp, tgtR, X, filt)] = pd.Series(out, dtype=float)
    return res


# ---------------- GF: gold front-runner ----------------
def GF(sym="XAUUSD"):
    f = SP + "GF_days.pkl"
    if os.path.exists(f): G = pickle.load(open(f, "rb"))
    else:
        df = frame(sym, "America/New_York"); df.index = df.index + pd.Timedelta(hours=6)    # gold day 18:00-17:00 NY -> 00:00-23:00
        G = days_grid(df, 0, 23 * 60); pickle.dump(G, open(f, "wb"))
    bp = mdata.MK[sym][2]; days = sorted(G); res = {}
    DH = pd.Series({d: G[d][1].max() for d in days}); DL = pd.Series({d: G[d][2].min() for d in days})
    atr = (DH - DL).rolling(14).mean().shift(1); pH, pL = DH.shift(1), DL.shift(1)
    W = {"london+ny": (9 * 60, 18 * 60), "all": (0, 22 * 60)}                               # shifted clock: 09:00 = 03:00 NY
    grid = itertools.product(W, (-0.05, 0.0, 0.05, 0.1), (0.25, 0.5), (0.25, 0.5, 1.0), (False, True), ("both", "low_only"))
    for wn, fr, s, t, tr, dirn in grid:
        a0, a1 = W[wn]; out = {}
        for d in days:
            A, yh, yl = atr.get(d), pH.get(d), pL.get(d)
            if not np.isfinite(A) or not np.isfinite(yh): continue
            o, h, l, c = (x[:a1] for x in G[d]); o0 = o[a0]
            if not (yl < o0 < yh): continue
            up, dn = yh - fr * A, yl + fr * A
            iu = first(h[a0:] >= up) if dirn == "both" else -1; idn = first(l[a0:] <= dn)
            if iu < 0 and idn < 0: continue
            if iu >= 0 and (idn < 0 or iu <= idn): side, i0, ent = 1, a0 + iu, max(up, o[a0 + iu])
            else: side, i0, ent = -1, a0 + idn, min(dn, o[a0 + idn])
            sl, tg = ent - side * s * A, ent + side * t * A
            pnl = trade(o, h, l, c, i0, side, ent, sl, tg, trail=s * A if tr else None)
            out[d] = (pnl - ent * bp / 1e4) / (s * A)
        res[(wn, fr, s, t, tr, dirn)] = pd.Series(out, dtype=float)
    return res


# ---------------- NM: NQ NY opening momentum ----------------
def rsi(x, n=14):
    d = np.diff(x, prepend=x[0]); up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n).mean(); dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).values


def NM(sym="NSXUSD"):
    D = mdata.load(sym); O, Hh, L, C = D["o"], D["h"], D["l"], D["c"]; nd = len(D["days"]); bp = D["bp"]
    # 10-min bars (39 per day), RSI on continuous RTH 10-min closes
    c10 = C[:, 9::10]; RS = rsi(c10.ravel()).reshape(nd, 39)
    dr = pd.Series(D["dh"] - D["dl"]); atr = dr.rolling(14).mean().shift(1).values
    res = {}
    grid = itertools.product((70, 75, 80), (6,), (None, 0.5, 1.0), (50, 60), (None, 0.25, 0.5))
    for U, nb, stretch, fade, stopk in grid:
        out = {}
        for i in range(15, nd):
            A = atr[i]
            if not np.isfinite(A): continue
            for b in range(nb):                                               # bars closing 09:40 .. 10:30
                r = RS[i, b]; side = 1 if r > U else (-1 if r < 100 - U else 0)
                if not side: continue
                if stretch is not None and abs(c10[i, b] - O[i, 0]) > stretch * A: break
                m0 = (b + 1) * 10; ent = O[i, m0]
                # exit: first later bar where RSI fades through 'fade' (long: below fade; short: above 100-fade) -> next bar open
                ex_m = 389; px = None
                for k in range(b + 1, 39):
                    if (side > 0 and RS[i, k] < fade) or (side < 0 and RS[i, k] > 100 - fade): ex_m = min((k + 1) * 10, 389); break
                hh, ll = Hh[i, m0:ex_m + 1], L[i, m0:ex_m + 1]
                if stopk is not None:
                    sl = ent - side * stopk * A; hit = first(ll <= sl) if side > 0 else first(hh >= sl)
                    if hit >= 0: px = sl
                if px is None: px = O[i, ex_m] if ex_m < 389 else C[i, -1]
                out[D["days"][i]] = side * (px - ent) / ent * 1e4 - bp
                break
        res[(U, nb, stretch, fade, stopk)] = pd.Series(out, dtype=float)
    return res


def summarize(name, res, unit):
    rows = []
    for k, s in res.items():
        if len(s) < 50: continue
        Y = s.index.year; I, Oo, V = s[Y <= 2019], s[Y >= 2020], s[Y >= 2021]
        t = lambda x: x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0
        pf = lambda x: x[x > 0].sum() / -x[x < 0].sum() if (x < 0).any() else np.inf
        yy = I.groupby(I.index.year).sum()
        rows.append(dict(strat=name, params=str(k), n_yr=len(s) / 14.8, win=100 * (s > 0).mean(), rr=s[s > 0].mean() / -s[s < 0].mean(),
                         IS_mean=I.mean(), IS_t=t(I), IS_pos_yrs=int((yy > 0).sum()), OOS_mean=Oo.mean(), OOS_t=t(Oo), OOS_pf=pf(Oo),
                         vid_period_sum=V.sum(), unit=unit))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    which = sys.argv[1:] or ["LB", "GF", "NM"]; F = {"LB": (LB, "R"), "GF": (GF, "R"), "NM": (NM, "bp")}
    for w in which:
        fn, unit = F[w]; res = fn(); pickle.dump(res, open(SP + w + "_res.pkl", "wb"))
        T = summarize(w, res, unit); T.to_csv(SP + w + "_grid.csv", index=False)
        pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 60)
        el = T[(T.IS_t >= 1.0) & (T.IS_pos_yrs >= 5)]
        print(f"\n===== {w}: {len(T)} variants; IS-eligible (t>=1, >=5/8 yrs) {len(el)}; of them OOS>0: {(el.OOS_mean > 0).sum()}")
        print(f"all variants OOS mean>0: {(T.OOS_mean > 0).mean()*100:.0f}% | median OOS t {T.OOS_t.median():.2f}")
        print(T.sort_values("IS_t", ascending=False).head(12).round(2).to_string(index=False))
        print("best by video period (2021-26 sum):"); print(T.sort_values("vid_period_sum", ascending=False).head(5).round(2).to_string(index=False))
