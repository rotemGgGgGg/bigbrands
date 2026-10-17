"""Iter 23 — evolutionary rule search on 14 years (NSXUSD 2012–2025). Entry grid every 5 min 09:45–15:00, both sides,
~20 price-only features (signed by side), labels = 2R-before-1R with stop k·σ. Fitness = MIN over (2012–19, 2020–23) of the Wilson
lower bound of the first-trade-per-day win rate (n ≥ 40 in each). 2024–25 is the untouched test. Logged to evo14.csv.gz."""
import sys, os, json, gzip, csv; sys.path.insert(0, "."); sys.path.insert(0, ".."); sys.path.insert(0, "../quant_loop")
import numpy as np, pandas as pd
from load import frame, RTH
from engine import walk
CACHE = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/evo14.pkl"
def wilson(k, n, z=1.96):
    if n == 0: return 0.0
    p = k / n; d = 1 + z * z / n; m = p + z * z / (2 * n); s = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)); return (m - s) / d
if os.path.exists(CACHE): df = pd.read_pickle(CACHE)
else:
    f = frame("NSXUSD"); D = RTH(f[f.index.notna()]); o, h, l, c = D.o, D.h, D.l, D.c; N = len(D.days)
    mv = np.abs(c[:, 389] / o[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
    pc = np.r_[np.nan, c[:-1, 389]]; ph = np.r_[np.nan, h[:-1].max(1)]; pl = np.r_[np.nan, l[:-1].min(1)]; cc = pd.Series(c[:, 389])
    r5 = (cc / cc.shift(5) - 1).shift().values; r20 = (cc / cc.shift(20) - 1).shift().values
    recs = []
    for i in range(21, N):
        if np.isnan(sig[i]) or np.isnan(pc[i]): continue
        sg = sig[i] * o[i, 0]; hmax = np.maximum.accumulate(h[i]); lmin = np.minimum.accumulate(l[i])
        for m in range(15, 331, 5):
            base = dict(i=i, m=m, yr=D.days[i].year, tod=m, dow=D.days[i].weekday(), rng=(hmax[m] - lmin[m]) / sg,
                        pos=(c[i, m] - lmin[m]) / max(hmax[m] - lmin[m], 1e-9), rv30=np.std(np.diff(c[i, max(0, m - 30):m + 1])) * np.sqrt(390) / sg)
            sv = dict(mv=(c[i, m] - o[i, 0]) / sg, mv5=(c[i, m] - c[i, m - 5]) / sg, mv15=(c[i, m] - c[i, m - 15]) / sg, mv60=(c[i, m] - c[i, max(0, m - 60)]) / sg,
                      d_hi=(hmax[m] - c[i, m]) / sg, d_lo=(c[i, m] - lmin[m]) / sg, gap=(o[i, 0] / pc[i] - 1) / sig[i], pret=(pc[i] / o[i - 1, 0] - 1) / sig[i],
                      vs_ph=(c[i, m] - ph[i]) / sg, vs_pl=(c[i, m] - pl[i]) / sg, r5=r5[i] / sig[i], r20=r20[i] / sig[i],
                      or30=((c[i, m] - h[i, :30].max()) / sg if m >= 30 else 0))
            for side in (1, -1):
                g = dict(base); g["side"] = side
                for k_, v_ in sv.items(): g[k_] = v_ * side if k_ not in ("d_hi", "d_lo") else (v_ if side == 1 else (sv["d_lo"] if k_ == "d_hi" else sv["d_hi"]))
                e = o[i, m + 1]; cost = 2.25 * e / 17000
                for kk in (0.1, 0.2, 0.3):
                    sp = kk * sg; px, _, _ = walk(o[i], h[i], l[i], c[i], m + 1, side, e, e - side * sp, e + side * 2 * sp, 384)
                    g[f"R{kk}"] = (side * (px - e) - cost) / sp
                recs.append(g)
    df = pd.DataFrame(recs); df.to_pickle(CACHE)
print("rows", len(df), flush=True)
df = df.sort_values(["i", "m", "side"]).reset_index(drop=True)
FE = [x for x in df.columns if x not in ("i", "m", "yr", "side") and not x.startswith("R")]
X = df[FE].to_numpy(np.float32); I = df.i.values; yr = df.yr.values; per = np.where(yr < 2020, 0, np.where(yr < 2024, 1, 2)); M = df.m.values; SIDE = df.side.values
Q = {f: np.nanquantile(X[per < 2, k], np.linspace(0.05, 0.95, 19)) for k, f in enumerate(FE)}
rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
def evaluate(r):
    mask = np.ones(len(df), bool)
    for f, op, t in r["conds"]:
        x = X[:, FE.index(f)]; mask &= (x > t) if op == ">" else (x < t)
    a, b = r["win"]; mask &= (M >= a) & (M < b)
    if r["side"]: mask &= SIDE == r["side"]
    idx = np.nonzero(mask)[0]
    if not len(idx): return None
    _, first = np.unique(I[idx], return_index=True); idx = idx[first]; Rv = df[f"R{r['stop']}"].values[idx]; p = per[idx]
    out = []
    for k in (0, 1, 2):
        x = Rv[p == k]; out.append((len(x), (x > 0).sum(), x.mean() if len(x) else np.nan))
    return out
def rand_rule():
    k = rng.integers(2, 5); fs = rng.choice(FE, k, replace=False)
    return dict(conds=[(f, str(rng.choice([">", "<"])), float(rng.choice(Q[f]))) for f in fs], win=[(15, 335), (15, 90), (60, 180), (150, 270), (240, 335)][rng.integers(5)],
                stop=float(rng.choice([0.1, 0.2, 0.3])), side=int(rng.choice([0, 1, -1])))
def mutate(r):
    r = json.loads(json.dumps(r)); j = rng.integers(len(r["conds"])); f = r["conds"][j][0]; r["conds"][j][2] = float(rng.choice(Q[f]))
    if rng.random() < 0.3: r["stop"] = float(rng.choice([0.1, 0.2, 0.3]))
    return r
log = gzip.open(f"evo14_{sys.argv[1] if len(sys.argv) > 1 else 0}.csv.gz", "wt", newline=""); w = csv.writer(log)
pop = [rand_rule() for _ in range(15000)]; elite_all = []; n_eval = 0
for gen in range(5):
    sc = []
    for r in pop:
        res = evaluate(r); n_eval += 1
        if res is None: continue
        (n0, k0, m0), (n1, k1, m1), (n2, k2, m2) = res
        fit = min(wilson(k0, n0), wilson(k1, n1)) if n0 >= 40 and n1 >= 40 else 0
        w.writerow([gen, json.dumps(r), n0, k0, n1, k1, n2, k2, round(fit, 4)])
        sc.append((fit, r, res))
    sc.sort(key=lambda x: -x[0]); elite = sc[:150]; elite_all += elite
    print(f"gen {gen}: evaluated {n_eval}, best fitness {elite[0][0]:.3f}", flush=True)
    pop = [mutate(e[1]) for e in elite for _ in range(60)] + [rand_rule() for _ in range(3000)]
log.close()
best = sorted(elite_all, key=lambda x: -x[0])[:20]
for fit, r, res in best[:10]:
    (n0, k0, m0), (n1, k1, m1), (n2, k2, m2) = res
    print(f"fit {fit:.3f} | 12-19 {100*k0/max(n0,1):.0f}% n{n0} R{m0:+.2f} | 20-23 {100*k1/max(n1,1):.0f}% n{n1} R{m1:+.2f} | TEST 24-25 {100*k2/max(n2,1):.0f}% n{n2} R{m2:+.2f} | {json.dumps(r)[:120]}")
