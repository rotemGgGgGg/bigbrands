"""Iter 31 — daily-bar exhaustion + intraday reversal trigger at planned 1:2 (three periods).
Setup (from the daily bars): yesterday's close is the lowest (highest) close of the last N days, or ≥ S consecutive down (up) closes,
or yesterday's range ≥ 1.8× the 14-day mean (climax). Trigger today: the first T minutes made a low (high) ≥ 0.1σ beyond the open; from minute T on, the first close back
through the 09:30 open → enter in the reversal direction at the next minute's open.
Stop: below the session extreme so far (structural, ≥ 0.1σ) or k·σ; target 2× stop; exit close. One trade a day."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
exec(open("iter26_web.py").read().split("\nres = []")[0])
res = []
for per, o, h, l, c, dow in grids():
    N = len(o); C = c[:, 389]; O = o[:, 0]; H = h.max(1); L = l.min(1)
    sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    rng14 = pd.Series(H - L).rolling(14).mean().shift().values
    dn = np.r_[False, C[1:] < C[:-1]]; up = np.r_[False, C[1:] > C[:-1]]
    def streak(b):
        s = np.zeros(N, int)
        for i in range(1, N): s[i] = s[i - 1] + 1 if b[i] else 0
        return s
    sd, su = streak(dn), streak(up)
    setups = {}
    for n in (3, 5, 10, 20):
        lo = pd.Series(C).rolling(n).min().values; hi = pd.Series(C).rolling(n).max().values
        setups[f"{n}d_extreme"] = (np.r_[0, (C == lo)[:-1]].astype(bool), np.r_[0, (C == hi)[:-1]].astype(bool))
    for s_ in (3, 4, 5):
        setups[f"{s_}_streak"] = (np.r_[0, (sd >= s_)[:-1]].astype(bool), np.r_[0, (su >= s_)[:-1]].astype(bool))
    clim = np.r_[0, ((H - L) >= 1.8 * rng14)[:-1]].astype(bool); ydir = np.r_[0, np.sign(C - O)[:-1]]
    setups["climax"] = (clim & (ydir < 0), clim & (ydir > 0))
    setups["none"] = (np.ones(N, bool), np.ones(N, bool))
    for (sn, (bull, bear)), T, stop_mode, side_mode in itertools.product(setups.items(), (15, 30, 60), ("struct", 0.25, 0.4), ("rev", "both")):
        R = []
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            sg = sig[i] * O[i]; trade = None
            for s, ok in ((1, bull[i]), (-1, bear[i])):
                if not ok and side_mode == "rev": continue
                # extreme in the first T minutes must be beyond the open; then first close back through the open
                ext = l[i, :T].min() if s == 1 else h[i, :T].max()
                if s * (O[i] - ext) < 0.1 * sg: continue
                # no look-ahead: wait until minute T is complete, then the first close back through the open
                cr = np.nonzero(s * (c[i, T - 1:300] - O[i]) > 0)[0]
                if not len(cr): continue
                m = T - 1 + cr[0] + 1
                ext = l[i, :m].min() if s == 1 else h[i, :m].max()      # extreme known at entry time
                if trade is None or m < trade[0]: trade = (m, s, ext)
            if trade is None: continue
            m, s, ext = trade; e = o[i, m]
            st = max(s * (e - ext), 0.1 * sg) if stop_mode == "struct" else stop_mode * sg
            px, _, _ = walk(o[i], h[i], l[i], c[i], m, s, e, e - s * st, e + s * 2 * st, 389)
            R.append((s * (px - e) - 2.25 * e / 17000) / st)
        R = np.array(R)
        if len(R) < 15: continue
        res.append(dict(per=per, setup=sn, T=T, stop=str(stop_mode), mode=side_mode, n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
X = pd.DataFrame(res); X.to_csv("iter31_exhaust.csv", index=False)
W = X.pivot_table(index=["setup", "T", "stop", "mode"], columns="per", values=["win", "R", "n"])
W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1); pd.set_option("display.width", 250)
print(W.sort_values("minR", ascending=False).head(20).round(3).to_string())
print("\nmax min-win:", W["minwin"].max(), "| rows minR>0:", (W["minR"] > 0).sum(), "of", len(W),
      "| 'none' baseline minR>0:", (W.xs("none", level="setup")["minR"] > 0).sum())
