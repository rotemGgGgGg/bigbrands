"""Stage 2+3 - code every theory and test it on the SELECTION years only (2012-2018 train, 2019-2022 validation).
Years 2023-2026 are masked to zero here and are never read until stage 4 (final test of <= 20 finalists, once).
Fills: limits need 1 tick through and fill at the better of level/open; stop orders fill at the worse of level/open; close and
reclaim triggers fill at the next minute's open. Stop is checked from the fill minute (a stop already beyond the fill exits at
the fill), target from the next minute, a same-minute stop+target = stop. One trade per day per theory.
Risk unit u = max(anchor range, 0.05% of price). Costs 2.25 pt x price/17000 per round trip."""
import os, time, math, pickle
import numpy as np, pandas as pd
from multiprocessing import Pool
import grid, theories as TH
A = grid.load("NSXUSD"); O, H, L, C = A["o"], A["h"], A["l"], A["c"]; N, NB = O.shape; MM = np.arange(NB); RTH = grid.RTH
YR = A["days"].year.values; SEL = YR <= 2022; YI = np.where(SEL, YR - 2012, 0); NY = 11; TICK = 0.25
PX = O[:, RTH]; COST = 2.25 * PX / 17000
OUT = grid.SP + "mega/"


def prev(x): y = np.full(len(x), np.nan); y[1:] = x[:-1]; return y
PDH, PDL, PDC = prev(H[:, RTH:].max(1)), prev(L[:, RTH:].min(1)), prev(C[:, -1])
FHH, FHL = prev(H[:, RTH:RTH + 60].max(1)), prev(L[:, RTH:RTH + 60].min(1))
LHH, LHL = prev(H[:, NB - 60:].max(1)), prev(L[:, NB - 60:].min(1))
P2H, P2L = np.fmax(PDH, prev(PDH)), np.fmin(PDL, prev(PDL))


def anchor(ai):
    nm, k, a, b = TH.ANCHORS[ai]
    if k == "bar": return H[:, a:b + 1].max(1), L[:, a:b + 1].min(1), b + 1
    if k == "pd": return PDH, PDL, 0
    if k == "pdfh": return FHH, FHL, 0
    if k == "pdlh": return LHH, LHL, 0
    if k == "p2d": return P2H, P2L, 0
    return np.fmax(O[:, RTH], PDC), np.fmin(O[:, RTH], PDC), RTH            # gap, known at the 09:30 open


def context(sd):
    """27 masks, all known at 04:00: previous-day direction, overnight drift to the 04:00 open, previous-day range vs 20d median."""
    pdir = np.sign(PDC - prev(O[:, RTH])) * sd; ovn = np.sign(O[:, 0] - PDC) * sd
    rng = PDH - PDL; med = pd.Series(rng).rolling(20).median().shift(1).values
    F = np.zeros((N, len(TH.CONTEXT)))
    for j, (a, b, c) in enumerate(TH.CONTEXT):
        m = np.ones(N, bool)
        if a != "any": m &= (pdir > 0) if a == "with" else (pdir < 0)
        if b != "any": m &= (ovn > 0) if b == "with" else (ovn < 0)
        if c != "any": m &= (rng < med) if c == "calm" else (rng > med)
        F[:, j] = m
    return F


def first(m): return np.where(m.any(1), m.argmax(1), 9999)


def run_group(ai, x, trg, w, sd, final=False, fills=False):
    hi, lo, ta = anchor(ai); r = hi - lo; ok = np.isfinite(r) & (r > 0) & np.isfinite(PDC)
    if not final: ok &= SEL
    lvl = np.where(ok, (lo + x * r) if sd > 0 else (hi - x * r), np.nan); lv = lvl[:, None]
    end = 660 if w == 9999 else min(ta + w, NB - 2); el = (MM[None] >= ta) & (MM[None] <= end)
    rr = np.arange(N)
    if trg == "lim":
        fm = first(el & ((L <= lv - TICK) if sd > 0 else (H >= lv + TICK))); om = O[rr, np.minimum(fm, NB - 1)]
        fp = np.minimum(lvl, om) if sd > 0 else np.maximum(lvl, om)
    elif trg == "stp":
        fm = first(el & ((H >= lv) if sd > 0 else (L <= lv))); om = O[rr, np.minimum(fm, NB - 1)]
        fp = np.maximum(lvl, om) if sd > 0 else np.minimum(lvl, om)
    else:
        pc = np.c_[np.full(N, np.nan), C[:, :-1]]
        if trg == "cls": sig = (C > lv) & (pc <= lv) if sd > 0 else (C < lv) & (pc >= lv)
        else: sig = (L < lv - TICK) & (C > lv) if sd > 0 else (H > lv + TICK) & (C < lv)
        ms = first(el & sig); fm = np.where(ms < NB - 1, ms + 1, 9999); fp = O[rr, np.minimum(fm, NB - 1)]
    tr = (fm < 9999) & ok; u = np.maximum(r, 0.0005 * PX)
    aft = MM[None] >= fm[:, None]; aft2 = MM[None] > fm[:, None]
    MS, SX = [], []
    for s in TH.STOPS:
        st = fp - sd * s * u; m = first(aft & ((L <= st[:, None]) if sd > 0 else (H >= st[:, None])))
        ox = O[rr, np.minimum(m, NB - 1)]
        MS.append(m); SX.append(np.where(m > fm, np.minimum(st, ox) if sd > 0 else np.maximum(st, ox), np.minimum(st, fp) if sd > 0 else np.maximum(st, fp)))
    MT, TX = [], []
    for t in TH.TGTS:
        tg = fp + sd * t * u; MT.append(first(aft2 & ((H >= tg[:, None] + TICK) if sd > 0 else (L <= tg[:, None] - TICK)))); TX.append(tg)
    cols = []
    for hd in TH.HOLD:
        ex = np.minimum(np.where(fm < 9999, fm + hd, NB - 1), NB - 1) if hd != 9999 else np.full(N, NB - 1)
        cx = C[rr, ex]
        for i in range(len(TH.STOPS)):
            for j in range(len(TH.TGTS)):
                ms, mt = MS[i], MT[j]
                xp = np.where((ms <= ex) & (ms <= mt), SX[i], np.where(mt <= ex, TX[j], cx))
                cols.append(np.where(tr, sd * (xp - fp) - COST, 0.0))
    if fills: return np.array(cols).T, fm, fp, u
    return np.array(cols).T                       # N x 60, zero outside traded (and, unless final, selection) days


def work(g):
    """aggregates per (exit plan, context): yearly sums/counts 2012-2022; keeps full rows only for train t >= 2.5."""
    P = run_group(*g); F = context(g[4])
    Y = np.zeros((N, NY)); Y[SEL, YI[SEL]] = 1
    Z = (F[:, :, None] * Y[:, None, :]).reshape(N, -1)
    s = (P.T @ Z).reshape(60, 27, NY); n = ((P != 0).T @ Z).reshape(60, 27, NY); q = ((P * P).T @ Z).reshape(60, 27, NY)
    ntr, s_tr, q_tr = n[:, :, :7].sum(2), s[:, :, :7].sum(2), q[:, :, :7].sum(2)
    mu = s_tr / np.maximum(ntr, 1); t = np.where(ntr >= 100, mu / np.sqrt(np.maximum(q_tr / np.maximum(ntr, 1) - mu ** 2, 1e-12)) * np.sqrt(ntr), 0)
    hist = np.histogram(t[ntr >= 100], bins=np.arange(-40, 40.5, 0.5))[0]; rows = []
    for e, c in zip(*np.nonzero(t >= 2.5)):
        rows.append((g, e, c, float(t[e, c]), s[e, c].astype(np.float32), n[e, c].astype(np.float32), q[e, c, 7:].sum()))
    return rows, hist, int((ntr >= 100).sum())


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True); G = TH.groups(); t0 = time.time()
    done = {f for f in os.listdir(OUT) if f.startswith("chunk_")}
    CH = 400
    with Pool(4) as pool:
        for c0 in range(0, len(G), CH):
            fn = f"chunk_{c0 // CH:04d}.pkl"
            if fn in done: continue
            res = pool.map(work, G[c0:c0 + CH], chunksize=4)
            rows = [r for x in res for r in x[0]]; hist = sum(x[1] for x in res); nv = sum(x[2] for x in res)
            pickle.dump(dict(rows=rows, hist=hist, nvalid=nv), open(OUT + fn, "wb"), protocol=4)
            print(f"{min(c0 + CH, len(G)):,}/{len(G):,} entry rules ({min(c0 + CH, len(G)) * 27 * 60:,} variants) {time.time() - t0:.0f}s", flush=True)
    print("search done")
