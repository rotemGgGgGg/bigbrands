"""Every filter combination × every exit config, per timeframe. TRAIN = first 60 % of the period, TEST = last 40 %.
Candidate = TRAIN n ≥ 30, TRAIN win ≥ 70 %, TRAIN expectancy > 0, planned R:R ≥ 2 reported separately. Logs counts honestly."""
import numpy as np, pandas as pd, pickle, itertools, sys
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
tf = sys.argv[1]
EV, sims, t0, t1 = pickle.load(open(S + f"cfvg_{tf}.pkl", "rb"))
keys = list(sims); E = np.vstack([sims[k] for k in keys])            # (configs, events)
cut = t0 + (t1 - t0) * 0.6; TR = (EV.ts < cut).values; TE = ~TR
F = {"corr": {"all": EV.side == EV.side, "any": EV.es | EV.ym, "both": EV.es & EV.ym, "not": ~(EV.es | EV.ym), "es": EV.es, "ym": EV.ym},
     "q": {"any": EV.q >= 0, **{f"Q{k}": EV.q == k for k in (1, 2, 3, 4)}},
     "sess": {"any": EV.sess == EV.sess, **{s: EV.sess == s for s in ("asia", "london", "nyam", "nypm")}},
     "bias": {"none": EV.side == EV.side, "ema": EV.bias_ema == 1, "dopen": EV.bias_dopen == 1, "both": (EV.bias_ema == 1) & (EV.bias_dopen == 1)},
     "size": {"any": EV.gap_atr >= 0, "g25": EV.gap_atr >= 0.25, "g50": EV.gap_atr >= 0.5},
     "disp": {"any": EV.disp_atr >= 0, "d1": EV.disp_atr >= 1.0},
     "dir": {"both": EV.side != 0, "long": EV.side == 1, "short": EV.side == -1}}
base = ~EV.ndog.values
rows = []; n_combo = 0
for combo in itertools.product(*[list(v.items()) for v in F.values()]):
    m = base.copy()
    for _, mk in combo: m &= mk.values
    if m.sum() < 20: n_combo += len(keys); continue
    sub = E[:, m]; trm, tem = TR[m], TE[m]
    for part, pm in (("tr", trm), ("te", tem)):
        x = sub[:, pm]; ok = ~np.isnan(x)
        n = ok.sum(1); w = (np.nan_to_num(x) > 0).sum(1); s = np.nansum(x, 1)
        if part == "tr": ntr, wtr, str_ = n, w, s
        else: nte, wte, ste = n, w, s
    n_combo += len(keys)
    good = (ntr >= 30) & (wtr >= 0.7 * np.maximum(ntr, 1)) & (str_ > 0)
    for j in np.nonzero(good)[0]:
        rows.append(dict(tf=tf, **{k: v[0] for k, v in zip(F, combo)}, entry=keys[j][0], stop=keys[j][1], rr=keys[j][2], after_q=keys[j][3],
                         alive=keys[j][4], n_tr=int(ntr[j]), win_tr=round(100 * wtr[j] / ntr[j], 1), R_tr=round(str_[j] / ntr[j], 3),
                         n_te=int(nte[j]), win_te=round(100 * wte[j] / max(nte[j], 1), 1), R_te=round(ste[j] / max(nte[j], 1), 3)))
R = pd.DataFrame(rows); R.to_csv(f"cand_{tf}.csv", index=False)
print(f"{tf}: combos evaluated {n_combo:,} | TRAIN candidates (win≥70, n≥30, exp>0): {len(R)}")
if len(R):
    print("  ... of which planned RR≥2:", int((R.rr >= 2).sum()))
    r2 = R[R.n_te >= 15]
    print("  TEST (n≥15): win≥70 & exp>0:", int(((r2.win_te >= 70) & (r2.R_te > 0)).sum()), "| with RR≥2:", int(((r2.win_te >= 70) & (r2.R_te > 0) & (r2.rr >= 2)).sum()))
    print("  mean TRAIN win %.1f → mean TEST win %.1f" % (R.win_tr.mean(), (R.win_te * R.n_te).sum() / max(R.n_te.sum(), 1)))
