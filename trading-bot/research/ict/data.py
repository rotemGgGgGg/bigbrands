"""Per-day 1-minute arrays for the ICT engine (from the sess24 grid: 18:00 → 16:59 NY, 1380 minutes, NQ 2010-19 + MNQ 2020-26)
plus pre-computed liquidity levels. A level is (price, ready_minute, first_breach_minute, closed_back_on_breach).
Level types (low side = sell-side liquidity, high side = buy-side):
  0 prior-day RTH (09:30-16:00) high/low       1 Asia 18:00-23:59        2 London 02:00-04:59
  3 overnight 18:00-09:29                        4 09:00-09:59 hour (Silver Bullet range)
  5 opening range 09:30-09:34   6 09:30-09:44   7 09:30-09:59
'first breach' is the first minute AFTER the level is complete whose low (high) trades through it — the sweep event."""
import os, sys, pickle
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gapfb"))
from sess24 import build, t2m
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/ict/"
os.makedirs(SP, exist_ok=True)
NL = 8
SEG = [None, (0, 360), (480, 660), (0, t2m("09:30")), (t2m("09:00"), t2m("10:00")),
       (t2m("09:30"), t2m("09:35")), (t2m("09:30"), t2m("09:45")), (t2m("09:30"), t2m("10:00"))]


def load():
    p = SP + "days.pkl"
    if os.path.exists(p): return pickle.load(open(p, "rb"))
    S = build(); d = pd.DatetimeIndex(np.r_[S["A"][0], S["B"][0]]); X = np.concatenate([S["A"][1], S["B"][1]]).astype(np.float64)
    n = len(d); prev_ok = np.r_[False, (d[1:] - d[:-1]).days <= 4]
    R0, R1 = t2m("09:30"), t2m("16:00")
    LV = np.full((n, NL, 2, 4), np.nan)        # [day, type, side(0 low,1 high), (price, ready, breach, closed_back)]
    for i in range(n):
        o, h, l, c = X[i, :, 0], X[i, :, 1], X[i, :, 2], X[i, :, 3]
        for t in range(NL):
            if t == 0:
                if not prev_ok[i]: continue
                ph, pl = X[i - 1, R0:R1, 1].max(), X[i - 1, R0:R1, 2].min(); ready = 0
            else:
                a, b = SEG[t]; ph, pl = h[a:b].max(), l[a:b].min(); ready = b
            for side, lev in ((0, pl), (1, ph)):
                hit = (l[ready:] < lev) if side == 0 else (h[ready:] > lev)
                if hit.any():
                    k = ready + int(np.argmax(hit)); cb = (c[k] > lev) if side == 0 else (c[k] < lev)
                else: k = 9999; cb = False
                LV[i, t, side] = (lev, ready, k, cb)
    # 1-minute EMA(200) of closes, carried across days (bias filter), and the day's 18:00 open
    cl = X[:, :, 3].ravel(); e200 = pd.Series(cl).ewm(span=200, adjust=False).mean().values.reshape(n, 1380)
    out = dict(days=d, X=X, LV=LV, ema200=e200, yr=d.year.values)
    pickle.dump(out, open(p, "wb"), protocol=4); return out


if __name__ == "__main__":
    D = load(); print(len(D["days"]), D["days"][0], D["days"][-1], np.isnan(D["LV"][:, :, :, 0]).mean())


def volume():
    """1-minute volume on the same (day, minute) grid: NQ (nq16) where available, MNQ (full1m) for the remaining days."""
    p = SP + "vol.pkl"
    if os.path.exists(p): return pickle.load(open(p, "rb"))
    D = load(); days = D["days"]; V = np.zeros((len(days), 1380), np.float32); pos = {d: i for i, d in enumerate(days)}
    base = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
    for fn in ("full1m.pkl", "nq16.pkl"):                      # NQ written last so it wins where both exist
        f = pd.read_pickle(base + fn); f = f[f.index.notna()]
        m = (f.index.hour * 60 + f.index.minute).values; s18 = (m - 1080) % 1440
        key = (f.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
        ok = s18 < 1380; idx = np.array([pos.get(k, -1) for k in key[ok]]); v = f.volume.values[ok].astype(np.float32); s = s18[ok]
        g = idx >= 0; V[idx[g], s[g]] = v[g]
    pickle.dump(V, open(p, "wb"), protocol=4); return V
