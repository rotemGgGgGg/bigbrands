"""Iter 26 — web batch, three periods (NSXUSD 2012–19 CFD; Databento MNQ 2020–23 / 2024–26), cost scaled to price.
1 Yu-Rentzler-Wolf (JOIM): last night's return (prior close → 09:30) predicts an intraday REVERSAL; conditioned on the sign of
  yesterday's intraday return and on Monday. Trade at 09:30 against the overnight move, exit 15:55 (and 1:2 σ-bracket variant).
2 Reddit 'open model' (long-only ORB on % deviation from the open): first time price > open × (1 + k·σ) → long to the close.
3 'Fair price' mean reversion to the NY open: price ≥ k σ away from the 09:30 open before 12:00 → fade back to the open (target),
  stop at 2× the distance (planned 1:0.5) and a 1:2 variant (target open, stop = half the distance)."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
from load import frame, RTH
from engine import walk
sys.path.insert(0, "../gapfb")
from sess24 import build, t2m
_S = build(); _R0 = t2m("09:30")
def grids():
    for nm, key, msk in (("2010-19", "A", None), ("2020-23", "B", "lt"), ("2024-26", "B", "ge")):
        days, X = _S[key]
        if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
        R = X[:, _R0:_R0 + 390]
        yield nm, R[:, :, 0], R[:, :, 1], R[:, :, 2], R[:, :, 3], days.weekday.values
res = []
for per, o, h, l, c, dow in grids():
    N = len(o); mv = np.abs(c[:, 389] / o[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
    pc = np.r_[np.nan, c[:-1, 389]]; pin = np.r_[np.nan, c[:-1, 389] / o[:-1, 0] - 1]
    cost = lambda e: 2.25 * e / 17000
    def tr(i, m, side, sl, tp):
        e = o[i, m]; px, _, _ = walk(o[i], h[i], l[i], c[i], m, side, e, sl, tp, 384); return side * (px - e) - cost(e), e
    def add(name, R):
        R = [r for r in R if np.isfinite(r)]
        if len(R) < 20: return
        R = np.array(R); w, lo = R[R > 0], R[R <= 0]
        res.append(dict(per=per, rule=name, n=len(R), win=round(100 * (R > 0).mean(), 1), rr=round(w.mean() / -lo.mean(), 2) if len(lo) and len(w) else np.nan, R=round(R.mean(), 3)))
    for cond, k in itertools.product(("all", "yday_same", "yday_opp", "monday"), (0.0, 0.5, 1.0)):
        R = []; R2 = []
        for i in range(15, N):
            if not np.isfinite(sig[i]) or not np.isfinite(pc[i]): continue
            ov = o[i, 0] / pc[i] - 1
            if abs(ov) < k * sig[i] or ov == 0: continue
            if cond == "yday_same" and np.sign(pin[i]) != np.sign(ov): continue
            if cond == "yday_opp" and np.sign(pin[i]) == np.sign(ov): continue
            if cond == "monday" and dow[i] != 0: continue
            side = -int(np.sign(ov)); sg = sig[i] * o[i, 0]
            p, e = tr(i, 0, side, None, None); R.append(p / sg)
            p2, e = tr(i, 0, side, o[i, 0] - side * 0.25 * sg, o[i, 0] + side * 0.5 * sg); R2.append(p2 / (0.25 * sg))
        add(f"1 overnight reversal {cond} |ov|>{k}σ → close (σ units)", R); add(f"1 overnight reversal {cond} |ov|>{k}σ 1:2 (R)", R2)
    for k in (0.25, 0.5, 1.0):
        R = []
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            lvl = o[i, 0] * (1 + k * sig[i]); hit = np.nonzero(h[i, 1:360] >= lvl)[0]
            if not len(hit): continue
            m = hit[0] + 2; p, e = tr(i, m, 1, None, None); R.append(p / (sig[i] * o[i, 0]))
        add(f"2 open model long-only +{k}σ → close (σ units)", R)
    for k, mode in itertools.product((0.5, 0.75, 1.0), ("tp_open_sl2x", "rr2")):
        R = []
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            sg = sig[i] * o[i, 0]; dev = (c[i, :150] - o[i, 0]) / sg; hit = np.nonzero(np.abs(dev[5:]) >= k)[0]
            if not len(hit): continue
            m = hit[0] + 6; side = -int(np.sign(dev[hit[0] + 5])); e = o[i, m]; dist = abs(e - o[i, 0])
            if dist <= 0: continue
            sl = e - side * (2 * dist if mode == "tp_open_sl2x" else 0.5 * dist); p, _ = tr(i, m, side, sl, o[i, 0]); R.append(p / abs(e - sl))
        add(f"3 fade to NY open |dev|≥{k}σ {mode} (R)", R)
T = pd.DataFrame(res); T.to_csv("iter26_web_real.csv", index=False)
P = T.pivot_table(index="rule", columns="per", values=["win", "R"]); pd.set_option("display.width", 250); pd.set_option("display.max_rows", 100)
P["minR"] = P["R"].min(axis=1); print(P.sort_values("minR", ascending=False).round(3).to_string())
