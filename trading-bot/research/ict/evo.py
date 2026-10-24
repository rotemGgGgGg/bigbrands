"""Evolutionary refinement (selection on TRAIN 2010-2017 only). Parents = top configs of the random search by a robust train
score (t-stat with ≥ 200 train trades); children = 1-3 parameter mutations. Every child is evaluated on train/validate/test
(2010-2023) and logged; selection pressure uses train only. Holdout 2024-26 untouched."""
import os, sys, json, time, glob
import numpy as np, pandas as pd
from multiprocessing import Pool
import data, search as S, ict_engine as E
from space import CHOICES, WINDOWS, make

OUT = data.SP + "evo/"; os.makedirs(OUT, exist_ok=True)


def score(r):
    return r["tr_t"] if (r["tr_n"] >= 200 and np.isfinite(r["tr_t"])) else -99


def mutate(cfg, rng):
    c = dict(cfg)
    for _ in range(int(rng.integers(1, 4))):
        k = rng.choice(["w", "mask"] + list(CHOICES))
        if k == "w": c["w"] = int(rng.integers(len(WINDOWS)))
        elif k == "mask":
            b = int(rng.integers(9)); m = c["mask"] ^ (1 << b); c["mask"] = m if m else c["mask"]
        else:
            v = CHOICES[k]; c[k] = v[int(rng.integers(len(v)))]
    return c


def evaluate(cfg):
    if not S._G: S.init()
    G = S._G; P = make(cfg["w"], cfg["mask"], **{k: cfg[k] for k in CHOICES})
    d, t, s, R, rk, pts = E.run(G["X"], G["LV"], G["E2"], G["prev"], P, 0, G["h"])
    return dict(cfg=json.dumps(cfg), **S.metrics(G["yr"][d], R, pts))


if __name__ == "__main__":
    gens, kids = int(sys.argv[1]), int(sys.argv[2])
    R = pd.concat([pd.read_csv(f) for f in glob.glob(S.OUT + "c*.csv.gz")])
    R["score"] = R.apply(score, axis=1); pop = R.sort_values("score", ascending=False).head(200)
    pop = [dict(json.loads(c), _score=s) for c, s in zip(pop.cfg, pop.score)]
    rng = np.random.default_rng(42); seen = set(json.dumps({k: v for k, v in p.items() if k != "_score"}, sort_keys=True) for p in pop)
    t0 = time.time(); allrows = []
    with Pool(4) as P:
        for g in range(gens):
            w = np.array([max(p["_score"], 0.01) for p in pop]); w = w / w.sum(); children = []
            while len(children) < kids:
                par = pop[int(rng.choice(len(pop), p=w))]; ch = mutate({k: v for k, v in par.items() if k != "_score"}, rng)
                key = json.dumps(ch, sort_keys=True)
                if key not in seen: seen.add(key); children.append(ch)
            rows = P.map(evaluate, children); allrows += [dict(gen=g, **r) for r in rows]
            for ch, r in zip(children, rows): ch["_score"] = score(r)
            pop = sorted(pop + children, key=lambda p: -p["_score"])[:200]
            print(f"gen {g}: best train t {pop[0]['_score']:.2f}, median top200 {np.median([p['_score'] for p in pop]):.2f}, "
                  f"evaluated {len(allrows)}, {time.time() - t0:.0f}s", flush=True)
            pd.DataFrame(allrows).to_csv(OUT + "evo.csv.gz", index=False)
