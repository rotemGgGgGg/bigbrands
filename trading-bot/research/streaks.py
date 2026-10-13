"""High-win-rate ideas that keep a positive edge. Pre-declared variants; IS 2020–23 / OOS 2024–26."""
import pickle, numpy as np, pandas as pd
from engine import S, walk, COST_PTS, IS_END
D = pickle.load(open(S + "D.pkl", "rb"))

def stats(name, rows):
    t = pd.DataFrame(rows, columns=["date", "pts"]); net = t.pts - COST_PTS
    y = pd.to_datetime(t.date); best = cur = 0
    for v in net:
        cur = cur + 1 if v > 0 else 0; best = max(best, cur)
    print(f"{name:34} n {len(t):4} win {100*(net>0).mean():5.1f}%  avg ${2*net.mean():+6.1f}  IS ${2*net[y<IS_END].mean():+6.1f}  OOS ${2*net[y>=IS_END].mean():+6.1f}  "
          f"yrs+ {int((net.groupby(y.dt.year).sum()>0).sum())}/7  max win streak {best}  avg win ${2*net[net>0].mean():.0f} / loss ${2*net[net<=0].mean():.0f}")

# A. Noise-Area with half taken off early at k·sigma (the rest keeps the normal exit)
def na_scale(k):
    move = np.abs(D.c / D.o[:, :1] - 1); marks = [29 + 30 * j for j in range(12)]; rows = []
    for i in range(14, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4: continue
        sig = move[i - 14:i].mean(0); o0, pc = D.o[i, 0], D.c[i - 1, 389]
        ub, lb = max(o0, pc) * (1 + sig), min(o0, pc) * (1 - sig)
        o, h, l, c = D.o[i], D.h[i], D.l[i], D.c[i]; p, ent, k0, half = 0, 0, 0, None
        def close_trade(px):
            full = (px - ent) * p
            return full if k is None else (0.5 * full + 0.5 * (half if half is not None else full))
        for k_ in marks:
            if p and k is not None and half is None:
                tgt = ent + p * k * sig[k0] * ent
                hit = next((j for j in range(k0, k_ + 1) if (h[j] >= tgt if p == 1 else l[j] <= tgt)), None)
                if hit is not None: half = (tgt - ent) * p
            want = p; cc = c[k_]
            if p == 1 and cc < lb[k_]: want = 0
            if p == -1 and cc > ub[k_]: want = 0
            if cc > ub[k_]: want = 1
            elif cc < lb[k_]: want = -1
            if want != p:
                if p: rows.append((D.days[i], close_trade(o[k_ + 1])))
                p, ent, k0, half = want, o[k_ + 1], k_ + 1, None
        if p:
            if k is not None and half is None:
                tgt = ent + p * k * sig[k0] * ent
                if any((h[j] >= tgt if p == 1 else l[j] <= tgt) for j in range(k0, 390)): half = (tgt - ent) * p
            rows.append((D.days[i], close_trade(c[389])))
    return rows

# B. Opening-gap fill: fade a small gap at 09:30, target = prior close, stop = m × gap beyond the open
def gap(lo=0.001, hi=0.005, m=1.0):
    rows = []
    for i in range(1, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4: continue
        pc, o0 = D.c[i - 1, 389], D.o[i, 0]; g = o0 - pc
        if not (lo * pc <= abs(g) <= hi * pc): continue
        side = -1 if g > 0 else 1
        px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], 0, side, o0, o0 - side * m * abs(g), pc, 384)
        rows.append((D.days[i], (px - o0) * side))
    return rows

stats("Noise-Area base", na_scale(None))
for k in (0.5, 1.0):
    stats(f"Noise-Area, half off at {k}σ", na_scale(k))
for lo, hi in ((0.001, 0.005), (0.001, 0.003), (0.003, 0.008)):
    for m in (1.0, 2.0):
        stats(f"Gap fill {lo*100:.1f}–{hi*100:.1f}% stop {m}×gap", gap(lo, hi, m))
