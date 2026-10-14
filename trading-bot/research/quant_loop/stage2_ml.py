"""Stage 2: machine learning on a dense entry grid. Every 5 minutes 09:45–15:00, both sides, stop = k·σ (k ∈ 0.1/0.2/0.3),
label = 2R target hit before 1R stop (first passage, costs included). ~45 features from all chart types, signed by side.
Model: sklearn HistGradientBoostingClassifier fit on TRAIN; thresholds chosen on VAL; TEST untouched."""
import sys, os, time, pickle
import numpy as np, pandas as pd
from core import F, D, o, h, l, c, v, N, SIG, VALID, SPLIT, first_passage, metrics, Logger, HERE
import charts as C
from sklearn.ensemble import HistGradientBoostingClassifier
CACHE = os.path.join(HERE, "stage2_data.pkl")
TIMES = list(range(15, 331, 5))          # decision minute m (entry m+1): 09:45 … 15:00
STOPK = (0.1, 0.2, 0.3)

def day_feats(i):
    o0 = o[i, 0]; sg = SIG[i] * o0; rows = []
    tp = (h[i] + l[i] + c[i]) / 3; cv = np.cumsum(v[i]); vw = np.cumsum(tp * v[i]) / np.maximum(cv, 1)
    rng = np.maximum(h[i] - l[i], 1e-9); clv = ((c[i] - l[i]) - (h[i] - c[i])) / rng; cd = np.cumsum(clv * v[i])
    hmax = np.maximum.accumulate(h[i]); lmin = np.minimum.accumulate(l[i])
    bricks = C.renko(i, 0.1 * sg); bm = np.array([b[0] for b in bricks]) if bricks else np.array([])
    ho, hh, hl, hc = C.ha(i, 5); hcol = np.sign(hc - ho)
    va = C.value_area(i - 1) if i > 0 and not D.roll[i] else (np.nan, np.nan, np.nan)
    pv = v[i - 1] if i > 0 else v[i]
    for m in TIMES:
        f = {}
        f["tod"] = m
        f["mv"] = (c[i, m] - o0) / sg; f["mv5"] = (c[i, m] - c[i, m - 5]) / sg; f["mv15"] = (c[i, m] - c[i, m - 15]) / sg
        f["mv60"] = (c[i, m] - c[i, max(0, m - 60)]) / sg
        f["pos"] = (c[i, m] - lmin[m]) / max(hmax[m] - lmin[m], 1e-9)
        f["rng"] = (hmax[m] - lmin[m]) / sg
        f["vwd"] = (c[i, m] - vw[m]) / sg
        f["d_hi"] = (hmax[m] - c[i, m]) / sg; f["d_lo"] = (c[i, m] - lmin[m]) / sg
        f["or30"] = ((c[i, m] - h[i, :30].max()) / sg if c[i, m] > h[i, :30].max() else (c[i, m] - l[i, :30].min()) / sg if c[i, m] < l[i, :30].min() else 0) if m >= 30 else np.nan
        f["rv30"] = np.std(np.diff(c[i, max(0, m - 30):m + 1])) * np.sqrt(390) / sg
        f["volr"] = cv[m] / max(pv[:m + 1].sum(), 1)
        f["cd"] = cd[m] / max(cv[m], 1)
        f["cd15"] = (cd[m] - cd[m - 15]) / max(v[i, m - 15:m + 1].sum(), 1)
        k = np.searchsorted(bm, m, side="right")
        if k > 0:
            d0 = bricks[k - 1][1]; run = 0
            for t in range(k - 1, -1, -1):
                if bricks[t][1] == d0: run += 1
                else: break
            f["renko_dir"] = d0; f["renko_run"] = run; f["renko_n"] = k
        else: f["renko_dir"] = 0; f["renko_run"] = 0; f["renko_n"] = 0
        t5 = (m + 1) // 5 - 1
        if t5 >= 0:
            col = hcol[t5]; run = 0
            for t in range(t5, -1, -1):
                if hcol[t] == col: run += 1
                else: break
            f["ha_col"] = col; f["ha_run"] = run
        f["ent30"] = C.perm_entropy(c[i, m - 29:m + 1])
        f["va_pos"] = (c[i, m] - va[2]) / sg if np.isfinite(va[2]) else np.nan
        f["in_va"] = (1 if va[0] < c[i, m] < va[1] else 0) if np.isfinite(va[0]) else np.nan
        f["va_w"] = (va[1] - va[0]) / sg if np.isfinite(va[0]) else np.nan
        for k_ in ("gap", "pret", "pclv", "on_pos", "on_range", "lon_ret", "vol_ratio", "ret5", "ret20", "dow", "tdm", "o_vs_ph", "o_vs_pl"):
            f[k_] = F[k_].values[i]
        f["sig"] = SIG[i]
        rows.append(f)
    return rows

SIGNED = ["mv", "mv5", "mv15", "mv60", "vwd", "or30", "cd", "cd15", "renko_dir", "ha_col", "va_pos", "gap", "pret", "lon_ret", "ret5", "ret20", "o_vs_ph", "o_vs_pl"]

def build():
    if os.path.exists(CACHE): return pickle.load(open(CACHE, "rb"))
    recs = []; t0 = time.time()
    for i in range(1, N):
        if not VALID[i]: continue
        for f, m in zip(day_feats(i), TIMES):
            for side in (1, -1):
                g = dict(f); g["i"] = i; g["m"] = m; g["side"] = side
                for s in SIGNED:
                    if g.get(s) is not None and np.isfinite(g[s]): g[s] = g[s] * side
                for k in STOPK:
                    sp = k * SIG[i] * o[i, 0]
                    g[f"R{k}"] = first_passage(i, m + 1, side, o[i, m + 1], sp, 2.0)[0]
                    g[f"sp{k}"] = sp
                recs.append(g)
        if i % 200 == 0: print("day", i, round(time.time() - t0), "s", flush=True)
    df = pd.DataFrame(recs); pickle.dump(df, open(CACHE, "wb")); return df

if __name__ == "__main__":
    df = build()
    df["split"] = SPLIT[df.i.values]
    feats = [x for x in df.columns if x not in ("i", "m") and not x.startswith("R") and not x.startswith("sp") and x != "split"]
    print("rows", len(df), "features", len(feats))
    L = Logger("stage2_ml"); out = []
    for k in STOPK:
        y = (df[f"R{k}"] > 0).astype(int).values; R = df[f"R{k}"].values; sp = df[f"sp{k}"].values
        tr, va = df.split.values == 0, df.split.values == 1
        print(f"stop {k}σ base win TRAIN {100*y[tr].mean():.1f}% VAL {100*y[va].mean():.1f}%")
        for lr, depth, leaf in ((0.05, 3, 200), (0.05, 6, 200), (0.03, None, 500), (0.1, 4, 1000)):
            mdl = HistGradientBoostingClassifier(learning_rate=lr, max_depth=depth, min_samples_leaf=leaf, max_iter=300,
                                                 early_stopping=True, validation_fraction=0.15, random_state=0)
            mdl.fit(df.loc[tr, feats], y[tr])
            pv = mdl.predict_proba(df.loc[va, feats])[:, 1]; ptr = mdl.predict_proba(df.loc[tr, feats])[:, 1]
            for q in (0.9, 0.97, 0.99, 0.997, 0.999):
                thr = np.quantile(ptr, q)                         # threshold fixed on TRAIN scores
                sel = pv >= thr
                m_va = metrics(R[va][sel], sp[va][sel])
                cfg = dict(stop_sig=k, lr=lr, depth=depth, leaf=leaf, top_q=q, rr=2.0)
                st = "val_pass" if m_va.get("n", 0) >= 30 and m_va["win"] >= 70 and m_va["exp_R"] > 0 else "val_fail"
                L.log("ml_hgb", cfg, "val", m_va, st, "" if st == "val_pass" else "val win<70 or n<30")
                out.append(dict(cfg, **{k2: m_va.get(k2) for k2 in ("n", "win", "realized_rr", "exp_R", "ci_win_lo", "ci_win_hi")}))
                print(cfg, {k2: m_va.get(k2) for k2 in ("n", "win", "realized_rr", "exp_R", "ci_win_lo", "ci_win_hi")}, flush=True)
    L.close()
    pd.DataFrame(out).to_csv(os.path.join(HERE, "stage2_ml_summary.csv"), index=False)
