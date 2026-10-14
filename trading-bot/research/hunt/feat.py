"""Per-day features known at 09:30 ET (no look-ahead) + RTH minute arrays. Cached to scratchpad/hunt_feat.pkl."""
import sys, os, pickle
sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S

OUT = S + "hunt_feat.pkl"

def build():
    D = pickle.load(open(S + "D.pkl", "rb"))
    full = D.full
    N = len(D.days)
    days = pd.to_datetime(D.days)
    o, h, l, c, v = D.o, D.h, D.l, D.c, D.v
    F = pd.DataFrame(index=days)
    pc = np.r_[np.nan, c[:-1, 389]]
    ph = np.r_[np.nan, h[:-1].max(1)]; pl = np.r_[np.nan, l[:-1].min(1)]; po = np.r_[np.nan, o[:-1, 0]]
    ok = ~(D.roll | (D.prev_gap_days > 4))
    F["valid"] = ok
    F["o"] = o[:, 0]
    F["pc"] = pc
    F["gap"] = o[:, 0] / pc - 1
    F["pret"] = pc / po - 1                                    # prior RTH return
    F["pret2"] = np.r_[np.nan, F.pret.values[:-1]]
    F["prange"] = (ph - pl) / pc
    F["pclv"] = (pc - pl) / (ph - pl)                         # prior close location in range
    F["o_vs_ph"] = (o[:, 0] - ph) / pc
    F["o_vs_pl"] = (o[:, 0] - pl) / pc
    move = np.abs(c[:, 389] / o[:, 0] - 1)
    F["sig"] = pd.Series(move).rolling(14).mean().shift().values      # typical |open→close| move
    rng = (h.max(1) - l.min(1)) / o[:, 0]
    F["rsig"] = pd.Series(rng).rolling(14).mean().shift().values
    F["vol_ratio"] = pd.Series(rng).shift().values / F.rsig            # yesterday's range vs typical
    cc = pd.Series(c[:, 389])
    for n in (5, 10, 20, 50):
        F[f"ret{n}"] = (cc / cc.shift(n) - 1).shift().values               # trend up to yesterday's close
    F["dow"] = days.dayofweek
    F["dom"] = days.day
    tdm = pd.Series(range(N), index=days).groupby([days.year, days.month]).rank()
    F["tdm"] = tdm.values                                      # trading day of month (1..)
    F["tdm_rev"] = pd.Series(range(N), index=days).groupby([days.year, days.month]).rank(ascending=False).values
    # overnight (18:00 prior day → 09:29) from the 24h frame
    m = full.index.hour * 60 + full.index.minute
    sd = (full.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    on = full[(m < 570) | (m >= 1080)]
    sd_on = sd[(m < 570) | (m >= 1080)]
    g = on.groupby(sd_on)
    onh, onl, onv = g.high.max(), g.low.min(), g.volume.sum()
    F["onh"] = onh.reindex(days).values; F["onl"] = onl.reindex(days).values
    F["on_range"] = (F.onh - F.onl) / F.o
    F["on_pos"] = (F.o - F.onl) / (F.onh - F.onl)
    F["on_vol"] = onv.reindex(days).values
    F["on_vol_ratio"] = F.on_vol / F.on_vol.rolling(20).mean().shift()
    eu = full[(m >= 180) & (m < 570)]                          # London 03:00–09:29
    ge = eu.groupby(sd[(m >= 180) & (m < 570)])
    F["lon_ret"] = (ge.close.last() / ge.open.first() - 1).reindex(days).values
    F.loc[~F.valid, ["gap", "pret", "o_vs_ph", "o_vs_pl", "pclv"]] = np.nan
    return F, D

def load():
    if os.path.exists(OUT):
        return pickle.load(open(OUT, "rb"))
    F, D = build()
    D.full = None
    pickle.dump((F, D), open(OUT, "wb"))
    return F, D

if __name__ == "__main__":
    F, D = load()
    print(F.describe().T.round(4).to_string())
