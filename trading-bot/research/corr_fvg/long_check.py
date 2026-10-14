"""Out-of-sample check of the two surviving candidates on Databento NQ 2020-01 → 2024-05 (data the Yahoo study never saw)
and on the full 2020–2026, single asset (neither candidate needs ES/YM). Same simulate() as grid.py."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import grid as G
S = G.S
full = pd.read_pickle(S + "full1m.pkl"); full = full[~full.index.duplicated()][["open", "high", "low", "close"]]
def bars(rule):
    return full.resample(rule, origin=pd.Timestamp("2020-01-01 18:00", tz=full.index.tz)).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def run(tf, cond, entry, stop, rr):
    nq = bars("1h" if tf == "1h" else "4h"); idx = nq.index
    o, h, l, c = (nq[k].values for k in ("open", "high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc))); atr = pd.Series(tr).ewm(alpha=1 / 14).mean().values
    nb, ns = G.fvg(nq); q, qend = G.quarter(idx, tf)
    med = np.median(np.diff(idx.asi8)); gb = np.r_[False, np.diff(idx.asi8) > 3 * med]
    out = []; busy = -1
    for t in range(60, len(nq) - 2):
        for side, flag in ((1, nb[t]), (-1, ns[t])):
            if not flag or t <= busy or gb[t] or gb[t - 1]: continue
            near = l[t] if side == 1 else h[t]; far = h[t - 2] if side == 1 else l[t - 2]
            ev = dict(t=t, side=side, near=near, far=far, gap_atr=abs(near - far) / atr[t], disp_atr=abs(c[t - 1] - o[t - 1]) / atr[t], q=int(q[t]), qend=qend[t], es=False, ym=False)
            if not cond(ev): continue
            r = G.simulate(pd.Series(ev), (o, h, l, c, atr), idx, entry, stop, rr, 24 if tf == "1h" else 12, False, None, False)
            if np.isfinite(r): out.append((idx[t], r)); busy = t + 1
    return pd.Series(dict(out))
cands = {"1h Q2(Tue) gap≥0.5ATR long, market, stop far−0.5ATR, 1:1": ("1h", lambda e: e["q"] == 2 and e["gap_atr"] >= 0.5 and e["side"] == 1, "market", "atr05", 1.0),
         "4h Q4(week4) gap≥0.25ATR disp≥1ATR both, market, stop edge, 1:1": ("4h", lambda e: e["q"] == 4 and e["gap_atr"] >= 0.25 and e["disp_atr"] >= 1.0, "market", "edge", 1.0)}
for name, (tf, cond, en, st, rr) in cands.items():
    x = run(tf, cond, en, st, rr)
    for nm, m in (("2020-01→2024-05 (never seen)", x.index < pd.Timestamp("2024-05-22", tz=x.index.tz)), ("2024-05→2026-10 (study period)", x.index >= pd.Timestamp("2024-05-22", tz=x.index.tz))):
        y = x[m]; print(f"{name} | {nm}: n {len(y)} win {100*(y>0).mean():.1f}% exp {y.mean():+.3f}R")
    print("   by year:", {k: (len(v), round(100 * (v > 0).mean()), round(v.mean(), 2)) for k, v in x.groupby(x.index.year)})
