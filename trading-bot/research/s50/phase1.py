"""Phase 1 — every template individually: 50 strategies × TF {5,15,60 m} × main lookback ×{0.5,1,2} × trend filter
{template, toggled} × side {both, long, short} × session {24h, RTH, AM} × stop {1,1.5,2,3 ATR} × target {0.5,1,1.5,2,3,4 ATR}
= 194,400 variants. Stats per period (train 2010-19 / validate 2020-23 / test 2024-26)."""
import os, sys, time, itertools
import numpy as np, pandas as pd
from multiprocessing import Pool
import bars, signals as G, engine as E
SP = bars.SP + "s50/"; os.makedirs(SP, exist_ok=True)
TFS = (5, 15, 60); MS = (0.5, 1.0, 2.0); TRS = (0, 1); SIDES = (0, 1, -1); SESS = (0, 1, 2)
SLS = (1.0, 1.5, 2.0, 3.0); TPS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
_B = {}


def get(tf):
    if tf not in _B: _B[tf] = G.prepare(bars.build(tf), tf); _B[tf]["yr"] = pd.DatetimeIndex(_B[tf]["day"]).year.values
    return _B[tf]


def pstats(yr, R):
    out = {}
    for nm, m in (("tr", yr <= 2019), ("va", (yr >= 2020) & (yr <= 2023)), ("te", yr >= 2024)):
        r = R[m]; out[nm + "_n"] = len(r); out[nm + "_R"] = r.mean() if len(r) else np.nan
        out[nm + "_win"] = 100 * (r > 0).mean() if len(r) else np.nan
        out[nm + "_t"] = r.mean() / r.std() * np.sqrt(len(r)) if len(r) > 2 and r.std() > 0 else np.nan
    ys = np.unique(yr); out["yrs_pos"] = int(sum(R[yr == y].sum() > 0 for y in ys)); out["all_R"] = R.mean() if len(R) else np.nan
    return out


def job(arg):
    sid, tf = arg; B = get(tf); rows = []
    for m, trd in itertools.product(MS, TRS):
        L, S = G.signals(B, sid, m, trd)
        for side, sess, sl, tp in itertools.product(SIDES, SESS, SLS, TPS):
            i, x, R, sd = E.sim(B["o"], B["h"], B["l"], B["c"], B["atr"], B["mod"], B["roll"], L, S, sl, tp, side, sess, 1.0)
            rows.append(dict(sid=sid, tf=tf, m=m, trend=trd, side=side, sess=sess, sl=sl, tp=tp, **pstats(B["yr"][i], R)))
    return rows


if __name__ == "__main__":
    t0 = time.time(); jobs = [(s, tf) for tf in TFS for s in range(1, 51)]; out = []
    with Pool(4) as P:
        for r in P.imap_unordered(job, jobs):
            out += r; print(len(out), f"{time.time() - t0:.0f}s", flush=True)
    G_ = pd.DataFrame(out); G_.to_csv(SP + "phase1.csv.gz", index=False); print("done", len(G_))
