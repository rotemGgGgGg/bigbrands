"""Iter 28 — Corte, Kosowski & Wang 'Market Closure and Short-Term Reversal' (cross-sectional overnight reversal across futures),
adapted: each day rank the overnight return (prior 15:59 close → 09:30 open, scaled by its 20-day std) of NQ, ES, gold, crude,
dollar index (HistData 1-minute 2012–2023/25). Trade NQ intraday only when NQ is the most extreme (rank 1 or 5): fade it, from 09:30
to 15:55 (and a 1:2 σ-bracket). Periods 2012–19 / 2020–23 / 2024–25 (crude missing 2024–25 → ranks over the other four)."""
import sys; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
from load import frame, RTH
from engine import walk
assets = {"NSXUSD": None, "SPXUSD": None, "XAUUSD": None, "WTIUSD": None, "UDXUSD": None}
ov = {}
for a in assets:
    f = frame(a); f = f[f.index.notna()]; m = f.index.hour * 60 + f.index.minute
    cl = f.close[m == 959]; cl.index = cl.index.normalize().tz_localize(None)
    op = f.open[m == 570]; op.index = op.index.normalize().tz_localize(None)
    r = (op / cl.shift(1).reindex(op.index, method="ffill") - 1)
    ov[a] = r / r.rolling(20).std().shift()
Z = pd.DataFrame(ov).dropna(subset=["NSXUSD"])
f = frame("NSXUSD"); D = RTH(f[f.index.notna()]); dd = pd.to_datetime(D.days)
o, h, l, c = D.o, D.h, D.l, D.c; mv = np.abs(c[:, 389] / o[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
cost = lambda e: 2.25 * e / 17000; rows = []
for i, d in enumerate(dd):
    if d not in Z.index or not np.isfinite(sig[i]): continue
    z = Z.loc[d].dropna()
    if len(z) < 4 or abs(z["NSXUSD"]) < 0.5: continue
    rk = z.rank()
    if rk["NSXUSD"] not in (1, len(z)): continue
    side = -int(np.sign(z["NSXUSD"])); e = o[i, 0]; sg = sig[i] * e
    px, _, _ = walk(o[i], h[i], l[i], c[i], 0, side, e, None, None, 384); r1 = (side * (px - e) - cost(e)) / sg
    px, _, _ = walk(o[i], h[i], l[i], c[i], 0, side, e, e - side * 0.25 * sg, e + side * 0.5 * sg, 384); r2 = (side * (px - e) - cost(e)) / (0.25 * sg)
    rows.append((d.year, r1, r2))
X = pd.DataFrame(rows, columns=["y", "hold", "b12"]); X["per"] = np.where(X.y < 2020, "2012-19", np.where(X.y < 2024, "2020-23", "2024-25"))
print(X.groupby("per").agg(n=("hold", "size"), hold_R=("hold", "mean"), hold_win=("hold", lambda s: 100 * (s > 0).mean()),
                           b12_R=("b12", "mean"), b12_win=("b12", lambda s: 100 * (s > 0).mean())).round(3).to_string())
