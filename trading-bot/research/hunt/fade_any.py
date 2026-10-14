"""Does the 'fade an outsized 60-min move' rule work at other clock times? Decision every 30 min, 02:00–15:00 ET.
z vs 20-day std of the same clock window; TP a·|move| retrace, SL b·|move|, time exit +240 min (max 15:55)."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S
COST, TICK = 2.25, 0.25          # includes +1 pt extra slippage
full = pd.read_pickle(S + "full1m.pkl"); full = full[~full.index.duplicated()]
mm = (full.index.hour * 60 + full.index.minute).values
dn = full.index.normalize()
O, H, Lo, C = full.open.values, full.high.values, full.low.values, full.close.values
pos = pd.Series(np.arange(len(full)), index=full.index)
rows = []
for T in range(120, 931, 30):
    idxT = np.nonzero(mm == T)[0]
    if len(idxT) < 800: continue
    recs = []
    for k in idxT:
        k0 = k - 60
        if k0 < 0 or (full.index[k] - full.index[k0]) != pd.Timedelta(minutes=60): continue
        recs.append((dn[k], k, C[k - 1] - O[k0], C[k - 1] / O[k0] - 1))
    df = pd.DataFrame(recs, columns=["d", "k", "mv", "ret"]).drop_duplicates("d").set_index("d")
    df["z"] = df.ret / df.ret.rolling(20).std().shift()
    for zt in (1.5, 2.0):
        for a, b in ((0.5, 1.0), (0.75, 1.0), (1.0, 1.0)):
            res = []
            for d, r in df[df.z.abs() > zt].iterrows():
                k = int(r.k); s = -int(np.sign(r.mv)); size = abs(r.mv); e = O[k]
                tp, sl = e + s * a * size, e - s * b * size
                endm = min(T + 240, 955); px = None
                for j in range(k, k + 400):
                    if j >= len(O) or dn[j] != d or mm[j] >= endm or (1020 <= mm[j] < 1080): px = O[min(j, len(O) - 1)]; break
                    if (Lo[j] <= sl) if s == 1 else (H[j] >= sl): px = (min(O[j], sl) if s == 1 else max(O[j], sl)); break
                    if (H[j] >= tp + TICK) if s == 1 else (Lo[j] <= tp - TICK): px = tp; break
                if px is None: continue
                res.append((d, (s * (px - e) - COST) / (b * size)))
            x = pd.DataFrame(res, columns=["d", "R"]).set_index("d").R
            if len(x) < 40: continue
            isd = x.index.year < 2024
            rows.append(dict(T=f"{T//60:02d}:{T%60:02d}", z=zt, tp=a, sl=b, n=len(x), win=round(100 * (x > 0).mean(), 1),
                             avgR=round(x.mean(), 3), IS=round(x[isd].mean(), 3), OOS=round(x[~isd].mean(), 3)))
    print(T, file=sys.stderr, flush=True)
R = pd.DataFrame(rows); R.to_csv("fade_any.csv", index=False)
pd.set_option("display.width", 200); pd.set_option("display.max_rows", 500)
print(R[(R.tp == 0.5) & (R.z == 2.0)].to_string())
print(R[(R.tp == 1.0) & (R.z == 1.5)].to_string())
