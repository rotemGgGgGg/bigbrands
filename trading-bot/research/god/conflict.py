"""One futures account = one net position. Re-test the final portfolio with the live-bot rule:
trades are taken in time order; a new trade whose side is OPPOSITE to an open position (from any component) is skipped,
same-side overlaps are allowed (size adds up). Sizes: No-Wick 1, GapFB 1, Pre-Fade 2, Opex 2 MNQ micros (Lucid 100K plan).
Strict fills, research cost model (2.25 pt × price/17000 per round trip). Entry/exit clock times come from the simulators."""
import os, sys, inspect, re, itertools
os.environ["STRESS"] = "1"
import numpy as np, pandas as pd
from numba import njit
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import components as K
import nowick as N
from sess24 import t2m
from proof import NW_ID, GFB_ID, PF_ID, OPX_ID
SIZE = {"No-Wick": 1, "GapFB": 1, "Pre-Fade": 2, "Opex": 2}


def patch(fn, extra_store, ret_extra):
    """add extra output arrays (exit index, side, risk) to a numba simulator."""
    src = inspect.getsource(fn.py_func).split("\n", 1)[1]
    src = src.replace("outr = np.empty(n)", "outr = np.empty(n); ox = np.empty(n, np.int64); osd = np.empty(n, np.int64); ok_ = np.empty(n)")
    src = re.sub(r"; nt \+= 1", f"; {extra_store}; nt += 1", src, count=1)
    src = src.replace("return outi[:nt], outr[:nt]", f"return outi[:nt], outr[:nt], {ret_extra}")
    ns = {"np": np}; exec(src, ns); return njit(ns[fn.__name__])


nw_sim = patch(N.sim, "ox[nt] = m; osd[nt] = s; ok_[nt] = risk", "ox[:nt], osd[:nt], ok_[:nt]")
gfb_sim = patch(K.gfb_sim, "ox[nt] = min(k, 385); osd[nt] = s; ok_[nt] = st", "ox[:nt], osd[:nt], ok_[:nt]")


def walk_i(o, h, l, c, j, s, e, sl, tp, last):
    for k in range(j, last + 1):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl): return (min(o[k], sl) if s == 1 else max(o[k], sl)), k
        if (h[k] >= tp) if s == 1 else (l[k] <= tp): return tp, k
    return c[last], last


def clock(day, minute_since_18):  # sess24 minute → NY timestamp on the trading day
    m = (minute_since_18 + 1080) % 1440
    return pd.Timestamp(day) + pd.Timedelta(minutes=int(m))


def trades():
    rows = []; cf, cmin = N.COST["NQ"]
    cfg = K.NW_CFGS[NW_ID]; A = K.nw_arrays(cfg["tf"]); w0, w1 = cfg["win"]; wm = (A["mins"] >= w0) & (A["mins"] < w1)
    sl = A["bull"] & (A["lw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["up"][cfg["filt"]] & wm
    ss = A["bear"] & (A["uw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["dn"][cfg["filt"]] & wm
    ti, R, xi, sd, rk = nw_sim(A["o"], A["h"], A["l"], A["c"], A["atr"], A["sess"], A["last"], sl, ss, 0.0, 0, cfg["expiry"], cfg["stopk"],
                               cfg["rr"], 0, cf, cmin, 0.25, cfg["side"])
    for a, r, x, s, k in zip(ti, R, xi, sd, rk):
        d = pd.Timestamp(A["day"][a]); rows.append(("No-Wick", d + pd.Timedelta(minutes=int(A["mins"][a])),
                                                  d + pd.Timedelta(minutes=int(A["mins"][x] + cfg["tf"])), s, r * k * 2, k * 2))
    d, g, O, H, L, C, AA, score = K.gfb_arrays(); c = K.GFB_CFGS[GFB_ID]
    ii, R, xi, sd, rk = gfb_sim(g, O, H, L, C, AA, score, c["orm"], c["stopk"], c["trail"], c["be"], c["cut"], c["gmin"], c["smin"], 1.0)
    for i, r, x, s, k in zip(ii, R, xi, sd, rk):
        j = c["orm"] + int(np.argmax((H[i, c["orm"]:] >= H[i, :c["orm"]].max()) if s == 1 else (L[i, c["orm"]:] <= L[i, :c["orm"]].min())))
        rows.append(("GapFB", d[i] + pd.Timedelta(minutes=570 + j), d[i] + pd.Timedelta(minutes=570 + int(x) + 1), s, r * k * 2, k * 2))
    d, X = K.x24(); o, h, l, cc = (X[:, :, q] for q in range(4))
    p = [dict(zip(K.PFG, v)) for v in itertools.product(*K.PFG.values())][PF_ID]; t0 = t2m(p["w0"]); t859, t9 = t2m("08:59"), t2m("09:00")
    pre = cc[:, t859] / o[:, t0] - 1; sdv = pd.Series(pre).rolling(20).std().shift().values
    for i in range(21, len(d)):
        if not sdv[i] > 0: continue
        mv = cc[i, t859] - o[i, t0]
        if abs(mv / o[i, t0] / sdv[i]) <= p["z"]: continue
        s = -1 if mv > 0 else 1; e = o[i, t9]; size = abs(mv); risk = p["sl"] * size
        px, k = walk_i(o[i], h[i], l[i], cc[i], t9, s, e, e - s * risk, e + s * p["tp"] * size, t2m(p["ex"]) - 1)
        rows.append(("Pre-Fade", clock(d[i], t9), clock(d[i], k + 1), s, (s * (px - e) - 2.25 * e / 17000) * 2, risk * 2))
    q = [dict(zip(K.OPXG, v)) for v in itertools.product(*K.OPXG.values())][OPX_ID]
    opex = np.array([(x.weekday() == 4) and (15 <= x.day <= 21) for x in d])
    sig = pd.Series(np.abs(cc[:, t2m("15:55")] / o[:, t2m("09:30")] - 1)).rolling(14).mean().shift().values; te = t2m(q["te"])
    for i in np.nonzero(opex & (sig > 0))[0]:
        e = o[i, te]; st = q["sl"] * sig[i] * e
        px, k = walk_i(o[i], h[i], l[i], cc[i], te, -1, e, e + st, e - q["tpm"] * st, t2m(q["ex"]) - 1)
        rows.append(("Opex", clock(d[i], te), clock(d[i], k + 1), -1, (e - px - 2.25 * e / 17000) * 2, st * 2))
    T = pd.DataFrame(rows, columns=["comp", "entry", "exit", "side", "usd1", "risk1"])
    T["usd"] = T.usd1 * T.comp.map(SIZE); return T.sort_values("entry").reset_index(drop=True)


def net_rule(T):
    keep = np.ones(len(T), bool); open_ = []          # (exit, side)
    for i, r in T.iterrows():
        open_ = [(x, s) for x, s in open_ if x > r.entry]
        if any(s != r.side for _, s in open_): keep[i] = False; continue
        open_.append((r.exit, r.side))
    return keep


def yearly(T):
    y = T.entry.dt.year
    return T.groupby(y).apply(lambda t: pd.Series(dict(trades=len(t), win=100 * (t.usd > 0).mean(),
                                                      rr=t.usd[t.usd > 0].mean() / -t.usd[t.usd <= 0].mean(), usd=t.usd.sum())))


if __name__ == "__main__":
    T = trades(); k = net_rule(T); T["kept"] = k; T.to_csv(os.path.join(HERE, "trades_netting.csv"), index=False)
    print("skipped:", (~k).sum(), "of", len(T), "| by comp:", T[~k].comp.value_counts().to_dict())
    pd.set_option("display.width", 200)
    A, B = yearly(T), yearly(T[T.kept])
    print(pd.concat([A.add_prefix("all_"), B.add_prefix("net_")], axis=1).round(1).to_string())
    for nm, t in (("all", T), ("netting", T[T.kept])):
        dd = t.groupby(t.entry.dt.normalize()).usd.sum().cumsum(); print(nm, "total $", round(t.usd.sum()), "maxDD $", round((dd.cummax() - dd).max()),
                                                                          "2024+ $/yr", round(t[t.entry.dt.year >= 2024].usd.sum() / 2.75))
