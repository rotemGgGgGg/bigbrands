"""'Gap + opening-range breakout' generalised to every session anchor of the NQ 24-hour day (2010-19 user Databento NQ,
2020-26 Databento MNQ). Grid per session (18:00 → 16:59 NY = 1380 minutes, forward-filled), ATR(14) on 1-minute bars.
Anchor T: the 'gap' is the move over the P minutes before T, expressed as z = move / mean|move| of the previous 20 sessions.
OR = first m minutes from T; stop entry at OR high/low within 60 minutes; direction with / against / both relative to the
pre-move; stop 2×ATR + 5×ATR trail; exit H minutes after T (capped at 16:55). One trade per day per rule."""
import sys, os, pickle, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
CACHE = SP + "sess24.pkl"
def build():
    if os.path.exists(CACHE): return pickle.load(open(CACHE, "rb"))
    nq = pd.read_pickle(SP + "nq16.pkl")[:"2019-12-31"]; mnq = pd.read_pickle(SP + "full1m.pkl")
    out = {}
    for nm, f in (("A", nq), ("B", mnq)):
        f = f[["open", "high", "low", "close"]].copy()
        pc = f.close.shift(); tr = pd.concat([f.high - f.low, (f.high - pc).abs(), (f.low - pc).abs()], axis=1).max(axis=1)
        f["atr"] = tr.rolling(14).mean().shift()
        key = (f.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
        mins = ((f.index.hour * 60 + f.index.minute) - 1080) % 1440                # minutes since 18:00
        f = f[mins < 1380]; key = key[mins < 1380]; mins = mins[mins < 1380]
        days, arr = [], []
        for k, g in f.groupby(key):
            if k.weekday() >= 5 or len(g) < 1000: continue
            m = mins[key == k]
            G = g.set_index(m).reindex(range(1380)); G["close"] = G.close.ffill().bfill()
            for c in ("open", "high", "low"): G[c] = G[c].fillna(G.close)
            G["atr"] = G.atr.ffill().bfill(); days.append(k); arr.append(G[["open", "high", "low", "close", "atr"]].values.astype(np.float32))
        out[nm] = (pd.DatetimeIndex(days), np.stack(arr))
        print(nm, len(days), flush=True)
    pickle.dump(out, open(CACHE, "wb")); return out
def t2m(hhmm):  # NY clock → minutes since 18:00
    h, m = map(int, hhmm.split(":")); return ((h * 60 + m) - 1080) % 1440
ANCH = ["18:00", "20:00", "02:00", "03:00", "08:00", "08:30", "09:30", "10:00", "11:30", "13:00", "14:00", "15:00"]
def run(days, X, T, P, m, z, mode, H):
    t0 = t2m(T); tp = t0 - P
    if tp < 0: return np.array([]), []
    o, h, l, c, a = (X[:, :, i] for i in range(5))
    mv = c[:, t0 - 1] - c[:, tp]; ref = pd.Series(np.abs(mv)).rolling(20).mean().shift().values
    R, D = [], []; tend = min(t0 + H, t2m("16:55"))
    for i in np.nonzero(np.abs(mv) >= z * np.nan_to_num(ref, nan=np.inf))[0]:
        gs = 1 if mv[i] > 0 else -1; orh, orl = h[i, t0:t0 + m].max(), l[i, t0:t0 + m].min()
        w0, w1 = t0 + m, min(t0 + m + 60, tend)
        tu = np.argmax(h[i, w0:w1] >= orh) if (h[i, w0:w1] >= orh).any() else 9999
        td = np.argmax(l[i, w0:w1] <= orl) if (l[i, w0:w1] <= orl).any() else 9999
        if mode == "with": tu, td = (tu, 9999) if gs == 1 else (9999, td)
        if mode == "against": tu, td = (9999, td) if gs == 1 else (tu, 9999)
        if tu == td: continue
        s, j = (1, tu + w0) if tu < td else (-1, td + w0)
        e = max(orh, o[i, j]) if s == 1 else min(orl, o[i, j]); A = a[i, j]
        if not A > 0: continue
        st = 2 * A; sl = e - s * st; best = e; px = None
        for k in range(j, tend + 1):
            if (l[i, k] <= sl) if s == 1 else (h[i, k] >= sl): px = sl if k == j else (min(o[i, k], sl) if s == 1 else max(o[i, k], sl)); break
            best = max(best, h[i, k]) if s == 1 else min(best, l[i, k]); sl = max(sl, best - 5 * A) if s == 1 else min(sl, best + 5 * A)
        if px is None: px = c[i, tend]
        R.append((s * (px - e) - 2.25 * e / 17000) / st); D.append(days[i])
    return np.array(R), D
GRID = dict(T=ANCH, P=(60, 240, 900), m=(5, 15, 30), z=(1.0, 1.5, 2.0), mode=("with", "against", "both"), H=(120, 360, 1380))
if __name__ == "__main__":
    S = build(); days, X = S["A"]; rows = []
    for vals in itertools.product(*GRID.values()):
        cfg = dict(zip(GRID, vals)); R, _ = run(days, X, **cfg)
        if len(R) < 150: continue
        rows.append(dict(cfg, n=len(R), win=100 * (R > 0).mean(), R=R.mean(), t=R.mean() / R.std() * np.sqrt(len(R))))
    T = pd.DataFrame(rows).sort_values("t", ascending=False); T.to_csv("sess24_train.csv", index=False)
    pd.set_option("display.width", 250); print(len(T), "configs"); print(T.head(30).round(3).to_string(index=False))
    print("\nbest t per anchor:"); print(T.groupby("T").t.max().round(2).sort_values(ascending=False).to_string())
