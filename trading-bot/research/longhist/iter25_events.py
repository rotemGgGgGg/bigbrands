"""Iter 25 — scheduled events in other markets (HistData 1-minute):
crude: EIA inventory report Wednesdays 10:30 NY (holiday shifts ignored) — fade / follow the 10:30–10:35 move at 1:2–1:3;
gold: London PM fix 10:00 NY (15:00 London) — fade / follow the 09:55–10:05 move at 1:2–1:3.
Stop = s × |event move| ; exit 14:00. Periods must each be ≥ 70 % wins."""
import sys; sys.path.insert(0, "."); sys.path.insert(0, "..")
import numpy as np, pandas as pd, itertools
from load import frame
rows = []
for pair, cf, (t0, t1), wday in (("WTIUSD", 0.0009, (630, 635), 2), ("XAUUSD", 0.0003, (595, 605), None)):
    f = frame(pair); f = f[f.index.notna()]; mm = f.index.hour * 60 + f.index.minute
    O, H, L, C = (f[k].values for k in ("open", "high", "low", "close"))
    days = pd.Series(np.arange(len(f))).groupby(f.index.date)
    for (mode, s, rr) in itertools.product(("fade", "follow"), (0.5, 1.0, 1.5), (2.0, 3.0)):
        R = []
        for d, idx in days:
            d = pd.Timestamp(d)
            if d.weekday() >= 5 or (wday is not None and d.weekday() != wday): continue
            idx = idx.values; m = mm[idx]
            a = idx[m == t0]; b = idx[m == t1 - 1]; ex = idx[(m >= t1) & (m < 840)]
            if not len(a) or not len(b) or len(ex) < 30: continue
            mv = C[b[0]] - O[a[0]]
            if abs(mv) < 1e-9: continue
            side = (-1 if mode == "fade" else 1) * int(np.sign(mv)); e = O[ex[0]]; sp = s * abs(mv)
            if sp < 1e-6: continue
            sl, tp = e - side * sp, e + side * rr * sp; px = None
            for k in ex:
                if (side == 1 and L[k] <= sl) or (side == -1 and H[k] >= sl): px = (min(O[k], sl) if side == 1 else max(O[k], sl)); break
                if (side == 1 and H[k] >= tp) or (side == -1 and L[k] <= tp): px = tp; break
            if px is None: px = C[ex[-1]]
            R.append((d.year, (side * (px - e) - cf * e) / sp))
        X = pd.DataFrame(R, columns=["y", "R"])
        if len(X) < 60: continue
        per = np.where(X.y < 2018, 0, np.where(X.y < 2021, 1, 2))
        d_ = dict(market=pair, mode=mode, stop=s, rr=rr, n=len(X))
        for k, nm in enumerate(("p1", "p2", "p3")): x = X.R[per == k]; d_[f"win_{nm}"] = round(100 * (x > 0).mean(), 1); d_[f"R_{nm}"] = round(x.mean(), 3)
        rows.append(d_)
out = pd.DataFrame(rows); out.to_csv("iter25_events.csv", index=False); pd.set_option("display.width", 200)
print(out.sort_values("win_p1", ascending=False).head(10).to_string(index=False))
print("PASS", int(((out[["win_p1", "win_p2", "win_p3"]].min(axis=1) >= 70) & (out[["R_p1", "R_p2", "R_p3"]].min(axis=1) > 0)).sum()), "of", len(out))
