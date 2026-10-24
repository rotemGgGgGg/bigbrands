"""Causal 1-minute ICT/SMC engine (numba). One parameter vector P describes a full rule set; the engine walks every day
minute by minute exactly as a live bot would: it only knows bars that have closed, resting limit orders are checked from the
next bar on, one position at a time.

Model:  liquidity level swept (window, level set, wick or close-back)  →  confirmation (none / MSS / CISD / displacement,
        optional displacement body filter, within N bars)  →  entry (market next open / limit at the FVG of the reversal leg:
        proximal, mid or distal edge, valid V bars / IFVG close)  →  stop (sweep extreme / FVG distal / ATR)  →
        target (fixed R / nearest opposite liquidity)  →  optional break-even  →  time exit.
Filters: bias (none / vs the 18:00 open / premium-discount vs the mid of the session range so far / EMA200 / prior RTH candle), side,
         max trades per day, stop size band, stop-for-the-day after a loss.
Costs (MNQ, in NQ points per contract): commission+fees P[25] round trip; P[26] slippage on every market fill
(market entries, stop exits, time exits). Limit entries/targets fill only when price trades THROUGH by P[24]."""
import numpy as np
from numba import njit

# parameter indices
WS, WE, LMASK, ROLLN, SWEEP, CONF, CONFN, DISP, PIVK, ENTRY, VALID, STOPM, SBUF, SATR, TPM, TPR, BER, TEXIT, BIAS, SIDE, MAXT, \
    MINR, MAXR, SAL, THRU, COST, SLIP = range(27)
NPAR = 27


@njit(cache=True)
def _pivot_level(h, l, sb, k, side, lo):
    """most recent confirmed pivot HIGH (side=1, for longs' MSS) / LOW (side=-1) completed before bar sb."""
    for j in range(sb - k - 1, lo + k - 1, -1):
        ok = True
        for q in range(1, k + 1):
            if side == 1:
                if h[j - q] >= h[j] or h[j + q] > h[j]: ok = False; break
            else:
                if l[j - q] <= l[j] or l[j + q] < l[j]: ok = False; break
        if ok: return h[j] if side == 1 else l[j]
    return np.nan


@njit(cache=True)
def run(X, LV, E200, prev_ok, P, d0, d1):
    nd = d1 - d0; cap = nd * 6
    o_day = np.empty(cap, np.int64); o_t = np.empty(cap, np.int64); o_s = np.empty(cap, np.int64)
    o_r = np.empty(cap); o_risk = np.empty(cap); o_pts = np.empty(cap); nt = 0
    ws = int(P[WS]); we = int(P[WE]); mask = int(P[LMASK]); rolln = int(P[ROLLN]); te = min(int(P[TEXIT]), 1319)
    conf = int(P[CONF]); confn = int(P[CONFN]); disp = P[DISP]; pk = int(P[PIVK]); entry = int(P[ENTRY]); valid = int(P[VALID])
    stopm = int(P[STOPM]); sbuf = P[SBUF]; satr = P[SATR]; tpm = int(P[TPM]); tpr = P[TPR]; ber = P[BER]; bias = int(P[BIAS])
    sidep = int(P[SIDE]); maxt = int(P[MAXT]); minr = P[MINR]; maxr = P[MAXR]; sal = int(P[SAL]); thru = P[THRU]
    cost = P[COST]; slip = P[SLIP]
    for d in range(d0, d1):
        o = X[d, :, 0]; h = X[d, :, 1]; l = X[d, :, 2]; c = X[d, :, 3]; a = X[d, :, 4]
        dayopen = o[0]
        rhi = -1e18; rlo = 1e18                      # running session high/low (18:00 → previous bar): premium/discount
        pdir = 0
        if prev_ok[d]:
            pdir = 1 if X[d - 1, 1319, 3] > X[d - 1, 930, 0] else -1
        ntr = 0; stopday = False
        arm = np.zeros(2, np.int64); sbar = np.zeros(2, np.int64); ext = np.zeros(2); mss = np.full(2, np.nan)
        pend = 0; pL = 0.0; pS = 0.0; pT = 0.0; pside = 0; pval = 0; prisk = 0.0
        pos = 0; e = 0.0; st = 0.0; tg = 0.0; risk = 0.0; tin = 0; bearm = False; mkt_in = False
        for q in range(0, max(ws, 1)):
            rhi = max(rhi, h[q]); rlo = min(rlo, l[q])
        for t in range(max(ws, 1), te + 1):
            if t > max(ws, 1):
                rhi = max(rhi, h[t - 1]); rlo = min(rlo, l[t - 1])
            # ---------- manage open position ----------
            if pos != 0:
                px = np.nan; ex_slip = 0.0
                if (l[t] <= st) if pos == 1 else (h[t] >= st):
                    px = (min(o[t], st) if pos == 1 else max(o[t], st)) if t > tin else st; ex_slip = slip
                elif t > tin and ((h[t] >= tg + thru) if pos == 1 else (l[t] <= tg - thru)):
                    px = max(o[t], tg) if pos == 1 else min(o[t], tg)
                elif t == te:
                    px = c[t]; ex_slip = slip
                if not np.isnan(px):
                    pts = pos * (px - e) - cost - ex_slip - (slip if mkt_in else 0.0)
                    o_day[nt] = d; o_t[nt] = tin; o_s[nt] = pos; o_r[nt] = pts / risk; o_risk[nt] = risk; o_pts[nt] = pts; nt += 1
                    if pts < 0 and sal == 1: stopday = True
                    pos = 0; arm[0] = 0; arm[1] = 0
                    continue
                if ber > 0 and not bearm and ((h[t] >= e + ber * risk) if pos == 1 else (l[t] <= e - ber * risk)):
                    bearm = True; st = e
                continue
            # ---------- resting limit order ----------
            if pend != 0:
                if t > pval or ((l[t] <= pS) if pend == 1 else (h[t] >= pS)):
                    pend = 0
                elif (l[t] <= pL - thru) if pend == 1 else (h[t] >= pL + thru):
                    e = min(o[t], pL) if pend == 1 else max(o[t], pL); pos = pend; st = pS; risk = abs(e - st)
                    tg = e + pos * tpr * risk if tpm == 0 else pT
                    if tpm == 1 and (pos * (tg - e) < risk): tg = e + pos * tpr * risk
                    tin = t; bearm = False; mkt_in = False; pend = 0; ntr += 1
                    if (l[t] <= st) if pos == 1 else (h[t] >= st):          # stopped on the fill bar
                        pts = -risk - cost - slip
                        o_day[nt] = d; o_t[nt] = tin; o_s[nt] = pos; o_r[nt] = pts / risk; o_risk[nt] = risk; o_pts[nt] = pts; nt += 1
                        if sal == 1: stopday = True
                        pos = 0
                    continue
                continue
            if stopday or ntr >= maxt or t > we: continue
            # ---------- sweep detection (both sides) ----------
            for k in range(2):
                s = 1 if k == 0 else -1
                if sidep != 0 and s != sidep: continue
                side = 0 if s == 1 else 1        # long setups sweep sell-side (low) levels
                swept = False; lvl = 0.0
                for typ in range(8):
                    if (mask >> typ) & 1 == 0: continue
                    if np.isnan(LV[d, typ, side, 0]): continue
                    if int(LV[d, typ, side, 2]) == t and t >= ws:
                        if int(P[SWEEP]) == 1 and LV[d, typ, side, 3] == 0: continue
                        swept = True; lvl = LV[d, typ, side, 0]
                if (mask >> 8) & 1 and t > rolln:
                    m = 1e18 if s == 1 else -1e18
                    for q in range(t - rolln, t):
                        m = min(m, l[q]) if s == 1 else max(m, h[q])
                    hit = (l[t] < m) if s == 1 else (h[t] > m)
                    if hit and (int(P[SWEEP]) == 0 or ((c[t] > m) if s == 1 else (c[t] < m))):
                        swept = True; lvl = m
                if swept:
                    arm[k] = 1; sbar[k] = t; ext[k] = l[t] if s == 1 else h[t]
                    mss[k] = _pivot_level(h, l, t, pk, s, 0) if conf == 1 else np.nan
            # ---------- confirmation & entry ----------
            for k in range(2):
                if arm[k] == 0: continue
                s = 1 if k == 0 else -1
                if t > sbar[k]:
                    ext[k] = min(ext[k], l[t]) if s == 1 else max(ext[k], h[t])
                if t - sbar[k] > confn: arm[k] = 0; continue
                body = (c[t] - o[t]) * s; okc = False; fvg_top = np.nan; fvg_bot = np.nan
                if entry == 4:                                   # IFVG: close through an opposite FVG of the sweep leg
                    for j in range(t - 1, max(sbar[k] - 30, 2) - 1, -1):
                        if s == 1 and l[j - 2] > h[j] and c[t] > l[j - 2] and c[t - 1] <= l[j - 2]: okc = True; break
                        if s == -1 and h[j - 2] < l[j] and c[t] < h[j - 2] and c[t - 1] >= h[j - 2]: okc = True; break
                elif conf == 0: okc = True
                elif conf == 1: okc = (not np.isnan(mss[k])) and ((c[t] > mss[k]) if s == 1 else (c[t] < mss[k]))
                elif conf == 2:
                    j = t - 1
                    while j > sbar[k] - 30 and j > 0 and ((c[j] < o[j]) if s == 1 else (c[j] > o[j])) == False: j -= 1
                    r0 = j
                    while r0 - 1 > 0 and ((c[r0 - 1] < o[r0 - 1]) if s == 1 else (c[r0 - 1] > o[r0 - 1])): r0 -= 1
                    okc = j > sbar[k] - 30 and ((c[t] > o[r0]) if s == 1 else (c[t] < o[r0]))
                else:
                    okc = body > 0
                if okc and disp > 0 and not (body >= disp * a[t]): okc = False
                if not okc: continue
                # bias
                if bias == 1 and (c[t] - dayopen) * s <= 0: arm[k] = 0; continue
                if bias == 2 and (c[t] - 0.5 * (rhi + rlo)) * s >= 0: arm[k] = 0; continue
                if bias == 3 and (c[t] - E200[d, t]) * s <= 0: arm[k] = 0; continue
                if bias == 4 and pdir != s: arm[k] = 0; continue
                # entry price / stop
                if entry in (1, 2, 3):
                    jj = -1
                    for j in range(t, sbar[k] + 1, -1):
                        if (s == 1 and h[j - 2] < l[j]) or (s == -1 and l[j - 2] > h[j]): jj = j; break
                    if jj < 0: arm[k] = 0; continue
                    prox = l[jj] if s == 1 else h[jj]; dist = h[jj - 2] if s == 1 else l[jj - 2]
                    L = prox if entry == 1 else (0.5 * (prox + dist) if entry == 2 else dist)
                    if stopm == 0: S = ext[k] - s * sbuf
                    elif stopm == 1: S = dist - s * sbuf
                    else: S = L - s * satr * a[t]
                    rk = s * (L - S)
                    if rk < minr or rk > maxr or rk <= 0: arm[k] = 0; continue
                    T = np.nan
                    if tpm == 1: T = _opp_level(LV, d, s, t, L, mask)
                    pend = s; pL = L; pS = S; pT = T if not np.isnan(T) else L + s * tpr * rk; pval = t + valid
                    arm[0] = 0; arm[1] = 0; break
                else:
                    if t + 1 > te: arm[k] = 0; continue
                    E_ = o[t + 1]
                    if stopm == 2: S = E_ - s * satr * a[t]
                    else: S = ext[k] - s * sbuf
                    rk = s * (E_ - S)
                    if rk < minr or rk > maxr or rk <= 0: arm[k] = 0; continue
                    pos = s; e = E_; st = S; risk = rk; tin = t + 1; bearm = False; mkt_in = True; ntr += 1
                    tg = e + s * tpr * rk
                    if tpm == 1:
                        T = _opp_level(LV, d, s, t, e, mask)
                        if not np.isnan(T) and s * (T - e) >= rk: tg = T
                    arm[0] = 0; arm[1] = 0; break
        if pos != 0:                                    # filled on the very last bar: flat at its close
            pts = pos * (c[te] - e) - cost - slip - (slip if mkt_in else 0.0)
            o_day[nt] = d; o_t[nt] = tin; o_s[nt] = pos; o_r[nt] = pts / risk; o_risk[nt] = risk; o_pts[nt] = pts; nt += 1
    return o_day[:nt], o_t[:nt], o_s[:nt], o_r[:nt], o_risk[:nt], o_pts[:nt]


@njit(cache=True)
def _opp_level(LV, d, s, t, ref, mask):
    """nearest opposite-side liquidity (still untouched at t) beyond ref."""
    side = 1 if s == 1 else 0; best = np.nan
    for typ in range(8):
        if (mask >> typ) & 1 == 0 or np.isnan(LV[d, typ, side, 0]): continue
        p = LV[d, typ, side, 0]
        if LV[d, typ, side, 1] > t or LV[d, typ, side, 2] <= t: continue
        if s * (p - ref) <= 0: continue
        if np.isnan(best) or s * (p - best) < 0: best = p
    return best
