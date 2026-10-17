"""Iter 35 — overseas index lead-lag into the NQ open (HistData CFDs: GRXEUR = DAX, JPXJPY = Nikkei 225; NY wall-clock time).
Windows (NY time): Europe 03:00 → 09:29, Tokyo 19:00 (prev day) → 02:00, NQ overnight 18:00 → 09:29 (same windows for NQ).
Signals at 09:30 (all known before the NQ cash open):
 R  residual catch-up: z(DAX_eu − β·NQ_eu) with β, σ from the previous 60 days → trade NQ in the residual sign if |z| ≥ t
 RJ same with Nikkei over the Tokyo window
 AG agreement: DAX_eu, Nikkei_tokyo and NQ_on all the same sign and each |ret| ≥ t·σ(60d) → follow at 09:30 (and fade variant)
Trade: 09:30 market, stop k·σ_day, target 2k·σ_day, exit close. Periods 2012–19 / 2020–23 (NSXUSD + Databento) / 2024–25."""
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
DAX, NKY, NSX = frame("GRXEUR"), frame("JPXJPY"), frame("NSXUSD")
dax_eu = win_ret(DAX, 180, 569); nky_tk = win_ret(NKY, 1140, 120); nq_eu = win_ret(NSX, 180, 569); nq_on = win_ret(NSX, 1080, 569)
X = pd.concat(dict(dax=dax_eu, nky=nky_tk, nqeu=nq_eu, nqon=nq_on), axis=1).dropna()
# rolling β / residual z using only past days
beta = (X.dax.rolling(60).cov(X.nqeu) / X.nqeu.rolling(60).var()).shift()
resid = X.dax - beta * X.nqeu; z_dax = (resid - resid.rolling(60).mean().shift()) / resid.rolling(60).std().shift()
bj = (X.nky.rolling(60).cov(X.nqon) / X.nqon.rolling(60).var()).shift()
rj = X.nky - bj * X.nqon; z_nky = (rj - rj.rolling(60).mean().shift()) / rj.rolling(60).std().shift()
zs = {c: X[c] / X[c].rolling(60).std().shift() for c in ("dax", "nky", "nqon")}
F = pd.DataFrame(dict(zd=z_dax, zn=z_nky, d=zs["dax"], n=zs["nky"], q=zs["nqon"]))
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
    for t, k in itertools.product((0.5, 1.0, 1.5, 2.0), (0.15, 0.25, 0.4)):
        rules = {}
        rules["R dax residual"] = np.where(np.abs(G.zd.values) >= t, np.sign(G.zd.values), 0)
        rules["RJ nikkei residual"] = np.where(np.abs(G.zn.values) >= t, np.sign(G.zn.values), 0)
        ag = (np.sign(G.d) == np.sign(G.n)) & (np.sign(G.n) == np.sign(G.q)) & (G[["d", "n", "q"]].abs().min(axis=1) >= t / 2)
        rules["AG agree follow"] = np.where(ag, np.sign(G.q.values), 0); rules["AG agree fade"] = -rules["AG agree follow"]
        for nm, sd in rules.items():
            sd = np.nan_to_num(sd).astype(int); R = run(sd, k)
            if len(R) >= 15:
                res.append(dict(per=per, rule=f"{nm} t{t} k{k}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(res); T.to_csv("iter35_leadlag.csv", index=False)
W = T.pivot_table(index="rule", columns="per", values=["win", "R", "n"]); W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
pd.set_option("display.width", 250); print(W.sort_values("minR", ascending=False).head(20).round(3).to_string())
print("rows minR>0:", (W.minR > 0).sum(), "of", len(W), "| max minwin", W.minwin.max())
