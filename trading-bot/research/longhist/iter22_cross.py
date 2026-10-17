"""Iter 22 — cross-asset on 14 years of 1-minute data (HistData NSXUSD / SPXUSD / UDXUSD 2012–2025, RTH grids aligned by date).
(a) NQ/ES relative-value: NQ's 30-min return minus beta × ES's 30-min return beyond k std → trade NQ back toward ES (1:2).
(b) SMT at the day's extreme after 10:30: NQ prints a new day high (low) while ES does not → fade, stop beyond the new extreme, 2R.
(c) Dollar shock: DXY 15-min move beyond k std → trade NQ opposite to the dollar (1:2).
Three periods must each show ≥ 70 % wins at planned 1:2: 2012–19, 2020–23, 2024–25. Cost 2.25 pt scaled to price."""
import sys; sys.path.insert(0, "."); sys.path.insert(0, "..")
import numpy as np, pandas as pd, itertools
from load import frame, RTH
from engine import walk
G = {}
for p in ("NSXUSD", "SPXUSD", "UDXUSD"):
    f = frame(p); G[p] = RTH(f[f.index.notna()])
common = sorted(set(G["NSXUSD"].days) & set(G["SPXUSD"].days) & set(G["UDXUSD"].days))
ix = {p: {d: k for k, d in enumerate(G[p].days)} for p in G}
def arr(p, a): x = getattr(G[p], a); return np.array([x[ix[p][d]] for d in common])
no, nh, nl, nc = (arr("NSXUSD", a) for a in "ohlc"); so, sh, sl_, sc = (arr("SPXUSD", a) for a in "ohlc"); dc = arr("UDXUSD", "c")
N = len(common); yr = np.array([d.year for d in common]); per = np.where(yr < 2020, 0, np.where(yr < 2024, 1, 2))
mv = np.abs(nc[:, 389] / no[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
cost = lambda e: 2.25 * e / 17000
def tr(i, m, side, stop_pts, rr):
    e = no[i, m]; px, _, _ = walk(no[i], nh[i], nl[i], nc[i], m, side, e, e - side * stop_pts, e + side * rr * stop_pts, 384)
    return (side * (px - e) - cost(e)) / stop_pts
rows = []
def rec(name, R):
    R = pd.DataFrame(R, columns=["i", "R"])
    if len(R) < 60: return
    d = dict(hyp=name, n=len(R))
    for k, nm in enumerate(("12-19", "20-23", "24-25")):
        x = R.R[per[R.i] == k]; d[f"win_{nm}"] = round(100 * (x > 0).mean(), 1) if len(x) else np.nan; d[f"R_{nm}"] = round(x.mean(), 3) if len(x) else np.nan
    rows.append(d)
rn = np.log(nc); rs = np.log(sc)
for look, k, s, rr in itertools.product((15, 30, 60), (2.0, 2.5, 3.0), (0.1, 0.2), (2.0, 3.0)):
    R = []
    for i in range(20, N):
        if np.isnan(sig[i]): continue
        dn = rn[i, look:] - rn[i, :-look]; ds = rs[i, look:] - rs[i, :-look]; spread = dn - ds
        sd = np.std(spread[:max(30, 1)]) if len(spread) > 30 else np.nan
        hist = np.concatenate([rn[j, look:] - rn[j, :-look] - (rs[j, look:] - rs[j, :-look]) for j in range(i - 5, i)]); sdh = hist.std()
        hit = np.nonzero(np.abs(spread[60 - look:300 - look]) > k * sdh)[0]
        if not len(hit): continue
        m = hit[0] + 60 + 1; side = -int(np.sign(spread[hit[0] + 60 - look])); R.append((i, tr(i, m, side, s * sig[i] * no[i, 0], rr)))
    rec(f"(a) NQ−ES spread {look}m >{k}sd stop{s}σ rr{rr}", R)
for s_mode, rr in itertools.product(("extreme", "0.1σ"), (2.0, 3.0)):
    R = []
    for i in range(20, N):
        if np.isnan(sig[i]): continue
        for m in range(60, 330):
            nhi = nh[i, m] > nh[i, :m].max(); shi = sh[i, m] > sh[i, :m].max()
            nlo = nl[i, m] < nl[i, :m].min(); slo = sl_[i, m] < sl_[i, :m].min()
            if (nhi and not shi) or (nlo and not slo):
                side = -1 if nhi else 1; e = no[i, m + 1]
                stp = (nh[i, m] + 0.25 - e) if side == -1 else (e - nl[i, m] + 0.25)
                if s_mode != "extreme": stp = 0.1 * sig[i] * no[i, 0]
                if stp > 0.5: R.append((i, tr(i, m + 1, side, stp, rr)))
                break
    rec(f"(b) SMT at day extreme after 10:30 stop={s_mode} rr{rr}", R)
for look, k, s, rr in itertools.product((15, 30), (2.0, 3.0), (0.1, 0.2), (2.0, 3.0)):
    R = []
    for i in range(20, N):
        if np.isnan(sig[i]): continue
        r = np.log(dc[i, look:]) - np.log(dc[i, :-look]); hist = np.concatenate([np.log(dc[j, look:]) - np.log(dc[j, :-look]) for j in range(i - 5, i)]); sdh = hist.std()
        hit = np.nonzero(np.abs(r[:300 - look]) > k * sdh)[0]
        if not len(hit): continue
        m = hit[0] + look + 1; side = -int(np.sign(r[hit[0]])); R.append((i, tr(i, m, side, s * sig[i] * no[i, 0], rr)))
    rec(f"(c) DXY shock {look}m >{k}sd → NQ opposite stop{s}σ rr{rr}", R)
out = pd.DataFrame(rows); out.to_csv("iter22_cross.csv", index=False); pd.set_option("display.width", 220); pd.set_option("display.max_colwidth", 60)
print(out.sort_values("win_12-19", ascending=False).head(12).to_string(index=False))
ok = (out[["win_12-19", "win_20-23", "win_24-25"]].min(1) >= 70) & (out[["R_12-19", "R_20-23", "R_24-25"]].min(1) > 0)
print("configs", len(out), "PASS", int(ok.sum()))
