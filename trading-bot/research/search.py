"""Systematic search, pre-declared grid. Select on IS (2020–23) only, then confirm on OOS (2024–26).
Families: A time-of-day momentum/reversal · B opening-range breakout · C opening gap fade/follow."""
import pickle, itertools, numpy as np, pandas as pd
from engine import S, walk, COST_PTS, IS_END
D = pickle.load(open(S + "D.pkl", "rb"))
N = len(D.days); dates = pd.to_datetime(D.days); isd = np.asarray(dates < pd.Timestamp(IS_END))
valid_x = ~(D.roll | (D.prev_gap_days > 4))                      # cross-day comparisons allowed
pc = np.r_[np.nan, D.c[:-1, 389]]

def score(pts, mask=None):
    """pts: per-day net points (nan = no trade). Returns IS/OOS stats."""
    out = {}
    for lab, sel in (("IS", isd), ("OOS", ~isd)):
        x = pts[sel]; x = x[~np.isnan(x)]
        out[lab + "_n"] = len(x)
        out[lab + "_avg"] = x.mean() if len(x) else np.nan
        out[lab + "_sh"] = x.mean() / x.std() * np.sqrt(252) if len(x) > 20 and x.std() > 0 else np.nan
        out[lab + "_win"] = 100 * (x > 0).mean() if len(x) else np.nan
    return out

rows = []
# ---------------- A: time-of-day
for E, H, ref, mode, k in itertools.product(range(0, 390, 30), (30, 60, 120, "close"), ("open", "prevclose", "last30"), (1, -1), (0, 0.5, 1.0)):
    if ref == "open" and E == 0: continue
    if ref == "last30" and E < 30: continue
    x = E + (390 - E if H == "close" else H) - 1
    if x > 389: continue
    base = {"open": D.o[:, 0], "prevclose": pc, "last30": D.c[:, E - 31] if E >= 31 else D.o[:, 0]}[ref]
    r = D.c[:, E - 1] / base - 1 if E > 0 else D.o[:, 0] / pc - 1
    sd = pd.Series(r).rolling(20).std().shift().values
    ok = np.abs(r) > k * sd if k else np.ones(N, bool)
    if ref == "prevclose" or E == 0: ok &= valid_x
    side = np.sign(r) * mode
    pts = np.where(ok & (side != 0) & ~np.isnan(r), (D.c[:, x] - D.o[:, E]) * side - COST_PTS, np.nan)
    rows.append(dict(fam="A", rule=f"enter {9 + (30 + E) // 60:02d}:{(30 + E) % 60:02d} hold {H} ref {ref} {'mom' if mode == 1 else 'rev'} k{k}", **score(pts)))
print("A done", len(rows), flush=True)

# ---------------- B: opening-range breakout
for L, stopm, tgt, cut in itertools.product((5, 15, 30, 60), ("other", "mid"), (1.0, 2.0, "eod"), (12 * 60, 15 * 60)):
    pts = np.full(N, np.nan); nb = L // 5; last = (cut - 570) // 5
    for i in range(N):
        o5, h5, l5, c5, _ = D.bars(i, 5); hi, lo = h5[:nb].max(), l5[:nb].min()
        k = next((k for k in range(nb, last) if c5[k] > hi or c5[k] < lo), None)
        if k is None: continue
        side = 1 if c5[k] > hi else -1; e = o5[k + 1] if k + 1 < 78 else c5[k]
        sp = (lo if side == 1 else hi) if stopm == "other" else (hi + lo) / 2
        risk = (e - sp) * side
        if risk <= 0: continue
        tp = None if tgt == "eod" else e + side * tgt * risk
        px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], (k + 1) * 5, side, e, sp, tp, 384)
        pts[i] = (px - e) * side - COST_PTS
    rows.append(dict(fam="B", rule=f"ORB{L} stop {stopm} tgt {tgt} cut {cut // 60}", **score(pts)))
print("B done", flush=True)

# ---------------- C: opening gap
g = D.o[:, 0] / pc - 1
for (lo_, hi_), mode, ex in itertools.product(((0.0005, 0.002), (0.001, 0.003), (0.002, 0.005), (0.005, 0.01), (0.01, 0.05)), (-1, 1), ("fill_1x", "fill_2x", "t1100", "eod")):
    pts = np.full(N, np.nan)
    for i in np.where(valid_x & (np.abs(g) >= lo_) & (np.abs(g) < hi_))[0]:
        side = int(-np.sign(g[i]) * (1 if mode == -1 else -1)); e = D.o[i, 0]; gap = abs(D.o[i, 0] - pc[i])
        if ex.startswith("fill"):
            m = 1 if ex == "fill_1x" else 2
            if mode == -1:  # fade: target prior close
                px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], 0, side, e, e - side * m * gap, pc[i], 384)
            else:           # follow: target = gap size further, stop = prior close
                px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], 0, side, e, pc[i], e + side * m * gap, 384)
        else:
            px = D.c[i, 89] if ex == "t1100" else D.c[i, 384]
        pts[i] = (px - e) * side - COST_PTS
    rows.append(dict(fam="C", rule=f"gap {lo_*100:.2f}-{hi_*100:.2f}% {'fade' if mode == -1 else 'follow'} {ex}", **score(pts)))
print("C done", flush=True)

r = pd.DataFrame(rows); r.to_csv("search_all.csv", index=False)
sel = r[(r.IS_n >= 150) & (r.IS_sh >= 1.0)].sort_values("IS_sh", ascending=False)
print(f"\n{len(r)} rules tested; {len(sel)} pass the IS bar (n≥150, Sharpe≥1.0)")
sel = sel.assign(OOS_ok=(sel.OOS_sh > 0.5) & (sel.OOS_avg > 0))
print(f"{sel.OOS_ok.sum()} of them also hold OOS (Sharpe>0.5)\n")
pd.set_option("display.width", 220)
print(sel.round(2).head(40).to_string(index=False))
