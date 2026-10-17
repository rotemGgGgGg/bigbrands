"""Iter 40 (queue 42) — Dalton's open types ('Mind Over Markets'), classified mechanically at 10:00 from the first 30 minutes:
 OD  open-drive: first-30 extreme on the open side within 0.05σ of the open, close at 10:00 ≥ d·σ away in the drive direction
 OTD open-test-drive: first moves ≥ 0.1σ one way, then closes at 10:00 ≥ d·σ the other way
 ORR open-rejection-reverse: moves ≥ d·σ one way, then closes at 10:00 back beyond the open on the other side (< d·σ)
 OA  open-auction: 30-minute range < 0.3σ (balanced) → trade the first break of the 30-minute range
Trades at 10:00 in the drive / reversal direction (OD, OTD, ORR), and fade variants; context = open inside / outside yesterday's
range. Stop k·σ or structural (other side of the 30-min range, capped 0.5σ), target 2× stop, exit close. Three periods."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
exec(open("iter26_web.py").read().split("\nres = []")[0])
res = []
for per, o, h, l, c, dow in grids():
    N = len(o); O = o[:, 0]; C = c[:, 389]; H = h.max(1); L = l.min(1)
    sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    for d, k, ctx, mode in itertools.product((0.2, 0.3, 0.5), (0.15, 0.25, 0.4, "struct"), ("any", "inside", "outside"), ("follow", "fade")):
        acc = {t: [] for t in ("OD", "OTD", "ORR", "OA")}
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            sg = sig[i] * O[i]; hh = h[i, :30].max(); ll = l[i, :30].min(); c30 = c[i, 29]
            inside = L[i - 1] <= O[i] <= H[i - 1]
            if ctx == "inside" and not inside or ctx == "outside" and inside: continue
            up_first = np.argmax(h[i, :30] >= O[i] + 0.1 * sg) if (h[i, :30] >= O[i] + 0.1 * sg).any() else 99
            dn_first = np.argmax(l[i, :30] <= O[i] - 0.1 * sg) if (l[i, :30] <= O[i] - 0.1 * sg).any() else 99
            mv = (c30 - O[i]) / sg; typ = None; s = 0
            if mv >= d and O[i] - ll <= 0.05 * sg: typ, s = "OD", 1
            elif mv <= -d and hh - O[i] <= 0.05 * sg: typ, s = "OD", -1
            elif mv >= d and dn_first < up_first: typ, s = "OTD", 1
            elif mv <= -d and up_first < dn_first: typ, s = "OTD", -1
            elif 0 < mv < d and (O[i] - ll) >= d * sg and dn_first < up_first: typ, s = "ORR", 1
            elif -d < mv < 0 and (hh - O[i]) >= d * sg and up_first < dn_first: typ, s = "ORR", -1
            elif hh - ll < 0.3 * sg: typ = "OA"
            if typ is None: continue
            m = 30
            if typ == "OA":
                bu = np.nonzero(h[i, 30:330] > hh)[0]; bd = np.nonzero(l[i, 30:330] < ll)[0]
                tu = bu[0] if len(bu) else 999; td = bd[0] if len(bd) else 999
                if tu == td: continue
                s = 1 if tu < td else -1; m = 30 + min(tu, td) + 1
            if mode == "fade": s = -s
            e = o[i, m]
            if k == "struct": st = min(max(s * (e - (ll if s == 1 else hh)), 0.1 * sg), 0.5 * sg)
            else: st = k * sg
            if st <= 0: continue
            px, _, _ = walk(o[i], h[i], l[i], c[i], m, s, e, e - s * st, e + s * 2 * st, 389)
            acc[typ].append((s * (px - e) - 2.25 * e / 17000) / st)
        for t, R in acc.items():
            if t == "OA" and d != 0.3: continue
            R = np.array(R)
            if len(R) >= 15: res.append(dict(per=per, rule=f"{t} d{d} k{k} {ctx} {mode}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(res); T.to_csv("iter40_opentypes.csv", index=False)
W = T.pivot_table(index="rule", columns="per", values=["win", "R", "n"]); W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
W = W[W["n"].notna().all(axis=1)]
pd.set_option("display.width", 250); print(W.sort_values("minR", ascending=False).head(15).round(3).to_string())
print("rows minR>0:", (W.minR > 0).sum(), "of", len(W), "| max minwin", W.minwin.max())
