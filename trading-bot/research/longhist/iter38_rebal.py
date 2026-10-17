"""Iter 38 (queue 40) — month-end / quarter-end pension rebalancing, conditioned on the month-to-date equity move.
MTD = previous month's last close → yesterday's close, scaled by σ_day·√(sessions so far). On the last D sessions of the month
(D = 1, 2, 3): MTD z ≥ t → SHORT (pensions sell winners), z ≤ −t → LONG. Entry 09:30 / 15:00 / 15:30, stop k·σ_day, target 2k,
exit 15:59. Variants: all months / quarter-ends only. Three periods, costs 2.25 pt scaled."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
exec(open("iter26_web.py").read().split("\nres = []")[0])
res = []
for per, o, h, l, c, dow in grids():
    if per == "2012-19":
        f0 = frame("NSXUSD"); days = RTH(f0[f0.index.notna()][:"2019-12-31"]).days
    else:
        import lib; days = lib.DAYS[(lib.YR < 2024) if per == "2020-23" else (lib.YR >= 2024)]
    days = pd.DatetimeIndex(days); N = len(o); O = o[:, 0]; C = c[:, 389]
    sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    ym = days.year * 12 + days.month
    first = np.r_[True, ym[1:] != ym[:-1]]; last = np.r_[ym[1:] != ym[:-1], False]
    to_end = np.zeros(N, int)            # sessions remaining until month end (0 = last day)
    for i in range(N - 2, -1, -1): to_end[i] = 0 if last[i] else to_end[i + 1] + 1
    to_end[-1] = 99
    base = np.full(N, np.nan); cnt = np.zeros(N, int)
    for i in range(1, N):
        if first[i]: base[i] = C[i - 1]; cnt[i] = 0
        else: base[i] = base[i - 1]; cnt[i] = cnt[i - 1] + 1
    mtd = (np.r_[np.nan, C[:-1]] / base - 1) / (np.r_[np.nan, sig[:-1]] * 1.25 * np.sqrt(np.maximum(cnt, 1)))
    quarter = np.isin(days.month, [3, 6, 9, 12])
    for D, t, em, k, qonly in itertools.product((1, 2, 3), (0.5, 1.0, 1.5), (0, 330, 360), (0.15, 0.25, 0.4), (False, True)):
        R = []
        for i in range(15, N):
            if to_end[i] >= D or not np.isfinite(mtd[i]) or not np.isfinite(sig[i]) or cnt[i] < 5: continue
            if qonly and not quarter[i]: continue
            if abs(mtd[i]) < t: continue
            s = -int(np.sign(mtd[i])); e = o[i, em]; st = k * sig[i] * e
            px, _, _ = walk(o[i], h[i], l[i], c[i], em, s, e, e - s * st, e + s * 2 * st, 389); R.append((s * (px - e) - 2.25 * e / 17000) / st)
        R = np.array(R)
        if len(R) >= 10:
            res.append(dict(per=per, rule=f"D{D} t{t} em{em} k{k} {'Q' if qonly else 'M'}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(res); T.to_csv("iter38_rebal.csv", index=False)
W = T.pivot_table(index="rule", columns="per", values=["win", "R", "n"]); W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
W = W[W["n"].notna().all(axis=1)]
pd.set_option("display.width", 250); print(W.sort_values("minR", ascending=False).head(15).round(3).to_string())
print("rows minR>0:", (W.minR > 0).sum(), "of", len(W), "| max minwin", W.minwin.max())
