"""Phase 2 — combinations.
 (a) Confirmation filters: each Phase-1 survivor family's best variant (by TRAIN t) × state of every other template B
     (B's last signal direction must agree; or B fired the same direction within the last N bars, N ∈ {1, 3, 10}) on the same TF.
 (b) Portfolio: daily-R series of the survivors (top 5 per strategy by train t) + the four earlier components
     (No-Wick, GapFB, Pre-Fade, Opex), greedy forward selection with weights {0.5, 1, 2} on TRAIN daily Sharpe (beam 20).
All selection on 2010-19 only; validate 2020-23 and test 2024-26 reported."""
import os, pickle, itertools, time
import numpy as np, pandas as pd
from multiprocessing import Pool
import bars, signals as G, engine as E
from phase1 import get, pstats, SP

P1 = pd.read_csv(SP + "phase1.csv.gz")
SURV = P1[(P1.tr_n >= 300) & (P1.tr_R > 0) & (P1.tr_t >= 3) & (P1.va_R > 0)]
KEY = ["sid", "tf", "m", "trend", "side", "sess", "sl", "tp"]


def run(cfg, L=None, S=None):
    B = get(cfg["tf"])
    if L is None: L, S = G.signals(B, cfg["sid"], cfg["m"], cfg["trend"])
    i, x, R, sd = E.sim(B["o"], B["h"], B["l"], B["c"], B["atr"], B["mod"], B["roll"], L, S, cfg["sl"], cfg["tp"], cfg["side"], cfg["sess"], 1.0)
    return i, R


def state(L, S):
    st = np.where(L, 1.0, np.where(S, -1.0, np.nan)); return pd.Series(st).ffill().fillna(0).values


def recent(X, n):
    return pd.Series(X.astype(float)).rolling(n, min_periods=1).max().values > 0


def confirm_job(cfg):
    cfg = dict(cfg); B = get(cfg["tf"]); L, S = G.signals(B, cfg["sid"], cfg["m"], cfg["trend"]); rows = []
    for b in range(1, 51):
        if b == cfg["sid"]: continue
        Lb, Sb = G.signals(B, b, 1.0, 0); stb = state(Lb, Sb)
        for mode, (fl, fs) in [("state", (stb == 1, stb == -1))] + [(f"recent{n}", (recent(Lb, n), recent(Sb, n))) for n in (1, 3, 10)]:
            i, R = run(cfg, L & fl, S & fs)
            rows.append(dict(**cfg, filt=b, mode=mode, **pstats(B["yr"][i], R)))
    return rows


if __name__ == "__main__":
    t0 = time.time()
    best = SURV.sort_values("tr_t", ascending=False).groupby("sid").head(1)
    base = [dict(r) for r in best[KEY].to_dict("records")]
    with Pool(4) as P:
        rows = sum(P.map(confirm_job, base), [])
    C = pd.DataFrame(rows); C.to_csv(SP + "phase2_confirm.csv.gz", index=False)
    print("confirmation variants:", len(C), f"{time.time() - t0:.0f}s")
    # daily series for the portfolio search
    top = SURV.sort_values("tr_t", ascending=False).groupby("sid").head(5)
    daily = {}
    for r in top[KEY].to_dict("records"):
        B = get(r["tf"]); i, R = run(r)
        daily["s%02d_%s" % (r["sid"], "_".join(str(r[k]) for k in KEY[1:]))] = pd.Series(R).groupby(pd.DatetimeIndex(B["day"][i])).sum()
    pickle.dump(daily, open(SP + "phase2_daily.pkl", "wb")); print("series:", len(daily), f"{time.time() - t0:.0f}s")
