"""Iter 41 (queue 43) — confluence of the weak survivors, decided at 10:00 (three periods):
 OD  open-drive direction (iter 40: first-30 extreme at the open, |close@10:00 − open| ≥ 0.2σ)
 POC direction from the 10:00 price to the prior-day TPO POC when ≥ 0.25σ away (iter 33 magnet)
 OM  Reddit open-model: +0.5σ above the open before 10:00 → +1 (long-only rule, iter 26)
 OPX opex Friday → −1 (iter 30)
Score = sum of the available signs. Trades at 10:00 (market, next minute open), stop k·σ, target 2k, exit close.
Reported: each signal alone, OD with each agreeing / disagreeing partner, and score ≥ 2 / ≥ 3."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
exec(open("iter30_calendar.py").read().split("\nres = []")[0])
res = []
for per, o, h, l, c, dow in grids():
    if per == "2012-19":
        f0 = frame("NSXUSD"); days = RTH(f0[f0.index.notna()][:"2019-12-31"]).days
    else:
        import lib; days = lib.DAYS[(lib.YR < 2024) if per == "2020-23" else (lib.YR >= 2024)]
    N = len(o); O = o[:, 0]; C = c[:, 389]; sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    opx = cal(days)["opex"]
    poc = np.full(N, np.nan)
    for i in range(N):
        if not np.isfinite(sig[i]): continue
        b = 0.02 * sig[i] * O[i]; q = np.round(c[i] / b); v, cnt = np.unique(q, return_counts=True); poc[i] = np.median(v[cnt == cnt.max()]) * b
    S = np.zeros((N, 4), int)
    for i in range(1, N):
        if not np.isfinite(sig[i]): continue
        sg = sig[i] * O[i]; c30 = c[i, 29]; mv = (c30 - O[i]) / sg
        if mv >= 0.2 and O[i] - l[i, :30].min() <= 0.05 * sg: S[i, 0] = 1
        if mv <= -0.2 and h[i, :30].max() - O[i] <= 0.05 * sg: S[i, 0] = -1
        if np.isfinite(poc[i - 1]) and abs(poc[i - 1] - c30) >= 0.25 * sg: S[i, 1] = int(np.sign(poc[i - 1] - c30))
        if (h[i, :30] >= O[i] + 0.5 * sg).any(): S[i, 2] = 1
        if opx[i]: S[i, 3] = -1
    names = ["OD", "POC", "OM", "OPX"]
    def run(side, k):
        R = []
        for i in range(15, N):
            s = side[i]
            if s == 0 or not np.isfinite(sig[i]): continue
            e = o[i, 30]; st = k * sig[i] * O[i]
            px, _, _ = walk(o[i], h[i], l[i], c[i], 30, s, e, e - s * st, e + s * 2 * st, 389); R.append((s * (px - e) - 2.25 * e / 17000) / st)
        return np.array(R)
    rules = {f"{n} alone": S[:, j] for j, n in enumerate(names)}
    for j, n in enumerate(names[1:], 1):
        rules[f"OD & {n} agree"] = np.where((S[:, 0] != 0) & (S[:, 0] == S[:, j]), S[:, 0], 0)
        rules[f"OD & {n} disagree"] = np.where((S[:, 0] != 0) & (S[:, j] == -S[:, 0]), S[:, 0], 0)
    sc = S.sum(1)
    rules["score>=2"] = np.where(np.abs(sc) >= 2, np.sign(sc), 0); rules["score>=3"] = np.where(np.abs(sc) >= 3, np.sign(sc), 0)
    for (nm, sd), k in itertools.product(rules.items(), (0.15, 0.25, 0.4)):
        R = run(sd.astype(int), k)
        if len(R) >= 10: res.append(dict(per=per, rule=f"{nm} k{k}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(res); T.to_csv("iter41_confluence.csv", index=False)
W = T.pivot_table(index="rule", columns="per", values=["win", "R", "n"]); W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
pd.set_option("display.width", 250); print(W.sort_values("minR", ascending=False).round(3).to_string())
