"""Faithful-as-possible replications of the named creator strategies (spreadsheet leads), each on 2010-06 → 2023-12
(holdout untouched). Same execution conventions as the ICT engine: decisions on closed bars, next-bar-open market fills
with 1 tick slippage, stop first when a bar touches stop and target, MNQ costs 0.75 pt + slippage per round trip.
Sources (rules copied from code / pages):
  ISO_GAP  Justme-Cliff/MNQ-strategy strategy/quant_gap.py      ISO_ORB  …/quant_orb.py (pullback + direct fallback)
  ISO_IB   …/quant_ib.py                                         ORB15    TradingView 6HYQYnFl '15 Min ORB Real Version MNQ'
  WIELAND  sevensinstrading/wieland-orb-backtest (variants A/B/C)
  SB_AM, V106, MACRO_A, SB_PM via the generic engine (ict_engine) with the closest parameterisation."""
import numpy as np, pandas as pd
import ict_data as data, ict_engine as E
from ict_data import t2m
from ict_space import COST_PTS, SLIP_PTS

D = data.load(); X = D["X"]; V = data.volume(); days = D["days"]; yr = D["yr"]
H = int(np.searchsorted(days.values, np.datetime64("2024-01-01")))
R930, R1600 = t2m("09:30"), t2m("16:00")


def bars(d, tf, a=R930, b=R1600):
    """tf-minute RTH bars of day d: arrays o,h,l,c,v and start minute index."""
    x = X[d, a:b]; v = V[d, a:b]; n = (b - a) // tf
    o = x[:n * tf:tf, 0]; c = x[tf - 1:n * tf:tf, 3]
    h = x[:n * tf, 1].reshape(n, tf).max(1); l = x[:n * tf, 2].reshape(n, tf).min(1); vv = v[:n * tf].reshape(n, tf).sum(1)
    return o, h, l, c, vv


def daily_atr():
    rh = X[:, R930:R1600, 1].max(1); rl = X[:, R930:R1600, 2].min(1); rc = X[:, R1600 - 1, 3]
    pc = np.r_[rc[0], rc[:-1]]; tr = np.maximum(rh - rl, np.maximum(abs(rh - pc), abs(rl - pc)))
    a5 = pd.Series(tr).rolling(5).mean().shift().values; a20 = pd.Series(tr).rolling(20).mean().shift().values
    return np.fmax(a5, a20), rc


ATRD, RCLOSE = daily_atr()


def walk(o, h, l, c, j, s, e, stop, tgt, last, partial=None):
    """exit from bar j (entry bar: stop only). partial = (t1, frac, be_after) for scale-out. Returns (avg exit pts, kind)."""
    rem = 1.0; pts = 0.0; st = stop; t1done = False
    for k in range(j, last + 1):
        if (l[k] <= st) if s == 1 else (h[k] >= st):
            px = st if k == j else (min(o[k], st) if s == 1 else max(o[k], st)); return pts + rem * s * (px - e), "stop"
        if k > j and partial is not None and not t1done and ((h[k] >= partial[0] + 0.25) if s == 1 else (l[k] <= partial[0] - 0.25)):
            pts += partial[1] * s * (partial[0] - e); rem -= partial[1]; t1done = True
            if partial[2]: st = e
        if k > j and ((h[k] >= tgt + 0.25) if s == 1 else (l[k] <= tgt - 0.25)):
            return pts + rem * s * (tgt - e), "target"
    return pts + rem * s * (c[last] - e), "time"


def rec(out, d, s, e, stop, res, kind, entry_mkt=True):
    risk = abs(e - stop); slip = (SLIP_PTS if entry_mkt else 0) + (SLIP_PTS if kind != "target" else 0)
    net = res - COST_PTS - slip; out.append((days[d], s, net / risk, net, risk))


def iso_gap():
    out = []
    for d in range(21, H):
        if days[d].weekday() == 0 or not (ATRD[d] > 0): continue
        o, h, l, c, v = bars(d, 5); pc = RCLOSE[d - 1]; gap = o[0] - pc; gs = abs(gap)
        if gs < 2 or gs / ATRD[d] > 0.30 or gs / pc > 0.0055: continue
        s = 1 if gap < 0 else -1
        if (c[0] - o[0]) * s <= 0: continue
        pm = X[d, t2m("09:00"):R930]; pmo, pmc = pm[0, 0], pm[-1, 3]
        if (pmc - pmo) * s <= 0: continue
        e = o[1] + s * 0; stop = (l[0] - 2) if s == 1 else (h[0] + 2)
        if abs(e - stop) > 25 or (e - pc) * s >= 0: continue
        tgt = pc + s * gs * 0.5; last = (t2m("12:00") - R930) // 5 - 1
        res, kind = walk(o, h, l, c, 1, s, e, stop, tgt, last); rec(out, d, s, e, stop, res, kind)
    return out


def iso_orb(causal=True):
    """causal=False reproduces the published code, whose 'direct' fallback enters at the open of the bar right after the
    breakout although the decision is only taken 4 bars later (look-ahead)."""
    out = []
    for d in range(21, H):
        if not (ATRD[d] > 0): continue
        o, h, l, c, v = bars(d, 5); orh, orl = h[0], l[0]; rg = orh - orl
        if rg < max(3.0, ATRD[d] * 0.025) or rg > ATRD[d] * 0.5: continue
        tp = (X[d, R930:R1600, 1] + X[d, R930:R1600, 2] + X[d, R930:R1600, 3]) / 3; vv = V[d, R930:R1600]
        vw1 = np.cumsum(tp * vv) / np.maximum(np.cumsum(vv), 1); vw = vw1[4::5]
        last = (t2m("12:00") - R930) // 5 - 1; bdir = 0; nb = 0; init = None
        for i in range(1, last):
            if bdir == 0:
                if c[i] > orh and c[i] >= vw[i]:
                    if days[d].weekday() == 0: break
                    bdir = 1; nb = 0; init = i + 1; continue
                if c[i] < orl and c[i] <= vw[i]: bdir = -1; nb = 0; init = i + 1; continue
                continue
            nb += 1; s = bdir; lvl = orh if s == 1 else orl
            zone = (orh <= c[i] <= orh + 0.25 * rg) if s == 1 else (orl - 0.25 * rg <= c[i] <= orl)
            if zone and ((c[i] - orl) / rg if s == 1 else (orh - c[i]) / rg) < 0.75: zone = False
            if zone and (c[i] - vw[i]) * s >= 0:
                e = o[i + 1]; stop = lvl - s * 2.0
                if s * (e - stop) > 25: stop = e - s * 25
                if s * (e - stop) <= 0: break
                tgt = e + s * min(rg, 3 * s * (e - stop)); res, kind = walk(o, h, l, c, i + 1, s, e, stop, tgt, last); rec(out, d, s, e, stop, res, kind); break
            if nb >= 4 and init is not None:
                j = i + 1 if causal else init
                e = o[j]; stop = lvl - s * 0.5 * rg
                if s * (e - stop) > 25: stop = e - s * 25
                tgt = e + s * min(rg, 3 * s * (e - stop))
                if abs(e - tgt) < 3 or s * (e - stop) <= 0: break
                res, kind = walk(o, h, l, c, j, s, e, stop, tgt, last); rec(out, d, s, e, stop, res, kind); break
            if (c[i] - lvl) * s < 0: bdir = 0
    return out


def iso_ib():
    out = []
    for d in range(21, H):
        if not (ATRD[d] > 0): continue
        o, h, l, c, v = bars(d, 5); ibh, ibl = h[:6].max(), l[:6].min(); rg = ibh - ibl
        if rg < max(5.0, ATRD[d] * 0.05) or rg > ATRD[d] * 0.65: continue
        bias = 1 if int(np.argmax(h[:6])) > int(np.argmin(l[:6])) else -1        # low first → bullish
        last = (t2m("12:00") - R930) // 5 - 1; bdir = 0; ext = 0.0; mx = 0.0
        for i in range(6, (t2m("11:30") - R930) // 5):
            if bdir == 0:
                if c[i] > ibh: bdir = 1; ext = h[i]; mx = c[i] - ibh; continue
                if c[i] < ibl: bdir = -1; ext = l[i]; mx = ibl - c[i]; continue
                continue
            s = bdir; lvl = ibh if s == 1 else ibl
            if (h[i] > ext) if s == 1 else (l[i] < ext): ext = h[i] if s == 1 else l[i]; mx = s * (ext - lvl)
            ret = s * (ext - c[i]) / mx if mx > 0 else 1.0
            if ret < 0.25 and (c[i] - lvl) * s > 0 and bias == s:
                e = o[i + 1]
                if s * (e - lvl) > 30: break
                stop = lvl - s * 2.0
                if s * (e - stop) > 25: stop = e - s * 25
                if s * (e - stop) <= 0: break
                tgt = lvl + s * 1.5 * rg; res, kind = walk(o, h, l, c, i + 1, s, e, stop, tgt, last); rec(out, d, s, e, stop, res, kind); break
            if (c[i] - lvl) * s < 0: bdir = 0; mx = 0.0
    return out


def orb15(vol_mult=1.5, last_entry="11:00"):
    out = []; vhist = []
    for d in range(21, H):
        o, h, l, c, v = bars(d, 15); orh, orl = h[:2].max(), l[:2].min(); rg = orh - orl
        avgv = np.mean(vhist[-20:]) if len(vhist) >= 20 else np.nan; vhist += list(v)
        if rg <= 0 or np.isnan(avgv): continue
        last = (t2m("15:50") - R930) // 15 - 1; done = set()
        for i in range(2, (t2m(last_entry) - R930) // 15):
            for s in (1, -1):
                if s in done: continue
                if ((c[i] > orh) if s == 1 else (c[i] < orl)) and v[i] > vol_mult * avgv:
                    done.add(s); e = o[i + 1]; stop = orl if s == 1 else orh
                    t1 = e + s * 0.35 * rg; t2 = e + s * 1.0 * rg
                    res, kind = walk(o, h, l, c, i + 1, s, e, stop, t2, last, partial=(t1, 0.5, True)); rec(out, d, s, e, stop, res, kind)
                    break
            if done: break
    return out


def wieland(variant="C"):
    out = []
    for d in range(21, H):
        x = X[d]; orh, orl = x[R930:t2m("09:45"), 1].max(), x[R930:t2m("09:45"), 2].min(); rg = orh - orl; mid = (orh + orl) / 2
        if rg <= 0: continue
        o, h, l, c = x[:, 0], x[:, 1], x[:, 2], x[:, 3]
        for j in range(t2m("09:45"), R1600 - 1):
            s = 1 if h[j] > orh else (-1 if l[j] < orl else 0)
            if s == 0: continue
            if h[j] > orh and l[j] < orl: break                  # both sides in one minute: ambiguous, skip day
            lvl = orh if s == 1 else orl; e = max(lvl, o[j]) if s == 1 else min(lvl, o[j]); stop = mid
            t1, t2 = e + s * 0.5 * rg, e + s * 1.0 * rg
            if variant == "A": res, kind = walk(o, h, l, c, j, s, e, stop, t1, R1600 - 1)
            elif variant == "B": res, kind = walk(o, h, l, c, j, s, e, stop, t2, R1600 - 1)
            else: res, kind = walk(o, h, l, c, j, s, e, stop, t2, R1600 - 1, partial=(t1, 0.5, True))
            rec(out, d, s, e, stop, res, kind); break
    return out


def engine_cfg(ws, we, te, mask, **kw):
    P = np.zeros(E.NPAR)
    base = dict(ROLLN=30, SWEEP=0, CONF=3, CONFN=30, DISP=1.0, PIVK=3, ENTRY=1, VALID=30, STOPM=0, SBUF=0.0, SATR=2.0, TPM=0, TPR=2.0,
                BER=0.0, BIAS=0, SIDE=0, MAXT=1, MINR=1.0, MAXR=1e9, SAL=0)
    base.update({k.upper(): v for k, v in kw.items()})
    P[E.WS], P[E.WE], P[E.TEXIT], P[E.LMASK] = t2m(ws), t2m(we), t2m(te), mask
    for k, v in base.items(): P[getattr(E, k)] = v
    P[E.THRU], P[E.COST], P[E.SLIP] = 0.25, COST_PTS, SLIP_PTS
    return P


ENGINE_NAMED = {
    # hindsight-finance Silver Bullet AM: 9:00 hour range swept 10-11, displacement ≥1.5 ATR, FVG entry, target opposite side, BE 3R
    "SB_AM": engine_cfg("10:00", "11:00", "11:30", 1 << 4, conf=3, disp=1.5, entry=1, stopm=0, tpm=1, tpr=2.5, ber=3.0),
    "SB_PM": engine_cfg("14:00", "15:00", "15:30", (1 << 8), rolln=60, conf=3, disp=1.5, entry=1, stopm=0, tpm=0, tpr=2.0),
    # cayao2012 ICT-bot V106: liquidity sweep → displacement → FVG touch entry, flat 1.1 RR, kill zone 08:30-15:30 ET, 3/side
    "V106": engine_cfg("08:30", "15:30", "15:55", 0b1111 | (1 << 8), rolln=60, conf=3, disp=1.0, entry=1, valid=60, stopm=0, sbuf=1.0,
                       tpm=0, tpr=1.1, maxt=3),
    # sarahleesoffice macro window A 08:30-09:10: swing sweep → MSS → FVG, SL 3 handles beyond sweep, TP nearest swing ≥ 1R
    "MACRO_A": engine_cfg("08:30", "09:10", "10:00", (1 << 3) | (1 << 8), rolln=30, conf=1, pivk=3, entry=1, stopm=0, sbuf=3.0, tpm=1, tpr=1.0),
    # PineGen ICT daily liquidity sweep: Asia/PDH-PDL sweep + close back inside, market entry, stop beyond wick, 2R
    "PINEGEN": engine_cfg("09:30", "12:00", "15:55", 0b11, sweep=1, conf=0, entry=0, stopm=0, sbuf=1.0, tpm=0, tpr=2.0),
}


def engine_named(name, cx=1.0):
    P = ENGINE_NAMED[name].copy(); P[E.COST] *= cx; P[E.SLIP] *= cx
    prev = np.r_[False, (days[1:] - days[:-1]).days <= 4]
    d, t, s, R, rk, pts = E.run(X, D["LV"], D["ema200"], prev, P, 0, H)
    return [(days[a], b, r, p, k) for a, b, r, p, k in zip(d, s, R, pts, rk)]


def summary(name, trades):
    T = pd.DataFrame(trades, columns=["date", "side", "R", "pts", "risk"]); y = T.date.dt.year
    row = dict(name=name, n=len(T), per_yr=len(T) / max(y.nunique(), 1))
    for nm, a, b in (("tr", 2010, 2017), ("va", 2018, 2020), ("te", 2021, 2023), ("all", 2010, 2023)):
        r = T.R[(y >= a) & (y <= b)]
        row[nm + "_win"] = 100 * (r > 0).mean() if len(r) else np.nan; row[nm + "_R"] = r.mean() if len(r) else np.nan
    w = T.R[T.R > 0]; ls = T.R[T.R <= 0]; eq = T.R.cumsum()
    row.update(avgW=w.mean(), avgL=ls.mean(), pf=w.sum() / -ls.sum() if len(ls) else np.nan, dd=(eq.cummax() - eq).max(),
               usd=2 * T.pts.sum(), yrs_pos=f"{(T.groupby(y).R.sum() > 0).sum()}/{y.nunique()}",
               t=T.R.mean() / T.R.std() * np.sqrt(len(T)) if len(T) > 2 else np.nan)
    return row, T


if __name__ == "__main__":
    rows = []; logs = {}
    for name, fn in (("ISO_GAP", iso_gap), ("ISO_ORB_published(lookahead)", lambda: iso_orb(False)), ("ISO_ORB", iso_orb), ("ISO_IB", iso_ib), ("ORB15", orb15),
                     ("WIELAND_A", lambda: wieland("A")), ("WIELAND_B", lambda: wieland("B")), ("WIELAND_C", lambda: wieland("C"))):
        r, T = summary(name, fn()); rows.append(r); logs[name] = T
    for name in ENGINE_NAMED:
        r, T = summary(name, engine_named(name)); rows.append(r); logs[name] = T
    S = pd.DataFrame(rows); pd.set_option("display.width", 250); print(S.round(3).to_string(index=False))
    S.to_csv("creators_summary.csv", index=False)
    pd.concat([T.assign(strategy=k) for k, T in logs.items()]).to_csv(data.SP + "creators_trades.csv.gz", index=False)
