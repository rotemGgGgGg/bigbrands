"""Random search over the ICT space (resumable). Each chunk = 1,000 configs sampled from seed (base + chunk id).
Evaluation uses only 2010-06 → 2023-12 (holdout 2024-01 → 2026-10 is never touched here).
Periods: TRAIN 2010-2017, VALIDATE 2018-2020, TEST 2021-2023. Every config and its metrics are saved."""
import os, sys, time, json
import numpy as np, pandas as pd
from multiprocessing import Pool
import ict_data as data, ict_engine as E
from ict_space import sample

OUT = data.SP + "search/"; os.makedirs(OUT, exist_ok=True)
PER = (("tr", 2010, 2017), ("va", 2018, 2020), ("te", 2021, 2023))
_G = {}


def init():
    D = data.load(); _G.update(X=D["X"], LV=D["LV"], E2=D["ema200"], yr=D["yr"],
                               prev=np.r_[False, (D["days"][1:] - D["days"][:-1]).days <= 4],
                               h=int(np.searchsorted(D["days"].values, np.datetime64("2024-01-01"))))


def metrics(yr, R, pts):
    out = {}
    for nm, a, b in PER:
        m = (yr >= a) & (yr <= b); r = R[m]; n = len(r); out[nm + "_n"] = n
        if n == 0: out.update({nm + "_win": np.nan, nm + "_R": np.nan, nm + "_t": np.nan, nm + "_pf": np.nan, nm + "_dd": 0.0, nm + "_usd": 0.0}); continue
        w = r[r > 0].sum(); ls = -r[r < 0].sum(); eq = np.cumsum(r)
        out.update({nm + "_win": 100 * (r > 0).mean(), nm + "_R": r.mean(), nm + "_t": r.mean() / r.std() * np.sqrt(n) if n > 2 and r.std() > 0 else np.nan,
                    nm + "_pf": w / ls if ls > 0 else np.nan, nm + "_dd": float((np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()),
                    nm + "_usd": 2.0 * pts[m].sum()})
    ys = np.arange(2010, 2024); s = np.array([R[yr == y].sum() for y in ys]); out["yrs_pos"] = int((s > 0).sum())
    return out


def chunk(cid, n=1000, base=1_000_000):
    f = f"{OUT}c{cid:05d}.csv.gz"
    if os.path.exists(f): return cid, 0
    if not _G: init()
    rng = np.random.default_rng(base + cid); rows = []
    for k in range(n):
        P, cfg = sample(rng, return_dict=True)
        d, t, s, R, rk, pts = E.run(_G["X"], _G["LV"], _G["E2"], _G["prev"], P, 0, _G["h"])
        rows.append(dict(cid=cid, k=k, cfg=json.dumps(cfg), **metrics(_G["yr"][d], R, pts)))
    pd.DataFrame(rows).to_csv(f, index=False); return cid, n


if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2]); t0 = time.time(); done = 0
    with Pool(4) as P:
        for cid, n in P.imap_unordered(chunk, range(a, b)):
            done += n; print(cid, done, f"{time.time() - t0:.0f}s", flush=True)
    print("done", done)
