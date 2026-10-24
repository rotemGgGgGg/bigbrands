"""Per-year results of the final portfolio traded with ONE MNQ micro per trade ($2 per NQ point), every component on.
Re-runs the four component simulators (patched to also return the stop distance in points), so $ = R × risk × $2.
Fills: strict (limit fills only when price trades 1 tick through). Costs: the research cost model, 2.25 pt × price/17000 per
round trip (≈ $4.5–6 per micro at 2024-26 prices — above real MNQ commission + 1 tick, so conservative).
MNQ started trading in May 2019; earlier years are NQ prices at micro size (NQ ÷ 10)."""
import os, sys, inspect, itertools, re
os.environ["STRESS"] = "1"
import numpy as np, pandas as pd
from numba import njit
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import components as K
import nowick as N
from sess24 import t2m
from proof import NW_ID, GFB_ID, PF_ID, OPX_ID


def with_risk(fn, risk_expr, extra=None):
    src = inspect.getsource(fn.py_func).split("\n", 1)[1]                      # drop the @njit line
    src = src.replace("outr = np.empty(n)", "outr = np.empty(n); outk = np.empty(n)")
    src = re.sub(r"; nt \+= 1", f"; outk[nt] = {risk_expr}; nt += 1", src, count=1)
    src = src.replace("return outi[:nt], outr[:nt]", "return outi[:nt], outr[:nt], outk[:nt]")
    ns = {"np": np, "walk": K.walk, **(extra or {})}; exec(src, ns); return njit(ns[fn.__name__])


nw_sim = with_risk(N.sim, "risk"); gfb_sim = with_risk(K.gfb_sim, "st")
pf_sim = with_risk(K.pf_sim, "slm * size"); opx_sim = with_risk(K.opx_sim, "st")


def run(cx=1.0, thru=0.25):
    out = []
    cfg = K.NW_CFGS[NW_ID]; A = K.nw_arrays(cfg["tf"]); w0, w1 = cfg["win"]; wm = (A["mins"] >= w0) & (A["mins"] < w1)
    sl = A["bull"] & (A["lw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["up"][cfg["filt"]] & wm
    ss = A["bear"] & (A["uw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["dn"][cfg["filt"]] & wm
    cf, cmin = N.COST["NQ"]
    ti, R, rk = nw_sim(A["o"], A["h"], A["l"], A["c"], A["atr"], A["sess"], A["last"], sl, ss, 0.0, 0, cfg["expiry"], cfg["stopk"], cfg["rr"], 0,
                       cf * cx, cmin * cx, thru, cfg["side"])
    out.append(pd.DataFrame(dict(comp="No-Wick", date=pd.DatetimeIndex(A["day"][ti]), R=R, risk=rk)))
    d, g, O, H, L, C, AA, score = K.gfb_arrays(); c = K.GFB_CFGS[GFB_ID]
    ii, R, rk = gfb_sim(g, O, H, L, C, AA, score, c["orm"], c["stopk"], c["trail"], c["be"], c["cut"], c["gmin"], c["smin"], cx)
    out.append(pd.DataFrame(dict(comp="GapFB", date=d[ii], R=R, risk=rk)))
    d, X = K.x24()
    c = [dict(zip(K.PFG, v)) for v in itertools.product(*K.PFG.values())][PF_ID]; t0 = t2m(c["w0"])
    pre = X[:, t2m("08:59"), 3] / X[:, t0, 0] - 1; sd = pd.Series(pre).rolling(20).std().shift().values
    ii, R, rk = pf_sim(X, sd, t0, t2m("08:59"), t2m("09:00"), c["z"], c["tp"], c["sl"], t2m(c["ex"]) - 1, cx)
    out.append(pd.DataFrame(dict(comp="Pre-Fade", date=d[ii], R=R, risk=rk)))
    c = [dict(zip(K.OPXG, v)) for v in itertools.product(*K.OPXG.values())][OPX_ID]
    opex = np.array([(x.weekday() == 4) and (15 <= x.day <= 21) for x in d])
    sig = pd.Series(np.abs(X[:, t2m("15:55"), 3] / X[:, t2m("09:30"), 0] - 1)).rolling(14).mean().shift().values
    ii, R, rk = opx_sim(X, opex, sig, t2m(c["te"]), c["sl"], c["tpm"], t2m(c["ex"]) - 1, cx)
    out.append(pd.DataFrame(dict(comp="Opex", date=d[ii], R=R, risk=rk)))
    T = pd.concat(out); T["usd"] = T.R * T.risk * 2.0
    return T.sort_values("date")


def yearly(T):
    y = T.date.dt.year
    def agg(t):
        w = t.usd[t.usd > 0]; l = t.usd[t.usd <= 0]
        return pd.Series(dict(trades=len(t), win=100 * len(w) / len(t), rr=w.mean() / -l.mean(), usd=t.usd.sum(), risk_usd=2 * t.risk.mean()))
    return T.groupby(y).apply(agg)


if __name__ == "__main__":
    T = run(); T.to_csv(os.path.join(HERE, "trades_1micro.csv"), index=False)
    pd.set_option("display.width", 200)
    Y = yearly(T); print(Y.round(2).to_string())
    print("total $", round(T.usd.sum()), "| per comp:", T.groupby("comp").usd.sum().round(0).to_dict())
    eq = T.groupby("date").usd.sum().cumsum(); print("max DD $", round((eq.cummax() - eq).max()))
    for c, t in T.groupby("comp"): print(c); print(yearly(t).round(2).to_string())
