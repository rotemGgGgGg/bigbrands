"""Iter 27 — open-source/protected TradingView NQ/ES strategies, three periods.
1 NY VIX Channel Trend: after the first W minutes of RTH, channel = open ± f × (VIX/100/√252) × open; first 1-minute close outside
  → follow; stop = s VIX-units, target = t VIX-units; flat 15:55.  (VIX: FRED, previous close.)
2 Opening Drive Continuation (NQ, 1m): a displacement candle in the first N minutes (body ≥ k × 20-bar average range) → follow at the
  next open; bracket 25/38 pts (scaled to price level for 2012–19) and a 1:2 variant."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
from load import frame, RTH
from engine import walk
exec(open("iter26_web.py").read().split("res = []")[0])
vix = pd.read_csv("../quant_loop/vix.csv", index_col=0, parse_dates=True).iloc[:, 0].apply(pd.to_numeric, errors="coerce").shift(1)
def days_of(per):
    if per == "2012-19":
        f = frame("NSXUSD"); f = f[f.index.notna()][:"2019-12-31"]; return pd.to_datetime(RTH(f).days)
    import lib; m = (lib.YR < 2024) if per == "2020-23" else (lib.YR >= 2024); return lib.DAYS[m]
out = []
for per, o, h, l, c, dow in grids():
    N = len(o); dd = days_of(per); vx = vix.reindex(dd, method="ffill").values / 100 / np.sqrt(252)
    cost = lambda e: 2.25 * e / 17000
    def tr(i, m, side, sl, tp):
        e = o[i, m]; px, _, _ = walk(o[i], h[i], l[i], c[i], m, side, e, sl, tp, 384); return side * (px - e) - cost(e)
    for W, fch, s, t in itertools.product((15, 30, 60), (0.5, 1.0), (0.5, 1.0), (1.0, 2.0)):
        R = []
        for i in range(N):
            if not np.isfinite(vx[i]): continue
            u = vx[i] * o[i, 0]; up, dn = o[i, 0] + fch * u, o[i, 0] - fch * u
            x = np.nonzero((c[i, W:360] > up) | (c[i, W:360] < dn))[0]
            if not len(x): continue
            m = W + x[0] + 1; side = 1 if c[i, m - 1] > up else -1; e = o[i, m]
            R.append(tr(i, m, side, e - side * s * u, e + side * t * u) / (s * u))
        R = np.array(R); out.append(dict(per=per, rule=f"VIX channel W{W} f{fch} stop{s} tgt{t}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3), rr_plan=t / s))
    for Nm, k, br in itertools.product((5, 15, 30), (2.0, 3.0), ("25/38", "1:2")):
        R = []
        for i in range(N):
            rg = h[i] - l[i]; avg = pd.Series(rg).rolling(20).mean().shift().values
            for m in range(20, Nm + 20):
                body = c[i, m] - o[i, m]
                if np.isfinite(avg[m]) and abs(body) >= k * avg[m]:
                    side = int(np.sign(body)); e = o[i, m + 1]; sc = e / 15000
                    sp = 25 * sc if br == "25/38" else 0.5 * abs(body); tp = 38 * sc if br == "25/38" else 2 * sp
                    R.append(tr(i, m + 1, side, e - side * sp, e + side * tp) / sp); break
        R = np.array(R)
        if len(R): out.append(dict(per=per, rule=f"Opening drive first{Nm}m body≥{k}×avg {br}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3), rr_plan=1.52 if br == "25/38" else 2.0))
T = pd.DataFrame(out); T.to_csv("iter27_tv.csv", index=False)
P = T.pivot_table(index="rule", columns="per", values=["win", "R"]); P["minR"] = P["R"].min(axis=1); P["minwin"] = P["win"].min(axis=1)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 80); print(P.sort_values("minR", ascending=False).head(15).round(3).to_string())
print("PASS (min win ≥ 70 & plan RR ≥ 2 & min R > 0):", int(((P.minwin >= 70) & (P.minR > 0)).sum()))
