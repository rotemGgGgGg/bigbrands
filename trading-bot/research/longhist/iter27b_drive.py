"""Robustness of the 'opening drive' finding: displacement candle (|body| ≥ k × average 1-minute range of the previous 20 bars) in a
window after the open → follow at the next open. Grid of k, window start/length and brackets (points scaled to price: ×price/15000),
three periods, n and per-year counts, plus a stop-at-candle-mid structural variant."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
from load import frame, RTH
from engine import walk
exec(open("iter26_web.py").read().split("res = []")[0])
out = []; years = {"2012-19": 8, "2020-23": 4, "2024-26": 2.75}
for per, o, h, l, c, dow in grids():
    N = len(o); cost = lambda e: 2.25 * e / 17000
    def tr(i, m, side, sl, tp):
        e = o[i, m]; px, _, _ = walk(o[i], h[i], l[i], c[i], m, side, e, sl, tp, 384); return side * (px - e) - cost(e)
    avgs = [pd.Series(h[i] - l[i]).rolling(20).mean().shift().values for i in range(N)]
    for k, (w0, w1), (sp_, tp_) in itertools.product((2.5, 3.0, 3.5, 4.0), ((20, 35), (20, 50), (35, 65), (60, 120)), ((25, 38), (20, 40), (30, 45), (25, 50), ("mid", 2))):
        R = []
        for i in range(N):
            for m in range(w0, w1):
                body = c[i, m] - o[i, m]
                if np.isfinite(avgs[i][m]) and abs(body) >= k * avgs[i][m]:
                    side = int(np.sign(body)); e = o[i, m + 1]; sc = e / 15000
                    if sp_ == "mid": sp = max(abs(e - (o[i, m] + c[i, m]) / 2), 1e-6); tp = tp_ * sp
                    else: sp, tp = sp_ * sc, tp_ * sc
                    R.append(tr(i, m + 1, side, e - side * sp, e + side * tp) / sp); break
        R = np.array(R)
        if len(R) >= 10: out.append(dict(per=per, rule=f"k{k} win{w0}-{w1} br{sp_}/{tp_}", n=len(R), per_yr=round(len(R) / years[per]), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(out); T.to_csv("iter27b_drive.csv", index=False)
P = T.pivot_table(index="rule", columns="per", values=["win", "R", "per_yr"]); P["minR"] = P["R"].min(axis=1)
pd.set_option("display.width", 260); pd.set_option("display.max_rows", 90)
print("rules positive in all 3 periods:", int((P.minR > 0).sum()), "of", len(P))
print(P.sort_values("minR", ascending=False).head(25).round(3).to_string())
