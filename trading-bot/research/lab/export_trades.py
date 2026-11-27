"""Per-trade R series for every strategy on the Edge Lab page (same sources as series.json), for the app's
Monte Carlo and portfolio engines. Writes trades.json: {id: {"t": [ISO date...], "r": [R...], "units": str}}."""
import os as _os; DATA = _os.path.join(_os.path.expanduser(_os.environ.get("EDGE_DATA", "~/edge-data")), "")  # raw data + caches (set EDGE_DATA to move it)
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "../creative"); sys.path.insert(0, "../macro"); sys.path.insert(0, "../allo"); sys.path.insert(0, "../spmodel")
SP = DATA
import rdm, fomc, convex as X, avp_port as P, avp_eq as AE
S, U = {}, {}
fo = set(fomc.dates())
g = pd.read_pickle(SP + "gotobi_book_usd.pkl"); S["gotobi"] = g / g[g.index.year <= 2019].abs().mean(); U["gotobi"] = "normalised R (1 = avg 2012-19 day)"
T = rdm.trades("none", "all"); T = T[~T.index.isin(fo)]; b = T.pts / T.entry * 1e4; S["rdm"] = b / b[b.index.year <= 2019].abs().mean(); U["rdm"] = "normalised R (1 = avg 2012-19 trade)"
S["rdm10"] = X.run("F2", 0.15, 10.0); U["rdm10"] = "R after 1 pt cost"
S["rdmtrail"] = X.run("F2", 0.25, "run"); U["rdmtrail"] = "R after 1 pt cost"
S["avp"] = P.run("USATECHIDXUSD", 5).R_cost; U["avp"] = "R after 1 pt cost"
D = pd.read_pickle(SP + "avp_eq_data.pkl"); Y = D.index.year; I = D[Y <= 2019]; F = AE.FEAT
mu, sd = I[F].values.mean(0), I[F].values.std(0); sd[sd == 0] = 1; Z = (I[F].values - mu) / sd; A = np.c_[np.ones(len(Z)), Z]
beta = np.linalg.solve(A.T @ A + 50 * np.diag([0] + [1] * len(F)), A.T @ I.R_cost.values); pr = np.c_[np.ones(len(D)), (D[F].values - mu) / sd] @ beta
S["avpeq"] = D.R_cost[pr > 0]; U["avpeq"] = "R after 1 pt cost"
for k in "AB":
    sp = pd.read_csv(SP + f"sp_trades_{k}.csv"); sp.index = pd.to_datetime(sp.entry_time, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    S["sp" if k == "A" else "sp_B"] = sp.r; U["sp" if k == "A" else "sp_B"] = "R before costs (5-min simulation)"
import pluto; S["pluto"] = pluto.run("NSXUSD", "full", "liquidity"); U["pluto"] = "R"
out = {}
for k, s in S.items():
    s = s.dropna().sort_index()
    out[k] = dict(units=U[k], t=[d.strftime("%Y-%m-%dT%H:%M") for d in s.index], r=[round(float(x), 4) for x in s.values])
json.dump(out, open("trades.json", "w"), separators=(",", ":"))
print({k: len(v["r"]) for k, v in out.items()})
