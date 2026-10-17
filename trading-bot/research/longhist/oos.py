"""True out-of-sample (2012-01 → 2019-12, never used in any selection) on HistData NSXUSD 1-minute (Nasdaq-100 CFD, scaled to
NQ-like points: CFD price ≈ index, cost 2.25 pt kept). Candidates: Pre-Open Fade (76 % and 1:2 versions), Monday London sweep,
Williams volatility breakout. Exact rules as in the MNQ research."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from load import frame
COST0, TICK = 2.25, 0.25          # 2.25 pt at the 2020–26 average price ≈ 17,000 → cost scaled to price (≈ 0.013 %)
f = frame("NSXUSD"); f = f[f.index.notna()]; f = f[:"2019-12-31"]
mm = (f.index.hour * 60 + f.index.minute).values; O, H, L, C = (f[k].values for k in ("open", "high", "low", "close"))
sess = (f.index + pd.Timedelta(hours=6)).normalize(); grp = pd.Series(np.arange(len(f))).groupby(sess.values).agg(["first", "last"])
dates = list(grp.index)
def walk(k0, kend, side, e, sl, tp, at_open=True):
    COST = COST0 * e / 17000
    for k in range(k0, kend + 1):
        if (side == 1 and L[k] <= sl) or (side == -1 and H[k] >= sl): return side * ((sl if (k == k0 and not at_open) else (min(O[k], sl) if side == 1 else max(O[k], sl))) - e) - COST
        if (k > k0 or at_open) and ((side == 1 and H[k] >= tp + TICK) or (side == -1 and L[k] <= tp - TICK)): return side * (tp - e) - COST
    return side * (C[kend] - e) - COST
def kat(a, b, lo, hi): x = np.nonzero((mm[a:b + 1] >= lo) & (mm[a:b + 1] < hi))[0] + a; return x
rth_move = {}
for d, (a, b) in grp.iterrows():
    r = kat(a, b, 570, 960)
    if len(r) > 300: rth_move[d] = abs(C[r[-1]] / O[r[0]] - 1)
sig = pd.Series(rth_move).rolling(14).mean().shift()
def report(name, R):
    R = pd.Series(R); w = R[R > 0]; lo = R[R <= 0]
    print(f"{name}: n {len(R)} ({len(R)/8:.0f}/yr) win {100*(R>0).mean():.1f}% realised RR {w.mean()/-lo.mean():.2f} exp {R.mean():+.3f}R "
          f"t {R.mean()/R.std()*np.sqrt(len(R)):.2f} years+ {(R.groupby(R.index.year).sum()>0).sum()}/{R.index.year.nunique()}")
# ---- Pre-Open Fade
pm = {}
for d, (a, b) in grp.iterrows():
    k8, k859, k9 = kat(a, b, 480, 481), kat(a, b, 539, 540), kat(a, b, 540, 541)
    if len(k8) and len(k859) and len(k9) and d.weekday() < 5: pm[d] = (O[k8[0]], C[k859[0]], k9[0], b)
s = pd.Series({d: v[1] - v[0] for d, v in pm.items()}); ret = pd.Series({d: v[1] / v[0] - 1 for d, v in pm.items()})
z = ret / ret.rolling(20).std().shift()
for nm, zt, tpm, slm in (("Pre-Open Fade 76% version (z>2, TP .5, SL 1)", 2.0, 0.5, 1.0), ("Pre-Open Fade 1:2 (z>2.5, TP 1, SL .5)", 2.5, 1.0, 0.5)):
    R = {}
    for d in z[z.abs() > zt].index:
        o8, c859, k9, b = pm[d]; side = -int(np.sign(s[d])); size = abs(s[d]); e = O[k9]
        kend = kat(k9, b, 540, 780); kend = kend[-1] if len(kend) else k9
        R[d] = walk(k9, kend, side, e, e - side * slm * size, e + side * tpm * size) / (slm * size)
    report(nm, R)
# ---- Monday London sweep (Friday Globex H/L; London 02:00–05:00; 5m MSS 09:30–11:00; target Friday opposite side)
R = {}
for j in range(1, len(dates)):
    d, dp = dates[j], dates[j - 1]
    if d.weekday() != 0 or (d - dp).days > 4 or d not in sig.index or not np.isfinite(sig.get(d, np.nan)): continue
    a, b = grp.loc[d]; pa, pb = grp.loc[dp]; rh, rl = H[pa:pb + 1].max(), L[pa:pb + 1].min()
    lk = kat(a, b, 120, 300); rth = kat(a, b, 570, 960)
    if len(lk) < 60 or len(rth) < 300: continue
    lh, ll = H[lk].max(), L[lk].min(); ts, tb = ll < rl - TICK, lh > rh + TICK
    if ts == tb: continue
    side = 1 if ts else -1; ext = ll if side == 1 else lh; tgt = rh if side == 1 else rl; sl = ext - side * 0.05 * sig[d] * C[a]
    ke = None; bars = [rth[x:x + 5] for x in range(0, 90, 5)]
    for t in range(3, len(bars)):
        prev = np.concatenate(bars[t - 3:t]); cur = bars[t]
        if (side == 1 and C[cur[-1]] > H[prev].max()) or (side == -1 and C[cur[-1]] < L[prev].min()): ke = cur[-1] + 1; break
    if ke is None: continue
    e = O[ke]; seg = slice(lk[-1] + 1, ke)
    if (side == 1 and (H[seg].max() >= tgt or L[seg].min() <= sl)) or (side == -1 and (L[seg].min() <= tgt or H[seg].max() >= sl)): continue
    if not ((side == 1 and sl < e < tgt) or (side == -1 and tgt < e < sl)): continue
    R[d] = walk(ke, rth[-1], side, e, sl, tgt) / abs(e - sl)
report("Monday London sweep → Friday liquidity", R)
# ---- Williams volatility breakout (open ± 0.6 × prior RTH range, stop 0.5 × range, exit close) — in $ per 1 point-unit
R = {}; prev = None
for d, (a, b) in grp.iterrows():
    rth = kat(a, b, 570, 960)
    if len(rth) < 300: prev = None; continue
    if prev is not None:
        rg = prev; op = O[rth[0]]; up, dn = op + 0.6 * rg, op - 0.6 * rg; f_ = None
        for k in rth[1:-6]:
            if H[k] >= up: f_ = (k, 1, max(O[k], up)); break
            if L[k] <= dn: f_ = (k, -1, min(O[k], dn)); break
        if f_:
            k, sd, e = f_; R[d] = walk(k, rth[-6], sd, e, e - sd * 0.5 * rg, e + sd * 99 * rg, at_open=False) / (0.5 * rg)
    prev = H[rth].max() - L[rth].min()
report("Williams volatility breakout (R units, stop = 0.5 × range)", R)
