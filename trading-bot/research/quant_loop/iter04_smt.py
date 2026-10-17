"""Iteration 4 — SMT / PSP across NQ, ES, YM (Yahoo 1h 2024-05 → 2026-10 and 5m last ~70 days; the only multi-asset data).
SMT: NQ makes a new N-bar high (low) while ES or YM does NOT → fade on NQ at the next bar open; stop = NQ extreme + tick;
target 2–3 R. PSP: on that bar NQ and the other index close in opposite colours. TRAIN = first 60 % of the period, TEST = last 40 %.
Exits on the same timeframe bars (stop first if both touched)."""
import numpy as np, pandas as pd, itertools
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
COST = 2.25; rows = []
for tf in ("1h", "5m"):
    d = {s: pd.read_pickle(S + f"yf_{s}_{tf}.pkl")[["open", "high", "low", "close"]] for s in ("NQ", "ES", "YM")}
    ix = d["NQ"].index.intersection(d["ES"].index).intersection(d["YM"].index); d = {k: x.loc[ix] for k, x in d.items()}
    nq = d["NQ"]; o, h, l, c = (nq[k].values for k in ("open", "high", "low", "close")); n = len(nq)
    cut = ix[0] + (ix[-1] - ix[0]) * 0.6; TR = ix < cut
    for look, need, psp, rr in itertools.product((5, 10, 20), ("any", "both"), (False, True), (2.0, 3.0)):
        R = []; busy = -1
        for t in range(look, n - 1):
            if t <= busy: continue
            for side in (-1, 1):
                nq_new = (h[t] > h[t - look:t].max()) if side == -1 else (l[t] < l[t - look:t].min())
                if not nq_new: continue
                fails = []
                for s in ("ES", "YM"):
                    x = d[s]; xh, xl, xo, xc = x.high.values, x.low.values, x.open.values, x.close.values
                    f = (xh[t] <= xh[t - look:t].max()) if side == -1 else (xl[t] >= xl[t - look:t].min())
                    if psp: f = f and (np.sign(xc[t] - xo[t]) != np.sign(c[t] - o[t]))
                    fails.append(f)
                if not (any(fails) if need == "any" else all(fails)): continue
                e = o[t + 1]; sl = h[t] + 0.25 if side == -1 else l[t] - 0.25; risk = abs(e - sl)
                if risk < 2 or (sl - e) * side > 0: continue
                tp = e + side * rr * risk; px = None
                for k in range(t + 1, min(t + 200, n)):
                    if (side == -1 and h[k] >= sl) or (side == 1 and l[k] <= sl): px = sl if k == t + 1 else (max(o[k], sl) if side == -1 else min(o[k], sl)); break
                    if (side == -1 and l[k] <= tp) or (side == 1 and h[k] >= tp): px = tp; break
                if px is None: continue
                R.append((t, (side * (px - e) - COST) / risk)); busy = k; break
        if len(R) < 30: continue
        X = pd.DataFrame(R, columns=["t", "R"]); tr = TR[X.t.values]; w = X.R > 0
        rows.append(dict(tf=tf, look=look, need=need, psp=psp, rr=rr, n=len(X), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1),
                         R_tr=round(X.R[tr].mean(), 3), R_te=round(X.R[~tr].mean(), 3)))
out = pd.DataFrame(rows); out.to_csv("iter04_smt.csv", index=False); pd.set_option("display.width", 200)
print(out.sort_values("R_tr", ascending=False).head(15).to_string(index=False))
print("configs", len(out), "| PASS:", int(((out.win_tr >= 70) & (out.win_te >= 70) & (out.R_tr > 0) & (out.R_te > 0)).sum()))
