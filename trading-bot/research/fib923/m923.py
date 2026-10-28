"""User model: pre-market candle Fib ladder (2 contracts per side).
Anchor candle (default 09:23) high H / low L, r = H - L. TradingView fib: drawn high->low puts 0 at the low, so long levels are
L + x*r (x<0 below the low); drawn low->high puts 0 at the high, short levels H - x*r (above the high).
Per side: contract 1 limit at level E1, contract 2 limit at level E2 (deeper). Orders live from the minute after the anchor
candle until LIVE (leg-1 only; leg 2 stays live while leg 1 is open). Before leg 2 fills: exit leg 1 at target T or at the stop.
After leg 2 fills: both exit at T2 = same target / average-price break-even / the E1 level, or at the stop S.
Time exit at EXIT. Long and short sides are independent (both can trade the same day).
Strict fills: limits/targets need 1 tick through, a stop+target tie = stop, a leg-2 fill and target in the same minute = leg 2
first then the target is only checked from the next minute; costs 2.25 pt x price/17000 per contract round trip.
Grid ~650k variants. Selection 2012-2019 only, validation 2020-2023, holdout 2024-2026-10 once."""
import sys, os, time, itertools, pickle, math
import numpy as np, pandas as pd
from multiprocessing import Pool
import data9
A = data9.load(); O, H, L, C = A["o"], A["h"], A["l"], A["c"]; N = len(A["days"]); MM = np.arange(420)
YR = A["days"].year.values; YI = YR - 2012; NY = YI.max() + 1; TICK = 0.25; COST = 2.25 * O[:, 30] / 17000
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/fib923/"
ANCH = (15, 20, 23, 25, 28)                       # 09:15 09:20 09:23 09:25 09:28 candles
E1S = (-1.0, -1.5, -2.0, -2.5, -3.0); E2S = (-3.0, -3.5, -4.0, -5.0, -6.0, None)
TGS = (-1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0)       # 3.0 = the opposite side's -2 level
STS = (-4.5, -5.0, -6.0, -7.0, -8.0, -10.0, -14.0, None)
T2S = ("same", "be", "e1"); LIVES = (45, 60, 90, 120, 180); EXITS = (60, 120, 180, 419)   # minute indexes from 09:00


def first(mask): return np.where(mask.any(1), mask.argmax(1), 9999)


def side_group(an, sd, e1, live):
    """all (e2, target, stop, t2, exit) combos for one side; returns P (N x combos) net pts and keys."""
    h, l = H[:, an], L[:, an]; r = h - l; ok = (r > 0) & A["real923"] if an == 23 else (r > 0)
    lv = (lambda x: l + x * r) if sd > 0 else (lambda x: h - x * r)
    r_ = np.arange(N); start = an + 1
    p1 = lv(e1); el = (MM[None] >= start) & (MM[None] <= live)
    f1 = first(el & ((L <= p1[:, None] - TICK) if sd > 0 else (H >= p1[:, None] + TICK))); f1 = np.where(ok, f1, 9999)
    o1 = O[r_, np.minimum(f1, 419)]; fp1 = np.minimum(p1, o1) if sd > 0 else np.maximum(p1, o1)
    aft1 = MM[None] > f1[:, None]
    def hit_up(px, aft): return first(aft & (H >= px[:, None] + TICK))
    def hit_dn(px, aft): return first(aft & (L <= px[:, None] - TICK))
    tgt_hit = (lambda px, aft: hit_up(px, aft)) if sd > 0 else (lambda px, aft: hit_dn(px, aft))
    MT1 = {tg: tgt_hit(lv(tg), aft1) for tg in TGS if tg > e1}
    cols, keys = [], []
    for e2 in E2S:
        if e2 is not None and e2 >= e1: continue
        if e2 is not None:
            p2 = lv(e2); af = MM[None] >= f1[:, None]
            f2 = first(af & ((L <= p2[:, None] - TICK) if sd > 0 else (H >= p2[:, None] + TICK)))
            o2 = O[r_, np.minimum(f2, 419)]; fp2 = np.minimum(p2, o2) if sd > 0 else np.maximum(p2, o2)
        else: f2 = np.full(N, 9999); fp2 = np.full(N, np.nan)
        aft2 = MM[None] > f2[:, None]; af2i = MM[None] >= f2[:, None]
        avg = (fp1 + fp2) / 2
        T2P = {"be": tgt_hit(avg, aft2), "e1": tgt_hit(p1, aft2)}
        MT2 = {tg: tgt_hit(lv(tg), aft2) for tg in MT1}
        deep = e2 if e2 is not None else e1
        for st in STS:
            if st is not None and st >= deep: continue
            if st is not None:
                sp = lv(st); a_ = af2i if e2 is not None else (MM[None] >= f1[:, None])
                ms = first(a_ & ((L <= sp[:, None]) if sd > 0 else (H >= sp[:, None])))
                so = O[r_, np.minimum(ms, 419)]; spx = np.minimum(sp, so) if sd > 0 else np.maximum(sp, so)
            else: ms = np.full(N, 9999); spx = np.zeros(N)
            for tg, mt1 in MT1.items():
                for t2 in (T2S if e2 is not None else ("same",)):
                    mt2 = MT2[tg] if t2 == "same" else T2P[t2]
                    t2px = lv(tg) if t2 == "same" else (avg if t2 == "be" else p1)
                    for ex in EXITS:
                        live1 = (f1 <= ex) & (f1 < 9999); cx = C[:, ex]
                        two = live1 & (f2 <= ex) & (f2 <= mt1)                        # leg 2 filled before leg-1 target
                        if e2 is None:   # single contract: stop from leg-1 fill
                            xs = (ms <= ex) & (ms <= mt1); x1 = np.where(xs, spx, np.where(mt1 <= ex, lv(tg), cx))
                            pnl = np.where(live1, sd * (x1 - fp1) - COST, 0.0)
                        else:
                            # one contract only: target or time (stop lies beyond leg 2, so leg 2 fills first)
                            x1 = np.where(mt1 <= ex, lv(tg), cx); one = sd * (x1 - fp1) - COST
                            xs = (ms <= ex) & (ms <= mt2); xp = np.where(xs, spx, np.where(mt2 <= ex, t2px, cx))
                            both = sd * (xp - fp1) + sd * (xp - fp2) - 2 * COST
                            pnl = np.where(two, both, np.where(live1, one, 0.0))
                        cols.append(pnl); keys.append((e2, st, tg, t2, ex))
    return np.array(cols).T, keys


def work(arg):
    an, e1, live = arg; out = {}
    for sd in (1, -1): out[sd] = side_group(an, sd, e1, live)
    keys = out[1][1]; assert keys == out[-1][1]
    Y = np.eye(NY)[YI]; rows = []
    S3 = np.stack([YR <= 2019, (YR >= 2020) & (YR <= 2023), YR >= 2024], 1).astype(float)
    for side, P in (("long", out[1][0]), ("short", out[-1][0]), ("both", out[1][0] + out[-1][0])):
        sy = P.T @ Y; ny = (P != 0).astype(float).T @ Y; sq = (P * P).T @ S3; wn = (P > 0).astype(float).T @ S3
        for k, key in enumerate(keys):
            n_tr = ny[k, :8].sum(); s_tr = sy[k, :8].sum(); mu = s_tr / max(n_tr, 1); v = sq[k, 0] / max(n_tr, 1) - mu * mu
            t = mu / math.sqrt(max(v, 1e-12)) * math.sqrt(n_tr) if n_tr >= 150 else 0.0
            rows.append((an, e1, live, side) + key + (t,) + tuple(sy[k]) + tuple(ny[k]) + tuple(sq[k]) + tuple(wn[k]))
    return rows


if __name__ == "__main__":
    os.makedirs(SP, exist_ok=True); jobs = list(itertools.product(ANCH, E1S, LIVES)); t0 = time.time(); rows = []
    with Pool(4) as p:
        for i, r in enumerate(p.imap_unordered(work, jobs)):
            rows += r
            if i % 10 == 0: print(f"{i}/{len(jobs)} groups, {len(rows):,} variants, {time.time() - t0:.0f}s", flush=True)
    cols = ["anchor", "e1", "live", "side", "e2", "stop", "tgt", "t2", "exit", "t_tr"] + [f"y{2012 + k}" for k in range(NY)] + \
           [f"n{2012 + k}" for k in range(NY)] + ["sq_tr", "sq_va", "sq_ho", "w_tr", "w_va", "w_ho"]
    R = pd.DataFrame(rows, columns=cols); R.to_pickle(SP + "grid.pkl"); print(f"done {len(R):,} variants {time.time() - t0:.0f}s")
