"""Causal (live-executable) No-Wick engine. The research simulator nowick.sim processes signals one at a time and, when a
signal's limit never fills within `expiry` bars, goes BACK and takes the next signal's earlier touch — a decision a live bot
cannot make (it would need to know the first limit never fills). Here, bar by bar, exactly as a bot would run:
  - while flat, every qualifying signal bar adds a resting buy limit at its open (valid `expiry` bars, same session);
  - on each bar, if any resting limit is traded through (low ≤ level − thru) the highest such level fills
    (price falls into it first) at min(open, level), all other resting limits are cancelled;
  - stop = level − k×ATR(signal bar), target = entry + rr × risk; stop checked from the fill bar, target from the next bar;
    flat at the session close; while in a trade no new limits are placed.
Compares the result with the original simulator for the final No-Wick configuration."""
import os, sys
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("STRESS", "1")
import components as K
import nowick as N
from proof import NW_ID


@njit(cache=True)
def causal(o, h, l, c, atr, sess, last, sig, k, rr, expiry, thru, cf, cmin):
    n = len(o); outi = np.empty(n, np.int64); outr = np.empty(n); nt = 0
    pl = np.empty(n); ps = np.empty(n); pe = np.empty(n, np.int64); pss = np.empty(n, np.int64); np_ = 0
    b = 0
    while b < n:
        # 1) fill check on bar b against limits placed on earlier bars
        best = -1; bl = -1e18
        for q in range(np_):
            if pe[q] >= b and pss[q] == sess[b] and l[b] <= pl[q] - thru and pl[q] > bl:
                best = q; bl = pl[q]
        if best >= 0:
            L = pl[best]; S = L - ps[best]; e = min(o[b], L); risk = e - S; np_ = 0
            if risk > 0:
                T = e + rr * risk; m = b; px = np.nan
                while True:
                    if l[m] <= S:
                        px = S if m == b else min(o[m], S); break
                    if m > b and h[m] >= T + thru:
                        px = max(o[m], T); break
                    if last[m] or m == n - 1:
                        px = c[m]; break
                    m += 1
                outi[nt] = b; outr[nt] = (px - e - max(cf * e, cmin)) / risk; nt += 1
                b = m + 1; continue
        # 2) drop expired / other-session limits, add this bar's signal (known at its close)
        w = 0
        for q in range(np_):
            if pe[q] > b and pss[q] == sess[b]:
                pl[w] = pl[q]; ps[w] = ps[q]; pe[w] = pe[q]; pss[w] = pss[q]; w += 1
        np_ = w
        if sig[b] and atr[b] > 0:
            pl[np_] = o[b]; ps[np_] = k * atr[b]; pe[np_] = b + expiry; pss[np_] = sess[b]; np_ += 1
        b += 1
    return outi[:nt], outr[:nt]


if __name__ == "__main__":
    cfg = K.NW_CFGS[NW_ID]; A = K.nw_arrays(cfg["tf"]); w0, w1 = cfg["win"]; wm = (A["mins"] >= w0) & (A["mins"] < w1)
    sl = A["bull"] & (A["lw"] <= cfg["tol"] * A["rng"] + A["eps"]) & A["up"][cfg["filt"]] & wm
    cf, cmin = N.COST["NQ"]; yr = A["yr"]
    for cx, thru in ((1.0, 0.0), (2.0, 0.25)):
        ti, R = N.sim(A["o"], A["h"], A["l"], A["c"], A["atr"], A["sess"], A["last"], sl, np.zeros(len(sl), bool), 0.0, 0,
                      cfg["expiry"], cfg["stopk"], cfg["rr"], 0, cf * cx, cmin * cx, thru, 1)
        tc, Rc = causal(A["o"], A["h"], A["l"], A["c"], A["atr"], A["sess"], A["last"], sl, cfg["stopk"], cfg["rr"], cfg["expiry"], thru, cf * cx, cmin * cx)
        for nm, t, r in (("original", ti, R), ("CAUSAL", tc, Rc)):
            y = yr[t]; g = pd.Series(r).groupby(y).sum()
            print(f"cost x{cx:.0f} {nm:8s}: n={len(r)} R/trade {r.mean():+.3f} win {100 * (r > 0).mean():.1f}% | "
                  f"tr {r[y <= 2019].mean():+.3f} va {r[(y >= 2020) & (y <= 2023)].mean():+.3f} te {r[y >= 2024].mean():+.3f} | yrs+ {(g > 0).sum()}/{len(g)}")
        for exp in (1, 5, 20, 50):
            tc, Rc = causal(A["o"], A["h"], A["l"], A["c"], A["atr"], A["sess"], A["last"], sl, cfg["stopk"], cfg["rr"], exp, thru, cf * cx, cmin * cx)
            y = yr[tc]; print(f"   causal expiry {exp:3d}: n={len(Rc)} R {Rc.mean():+.3f} te {Rc[y >= 2024].mean():+.3f} yrs+ {(pd.Series(Rc).groupby(y).sum() > 0).sum()}")
