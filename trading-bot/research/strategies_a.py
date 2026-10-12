"""Group A: the simply-specified strategies (ranks 1–6, 11, 12, 15, 17–20). Rules from top_20_strategies.md;
every interpretation of an UNSPECIFIED rule is marked "interp:". Each function returns a trade DataFrame:
date, side, pts (gross points, 1 contract), risk (points or NaN)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import walk

NAN = float("nan")


def _df(rows):
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])


# ---------------------------------------------------------------- 1. Noise-Area intraday momentum
def noise_area(D, vwap_entry=True, vwap_trail=True):
    move = np.abs(D.c / D.o[:, :1] - 1)                       # (ndays, 390)
    rows = []
    marks = [k for k in range(390) if (k + 1) % 30 == 0 and k < 389]   # bars closing 10:00 … 15:30
    for i in range(14, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4:
            continue
        sig = move[i - 14:i].mean(0)
        o0, pc = D.o[i, 0], D.c[i - 1, 389]
        ub, lb = max(o0, pc) * (1 + sig), min(o0, pc) * (1 - sig)
        vw = D.vwap(i)
        c, o = D.c[i], D.o[i]
        pos, ent = 0, 0.0
        for k in marks:
            want = pos
            if pos == 1:
                stop = max(ub[k], vw[k]) if vwap_trail else lb[k]
                if c[k] < stop:
                    want = 0
            elif pos == -1:
                stop = min(lb[k], vw[k]) if vwap_trail else ub[k]
                if c[k] > stop:
                    want = 0
            if c[k] > ub[k] and (not vwap_entry or c[k] > vw[k]):
                want = 1
            elif c[k] < lb[k] and (not vwap_entry or c[k] < vw[k]):
                want = -1
            if want != pos:
                px = o[k + 1]
                if pos:
                    rows.append((D.days[i], pos, (px - ent) * pos, NAN))
                pos, ent = want, px
        if pos:
            rows.append((D.days[i], pos, (c[389] - ent) * pos, NAN))
    return _df(rows)


# ---------------------------------------------------------------- 2. 5-minute ORB, first-candle direction
def orb5_first_candle(D, target_r=10.0, doji=0.1):
    rows = []
    for i in range(len(D.days)):
        o5, h5, l5, c5, _ = D.bars(i, 5)
        rng = h5[0] - l5[0]
        if rng <= 0 or abs(c5[0] - o5[0]) <= doji * rng:      # interp: doji = body ≤ 10 % of range
            continue
        side = 1 if c5[0] > o5[0] else -1
        e = D.o[i, 5]
        stop = l5[0] if side == 1 else h5[0]
        risk = (e - stop) * side
        if risk <= 0:
            continue
        px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], 5, side, e, stop, e + side * target_r * risk, 389)
        rows.append((D.days[i], side, (px - e) * side, risk))
    return _df(rows)


# ---------------------------------------------------------------- 3. Last-30-minute momentum
def last30(D, variant="rROD"):
    rows = []
    for i in range(1, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4:
            continue
        pc = D.c[i - 1, 389]
        r_ond = D.c[i, 29] / pc - 1                            # 10:00 vs prior close
        r_rod = D.c[i, 359] / pc - 1                           # 15:30 vs prior close
        if variant == "rROD":
            side = 1 if r_rod > 0 else -1
        elif variant == "rONFH":
            side = 1 if r_ond > 0 else -1
        else:
            if r_ond > 0 and r_rod > 0:
                side = 1
            elif r_ond < 0 and r_rod < 0:
                side = -1
            else:
                continue
        e = D.o[i, 360]
        rows.append((D.days[i], side, (D.c[i, 389] - e) * side, NAN))
    return _df(rows)


# ---------------------------------------------------------------- 4. Session VWAP trend (always in)
def vwap_trend(D):
    rows = []
    for i in range(len(D.days)):
        vw, c, o = D.vwap(i), D.c[i], D.o[i]
        pos, ent = 0, 0.0
        for k in range(1, 388):
            want = 1 if c[k] > vw[k] else -1 if c[k] < vw[k] else pos
            if want != pos:
                px = o[k + 1]
                if pos:
                    rows.append((D.days[i], pos, (px - ent) * pos, NAN))
                pos, ent = want, px
        if pos:
            rows.append((D.days[i], pos, (o[389] - ent) * pos, NAN))
    return _df(rows)


# ---------------------------------------------------------------- 5. 30-minute ORB, fixed-bar time exit
def orb30_time(D, hold_bars=15):
    rows = []
    for i in range(len(D.days)):
        o5, h5, l5, c5, _ = D.bars(i, 5)
        hi, lo = h5[:6].max(), l5[:6].min()
        done = {1: False, -1: False}
        k = 6
        while k < 77:
            side = 1 if c5[k] > hi and not done[1] else -1 if c5[k] < lo and not done[-1] else 0
            if side:
                done[side] = True
                ex = min(k + 1 + hold_bars, 78) - 1
                e = o5[k + 1]
                rows.append((D.days[i], side, (c5[ex] - e) * side, NAN))
                k = ex + 1
                continue
            k += 1
    return _df(rows)


# ---------------------------------------------------------------- 6. Zone-filtered opening gap fill
def gap_fill(D, es_ref=3000.0):
    """ES-point parameters rescaled by price: interp: 1 ES point = price/es_ref of NQ."""
    rows = []
    O, H, L, C = D.o[:, 0], D.h.max(1), D.l.min(1), D.c[:, 389]
    for i in range(5, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4 or any(D.roll[i - 4:i]):
            continue
        wd = pd.Timestamp(D.days[i]).weekday()
        if wd in (0, 4):
            continue
        o, pc, ph, pl, po = O[i], C[i - 1], H[i - 1], L[i - 1], O[i - 1]
        k = o / es_ref                                          # NQ points per ES point
        rng2 = H[i - 2:i].max() - L[i - 2:i].min()
        rng5 = H[i - 5:i].max() - L[i - 5:i].min()
        sma5 = C[i - 5:i].mean()
        body_ok = abs(pc - po) / max(ph - pl, 1e-9) > 0.2
        side = 0
        if o < pc and ((pc > po and o > pl) or pc < po) and D.c[i, 0] > sma5 and body_ok:
            side = 1
        elif o > pc and o < ph and (o - pc) < 0.2 * rng2:
            side = -1
        if not side:
            continue
        lim = o - side * 2 * k
        stop_dist = min(0.5 * rng5, (10 if side == 1 else 13) * k)       # $500 / $650 per ES
        tgt_dist = (5 if side == 1 else 13) * k                         # $250 / $650 per ES
        hi_, lo_ = D.h[i], D.l[i]
        f = next((j for j in range(1, 389) if (lo_[j] <= lim if side == 1 else hi_[j] >= lim)), None)
        if f is None:
            continue
        e = min(D.o[i, f], lim) if side == 1 else max(D.o[i, f], lim)
        px, _, _ = walk(D.o[i], hi_, lo_, D.c[i], f, side, e, e - side * stop_dist, e + side * tgt_dist, 389, at_open=False)
        rows.append((D.days[i], side, (px - e) * side, stop_dist))
    return _df(rows)


# ---------------------------------------------------------------- 11. 9/21 EMA cross at the open + VWAP
def ema_cross_open(D, full_close: pd.Series, atr1: pd.Series):
    e9 = full_close.ewm(span=9, adjust=False).mean()
    e21 = full_close.ewm(span=21, adjust=False).mean()
    diff = (e9 - e21)
    rows = []
    for i in range(len(D.days)):
        d0 = pd.Timestamp(D.days[i]).tz_localize("America/New_York") + pd.Timedelta(minutes=570)
        dd = diff.reindex(pd.date_range(d0 - pd.Timedelta(minutes=1), periods=31, freq="1min")).values
        at = atr1.reindex(pd.date_range(d0, periods=30, freq="1min")).values
        vw = D.vwap(i)
        for k in range(30):
            if np.isnan(dd[k]) or np.isnan(dd[k + 1]):
                continue
            side = 1 if dd[k] <= 0 < dd[k + 1] else -1 if dd[k] >= 0 > dd[k + 1] else 0
            if not side or (D.c[i, k] - vw[k]) * side <= 0 or np.isnan(at[k]):
                continue
            e = D.c[i, k]
            sd = 1.5 * at[k]
            px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], k + 1, side, e, e - side * sd, e + side * sd, 384)
            rows.append((D.days[i], side, (px - e) * side, sd))
            break
    return _df(rows)


# ---------------------------------------------------------------- 12. Initial-balance breakout + VWAP
def ib_breakout(D, vwap_filter=True, close_entry=True):
    rows = []
    for i in range(len(D.days)):
        hi, lo = D.h[i, :60].max(), D.l[i, :60].min()
        rng = hi - lo
        o5, h5, l5, c5, _ = D.bars(i, 5)
        vw = D.vwap(i)
        used = set()
        k = 12                                                  # 5-min bar 12 = 10:30
        while k < 60:                                           # entries until 14:30
            vwk = vw[k * 5 + 4]
            side = 0
            if close_entry:
                if c5[k] > hi and 1 not in used and (not vwap_filter or c5[k] > vwk):
                    side = 1
                elif c5[k] < lo and -1 not in used and (not vwap_filter or c5[k] < vwk):
                    side = -1
                if not side:
                    k += 1
                    continue
                j0, e, at_open = (k + 1) * 5, o5[k + 1], True
            else:
                if h5[k] > hi and 1 not in used and (not vwap_filter or vw[k * 5] > hi):
                    side = 1
                elif l5[k] < lo and -1 not in used and (not vwap_filter or vw[k * 5] < lo):
                    side = -1
                if not side:
                    k += 1
                    continue
                lvl = hi if side == 1 else lo
                j0 = next(j for j in range(k * 5, k * 5 + 5) if (D.h[i, j] > hi if side == 1 else D.l[i, j] < lo))
                e, at_open = (max(D.o[i, j0], lvl) if side == 1 else min(D.o[i, j0], lvl)), False
            used.add(side)
            stop = lo if side == 1 else hi
            tgt = (hi + 1.5 * rng) if side == 1 else (lo - 1.5 * rng)
            px, jx, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], j0, side, e, stop, tgt, 384, at_open=at_open)
            rows.append((D.days[i], side, (px - e) * side, abs(e - stop)))
            k = jx // 5 + 1
    return _df(rows)


# ---------------------------------------------------------------- 15. Crabel stretch ORB
def crabel(D, mult=1.0, nr=0):
    O, H, L = D.o[:, 0], D.h.max(1), D.l.min(1)
    noise = np.minimum(H - O, O - L)
    rng = H - L
    rows = []
    for i in range(20, len(D.days)):
        if nr and not rng[i - 1] <= rng[i - nr:i].min():
            continue
        st = noise[i - 10:i].mean() * mult
        up, dn = O[i] + st, O[i] - st
        hh, ll = D.h[i], D.l[i]
        j = next((j for j in range(390) if hh[j] >= up or ll[j] <= dn), None)
        if j is None or st <= 0:
            continue
        if hh[j] >= up and ll[j] <= dn:
            rows.append((D.days[i], 1, -(up - dn), up - dn))     # both in the first minute: one losing round trip
            continue
        side = 1 if hh[j] >= up else -1
        e = max(D.o[i, j], up) if side == 1 else min(D.o[i, j], dn)
        stop = dn if side == 1 else up
        px, _, _ = walk(D.o[i], hh, ll, D.c[i], j, side, e, stop, None, 389, at_open=False)
        rows.append((D.days[i], side, (px - e) * side, abs(e - stop)))
    return _df(rows)


# ---------------------------------------------------------------- 17. Overnight drift 02:00–03:00
def overnight_drift(full: pd.DataFrame):
    m = full.index.hour * 60 + full.index.minute
    a = full[m == 120].open
    b = full[m == 179].close
    a.index, b.index = a.index.date, b.index.date
    j = pd.concat([a, b], axis=1, keys=["a", "b"]).dropna()
    j = j[[pd.Timestamp(d).weekday() < 5 for d in j.index]]
    return _df([(d, 1, r.b - r.a, NAN) for d, r in j.iterrows()])


# ---------------------------------------------------------------- 18. Larry Williams volatility breakout
def williams(D, k=0.25):
    H, L = D.h.max(1), D.l.min(1)
    rows = []
    for i in range(1, len(D.days)):
        if D.prev_gap_days[i] > 4:
            continue
        r = k * (H[i - 1] - L[i - 1])
        o0 = D.o[i, 0]
        up, dn = o0 + r, o0 - r
        j = next((j for j in range(390) if D.h[i, j] >= up or D.l[i, j] <= dn), None)
        if j is None or r <= 0:
            continue
        if D.h[i, j] >= up and D.l[i, j] <= dn:
            continue                                            # interp: ambiguous first minute → skip
        side = 1 if D.h[i, j] >= up else -1
        e = max(D.o[i, j], up) if side == 1 else min(D.o[i, j], dn)
        px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], j, side, e, e - side * 2 * r, e + side * 2 * r, 389, at_open=False)
        rows.append((D.days[i], side, (px - e) * side, 2 * r))
    return _df(rows)


# ---------------------------------------------------------------- 19. ORB with two targets (Edgeful)
def orb_2tp(D, or_min=15, max_or_pct=0.005, max_loss_pts=50.0):
    rows = []
    nb = or_min // 5
    for i in range(len(D.days)):
        o5, h5, l5, c5, _ = D.bars(i, 5)
        hi, lo = h5[:nb].max(), l5[:nb].min()
        size = hi - lo
        if size <= 0 or size > max_or_pct * D.o[i, 0]:
            continue
        k = next((k for k in range(nb, 77) if c5[k] > hi or c5[k] < lo), None)
        if k is None:
            continue
        side = 1 if c5[k] > hi else -1
        e = c5[k]
        sd = min(size, max_loss_pts)                           # $1,000 per NQ = 50 points
        j0 = (k + 1) * 5
        pts = 0.0
        for frac in (0.4, 0.5):
            px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], j0, side, e, e - side * sd, e + side * frac * size, 384)
            pts += (px - e) * side / 2                          # average of the two contracts
        rows.append((D.days[i], side, pts, sd))
    return _df(rows)


# ---------------------------------------------------------------- 20. Value-area 80 % rule
def value_area(lo_, hi_, vol, bin_=1.0, pct=0.7):
    base = np.floor(lo_.min())
    nb = int(np.ceil(hi_.max() - base) / bin_) + 1
    prof = np.zeros(nb)
    for a, b, v in zip(lo_, hi_, vol):
        i0, i1 = int((a - base) // bin_), int((b - base) // bin_)
        prof[i0:i1 + 1] += v / (i1 - i0 + 1)
    poc = int(prof.argmax())
    lo_i = hi_i = poc
    tot, acc = prof.sum(), prof[poc]
    while acc < pct * tot and (lo_i > 0 or hi_i < nb - 1):
        up = prof[hi_i + 1] if hi_i < nb - 1 else -1
        dn = prof[lo_i - 1] if lo_i > 0 else -1
        if up >= dn:
            hi_i += 1; acc += up
        else:
            lo_i -= 1; acc += dn
    return base + lo_i * bin_, base + (hi_i + 1) * bin_


def va80(D, buf=2.5):
    rows = []
    for i in range(1, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4:
            continue
        val, vah = value_area(D.l[i - 1], D.h[i - 1], D.v[i - 1])
        o0 = D.o[i, 0]
        if val <= o0 <= vah:
            continue
        side = 1 if o0 < val else -1
        c30 = D.c[i, 29::30]
        ins = (c30 >= val) & (c30 <= vah)
        k = next((k for k in range(1, 12) if ins[k] and ins[k - 1]), None)   # two consecutive 30-min closes inside
        if k is None:
            continue
        j0 = (k + 1) * 30
        e = D.o[i, j0]
        stop = val - buf if side == 1 else vah + buf
        tgt = vah if side == 1 else val
        if (tgt - e) * side <= 0 or (e - stop) * side <= 0:
            continue
        px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], j0, side, e, stop, tgt, 384)
        rows.append((D.days[i], side, (px - e) * side, (e - stop) * side))
    return _df(rows)
