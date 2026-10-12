"""Group B: liquidity-sweep / ICT strategies (ranks 7, 8, 10) on the 24h 1-minute series.
Session day = Globex day 18:00 → 17:00 ET, labelled by its 17:00 date. Interpretations marked "interp:".
All entries flat by 15:55 ET (prop-firm rule; the sources leave the cutoff open)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import walk

NAN = float("nan")


def sessions(full: pd.DataFrame):
    """Yield (date, tod_minutes, o, h, l, c, prev_high, prev_low) per Globex day."""
    sd = (full.index + pd.Timedelta(hours=6)).date
    tod = (full.index.hour * 60 + full.index.minute).values
    o, h, l, c = (full[k].values for k in ("open", "high", "low", "close"))
    idx = pd.Series(np.arange(len(full))).groupby(sd).agg(["first", "last"])
    prev = None
    for d, (a, b) in idx.iterrows():
        sl = slice(a, b + 1)
        if pd.Timestamp(d).weekday() < 5 and prev is not None:
            yield d, tod[sl], o[sl], h[sl], l[sl], c[sl], prev[0], prev[1], a
        prev = (h[sl].max(), l[sl].min())


def _tod_idx(tod, minute):
    k = np.searchsorted(np.where(tod >= 18 * 60, tod - 1440, tod), minute)
    return k


def _rel(tod):
    return np.where(tod >= 18 * 60, tod - 1440, tod)       # minutes from midnight, evening negative


# ---------------------------------------------------------------- 7. Asia/London sweep + FVG reversal
def sweep_fvg(full, rr_skip=(10, 20)):
    rows = []
    for d, tod, o, h, l, c, pdh, pdl, _ in sessions(full):
        r = _rel(tod)
        lon = (r >= 120) & (r < 420)
        if lon.sum() < 200:
            continue
        levels = {"PDH": [pdh, 1, False], "PDL": [pdl, -1, False],
                  "LH": [h[lon].max(), 1, False], "LL": [l[lon].min(), -1, False]}
        start = int(np.argmax(r >= 420))
        stop_i = int(np.argmax(r >= 15 * 60 + 55)) if (r >= 15 * 60 + 55).any() else len(r) - 1
        fvgs = []                                           # [kind(+1 bull / -1 bear), lo, hi]
        first = int(np.argmax(r >= 120))
        setup = None
        busy = -1
        for i in range(first + 2, stop_i):
            # FVG bookkeeping (approach-leg gaps from 02:00 on)
            if h[i - 2] < l[i]:
                fvgs.append([1, h[i - 2], l[i]])
            if l[i - 2] > h[i]:
                fvgs.append([-1, h[i], l[i - 2]])
            fvgs = [f for f in fvgs if not ((f[0] == 1 and c[i] < f[1]) or (f[0] == -1 and c[i] > f[2]))]
            if i < start or r[i] >= 11 * 60 or i <= busy:
                continue
            # sweeps
            for name, lv in levels.items():
                px, kind, done = lv
                if done:
                    continue
                if (kind == -1 and l[i] < px) or (kind == 1 and h[i] > px):
                    lv[2] = True
                    side = 1 if kind == -1 else -1
                    ref = next((f for f in reversed(fvgs) if f[0] == -side), None)
                    setup = None if ref is None else dict(side=side, lvl=px, zone=ref, confirmed=False)
            if setup is None:
                continue
            s = setup
            lo_, hi_ = s["zone"][1], s["zone"][2]
            if not s["confirmed"]:
                if (s["side"] == 1 and c[i] > hi_) or (s["side"] == -1 and c[i] < lo_):
                    s["confirmed"] = True
                continue
            mid = (lo_ + hi_) / 2
            if not ((s["side"] == 1 and l[i] <= mid) or (s["side"] == -1 and h[i] >= mid)):
                continue
            side, e, stop = s["side"], mid, s["lvl"]
            risk = (e - stop) * side
            setup = None
            if risk <= 0:
                continue
            opp = [lv[0] for lv in levels.values() if not lv[2] and lv[1] == side and (lv[0] - e) * side > 0]
            if not opp:
                continue
            tgt = min(opp) if side == 1 else max(opp)
            rr = (tgt - e) * side / risk
            if rr_skip[0] <= rr <= rr_skip[1]:
                continue
            e = min(o[i], mid) if side == 1 else max(o[i], mid)
            px, j, _ = walk(o, h, l, c, i, side, e, stop, tgt, stop_i, at_open=False)
            rows.append((d, side, (px - e) * side, risk))
            busy = j
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])


# ---------------------------------------------------------------- 8. ICT Silver Bullet AM
def silver_bullet(full, atr1: np.ndarray, min_rr=2.5, be_r=3.0, disp_atr=1.5, fvg_atr=0.3):
    rows = []
    for d, tod, o, h, l, c, _, _, a0 in sessions(full):
        r = _rel(tod)
        rng = (r >= 540) & (r < 600)
        if rng.sum() < 55:
            continue
        hi, lo = h[rng].max(), l[rng].min()
        i0 = int(np.argmax(r >= 600))
        i1 = int(np.argmax(r >= 660))
        iend = int(np.argmax(r >= 15 * 60 + 55)) if (r >= 15 * 60 + 55).any() else len(r) - 1
        at = atr1[a0:a0 + len(r)]
        swept = {1: None, -1: None}                         # side → sweep extreme
        pend = None
        for i in range(i0, i1):
            if h[i] > hi:
                swept[-1] = max(swept[-1] or h[i], h[i])
            if l[i] < lo:
                swept[1] = min(swept[1] or l[i], l[i])
            # displacement candle back inside → FVG with the next candle (needs i+1 closed)
            if pend is None and i + 1 < i1:
                body = abs(c[i] - o[i])
                if body > disp_atr * at[i - 1] and body >= 0.7 * (h[i] - l[i]):
                    if swept[-1] is not None and c[i] < o[i] and c[i] < hi and l[i - 1] > h[i + 1] and l[i - 1] - h[i + 1] >= fvg_atr * at[i - 1]:
                        pend = dict(side=-1, entry=h[i + 1], stop=swept[-1], tgt=lo, ready=i + 2)
                    elif swept[1] is not None and c[i] > o[i] and c[i] > lo and h[i - 1] < l[i + 1] and l[i + 1] - h[i - 1] >= fvg_atr * at[i - 1]:
                        pend = dict(side=1, entry=l[i + 1], stop=swept[1], tgt=hi, ready=i + 2)
                    if pend:
                        risk = (pend["entry"] - pend["stop"]) * pend["side"]
                        if risk <= 0 or (pend["tgt"] - pend["entry"]) * pend["side"] < min_rr * risk:
                            pend = None
            if pend and i >= pend["ready"]:
                s = pend["side"]
                if (s == 1 and l[i] <= pend["entry"]) or (s == -1 and h[i] >= pend["entry"]):
                    e = min(o[i], pend["entry"]) if s == 1 else max(o[i], pend["entry"])
                    risk = (e - pend["stop"]) * s
                    if risk > 0:
                        px, _, _ = walk(o, h, l, c, i, s, e, pend["stop"], pend["tgt"], iend, at_open=False, be_at=be_r * risk)
                        rows.append((d, s, (px - e) * s, risk))
                    break
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])


# ---------------------------------------------------------------- 10. HTF-bias sweep and reclaim
def _pivots(hh, ll, n):
    ph = np.full(len(hh), np.nan)
    pl = np.full(len(hh), np.nan)
    for i in range(n, len(hh) - n):
        if hh[i] == hh[i - n:i + n + 1].max():
            ph[i] = hh[i]
        if ll[i] == ll[i - n:i + n + 1].min():
            pl[i] = ll[i]
    return ph, pl


def _bias_series(full, tf, n=3):
    """interp: structure bias = +1 after higher-high & higher-low pivots, −1 after lower-high & lower-low,
    else 0. Pivot confirmed n bars after it; value usable from the close of the confirming bar."""
    b = full.resample(tf, label="left", closed="left").agg({"high": "max", "low": "min"}).dropna()
    ph, pl = _pivots(b.high.values, b.low.values, n)
    out = np.zeros(len(b))
    hs, ls = [], []
    for i in range(len(b)):
        j = i - n
        if j >= 0 and not np.isnan(ph[j]):
            hs.append(ph[j])
        if j >= 0 and not np.isnan(pl[j]):
            ls.append(pl[j])
        if len(hs) >= 2 and len(ls) >= 2:
            out[i] = 1 if hs[-1] > hs[-2] and ls[-1] > ls[-2] else -1 if hs[-1] < hs[-2] and ls[-1] < ls[-2] else 0
    step = pd.Timedelta(tf)
    s = pd.Series(out, index=b.index + step)                 # known once the bar has closed
    return s.reindex(full.index, method="ffill").fillna(0).values


def htf_sweep(full, atr1: np.ndarray, leg_atr=1.5, window=15, piv=5):
    b5 = _bias_series(full, "5min")
    b30 = _bias_series(full, "30min")
    bias = np.where((b5 == b30) & (b5 != 0), b5, 0)
    rows = []
    for d, tod, o, h, l, c, pdh, pdl, a0 in sessions(full):
        r = _rel(tod)
        n = len(r)
        lon = (r >= 120) & (r < 420)
        if lon.sum() < 200:
            continue
        lows = [pdl, l[lon].min()]
        highs = [pdh, h[lon].max()]
        bi = bias[a0:a0 + n]
        at = atr1[a0:a0 + n]
        ent0 = int(np.argmax(r >= 570))
        last_e = int(np.argmax(r >= 930))
        iend = int(np.argmax(r >= 15 * 60 + 55)) if (r >= 15 * 60 + 55).any() else n - 1
        arm = None
        busy = -1
        for i in range(piv * 2, iend):
            j = i - piv                                     # confirmed 1-minute pivots join the pools
            if h[j] == h[j - piv:i + 1].max():
                highs.append(h[j]); highs = highs[-52:]
            if l[j] == l[j - piv:i + 1].min():
                lows.append(l[j]); lows = lows[-52:]
            if i < ent0 or i > last_e or i <= busy:
                continue
            if arm is None:
                if bi[i - 1] == 1:
                    sw = [x for x in lows if l[i] < x]
                    if sw:
                        lv = max(sw); lows = [x for x in lows if x not in sw]
                        arm = dict(side=1, lvl=lv, ext=l[i], t=i)
                elif bi[i - 1] == -1:
                    sw = [x for x in highs if h[i] > x]
                    if sw:
                        lv = min(sw); highs = [x for x in highs if x not in sw]
                        arm = dict(side=-1, lvl=lv, ext=h[i], t=i)
            if arm is None:
                continue
            s = arm["side"]
            arm["ext"] = min(arm["ext"], l[i]) if s == 1 else max(arm["ext"], h[i])
            if i - arm["t"] > window or bi[i - 1] != s:
                arm = None
                continue
            reclaim = c[i] > arm["lvl"] if s == 1 else c[i] < arm["lvl"]
            if reclaim and (c[i] - arm["ext"]) * s >= leg_atr * at[i]:
                e = c[i]
                stop = arm["ext"] - s * 0.1 * at[i]
                risk = (e - stop) * s
                px, jx, _ = walk(o, h, l, c, i + 1, s, e, stop, e + s * risk, iend)
                rows.append((d, s, (px - e) * s, risk))
                busy, arm = jx, None
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])
