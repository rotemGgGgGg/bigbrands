"""Stage 4 — 24h discovery on 5-minute bars (Globex hours included). At each 30-min decision time t,
condition on the past move over L minutes (in units of its rolling 20-day std at that clock time), trade
momentum or reversal, hold H minutes. Selection on 2020–23 only; 2024–26 reported."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S
full = pd.read_pickle(S + "full1m.pkl")
b = full.resample("5min", label="left", closed="left").agg({"open": "first", "close": "last"}).dropna()
b = b[~b.index.duplicated()]
tod = b.index.hour * 60 + b.index.minute
COST = 1.25
rows = []
px = b.close
yr = b.index.year
for t in range(0, 1440, 30):
    if 1020 <= t < 1080: continue                      # 17:00–18:00 halt
    at = b[tod == t]                                   # bar opening at t: entry at its open
    if len(at) < 500: continue
    for L in (30, 60, 120, 240):
        prev = b.close.shift(1).reindex(at.index)                       # close of the bar before t
        base = b.open.shift(L // 5).reindex(at.index)                   # open L minutes earlier
        mv = (prev / base - 1)
        z = mv / mv.rolling(20).std().shift()
        for H in (30, 60, 120, 240):
            fut = b.close.shift(-(H // 5 - 1)).reindex(at.index)
            # guard: future bar must be ~H minutes away (no weekend/halt jump)
            ft = pd.Series(b.index, index=b.index).shift(-(H // 5 - 1)).reindex(at.index)
            ok = ((ft - at.index) <= pd.Timedelta(minutes=H)) & ((at.index - pd.Series(b.index, index=b.index).shift(L // 5).reindex(at.index)) <= pd.Timedelta(minutes=L))
            r = (fut - at.open)
            for zt in (1.0, 1.5, 2.0):
                for sgn in (1, -1):
                    m = ok & ((z > zt) if sgn == 1 else (z < -zt))
                    if m.sum() < 60: continue
                    rr = r[m] * sgn                                       # momentum side: +1 if past up
                    isd = rr.index.year < 2024
                    ri, ro = rr[isd], rr[~isd]
                    if len(ro) < 20 or len(ri) < 40: continue
                    play = 1 if ri.mean() > 0 else -1                     # 1 = momentum, -1 = reversal (chosen IS)
                    ni, no = play * ri - COST, play * ro - COST
                    rows.append(dict(t=f"{t//60:02d}:{t%60:02d}", L=L, H=H, z=zt, past="up" if sgn == 1 else "down",
                                     play="momo" if play == 1 else "rev", nIS=len(ni), nOOS=len(no), IS=2 * ni.mean(), OOS=2 * no.mean(),
                                     tIS=ni.mean() / ni.std() * np.sqrt(len(ni)), tOOS=no.mean() / no.std() * np.sqrt(len(no)),
                                     winIS=(ni > 0).mean(), winOOS=(no > 0).mean()))
    print(t, len(rows), file=sys.stderr, flush=True)
R = pd.DataFrame(rows); R.to_pickle(S + "hunt_R4.pkl")
print("tests", len(R))
for th in (2, 2.5, 3):
    s = R[R.tIS > th]; print(th, len(s), "OOS>0", round((s.OOS > 0).mean(), 3), "base", round((R.OOS > 0).mean(), 3))
pd.set_option("display.width", 250)
print(R[(R.tIS > 2.5) & (R.tOOS > 1.5)].sort_values("tOOS", ascending=False).head(40).round(2).to_string())
