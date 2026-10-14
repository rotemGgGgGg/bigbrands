"""Correlated FVG (LuxAlgo FVG logic + same-bar, same-direction gap on ES/YM) — does correlation make NQ FVG retrace trades better?
Data: Yahoo NQ=F/ES=F/YM=F 1h (2024-05 → 2026-10) and 5m (last ~70 days). Bars aligned on common timestamps.
LuxAlgo FVG (threshold 0): bull if low > high[2] and close[1] > high[2]; bear if high < low[2] and close[1] < low[2].
Trade on NQ: limit at the gap's near edge (bull: top = low[t]), stop beyond the far edge (+10 % of gap), target = rr × risk.
Cancel if a bar CLOSES through the far edge before the fill, or after `expire` bars. Same-bar touch of entry & stop = loss;
target is not counted on the fill bar (conservative). Costs 1.25 pt + 1 pt stress per round trip."""
import numpy as np, pandas as pd, sys
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
COST = 2.25
def load(tf):
    d = {s: pd.read_pickle(S + f"yf_{s}_{tf}.pkl")[["open", "high", "low", "close"]] for s in ("NQ", "ES", "YM")}
    idx = d["NQ"].index.intersection(d["ES"].index).intersection(d["YM"].index)
    return {s: x.loc[idx] for s, x in d.items()}
def fvg(x):
    h, l, c = x.high.values, x.low.values, x.close.values
    bull = np.zeros(len(x), bool); bear = np.zeros(len(x), bool)
    bull[2:] = (l[2:] > h[:-2]) & (c[1:-1] > h[:-2]); bear[2:] = (h[2:] < l[:-2]) & (c[1:-1] < l[:-2])
    return bull, bear
def run(tf, rr, expire, corr_mode):
    d = load(tf); nq = d["NQ"]; o, h, l, c = (nq[k].values for k in ("open", "high", "low", "close"))
    nb, ns = fvg(nq); eb, es_ = fvg(d["ES"]); yb, ys = fvg(d["YM"])
    hrs = nq.index.hour
    R = []; busy = -1
    for t in range(2, len(nq) - 1):
        for side, flag, other in ((1, nb[t], eb[t] | yb[t]), (-1, ns[t], es_[t] | ys[t])):
            if not flag or t <= busy: continue
            if corr_mode == "corr" and not other: continue
            if corr_mode == "not" and other: continue
            near = l[t] if side == 1 else h[t]; far = h[t - 2] if side == 1 else l[t - 2]
            gap = abs(near - far); e = near; sl = far - side * 0.1 * gap; risk = abs(e - sl)
            if risk < 2: continue
            tp = e + side * rr * risk; fill = None
            for k in range(t + 1, min(t + 1 + expire, len(nq))):
                if (side == 1 and l[k] <= e) or (side == -1 and h[k] >= e): fill = k; break
                if (side == 1 and c[k] < far) or (side == -1 and c[k] > far): break
            if fill is None: continue
            px = None
            for k in range(fill, len(nq)):
                if (side == 1 and l[k] <= sl) or (side == -1 and h[k] >= sl): px = sl if k == fill else (min(o[k], sl) if side == 1 else max(o[k], sl)); break
                if k > fill and ((side == 1 and h[k] >= tp) or (side == -1 and l[k] <= tp)): px = tp; break
                if k - fill > 200: px = c[k]; break
            if px is None: continue
            R.append((nq.index[t], (side * (px - e) - COST) / risk)); busy = k
    return pd.DataFrame(R, columns=["t", "R"]).set_index("t").R
rows = []
for tf, expire in (("1h", 24), ("5m", 36)):
    for rr in (1.0, 2.0, 3.0):
        for mode in ("all", "corr", "not"):
            x = run(tf, rr, expire, mode)
            if len(x) == 0: continue
            half = x.index < x.index[0] + (x.index[-1] - x.index[0]) / 2
            w, lo = x[x > 0], x[x <= 0]
            rows.append(dict(tf=tf, rr=rr, mode=mode, n=len(x), win=round(100 * (x > 0).mean(), 1),
                             realized_rr=round(w.mean() / -lo.mean(), 2) if len(lo) and len(w) else np.nan,
                             exp_R=round(x.mean(), 3), first_half=round(x[half].mean(), 3), second_half=round(x[~half].mean(), 3)))
print(pd.DataFrame(rows).to_string(index=False))
