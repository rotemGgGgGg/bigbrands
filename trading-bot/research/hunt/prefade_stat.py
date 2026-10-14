"""Significance of the 09:00 fade: t-stats, side-randomization test, and Bonferroni across the 28 clock times."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from prefade import pre_move, trade
rng = np.random.default_rng(0)
s, z = pre_move(60)
days = list(z[z.abs() > 2.0].index)
def R(d, side): return (trade(d, side, abs(s[d]), 0.5, 1.0, 780) - 1.0) / abs(s[d])
fade = np.array([R(d, -int(np.sign(s[d]))) for d in days])
follow = np.array([R(d, int(np.sign(s[d]))) for d in days])
yr = np.array([d.year for d in days])
t = lambda x: x.mean() / x.std(ddof=1) * np.sqrt(len(x))
print("fade avgR %.3f t=%.2f | IS t=%.2f OOS t=%.2f" % (fade.mean(), t(fade), t(fade[yr < 2024]), t(fade[yr >= 2024])))
print("follow (same days, opposite side) avgR %.3f" % follow.mean())
# side randomisation: each day independently fade or follow at random
perm = []
for _ in range(5000):
    m = rng.random(len(days)) < 0.5
    perm.append(np.where(m, fade, follow).mean())
perm = np.array(perm)
p = (perm >= fade.mean()).mean()
print("side-randomisation p = %.4f  → Bonferroni ×28 clock times = %.3f" % (p, min(1, p * 28)))
