"""Stage 3 — entries & exits on Noise-Area momentum days (the one edge that survives out-of-sample).
Direction = first half-hour close outside the noise band (10:00 … 15:30). Then up to K pullback entries
(limit orders, filled only if price trades through by 1 tick), each with target a·σ and a stop,
stop trading for the day after a loss. σ = 14-day mean |close/open−1| × price."""
import sys; sys.path.insert(0, "../winrate"); sys.path.insert(0, "..")
import numpy as np, pandas as pd
from signals import D, sig_na_first, day_sig, IS_END
COST, TICK, LAST = 1.25, 0.25, 384
o, h, l, c, v = D.o, D.h, D.l, D.c, D.v
yr = np.array([d.year for d in D.days])
BREAKS = sig_na_first()                  # (i, k0 = minute after the mark, side, None)
move = np.abs(D.c / D.o[:, :1] - 1)
pcl = np.r_[np.nan, D.c[:-1, 389]]

def band(i):
    sig = move[i - 14:i].mean(0); o0 = o[i, 0]
    return max(o0, pcl[i]) * (1 + sig), min(o0, pcl[i]) * (1 - sig)

def ema(x, n):
    a = 2 / (n + 1); out = np.empty_like(x); out[0] = x[0]
    for t in range(1, len(x)): out[t] = a * x[t] + (1 - a) * out[t - 1]
    return out

def levels_for(i, k0, s, kind, p):
    """Return array lv[t] = limit price that is live at minute t (nan = none). Computed from bars < t only."""
    hh, ll, cc = h[i], l[i], c[i]
    lv = np.full(390, np.nan)
    if kind == "fvg":                        # most recent un-traded FVG edge in direction (formed after k0)
        cur = np.nan
        for t in range(k0 + 2, 390):
            j = t - 1                            # bar j just closed: FVG between j-2 and j
            if j - 2 >= k0 and ((s == 1 and hh[j - 2] < ll[j]) or (s == -1 and ll[j - 2] > hh[j])):
                cur = ll[j] if s == 1 else hh[j]
            lv[t] = cur
    elif kind == "vwap":
        tp = (hh + ll + cc) / 3; cv = np.cumsum(v[i]); vw = np.cumsum(tp * v[i]) / np.maximum(cv, 1)
        lv[k0 + 1:] = vw[k0:389] + s * p * day_sig[i] * o[i, 0]      # vwap offset p·σ toward the trend
    elif kind == "ema":
        e = ema(cc, int(p)); lv[k0 + 1:] = e[k0:389]
    elif kind == "retr":                     # retrace p of the move from the open to the running extreme
        o0 = o[i, 0]
        ext = np.maximum.accumulate(hh) if s == 1 else np.minimum.accumulate(ll)
        lv[k0 + 1:] = (ext[k0:389] - s * p * np.abs(ext[k0:389] - o0))
    elif kind == "band":                     # retest of the band edge that was broken
        ub, lb = band(i); m = (k0 // 30) - 1
        lv[k0:] = ub[m] if s == 1 else lb[m]
    return lv

def run_day(i, k0, s, kind, p, a, b, K, win_mins, stop_kind):
    sc = day_sig[i] * o[i, 0]
    lv = levels_for(i, k0, s, kind, p)
    hh, ll, oo = h[i], l[i], o[i]
    out = []; t = k0; end_entry = min(k0 + win_mins, LAST)
    ub, lb = band(i)
    while len(out) < K and t < end_entry:
        # find fill: price trades through the live level
        f = None
        for x in range(t, end_entry):
            L_ = lv[x]
            if np.isnan(L_): continue
            if (s == 1 and ll[x] <= L_ - TICK and oo[x] > L_) or (s == -1 and hh[x] >= L_ + TICK and oo[x] < L_):
                f = x; break
        if f is None: break
        e = lv[f]; tp = e + s * a * sc
        sl = e - s * b * sc
        px = None
        for x in range(f, LAST + 1):
            if (ll[x] <= sl) if s == 1 else (hh[x] >= sl):
                px = sl if x == f else (min(oo[x], sl) if s == 1 else max(oo[x], sl)); break
            if x > f and ((hh[x] >= tp + TICK) if s == 1 else (ll[x] <= tp - TICK)):
                px = tp; break
            if stop_kind == "na" and x > f and (x + 1) % 30 == 0 and 0 <= (x + 1) // 30 - 1 <= 11:
                m = (x + 1) // 30 - 1                   # half-hour close back through the opposite band → exit
                if (s == 1 and c[i, x] < lb[m]) or (s == -1 and c[i, x] > ub[m]):
                    px = c[i, x]; break
        if px is None: px = c[i, LAST]; x = LAST
        pts = s * (px - e) - COST
        out.append(pts)
        if pts <= 0: break
        t = x + 1
    return out

def evaluate(kind, p, a, b, K=1, win_mins=60, stop_kind="fixed"):
    rows = []
    for i, k0, s, _ in BREAKS:
        if np.isnan(day_sig[i]) or k0 >= LAST: continue
        for pts in run_day(i, k0, s, kind, p, a, b, K, win_mins, stop_kind):
            rows.append((i, pts))
    if not rows: return None
    r = pd.DataFrame(rows, columns=["i", "pts"]); r["y"] = yr[r.i]
    p_ = r.pts.values; isd = r.y.values < 2024
    day = r.groupby("i").pts.sum()
    w, lo = p_[p_ > 0], p_[p_ <= 0]
    cs = np.cumsum(day.values * 2)
    return dict(kind=kind, p=p, a=a, b=b, K=K, win=win_mins, stop=stop_kind, n=len(r), days=len(day),
                winr=round(100 * (p_ > 0).mean(), 1), avg=round(2 * p_.mean(), 1), avg_w=round(2 * w.mean(), 0) if len(w) else 0,
                avg_l=round(2 * lo.mean(), 0) if len(lo) else 0, IS=round(2 * p_[isd].mean(), 1), OOS=round(2 * p_[~isd].mean(), 1),
                tot=round(2 * p_.sum()), maxdd=round((cs - np.maximum.accumulate(cs)).min()),
                yrs=int((r.groupby("y").pts.sum() > 0).sum()), pf=round(w.sum() / -lo.sum(), 2) if len(lo) else 99)

if __name__ == "__main__":
    import itertools, sys
    grid = []
    for kind, ps in (("fvg", [0]), ("vwap", [0.0, 0.1, 0.25]), ("ema", [9, 20, 50]), ("retr", [0.2, 0.33, 0.5]), ("band", [0])):
        for p, a, b, K, wm, sk in itertools.product(ps, (0.1, 0.15, 0.25), (1.0, 2.0), (1, 3), (60, 180), ("fixed", "na")):
            res = evaluate(kind, p, a, b, K, wm, sk)
            if res: grid.append(res); print(res, file=sys.stderr, flush=True)
    G = pd.DataFrame(grid); G.to_csv("momo_grid.csv", index=False)
    pd.set_option("display.width", 250)
    print(G.sort_values("IS", ascending=False).head(40).to_string())
