"""Creative batch: event/flow ideas beyond price-pattern mining. Each idea is a precise rule, tested IS 2020–23 / OOS 2024–26,
costs 2.25 pt (1.25 + 1 pt stress). R = pts / risk where a stop exists; otherwise $ per MNQ."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S
COST, TICK = 2.25, 0.25
full = pd.read_pickle(S + "full1m.pkl"); full = full[~full.index.duplicated()]
mm = (full.index.hour * 60 + full.index.minute).values
dn = full.index.normalize()
O, H, L, C = full.open.values, full.high.values, full.low.values, full.close.values
first = pd.Series(np.arange(len(full)), index=full.index).groupby(dn).first()
bydaymin = {}
for k, (d, m) in enumerate(zip(dn, mm)):
    pass
key = pd.Series(np.arange(len(full)), index=pd.MultiIndex.from_arrays([dn, mm]))
key = key[~key.index.duplicated()]
def at(d, m):
    try: return int(key[(d, m)])
    except KeyError: return None

def walk(k, side, e, tp, sl, end_day, end_min):
    j = k
    while j < len(O):
        if dn[j] != end_day and dn[j] > end_day: return O[j]
        if dn[j] == end_day and mm[j] >= end_min: return O[j]
        if sl is not None and ((L[j] <= sl) if side == 1 else (H[j] >= sl)): return (min(O[j], sl) if side == 1 else max(O[j], sl))
        if tp is not None and ((H[j] >= tp + TICK) if side == 1 else (L[j] <= tp - TICK)): return tp
        j += 1
    return C[-1]

def report(name, rows):
    if not rows: print(name, "no trades"); return None
    x = pd.DataFrame(rows, columns=["d", "R", "usd"]).set_index("d")
    isd = x.index < pd.Timestamp("2024-01-01", tz=x.index.tz)
    def t(v): return v.mean() / v.std() * np.sqrt(len(v)) if len(v) > 2 and v.std() > 0 else 0
    out = dict(idea=name, n=len(x), per_yr=round(len(x) / 6.75, 1), win=round(100 * (x.usd > 0).mean(), 1),
               avgR=round(x.R.mean(), 3), IS_R=round(x.R[isd].mean(), 3), OOS_R=round(x.R[~isd].mean(), 3),
               t_IS=round(t(x.R[isd]), 2), t_OOS=round(t(x.R[~isd]), 2), usd=round(x.usd.mean(), 1),
               yrs=f"{int((x.usd.groupby(x.index.year).sum() > 0).sum())}/{x.index.year.nunique()}")
    print(out, flush=True); return out

days = sorted(set(dn))
wk = [d for d in days if d.weekday() < 5]

def window_fade(name, s_min, e_min, zt=2.0, a=0.5, b=1.0, end_min=None, follow=False, lookback=20):
    """Move from s_min open to (e_min−1) close; |z| vs previous `lookback` days; enter at e_min open."""
    recs = []
    for d in wk:
        k0, k1, k2 = at(d, s_min), at(d, e_min - 1), at(d, e_min)
        if None in (k0, k1, k2): continue
        recs.append((d, k2, C[k1] - O[k0], C[k1] / O[k0] - 1))
    df = pd.DataFrame(recs, columns=["d", "k", "mv", "ret"]).set_index("d")
    df["z"] = df.ret / df.ret.rolling(lookback).std().shift()
    rows = []
    for d, r in df[df.z.abs() > zt].iterrows():
        side = int(np.sign(r.mv)) * (1 if follow else -1); size = abs(r.mv); e = O[int(r.k)]
        tp = e + side * a * size if a else None; sl = e - side * b * size
        px = walk(int(r.k), side, e, tp, sl, d, end_min or min(e_min + 240, 955))
        pts = side * (px - e) - COST
        rows.append((d, pts / (b * size), 2 * pts))
    return report(name, rows)

R = []
print("== news windows (fade, 50% target / 100% stop) ==")
R.append(window_fade("pre-open 08:00-09:00 fade (reference)", 480, 540, end_min=780))
R.append(window_fade("08:30-08:45 fade", 510, 525, end_min=780))
R.append(window_fade("08:30-09:00 fade", 510, 540, end_min=780))
R.append(window_fade("08:30-08:45 follow", 510, 525, end_min=780, follow=True, a=1.0))
R.append(window_fade("09:30-09:45 open spike fade", 570, 585))
R.append(window_fade("10:00-10:15 fade (10:00 data)", 600, 615))
R.append(window_fade("10:00-10:15 follow", 600, 615, follow=True, a=1.0))
R.append(window_fade("14:00-14:30 fade (Fed)", 840, 870, end_min=955))
R.append(window_fade("14:00-14:30 follow (Fed)", 840, 870, end_min=955, follow=True, a=1.0))
R.append(window_fade("14:30-15:00 fade (presser)", 870, 900, end_min=955))
R.append(window_fade("overnight 18:00-08:00 extreme fade @08:00? (same-day window 00:00-08:00)", 0, 480, end_min=780))
R.append(window_fade("Asia 00:00-03:00 fade at 03:00", 0, 180, end_min=570))
R.append(window_fade("London 03:00-08:00 fade at 08:00", 180, 480, end_min=780))
R.append(window_fade("London 03:00-08:00 follow at 08:00", 180, 480, end_min=780, follow=True, a=1.0))
R.append(window_fade("pre-open 08:00-09:00 fade, z>1.5", 480, 540, zt=1.5, end_min=780))

print("== last half-hour momentum (Gao et al.): sign(prev close→10:00) → trade 15:30→15:59 ==")
rows = []
for d in wk:
    k10, k1530, k1559 = at(d, 599), at(d, 930), at(d, 959)
    i = days.index(d)
    if i == 0 or None in (k10, k1530, k1559): continue
    kpc = at(days[i - 1], 959)
    if kpc is None: continue
    r1 = C[k10] / C[kpc] - 1
    r_mid = C[k1530 - 1] / C[k10] - 1
    side = int(np.sign(r1))
    pts = side * (C[k1559] - O[k1530]) - COST
    rows.append((d, pts / 20, 2 * pts))
R.append(report("last 30m momentum (first-30m sign)", rows))

print("== month-end rebalancing: last trading day, 15:00→15:59 against month-to-date return ==")
dser = pd.Series(wk)
month_last = dser.groupby([dser.dt.year, dser.dt.month]).max().tolist()
month_first = dser.groupby([dser.dt.year, dser.dt.month]).min().tolist()
for thr in (0.0, 0.03):
    rows = []
    for d, d0 in zip(month_last, month_first):
        k0, k15, k1559 = at(d0, 570), at(d, 900), at(d, 959)
        if None in (k0, k15, k1559): continue
        mtd = C[k15 - 1] / O[k0] - 1
        if abs(mtd) < thr: continue
        side = -int(np.sign(mtd)); pts = side * (C[k1559] - O[k15]) - COST
        rows.append((d, pts / 20, 2 * pts))
    R.append(report(f"month-end rebalance fade |MTD|>{thr}", rows))

print("== turn of month: long last day 15:00 → 3rd day 15:59 (no stop) ==")
rows = []
for j, d in enumerate(month_last):
    if j + 1 >= len(month_first): break
    ii = days.index(month_first[j + 1])
    d3 = days[min(ii + 2, len(days) - 1)]
    k0, k1 = at(d, 900), at(d3, 959)
    if None in (k0, k1): continue
    pts = C[k1] - O[k0] - COST; rows.append((d, pts / 100, 2 * pts))
R.append(report("turn-of-month long", rows))

print("== weekend gap: Sunday 18:00 open vs Friday 16:59 close, fade from 18:05 to Monday 09:25 ==")
for zt in (1.0, 1.5):
    recs = []
    for d in days:
        if d.weekday() != 6: continue
        kf = None
        for back in (2, 3):
            f = d - pd.Timedelta(days=back)
            kf = at(f, 1019) or at(f, 1014)
            if kf: break
        ks = at(d, 1085)
        if not kf or not ks: continue
        recs.append((d, ks, O[at(d, 1080)] - C[kf] if at(d, 1080) else np.nan, C[kf]))
    df = pd.DataFrame(recs, columns=["d", "k", "gap", "ref"]).dropna().set_index("d")
    df["z"] = (df.gap / df.ref) / (df.gap / df.ref).rolling(20).std().shift()
    rows = []
    for d, r in df[df.z.abs() > zt].iterrows():
        side = -int(np.sign(r.gap)); size = abs(r.gap); k = int(r.k); e = O[k]
        px = walk(k, side, e, e + side * 1.0 * size, e - side * 1.0 * size, d + pd.Timedelta(days=1), 565)
        pts = side * (px - e) - COST; rows.append((d, pts / size, 2 * pts))
    R.append(report(f"weekend gap fill |z|>{zt}", rows))

print("== monthly opex (3rd Friday): pin — fade 09:30-11:00 move into 15:30 ==")
rows = []
for d in wk:
    if d.weekday() == 4 and 15 <= d.day <= 21:
        k0, k1, k2 = at(d, 570), at(d, 659), at(d, 660)
        k3 = at(d, 930)
        if None in (k0, k1, k2, k3): continue
        mv = C[k1] - O[k0]; side = -int(np.sign(mv)); e = O[k2]
        px = walk(k2, side, e, e + side * 0.5 * abs(mv), e - side * 1.0 * abs(mv), d, 930)
        pts = side * (px - e) - COST; rows.append((d, pts / max(abs(mv), 1), 2 * pts))
R.append(report("opex pin fade", rows))

pd.DataFrame([r for r in R if r]).to_csv("creative.csv", index=False)
