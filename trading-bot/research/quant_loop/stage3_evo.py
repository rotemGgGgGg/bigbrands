"""Stage 3: evolutionary rule search. A rule = conjunction of 2–4 conditions (feature ≶ TRAIN-quantile threshold) on the
stage-2 entry grid (features already signed by side), optional time window. Trade = FIRST qualifying entry of the day.
Fitness (TRAIN only) = Wilson lower bound of the 2R-before-1R win rate, n_days ≥ 40. Generations: random → mutate the elite.
Every evaluated rule is logged (compact) to logs/stage3_<worker>.csv.gz; elite go to VAL. Seeded & resumable per worker."""
import sys, os, pickle, json, time, gzip, csv
import numpy as np, pandas as pd
from core import SPLIT, wilson, HERE
W, NW = int(sys.argv[1]), int(sys.argv[2]); GENS = int(sys.argv[3]) if len(sys.argv) > 3 else 6
rng = np.random.default_rng(1000 + W)
df = pickle.load(open(os.path.join(HERE, "stage2_data.pkl"), "rb"))
df = df.sort_values(["i", "m", "side"]).reset_index(drop=True)
FEATS = [x for x in df.columns if x not in ("i", "m", "side") and not x.startswith("R") and not x.startswith("sp")]
X = df[FEATS].to_numpy(np.float32); I = df.i.values; M = df.m.values; split = SPLIT[I]
TR = split == 0; VA = split == 1
Q = {f: np.nanquantile(X[TR, k], np.linspace(0.05, 0.95, 19)) for k, f in enumerate(FEATS)}
LAB = {k: df[f"R{k}"].values for k in (0.1, 0.2, 0.3)}
day_start = np.r_[0, np.nonzero(np.diff(I))[0] + 1]

def first_per_day(mask):
    idx = np.nonzero(mask)[0]
    if len(idx) == 0: return idx
    _, first = np.unique(I[idx], return_index=True)
    return idx[first]

def evaluate(rule, part):
    mask = part.copy()
    for f, op, t in rule["conds"]:
        x = X[:, FEATS.index(f)]
        mask &= (x > t) if op == ">" else (x < t)
    a, b = rule["win"]; mask &= (M >= a) & (M < b)
    if rule["side"]: mask &= df.side.values == rule["side"]
    idx = first_per_day(mask)
    R = LAB[rule["stop"]][idx]
    n = len(R)
    if n == 0: return n, 0, 0, 0
    w = (R > 0).sum(); lo, _ = wilson(w, n)
    return n, w / n, R.mean(), lo

def random_rule():
    k = rng.integers(2, 5); fs = rng.choice(FEATS, k, replace=False)
    conds = [(f, rng.choice([">", "<"]), float(rng.choice(Q[f]))) for f in fs]
    wins = [(0, 400), (0, 90), (60, 180), (150, 270), (240, 331)]
    return dict(conds=conds, win=wins[rng.integers(len(wins))], stop=float(rng.choice([0.1, 0.2, 0.3])), side=int(rng.choice([0, 1, -1])))

def mutate(r):
    r = json.loads(json.dumps(r)); r["conds"] = [tuple(c) for c in r["conds"]]; r["win"] = tuple(r["win"])
    op = rng.integers(4)
    if op == 0:
        j = rng.integers(len(r["conds"])); f, o_, t = r["conds"][j]; r["conds"][j] = (f, o_, float(rng.choice(Q[f])))
    elif op == 1 and len(r["conds"]) < 4:
        f = rng.choice([x for x in FEATS if x not in [c[0] for c in r["conds"]]]); r["conds"].append((f, rng.choice([">", "<"]), float(rng.choice(Q[f]))))
    elif op == 2 and len(r["conds"]) > 2: r["conds"].pop(rng.integers(len(r["conds"])))
    else: r["stop"] = float(rng.choice([0.1, 0.2, 0.3]))
    return r

out = gzip.open(os.path.join(HERE, "logs", f"stage3_{W}.csv.gz"), "at", newline="")
wr = csv.writer(out); n_eval = 0
pop = [random_rule() for _ in range(int(sys.argv[4]) if len(sys.argv) > 4 else 20000)]
elite_all = []
for g in range(GENS):
    scored = []
    for r in pop:
        n, win, eR, lo = evaluate(r, TR); n_eval += 1
        wr.writerow([W, g, json.dumps(r), n, round(win, 4), round(eR, 4), round(lo, 4)])
        if n >= 40: scored.append((lo, win, eR, n, r))
    scored.sort(key=lambda x: -x[0]); elite = scored[:200]; elite_all += elite
    print(f"worker {W} gen {g}: evaluated {n_eval}, best train win-LB {elite[0][0]:.3f} win {elite[0][1]:.3f} n {elite[0][3]}", flush=True)
    pop = [mutate(e[4]) for e in elite for _ in range(50)] + [random_rule() for _ in range(5000)]
out.close()
# VAL check of the final unique elite (top 300 by train LB)
seen = set(); res = []
for lo, win, eR, n, r in sorted(elite_all, key=lambda x: -x[0]):
    key = json.dumps(r, sort_keys=True)
    if key in seen: continue
    seen.add(key)
    vn, vw, vR, vlo = evaluate(r, VA)
    res.append(dict(rule=key, train_n=n, train_win=round(100 * win, 1), train_R=round(eR, 3), train_lb=round(100 * lo, 1),
                    val_n=vn, val_win=round(100 * vw, 1), val_R=round(vR, 3)))
    if len(res) >= 300: break
pd.DataFrame(res).to_csv(os.path.join(HERE, "logs", f"stage3_val_{W}.csv"), index=False)
print("worker", W, "done, evaluated", n_eval, flush=True)
