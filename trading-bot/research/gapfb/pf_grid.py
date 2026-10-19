"""Iter 76 (queue 77) — Pre-Open Fade grid on real NQ: pre-window L (60/90/120 min ending 08:59), |z| threshold, TP a×move,
SL b×move, exit time. Select on TRAIN 2010–19 (by t), keep those with VALIDATE 2020–23 t > 1, then TEST 2024–26 for the top 3."""
import sys, itertools; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m
S = build(); t9 = t2m("09:00")
def run(days, X, L, z, a, b, ex):
    o, h, l, c = (X[:, :, i] for i in range(4)); t0 = t9 - L; te = t2m(ex)
    pre = c[:, t9 - 1] / o[:, t0] - 1; sd = pd.Series(pre).rolling(20).std().shift().values; R = []
    for i in np.nonzero(np.abs(pre / np.where(sd > 0, sd, np.nan)) > z)[0]:
        mv = c[i, t9 - 1] - o[i, t0]; s = -1 if mv > 0 else 1; e = o[i, t9]; size = abs(mv); sl = e - s * b * size; tp = e + s * a * size; px = None
        for k in range(t9, te + 1):
            if (l[i, k] <= sl) if s == 1 else (h[i, k] >= sl): px = min(o[i, k], sl) if s == 1 else max(o[i, k], sl); break
            if (h[i, k] >= tp) if s == 1 else (l[i, k] <= tp): px = tp; break
        if px is None: px = c[i, te]
        R.append((s * (px - e) - 2.25 * e / 17000) / (b * size))
    return np.array(R)
def split(key, msk):
    days, X = S[key]
    if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
    return days, X
TR, VA, TE = split("A", None), split("B", "lt"), split("B", "ge")
rows = []
for L, z, a, b, ex in itertools.product((60, 90, 120), (1.5, 2.0, 2.5, 3.0), (0.3, 0.5, 0.75, 1.0), (0.5, 1.0, 1.5), ("11:00", "13:00", "15:55")):
    R = run(*TR, L, z, a, b, ex)
    if len(R) < 60: continue
    rows.append(dict(L=L, z=z, a=a, b=b, ex=ex, n=len(R), win=100 * (R > 0).mean(), R=R.mean(), t=R.mean() / R.std() * np.sqrt(len(R))))
T = pd.DataFrame(rows).sort_values("t", ascending=False).head(40); out = []
for _, r in T.iterrows():
    V = run(*VA, int(r.L), r.z, r.a, r.b, r.ex)
    out.append(dict(r, n_val=len(V), win_val=100 * (V > 0).mean(), R_val=V.mean(), t_val=V.mean() / V.std() * np.sqrt(len(V))))
V = pd.DataFrame(out); K = V[V.t_val > 1].sort_values("t", ascending=False).head(3)
pd.set_option("display.width", 250); print(V.head(15).round(3).to_string(index=False))
print("\nTEST 2024-26 (top 3 that passed validation; base L60 z2 a0.5 b1.0 ex13:00 for reference):")
for _, r in pd.concat([K, pd.DataFrame([dict(L=60, z=2.0, a=0.5, b=1.0, ex="13:00")])]).iterrows():
    R = run(*TE, int(r.L), r.z, r.a, r.b, r.ex)
    print(f"  L{int(r.L)} z{r.z} a{r.a} b{r.b} exit {r.ex}: n={len(R)} win={100*(R>0).mean():.1f}% R={R.mean():+.3f}")
