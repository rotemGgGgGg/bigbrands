"""Model 2: candle sweep / Candle Range Theory (CRT).
Candle A (previous bar) defines a range. Candle B sweeps one side (wick beyond A's high or low) and then:
   'inside' : closes back inside A's range (classic CRT)            -> trade back toward the other side
   'engulf' : closes beyond the OTHER side of A (sweep high, close below A's low)  -> trade in the close direction
Entry at B's close. Stops: B's sweep extreme ('wick'), wick + 10% of A range ('wick+'), or A's midpoint ('mid', tighter).
Targets: A's opposite side ('range'), A's midpoint ('half'), or 1R / 2R / 3R. Time stop after 1, 3 or 6 bars of the timeframe.
Filters: sweep depth >= 0 / 10% of A's range; A's range >= its 20-bar average ('real range'); session (intraday TFs:
B closes 02:00-12:00 New York, London+NY) or any time.
Timeframes 15m, 30m, 1h, 4h, 1D (bars anchored at 17:00 New York). 9 markets, 2012-2026, 1-minute path for exits
(stop wins a same-minute tie). Results in R net of the market's round-trip cost. Choose on 2012-19, judge on 2020-26."""
import os as _os; DATA = _os.path.join(_os.path.expanduser(_os.environ.get("EDGE_DATA", "~/edge-data")), "")  # raw data + caches (set EDGE_DATA to move it)
import sys, os, math, itertools, pickle
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi")); sys.path.insert(0, os.path.join(H, "../vidstrats"))
import numpy as np, pandas as pd, mdata
from vs import frame
SP = DATA + "sweep/"; os.makedirs(SP, exist_ok=True)
MKT = {"NQ": "NSXUSD", "SPX": "SPXUSD", "GOLD": "XAUUSD", "USDJPY": "USDJPY", "EURUSD": "EURUSD", "EURJPY": "EURJPY",
       "GBPJPY": "GBPJPY", "DAX": "DEUIDXEUR", "OIL": "LIGHTCMDUSD"}
COST = {"NQ": 1.3, "SPX": 1.3, "GOLD": 1.6, "USDJPY": 1.0, "EURUSD": 0.8, "EURJPY": 1.2, "GBPJPY": 1.4, "DAX": 1.3, "OIL": 4.0}
TFS = [15, 30, 60, 240, 1440]; HOLDS = [1, 3, 6]; STOPS = ["wick", "wick+", "mid"]; TGTS = ["range", "half", "1R", "2R", "3R"]


def minutes(name):
    f = SP + f"min_{name}.npz"
    if os.path.exists(f): z = np.load(f); return z["t"], z["h"], z["l"], z["c"], z["o"]
    df = frame(MKT[name], "America/New_York"); t = (df.index.values.astype("datetime64[m]").astype(np.int64))
    np.savez(f, t=t, o=df.o.values, h=df.h.values, l=df.l.values, c=df.c.values); return t, df.h.values, df.l.values, df.c.values, df.o.values


def bars(t, h, l, c, o, tf):
    """bars anchored at 17:00 NY: key = floor((t - 17:00 offset)/tf). returns per-bar o,h,l,c, first and last minute index, bar start time"""
    k = (t - 17 * 60) // tf
    st = np.r_[0, np.nonzero(np.diff(k))[0] + 1]; en = np.r_[st[1:], len(t)]
    bo = o[st]; bc = c[en - 1]; bh = np.maximum.reduceat(h, st); bl = np.minimum.reduceat(l, st)
    return dict(o=bo, h=bh, l=bl, c=bc, st=st, en=en, key=k[st])


def signals(name, tf):
    f = SP + f"sig_{name}_{tf}.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    t, h, l, c, o = minutes(name); B = bars(t, h, l, c, o, tf); n = len(B["o"]); rows = []
    rng = B["h"] - B["l"]; avg = pd.Series(rng).rolling(20).mean().shift(2).values
    maxmin = max(HOLDS) * tf
    for i in range(1, n - 1):
        if B["key"][i] - B["key"][i - 1] != 1: continue                       # consecutive bars only
        ah, al, bh, bl, bc = B["h"][i - 1], B["l"][i - 1], B["h"][i], B["l"][i], B["c"][i]; ar = ah - al
        if ar <= 0: continue
        up, dn = bh > ah, bl < al
        if up and dn:                                                          # outside bar: engulf only
            if bc < al: kind, side, ext, depth = "engulf", -1, bh, (bh - ah) / ar
            elif bc > ah: kind, side, ext, depth = "engulf", 1, bl, (al - bl) / ar
            else: continue
        elif up and al < bc < ah: kind, side, ext, depth = "inside", -1, bh, (bh - ah) / ar
        elif dn and al < bc < ah: kind, side, ext, depth = "inside", 1, bl, (al - bl) / ar
        else: continue
        e = B["en"][i]                                                         # first minute after B
        if e >= len(t) - 2: continue
        ent = o[e]; ph, pl, pc = h[e:e + maxmin], l[e:e + maxmin], c[e:e + maxmin]; pt = t[e:e + maxmin] - t[e]
        stops = {"wick": ext, "wick+": ext - side * 0.1 * ar, "mid": (ah + al) / 2}
        tg_lvl = {"range": al if side < 0 else ah, "half": (ah + al) / 2}
        res = {}
        for sn, sl in stops.items():
            risk = side * (ent - sl)
            if risk <= ent * 1e-5: continue
            hs = np.nonzero(pl <= sl)[0] if side > 0 else np.nonzero(ph >= sl)[0]; ts = hs[0] if len(hs) else 10 ** 9
            for tn in TGTS:
                tg = tg_lvl[tn] if tn in tg_lvl else ent + side * float(tn[0]) * risk
                if side * (tg - ent) <= 0: continue
                ht = np.nonzero(ph >= tg)[0] if side > 0 else np.nonzero(pl <= tg)[0]; tt = ht[0] if len(ht) else 10 ** 9
                for hd in HOLDS:
                    lim = np.searchsorted(pt, hd * tf)                          # minutes within the time stop
                    if ts < lim and ts <= tt: px = sl
                    elif tt < lim: px = tg
                    else: px = pc[min(lim, len(pc)) - 1]
                    res[(sn, tn, hd)] = (side * (px - ent) - ent * COST[name] / 1e4) / risk
        if not res: continue
        bt = pd.Timestamp(int(t[B["en"][i] - 1]) * 60, unit="s")
        rows.append(dict(time=bt, kind=kind, side=side, depth=depth, real=ar >= (avg[i] if np.isfinite(avg[i]) else np.inf),
                         hour=bt.hour, **{f"{k[0]}|{k[1]}|{k[2]}": v for k, v in res.items()}))
    S = pd.DataFrame(rows); pd.to_pickle(S, f); return S


def tst(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0


if __name__ == "__main__":
    names = sys.argv[1:] or list(MKT)
    for nm in names:
        for tf in TFS:
            S = signals(nm, tf); print(nm, tf, len(S), flush=True)
