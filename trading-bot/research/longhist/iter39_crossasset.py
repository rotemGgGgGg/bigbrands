"""Iter 39 (queue 41) — cross-asset overnight leads into the NQ open: USDJPY (risk-on/off carry), silver XAGUSD, Brent BCOUSD
(HistData, NY wall clock). For each asset: residual of its overnight (18:00 → 09:29) return vs NQ's overnight return (rolling 60-day
β), z-scored on past data → trade NQ at 09:30 in the residual's sign (catch-up) and the opposite (fade). Plus a risk-on composite
(mean of the three asset z's). Stop k·σ_day, target 2k, exit close. Three periods."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
exec(open("iter26_web.py").read().split("\nres = []")[0])
from load import frame
def win_ret(f, a, b):
    """return over [a, b) NY minutes for each session key; a > b means a starts the previous evening."""
    f = f[f.index.notna()]; m = f.index.hour * 60 + f.index.minute
    key = (f.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)    # 18:00 belongs to the next day
    sel = ((m >= a) | (m < b)) if a > b else ((m >= a) & (m < b))
    g = f[sel].groupby(key[sel]); first = g.open.first(); last = g.close.last(); n = g.size()
    r = (last / first - 1); return r[n >= 30]
A = {nm: win_ret(frame(p), 1080, 569) for nm, p in (("jpy", "USDJPY"), ("xag", "XAGUSD"), ("brent", "BCOUSD"))}
nq_on = win_ret(frame("NSXUSD"), 1080, 569)
X = pd.concat(dict(nq=nq_on, **A), axis=1, sort=True).dropna()
Z = {}
for nm in A:
    b = (X[nm].rolling(60).cov(X.nq) / X.nq.rolling(60).var()).shift(); r = X[nm] - b * X.nq
    Z[nm] = (r - r.rolling(60).mean().shift()) / r.rolling(60).std().shift()
Z["composite"] = pd.concat(Z, axis=1).mean(axis=1) * np.sqrt(3)
F = pd.DataFrame(Z)
res = []
for per, o, h, l, c, dow in grids():
    if per == "2012-19":
        f0 = frame("NSXUSD"); days = RTH(f0[f0.index.notna()][:"2019-12-31"]).days
    else:
        import lib; days = lib.DAYS[(lib.YR < 2024) if per == "2020-23" else (lib.YR >= 2024)]
    G = F.reindex(pd.DatetimeIndex(days)); N = len(o); O = o[:, 0]; C = c[:, 389]
    sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    def run(sides, k):
        R = []
        for i in range(15, N):
            s = sides[i]
            if not s or not np.isfinite(sig[i]): continue
            e = O[i]; st = k * sig[i] * e
            px, _, _ = walk(o[i], h[i], l[i], c[i], 0, s, e, e - s * st, e + s * 2 * st, 389); R.append((s * (px - e) - 2.25 * e / 17000) / st)
        return np.array(R)
    for nm, t, k, mode in itertools.product(F.columns, (0.5, 1.0, 1.5, 2.0), (0.15, 0.25, 0.4), ("catchup", "fade")):
        z = G[nm].values; sd = np.where(np.abs(z) >= t, np.sign(z), 0) * (1 if mode == "catchup" else -1)
        R = run(np.nan_to_num(sd).astype(int), k)
        if len(R) >= 15:
            res.append(dict(per=per, rule=f"{nm} {mode} t{t} k{k}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(res); T.to_csv("iter39_crossasset.csv", index=False)
W = T.pivot_table(index="rule", columns="per", values=["win", "R", "n"]); W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
W = W[W["n"].notna().all(axis=1)]
pd.set_option("display.width", 250); print(W.sort_values("minR", ascending=False).head(15).round(3).to_string())
print("rows minR>0:", (W.minR > 0).sum(), "of", len(W), "| max minwin", W.minwin.max())
