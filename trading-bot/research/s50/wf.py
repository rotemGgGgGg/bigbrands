"""Phase 4 — walk-forward for every Phase-1 survivor family (strategy id): each year Y (2013 → 2026) pick the variant with the best
t-stat over the previous 3 years (all 3,888 variants of that strategy), trade it in year Y. The concatenated out-of-sample years are
the honest estimate of 'optimize-then-trade'. Costs ×1 and ×2."""
import itertools, time
import numpy as np, pandas as pd
from multiprocessing import Pool
import signals as G, engine as E
from phase1 import get, SP, TFS, MS, TRS, SIDES, SESS, SLS, TPS

YEARS = list(range(2010, 2027))


def family(arg):
    sid, cx = arg; rows = []
    for tf in TFS:
        B = get(tf)
        for m, trd in itertools.product(MS, TRS):
            L, S = G.signals(B, sid, m, trd)
            for side, sess, sl, tp in itertools.product(SIDES, SESS, SLS, TPS):
                i, x, R, sd = E.sim(B["o"], B["h"], B["l"], B["c"], B["atr"], B["mod"], B["roll"], L, S, sl, tp, side, sess, cx)
                y = B["yr"][i]; s = np.bincount(y - 2010, weights=R, minlength=17); n = np.bincount(y - 2010, minlength=17)
                q = np.bincount(y - 2010, weights=R * R, minlength=17)
                rows.append((sid, tf, m, trd, side, sess, sl, tp, s, n, q))
    return cx, rows


def walk(rows, cx):
    S = np.array([r[8] for r in rows]); N = np.array([r[9] for r in rows]); Q = np.array([r[10] for r in rows]); out = []
    for k, Y in enumerate(YEARS):
        if Y < 2013: continue
        w = slice(Y - 3 - 2010, Y - 2010); s, n, q = S[:, w].sum(1), N[:, w].sum(1), Q[:, w].sum(1)
        mu = s / np.maximum(n, 1); sd = np.sqrt(np.maximum(q / np.maximum(n, 1) - mu ** 2, 1e-12)); t = np.where(n >= 60, mu / sd * np.sqrt(n), -9)
        j = int(np.argmax(t)); out.append(dict(sid=rows[0][0], cx=cx, year=Y, pick="_".join(map(str, rows[j][1:8])), train_t=t[j],
                                               n=int(N[j, k]), R=S[j, k] / max(N[j, k], 1), tot=S[j, k]))
    return out


if __name__ == "__main__":
    P1 = pd.read_csv(SP + "phase1.csv.gz")
    fams = sorted(P1[(P1.tr_n >= 300) & (P1.tr_R > 0) & (P1.tr_t >= 3) & (P1.va_R > 0)].sid.unique())
    t0 = time.time(); res = []
    with Pool(4) as P:
        for cx, rows in P.imap_unordered(family, [(int(s), cx) for s in fams for cx in (1.0, 2.0)]):
            res += walk(rows, cx); print(rows[0][0], cx, f"{time.time() - t0:.0f}s", flush=True)
    W = pd.DataFrame(res); W.to_csv(SP + "wf.csv", index=False)
    S = W.groupby(["sid", "cx"]).agg(years=("year", "size"), n=("n", "sum"), tot=("tot", "sum"), yrs_pos=("tot", lambda x: int((x > 0).sum())))
    S["R"] = S.tot / S.n; print(S.round(3).to_string())
    print(W[W.cx == 1.0].pivot(index="year", columns="sid", values="tot").round(1).to_string())
