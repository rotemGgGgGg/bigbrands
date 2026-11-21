"""AVP zones, honest optimisation. Same zones as avp.py (LVN of a 5-session time-at-price profile, built before the day).
Grid (540): stop = wick+buffer | zone far edge; max risk 0.15% / 0.3% / none; target 1/2/3/5/12 R (flat 15:55 otherwise);
window = London 03:00-09:30 | NY 09:35-15:30 | both; trend = none | 50-day | day (price vs 00:00 open); max 1 or 3 trades a day;
one signal per zone per side per day. Gates: choose on 2012-19 (t >= 2.5, >= 5/8 positive years) -> 2020-26 (same sign,
t >= 1.5) -> shifted-zone random baseline (100 runs, p <= 5%) on the 2020-26 result. Cost 1.3 bp. NQ (HistData) 00:00-16:00."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "../multi"))
import avp, mdata
G, DL, BP, TICK = avp.G, avp.DL, avp.BP, avp.TICK
dcs = mdata.load("NSXUSD"); dc = pd.Series(dcs["dc"], index=dcs["days"]); UP = (dc > dc.rolling(50).mean()).shift(1)
for j in range(6, len(DL)):
    if j not in avp.ZCACHE: avp.ZCACHE[j] = avp.zones_for(j)
WIN = {"London": (180, 570), "NY": (575, 930), "both": (180, 930)}


def run(stop, risk, tgt, win, trend, maxn, shift_rng=None):
    out = {}; a0, a1 = WIN[win]
    for j in range(6, len(DL)):
        d = DL[j]; Z = avp.ZCACHE[j]
        if not Z: continue
        if shift_rng is not None:
            Z = [(lo + s * (hi - lo), hi + s * (hi - lo)) for (lo, hi), s in zip(Z, shift_rng.choice([-1, 1], len(Z)) * shift_rng.uniform(1.0, 3.0, len(Z)))]
        up = UP.get(d); o, h, l, c = G[d]; usedL = set(); usedS = set(); n = 0
        for i in range(a0 + 4, a1, 5):
            bh, bl, bc, pc = h[i - 4:i + 1].max(), l[i - 4:i + 1].min(), c[i], c[i - 5]
            sig = None
            for zi, (lo, hi) in enumerate(Z):
                if zi not in usedL and pc > hi and bl <= hi and bc > hi:
                    sig = (1, (bl if stop == "wick" else min(lo, bl)) - 2 * TICK - 2 * TICK, zi); break
                if zi not in usedS and pc < lo and bh >= lo and bc < lo:
                    sig = (-1, (bh if stop == "wick" else max(hi, bh)) + 2 * TICK + 2 * TICK, zi); break
            if sig is None: continue
            s, sl, zi = sig; (usedL if s == 1 else usedS).add(zi)
            if trend == "50d" and (pd.isna(up) or (s == 1) != bool(up)): continue
            if trend == "day" and (s == 1) != (c[i] > o[0]): continue
            e0 = i + 1; ent = o[e0]; rk = s * (ent - sl)
            if rk <= ent * 0.0002 or (risk is not None and rk > ent * risk): continue
            tg = ent + s * tgt * rk; hh, ll = h[e0:955], l[e0:955]
            hs = np.nonzero(ll <= sl)[0] if s == 1 else np.nonzero(hh >= sl)[0]; ht = np.nonzero(hh >= tg)[0] if s == 1 else np.nonzero(ll <= tg)[0]
            ts, tt = (hs[0] if len(hs) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
            px = sl if ts <= tt and ts < 10 ** 9 else (tg if tt < 10 ** 9 else c[954])
            out[(d, i)] = (s * (px - ent) - ent * BP / 1e4) / rk; n += 1
            if n >= maxn: break
    s = pd.Series(out, dtype=float)
    if len(s): s.index = pd.DatetimeIndex([k[0] for k in s.index])
    return s


def tst(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0


if __name__ == "__main__":
    rows = []; SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
    grid = list(itertools.product(("wick", "zone"), (0.0015, 0.003, None), (1, 2, 3, 5, 12), WIN, ("none", "50d", "day"), (1, 3)))
    for k, (stp, rk, tg, w, tr, mx) in enumerate(grid):
        s = run(stp, rk, tg, w, tr, mx)
        if len(s) < 100: continue
        Y = s.index.year; I, O = s[Y <= 2019], s[Y >= 2020]; yy = I.groupby(I.index.year).sum()
        rows.append(dict(stop=stp, maxrisk=rk, tgtR=tg, window=w, trend=tr, maxn=mx, n_yr=len(s) / 14.8, win=100 * (s > 0).mean(),
                         IS_R=I.mean(), IS_t=tst(I), IS_pos=int((yy > 0).sum()), OOS_R=O.mean(), OOS_t=tst(O), last2y=s[s.index >= "2024-10-24"].mean()))
        if k % 60 == 0: print(k, "/", len(grid), flush=True)
    T = pd.DataFrame(rows); T.to_csv(SP + "avp2_grid.csv", index=False); pd.set_option("display.width", 240)
    el = T[(T.IS_t >= 2.5) & (T.IS_pos >= 5)]
    print(f"\n{len(T)} variants | IS-eligible {len(el)} | of them OOS same sign t>=1.5: {((el.OOS_R > 0) & (el.OOS_t >= 1.5)).sum()}")
    print("family means (OOS R):", {c: T.groupby(c).OOS_R.mean().round(3).to_dict() for c in ("window", "trend", "stop", "tgtR")})
    print("\nTOP 15 by 2012-19 t:\n", T.sort_values("IS_t", ascending=False).head(15).round(3).to_string(index=False))
    fin = el[(el.OOS_R > 0) & (el.OOS_t >= 1.5)].sort_values("IS_t", ascending=False).head(3)
    for _, r in fin.iterrows():
        args = (r.stop, None if pd.isna(r.maxrisk) else r.maxrisk, int(r.tgtR), r.window, r.trend, int(r.maxn)); rng = np.random.default_rng(9)
        nul = [run(*args, shift_rng=rng) for _ in range(100)]; nul = [x[x.index.year >= 2020].mean() for x in nul]
        print(f"FINALIST {args}: OOS {r.OOS_R:+.3f}R vs shifted zones median {np.median(nul):+.3f} -> p={np.mean(np.array(nul) >= r.OOS_R):.2f}")
    if not len(fin): print("no finalist passed the 2012-19 -> 2020-26 gates")
