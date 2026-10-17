"""Control for the 'open model': is it more than long drift? Compare, per period, (a) the rule, (b) an unconditional long from the
SAME minute on random days, (c) buy at 09:30 → close, (d) the mirrored short rule (open − kσ). Also 1:2 bracket versions."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd
from load import frame, RTH
from engine import walk
exec(open("iter26_web.py").read().split("res = []")[0])          # reuse grids()
rng = np.random.default_rng(0); out = []
for per, o, h, l, c, dow in grids():
    N = len(o); mv = np.abs(c[:, 389] / o[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
    cost = lambda e: 2.25 * e / 17000
    def tr(i, m, side, sl=None, tp=None):
        e = o[i, m]; px, _, _ = walk(o[i], h[i], l[i], c[i], m, side, e, sl, tp, 384); return side * (px - e) - cost(e)
    for k in (0.25, 0.5, 1.0):
        rule, ctrl, short, b12 = [], [], [], []
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            sg = sig[i] * o[i, 0]
            up = np.nonzero(h[i, 1:360] >= o[i, 0] * (1 + k * sig[i]))[0]; dn = np.nonzero(l[i, 1:360] <= o[i, 0] * (1 - k * sig[i]))[0]
            if len(up):
                m = up[0] + 2; rule.append(tr(i, m, 1) / sg)
                j = rng.integers(15, N)
                if np.isfinite(sig[j]): ctrl.append(tr(j, m, 1) / (sig[j] * o[j, 0]))
                e = o[i, m]; b12.append(tr(i, m, 1, e - 0.25 * sg, e + 0.5 * sg) / (0.25 * sg))
            if len(dn): m = dn[0] + 2; short.append(tr(i, m, -1) / sg)
        hold = [tr(i, 0, 1) / (sig[i] * o[i, 0]) for i in range(15, N) if np.isfinite(sig[i])]
        f = lambda x: (round(np.mean(x), 3), round(100 * np.mean(np.array(x) > 0), 1), len(x))
        out.append(dict(per=per, k=k, rule=f(rule), random_day_same_minute=f(ctrl), buy_open_hold=f(hold), mirrored_short=f(short), rule_1to2=f(b12)))
pd.set_option("display.width", 250); print(pd.DataFrame(out).to_string(index=False))
