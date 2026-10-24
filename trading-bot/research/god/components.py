"""'God strategy' stage 1 — every edge that survived earlier research, re-gridded on 16 years of NQ (2010-06 → 2026-10).
Components (all costs = 2.25 NQ pt × price/17000 per round trip, stop-first, no look-ahead, results in R):
  NW   No-Wick pullback (research/nowick): 243,000 variants = TF {3,5,15m} × wick tol {5,10,15 %} × trend filter (5) ×
       entry {limit at open, limit 25 % into body, next open after touch} × stop {0.75,1,1.25,1.5,2 ATR} × RR {1.5,2,3,4,5} ×
       expiry {20,50,100 bars} × signal window {09:30-16, 09:30-12, 12-16, 10-15:30} × side {both, long, short}.
  GFB  GapFB gap-direction opening-range breakout: 6,480 = OR {5,15,30 min} × stop {1.5,2,3 ATR} × trail {off,3,4,5,6 ATR} ×
       BE {off,1R,2R} × entry cut-off {30,60,90 min} × min gap {0.2,0.3,0.4,0.5 %} × quality score ≥ {0,1,2,3}.
  PF   Pre-Open Fade: 324 = window start {07:30,08:00,08:30}→08:59 × |z| ≥ {1.5,2,2.5,3} × TP {0.5,0.75,1}×move ×
       SL {0.75,1,1.5}×move × exit {11:00,13:00,15:55}.
  OPX  Opex-Friday short: 54 = SL {0.3,0.4,0.5}σ × TP {1.5,2,3}×SL × entry {09:30,09:45,10:00} × exit {12:00,15:55}.
Selection statistics use 2010-19 only (train); 2020-23 = validate, 2024-26 = test."""
import os, sys, itertools, time, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "nowick"), os.path.join(HERE, "..", "gapfb"), os.path.join(HERE, ".."), os.path.join(HERE, "..", "longhist")]
import numpy as np, pandas as pd
from numba import njit
from multiprocessing import Pool
STRESS = os.environ.get("STRESS", "0") == "1"          # strict fills (1 tick through) + 2x costs everywhere
CX, THRU = (2.0, 0.25) if STRESS else (1.0, 0.0)
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/god" + ("_stress/" if STRESS else "/")
os.makedirs(SP, exist_ok=True)
TOPK = {"NW": 25, "GFB": 10, "PF": 6, "OPX": 4}


def pstats(yr, R):
    out = {}
    for nm, m in (("tr", yr <= 2019), ("va", (yr >= 2020) & (yr <= 2023)), ("te", yr >= 2024)):
        r = R[m]; out[nm + "_n"] = len(r); out[nm + "_R"] = r.mean() if len(r) else np.nan
        out[nm + "_win"] = 100 * (r > 0).mean() if len(r) else np.nan
        out[nm + "_t"] = r.mean() / r.std() * np.sqrt(len(r)) if len(r) > 2 and r.std() > 0 else np.nan
    out["all_R"] = R.mean() if len(R) else np.nan; out["all_tot"] = R.sum()
    ys = np.unique(yr); out["yrs_pos"] = int(sum(R[yr == y].sum() > 0 for y in ys)); out["yrs"] = len(ys)
    return out


# ---------------------------------------------------------------- NW
import nowick as N
from robust import prep as nw_prep
NWG = dict(tf=(3, 5, 15), tol=(0.05, 0.10, 0.15), filt=N.FILT, entry=((0.0, 0), (0.25, 0), (0.0, 1)), stopk=(0.75, 1.0, 1.25, 1.5, 2.0),
           rr=(1.5, 2.0, 3.0, 4.0, 5.0), expiry=(20, 50, 100), win=((570, 960), (570, 720), (720, 960), (600, 930)), side=(0, 1, -1))
_NW = {}


def nw_arrays(tf):
    if tf in _NW: return _NW[tf]
    o, h, l, c, atr, sess, last, up, dn, day = nw_prep("NQ", tf)
    first = np.r_[True, sess[1:] != sess[:-1]]; i = np.arange(len(o)); k = i - np.maximum.accumulate(np.where(first, i, 0))
    mins = 570 + k * tf
    rng = h - l; lw = np.minimum(o, c) - l; uw = h - np.maximum(o, c); eps = 1e-9 * c
    _NW[tf] = dict(o=o, h=h, l=l, c=c, atr=atr, sess=sess, last=last, up=up, dn=dn, yr=day.year.values, day=day.values,
                   mins=mins, bull=c > o, bear=c < o, lw=lw, uw=uw, rng=rng, eps=eps)
    return _NW[tf]


def nw_run(cfg, daily=False):
    A = nw_arrays(cfg["tf"]); w0, w1 = cfg["win"]; wm = (A["mins"] >= w0) & (A["mins"] < w1)
    sl = A["bull"] & (A["lw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["up"][cfg["filt"]] & wm
    ss = A["bear"] & (A["uw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["dn"][cfg["filt"]] & wm
    lv, mode = cfg["entry"]; cf, cmin = N.COST["NQ"]
    ti, R = N.sim(A["o"], A["h"], A["l"], A["c"], A["atr"], A["sess"], A["last"], sl, ss, lv, mode, cfg["expiry"], cfg["stopk"],
                  cfg["rr"], 0, cf * CX, cmin * CX, THRU, cfg["side"])
    if daily: return pd.Series(R).groupby(pd.DatetimeIndex(A["day"][ti])).sum()
    return pstats(A["yr"][ti], R)


def nw_job(chunk):
    return [dict(id=i, **pstats_wrap(cfg)) for i, cfg in chunk]


def pstats_wrap(cfg): return nw_run(cfg)


NW_CFGS = [dict(zip(NWG, v)) for v in itertools.product(*NWG.values())]


# ---------------------------------------------------------------- GapFB
GFBG = dict(orm=(5, 15, 30), stopk=(1.5, 2.0, 3.0), trail=(0.0, 3.0, 4.0, 5.0, 6.0), be=(0.0, 1.0, 2.0), cut=(30, 60, 90),
            gmin=(0.002, 0.003, 0.004, 0.005), smin=(0, 1, 2, 3))


def gfb_arrays():
    from gapfb2 import arrays
    rows = [r for v in arrays().values() for r in v]
    d = pd.DatetimeIndex([r[0] for r in rows]); g = np.array([r[1] for r in rows])
    O, H, L, C, A = (np.array([r[k] for r in rows]) for k in range(2, 7))
    s = np.sign(g); pc = np.r_[np.nan, C[:-1, 389]]; po = np.r_[np.nan, O[:-1, 0]]
    ph = np.r_[np.nan, H[:-1].max(1)]; pl = np.r_[np.nan, L[:-1].min(1)]
    ok = np.r_[False, (d[1:] - d[:-1]).days <= 4]
    yday_against = (np.sign(pc - po) == -s) & ok
    beyond = ((O[:, 0] > ph) | (O[:, 0] < pl)) & ok
    score = yday_against.astype(int) + beyond.astype(int)            # + 09:44 close in gap direction, added per OR length below
    return d, g, O, H, L, C, A, score


@njit(cache=True)
def gfb_sim(g, O, H, L, C, A, score, orm, stopk, trail, be, cut, gmin, smin, cx):
    n = len(g); outi = np.empty(n, np.int64); outr = np.empty(n); nt = 0
    for i in range(n):
        if abs(g[i]) < gmin: continue
        s = 1 if g[i] > 0 else -1; o, h, l, c, a = O[i], H[i], L[i], C[i], A[i]
        sc = score[i] + (1 if s * (c[14] - o[0]) > 0 else 0)
        if sc < smin: continue
        orh = h[:orm].max(); orl = l[:orm].min(); j = -1
        for k in range(orm, min(cut, 389) + 1):
            if (h[k] >= orh) if s == 1 else (l[k] <= orl):
                j = k; break
        if j < 0: continue
        e = max(orh, o[j]) if s == 1 else min(orl, o[j]); at = a[j]; st = stopk * at
        if not st > 0: continue
        sl = e - s * st; best = e; px = np.nan
        for k in range(j, 386):
            if (l[k] <= sl) if s == 1 else (h[k] >= sl):
                px = sl if k == j else (min(o[k], sl) if s == 1 else max(o[k], sl)); break
            best = max(best, h[k]) if s == 1 else min(best, l[k])
            if be > 0 and s * (best - e) >= be * st: sl = max(sl, e) if s == 1 else min(sl, e)
            if trail > 0: sl = max(sl, best - trail * at) if s == 1 else min(sl, best + trail * at)
        if np.isnan(px): px = c[385]
        outi[nt] = i; outr[nt] = (s * (px - e) - cx * 2.25 * e / 17000) / st; nt += 1
    return outi[:nt], outr[:nt]


GFB_CFGS = [dict(zip(GFBG, v)) for v in itertools.product(*GFBG.values())]


# ---------------------------------------------------------------- PF and OPX (24 h grid)
@njit(cache=True)
def walk(o, h, l, c, j, s, e, sl, tp, last):
    for k in range(j, last + 1):
        if (l[k] <= sl) if s == 1 else (h[k] >= sl): return min(o[k], sl) if s == 1 else max(o[k], sl)
        if (h[k] >= tp) if s == 1 else (l[k] <= tp): return tp
    return c[last]


@njit(cache=True)
def pf_sim(X, sd, t0, t859, t9, z, tp, slm, tex, cx):
    n = X.shape[0]; outi = np.empty(n, np.int64); outr = np.empty(n); nt = 0
    for i in range(21, n):
        if not sd[i] > 0: continue
        mv = X[i, t859, 3] - X[i, t0, 0]
        if abs(mv / X[i, t0, 0] / sd[i]) <= z: continue
        s = -1 if mv > 0 else 1; e = X[i, t9, 0]; size = abs(mv)
        px = walk(X[i, :, 0], X[i, :, 1], X[i, :, 2], X[i, :, 3], t9, s, e, e - s * slm * size, e + s * tp * size, tex)
        outi[nt] = i; outr[nt] = (s * (px - e) - cx * 2.25 * e / 17000) / (slm * size); nt += 1
    return outi[:nt], outr[:nt]


@njit(cache=True)
def opx_sim(X, opex, sig, te, slk, tpm, tex, cx):
    n = X.shape[0]; outi = np.empty(n, np.int64); outr = np.empty(n); nt = 0
    for i in range(n):
        if not opex[i] or not sig[i] > 0: continue
        e = X[i, te, 0]; st = slk * sig[i] * e
        px = walk(X[i, :, 0], X[i, :, 1], X[i, :, 2], X[i, :, 3], te, -1, e, e + st, e - tpm * st, tex)
        outi[nt] = i; outr[nt] = (e - px - cx * 2.25 * e / 17000) / st; nt += 1
    return outi[:nt], outr[:nt]


def x24():
    from sess24 import build
    S = build(); d = pd.DatetimeIndex(np.r_[S["A"][0], S["B"][0]]); X = np.concatenate([S["A"][1], S["B"][1]]).astype(np.float64)
    return d, X


PFG = dict(w0=("07:30", "08:00", "08:30"), z=(1.5, 2.0, 2.5, 3.0), tp=(0.5, 0.75, 1.0), sl=(0.75, 1.0, 1.5), ex=("11:00", "13:00", "15:55"))
OPXG = dict(sl=(0.3, 0.4, 0.5), tpm=(1.5, 2.0, 3.0), te=("09:30", "09:45", "10:00"), ex=("12:00", "15:55"))


def small_components():
    from sess24 import t2m
    d, X = x24(); yr = d.year.values; out = {}
    rows, series = [], {}
    for v in itertools.product(*PFG.values()):
        cfg = dict(zip(PFG, v)); t0 = t2m(cfg["w0"])
        pre = X[:, t2m("08:59"), 3] / X[:, t0, 0] - 1; sd = pd.Series(pre).rolling(20).std().shift().values
        ii, R = pf_sim(X, sd, t0, t2m("08:59"), t2m("09:00"), cfg["z"], cfg["tp"], cfg["sl"], t2m(cfg["ex"]) - 1, CX)
        k = len(rows); rows.append(dict(id=k, **cfg, **pstats(yr[ii], R))); series[k] = pd.Series(R).groupby(d[ii]).sum()
    out["PF"] = (pd.DataFrame(rows), series)
    opex = np.array([(x.weekday() == 4) and (15 <= x.day <= 21) for x in d])
    sig = pd.Series(np.abs(X[:, t2m("15:55"), 3] / X[:, t2m("09:30"), 0] - 1)).rolling(14).mean().shift().values
    rows, series = [], {}
    for v in itertools.product(*OPXG.values()):
        cfg = dict(zip(OPXG, v))
        ii, R = opx_sim(X, opex, sig, t2m(cfg["te"]), cfg["sl"], cfg["tpm"], t2m(cfg["ex"]) - 1, CX)
        k = len(rows); rows.append(dict(id=k, **cfg, **pstats(yr[ii], R))); series[k] = pd.Series(R).groupby(d[ii]).sum()
    out["OPX"] = (pd.DataFrame(rows), series)
    d, g, O, H, L, C, A, score = gfb_arrays(); yr = d.year.values; rows, series = [], {}
    for k, cfg in enumerate(GFB_CFGS):
        ii, R = gfb_sim(g, O, H, L, C, A, score, cfg["orm"], cfg["stopk"], cfg["trail"], cfg["be"], cfg["cut"], cfg["gmin"], cfg["smin"], CX)
        rows.append(dict(id=k, **cfg, **pstats(yr[ii], R))); series[k] = pd.Series(R).groupby(d[ii]).sum()
    out["GFB"] = (pd.DataFrame(rows), series)
    return out


def pick(T, k, nmin):
    T = T[(T.tr_n >= nmin) & (T.tr_R > 0)].sort_values("tr_t", ascending=False)
    return list(T.id.head(k))


if __name__ == "__main__":
    t0 = time.time()
    sm = small_components(); daily = {}
    for c, (T, ser) in sm.items():
        T.to_csv(SP + f"stats_{c}.csv.gz", index=False); ids = pick(T, TOPK[c], {"GFB": 150, "PF": 60, "OPX": 40}[c])
        daily[c] = pd.DataFrame({f"{c}{i}": ser[i] for i in ids}); print(c, len(T), "variants, picked", ids, f"{time.time() - t0:.0f}s", flush=True)
    chunks = [[(i, NW_CFGS[i]) for i in range(j, len(NW_CFGS), 64)] for j in range(64)]
    rows = []
    with Pool(4) as P:
        for r in P.imap_unordered(nw_job, chunks):
            rows += r; print("NW", len(rows), f"{time.time() - t0:.0f}s", flush=True)
    T = pd.DataFrame(rows).sort_values("id")
    T = pd.concat([pd.DataFrame(NW_CFGS).assign(id=range(len(NW_CFGS))).astype({"win": str, "entry": str}).set_index("id"), T.set_index("id")], axis=1).reset_index()
    T.to_csv(SP + "stats_NW.csv.gz", index=False)
    ids = pick(T, TOPK["NW"], 1000)
    daily["NW"] = pd.DataFrame({f"NW{i}": nw_run(NW_CFGS[i], daily=True) for i in ids}); print("NW picked", ids)
    pickle.dump(daily, open(SP + "daily.pkl", "wb"))
    print("stage-1 variants:", len(T) + sum(len(v[0]) for v in sm.values()), f"{time.time() - t0:.0f}s")
