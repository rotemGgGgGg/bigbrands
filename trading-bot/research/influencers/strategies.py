"""Public strategies of trading educators/influencers, implemented as published (parameters NOT tuned).
Where a source leaves something open, the choice is written next to it as 'impl:'. Every function returns rows (i, pts, risk)."""
from lib import *
from collections import defaultdict

def run_seq(cands):
    """cands: {day: [(m, side, stop, target, entry, at_open), ...]} → sequential, non-overlapping trades."""
    rows = []
    for i, lst in cands.items():
        busy = -1
        for m, side, stop, tgt, entry, at_open in sorted(lst, key=lambda x: x[0]):
            if m <= busy: continue
            r = trade(i, m, side, stop, tgt, entry, at_open)
            if r is None: continue
            rows.append((i, r[0], r[1])); busy = r[2]
    return rows

g5, g15, g30 = G(5), G(15), G(30)
E20_5, E9_5 = ema(g5.c, 20), ema(g5.c, 9)
ADX5, PDI5, NDI5 = adx(g5.h, g5.l, g5.c, 14)
ATR5 = atr(g5.h, g5.l, g5.c, 14); ATR15 = atr(g15.h, g15.l, g15.c, 14)

def bar_entry(g, gi, side, stop, tgt=None):
    i = g.day(gi); m = g.next_min(gi)
    return i, (m, side, stop, tgt, None, True)

# ---------------------------------------------------------------- Toby Crabel
def crabel_stretch():
    """Crabel: stretch = 10-day avg of min(|open−high|, |open−low|). Buy stop open+stretch, sell stop open−stretch, first fill,
    stop at the opposite level, exit at the close."""
    st = pd.Series(np.minimum(abs(DO - DH), abs(DO - DL))).rolling(10).mean().shift().values; cands = defaultdict(list)
    for i in range(20, N):
        if not VALID[i] or np.isnan(st[i]): continue
        up, dn = DO[i] + st[i], DO[i] - st[i]
        a, b = stop_fill(i, 1, 384, up, 1), stop_fill(i, 1, 384, dn, -1)
        f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
        if f: (m, px), s = f; cands[i].append((m, s, dn if s == 1 else up, None, px, False))
    return run_seq(cands)
def crabel_nr7():
    """Crabel NR7: yesterday's range is the narrowest of 7 → trade the break of the 30-minute opening range, stop at the other side, exit close."""
    cands = defaultdict(list)
    for i in range(8, N):
        if not okprev[i] or RANGE[i - 1] > RANGE[i - 7:i].min(): continue
        hi, lo = h[i, :30].max(), l[i, :30].min()
        a, b = stop_fill(i, 30, 384, hi + TICK, 1), stop_fill(i, 30, 384, lo - TICK, -1)
        f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
        if f: (m, px), s = f; cands[i].append((m, s, lo if s == 1 else hi, None, px, False))
    return run_seq(cands)
# ---------------------------------------------------------------- Larry Williams
def williams_volbreak():
    """Williams volatility breakout: buy stop open + 0.6×yesterday's range (sell stop mirror); money stop 0.5×range; exit close."""
    cands = defaultdict(list)
    for i in range(1, N):
        if not okprev[i]: continue
        r = RANGE[i - 1]; up, dn = DO[i] + 0.6 * r, DO[i] - 0.6 * r
        a, b = stop_fill(i, 1, 384, up, 1), stop_fill(i, 1, 384, dn, -1)
        f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
        if f: (m, px), s = f; cands[i].append((m, s, px - s * 0.5 * r, None, px, False))
    return run_seq(cands)
def williams_oops():
    """Williams OOPS: open below yesterday's low → buy stop at yesterday's low (mirror above high); stop = day's extreme at entry; exit close."""
    cands = defaultdict(list)
    for i in range(1, N):
        if not okprev[i]: continue
        if DO[i] < PDL[i]:
            f = stop_fill(i, 1, 360, PDL[i], 1)
            if f: m, px = f; cands[i].append((m, 1, l[i, :m + 1].min() - TICK, None, px, False))
        elif DO[i] > PDH[i]:
            f = stop_fill(i, 1, 360, PDH[i], -1)
            if f: m, px = f; cands[i].append((m, -1, h[i, :m + 1].max() + TICK, None, px, False))
    return run_seq(cands)
# ---------------------------------------------------------------- Linda Raschke
def raschke_holy_grail():
    """Holy Grail (5m): ADX(14) > 30 and rising; price pulls back to the 20 EMA → buy stop above that bar's high (next 3 bars),
    stop below the bar's low, target = the recent swing high (20 bars); mirror for shorts."""
    cands = defaultdict(list); g = g5
    for gi in range(25, len(g.c) - 4):
        k = g.k(gi)
        if k < 6 or k > 70 or ADX5[gi] <= 30 or ADX5[gi] <= ADX5[gi - 1]: continue
        i = g.day(gi)
        for side in (1, -1):
            trend = PDI5[gi] > NDI5[gi] if side == 1 else NDI5[gi] > PDI5[gi]
            touch = g.l[gi] <= E20_5[gi] if side == 1 else g.h[gi] >= E20_5[gi]
            if not (trend and touch): continue
            lvl = g.h[gi] + TICK if side == 1 else g.l[gi] - TICK
            f = stop_fill(i, g.next_min(gi), g.next_min(gi) + 15, lvl, side)
            if not f: continue
            tgt = g.h[gi - 20:gi].max() if side == 1 else g.l[gi - 20:gi].min()
            if (tgt - f[1]) * side <= 0: continue
            cands[i].append((f[0], side, g.l[gi] - TICK if side == 1 else g.h[gi] + TICK, tgt, f[1], False))
    return run_seq(cands)
def raschke_8020():
    """80-20: yesterday opened in the top 20 % of its range and closed in the bottom 20 % → today, if price trades ≥ 5 pts below
    yesterday's low, buy stop back at yesterday's low; stop = today's low; exit close. Mirror."""
    cands = defaultdict(list)
    for i in range(1, N):
        if not okprev[i]: continue
        r = RANGE[i - 1]; op = (o[i - 1, 0] - PDL[i]) / r; cl = (PDC[i] - PDL[i]) / r
        if op >= 0.8 and cl <= 0.2:
            below = np.nonzero(l[i, :300] <= PDL[i] - 5)[0]
            if len(below):
                f = stop_fill(i, below[0] + 1, 330, PDL[i], 1)
                if f: cands[i].append((f[0], 1, l[i, :f[0] + 1].min() - TICK, None, f[1], False))
        if op <= 0.2 and cl >= 0.8:
            above = np.nonzero(h[i, :300] >= PDH[i] + 5)[0]
            if len(above):
                f = stop_fill(i, above[0] + 1, 330, PDH[i], -1)
                if f: cands[i].append((f[0], -1, h[i, :f[0] + 1].max() + TICK, None, f[1], False))
    return run_seq(cands)
def raschke_turtle_soup():
    """Turtle Soup (5m): new 20-bar low, the previous 20-bar low is ≥ 4 bars old → buy stop at the previous low (next 3 bars);
    stop = the new low; target 2R (impl: Raschke trails — 2R is the stand-in). Mirror."""
    cands = defaultdict(list); g = g5
    for gi in range(25, len(g.c) - 4):
        if g.k(gi) < 4 or g.k(gi) > 70: continue
        i = g.day(gi); win = slice(gi - 20, gi)
        lo_k = gi - 20 + int(np.argmin(g.l[win])); hi_k = gi - 20 + int(np.argmax(g.h[win]))
        if g.l[gi] < g.l[win].min() and gi - lo_k >= 4:
            f = stop_fill(i, g.next_min(gi), g.next_min(gi) + 15, g.l[lo_k], 1)
            if f: r = f[1] - (g.l[gi] - TICK); cands[i].append((f[0], 1, g.l[gi] - TICK, f[1] + 2 * r, f[1], False))
        if g.h[gi] > g.h[win].max() and gi - hi_k >= 4:
            f = stop_fill(i, g.next_min(gi), g.next_min(gi) + 15, g.h[hi_k], -1)
            if f: r = (g.h[gi] + TICK) - f[1]; cands[i].append((f[0], -1, g.h[gi] + TICK, f[1] - 2 * r, f[1], False))
    return run_seq(cands)
def raschke_anti():
    """'Anti' (5m): slow stochastic line (%D of 16) sloping up, fast %K(7) pulls back then hooks up → buy next bar;
    stop = 5-bar low; target 2R (impl). Mirror."""
    g = g5; lo7 = pd.Series(g.l).rolling(7).min().values; hi7 = pd.Series(g.h).rolling(7).max().values
    k = 100 * (g.c - lo7) / np.maximum(hi7 - lo7, 1e-9); fast = sma(k, 3); slow = sma(fast, 16)
    cands = defaultdict(list)
    for gi in range(30, len(g.c) - 1):
        if g.k(gi) < 6 or g.k(gi) > 72: continue
        for side in (1, -1):
            s_up = (slow[gi] - slow[gi - 3]) * side > 0
            hook = (fast[gi] - fast[gi - 1]) * side > 0 and (fast[gi - 1] - fast[gi - 2]) * side < 0 and ((fast[gi - 1] < slow[gi - 1]) if side == 1 else (fast[gi - 1] > slow[gi - 1]))
            if s_up and hook:
                stp = g.l[gi - 4:gi + 1].min() - TICK if side == 1 else g.h[gi - 4:gi + 1].max() + TICK
                i, cand = bar_entry(g, gi, side, stp); e = o[i, min(cand[0], 389)]; r = abs(e - stp)
                cands[i].append((cand[0], side, stp, e + side * 2 * r, None, True))
    return run_seq(cands)
# ---------------------------------------------------------------- Larry Connors (daily swing — not prop-compatible: holds overnight)
def daily_swing(entries):
    """entries: list of (i_entry_close, exit_rule) on RTH closes; P&L close-to-close incl. overnight, 2.25 pt cost."""
    return entries
def connors_rsi2():
    """RSI(2) < 10 and close > SMA200 → buy the close; exit at the close when close > SMA5."""
    r2 = rsi(DC, 2); s200 = sma(DC, 200); s5 = sma(DC, 5); rows = []; i = 201
    while i < N - 1:
        if r2[i] < 10 and DC[i] > s200[i]:
            j = next((x for x in range(i + 1, min(i + 30, N)) if DC[x] > s5[x]), min(i + 29, N - 1))
            rows.append((j, DC[j] - DC[i] - COST, np.nan)); i = j + 1
        else: i += 1
    return rows
def connors_double7():
    """Double 7s: close > SMA200 and close at a 7-day low → buy the close; exit at a 7-day high close."""
    s200 = sma(DC, 200); rows = []; i = 201
    while i < N - 1:
        if DC[i] > s200[i] and DC[i] <= DC[i - 6:i + 1].min():
            j = next((x for x in range(i + 1, min(i + 40, N)) if DC[x] >= DC[x - 6:x + 1].max()), min(i + 39, N - 1))
            rows.append((j, DC[j] - DC[i] - COST, np.nan)); i = j + 1
        else: i += 1
    return rows
# ---------------------------------------------------------------- Mark Fisher
def fisher_acd():
    """ACD (The Logical Trader): opening range = first 15 min; A value = 15 % of the 10-day average range (impl).
    A-up: price above ORH + A and holds there for 7 minutes → long; stop at the OR midpoint; exit close. Mirror for A-down."""
    avgr = pd.Series(RANGE).rolling(10).mean().shift().values; cands = defaultdict(list)
    for i in range(11, N):
        if not VALID[i] or np.isnan(avgr[i]): continue
        orh, orl = h[i, :15].max(), l[i, :15].min(); A = 0.15 * avgr[i]; mid = (orh + orl) / 2
        for side, lvl in ((1, orh + A), (-1, orl - A)):
            run = 0
            for m in range(15, 300):
                inside = c[i, m] > lvl if side == 1 else c[i, m] < lvl
                run = run + 1 if inside else 0
                if run >= 7: cands[i].append((m + 1, side, mid, None, None, True)); break
    return run_seq(cands)
# ---------------------------------------------------------------- John Carter
def carter_squeeze():
    """TTM Squeeze (5m): Bollinger(20,2) inside Keltner(20, 1.5 ATR) for ≥ 6 bars, then it releases → trade the momentum sign
    (close − midline); stop 1.5 ATR; target 2R (impl). """
    g = g5; m20 = sma(g.c, 20); sd = pd.Series(g.c).rolling(20).std().values; a = ATR5
    sq = (m20 + 2 * sd < m20 + 1.5 * a) & (m20 - 2 * sd > m20 - 1.5 * a)
    run = np.zeros(len(sq), int)
    for x in range(1, len(sq)): run[x] = run[x - 1] + 1 if sq[x] else 0
    cands = defaultdict(list)
    for gi in range(21, len(g.c) - 1):
        if g.k(gi) < 4 or g.k(gi) > 72 or sq[gi] or run[gi - 1] < 6: continue
        side = 1 if g.c[gi] > m20[gi] else -1; i = g.day(gi); m = g.next_min(gi); e = o[i, m]
        stp = e - side * 1.5 * a[gi]; cands[i].append((m, side, stp, e + side * 3 * a[gi], None, True))
    return run_seq(cands)
# ---------------------------------------------------------------- Al Brooks
def brooks_h2():
    """High 2 (5m): close above a rising 20 EMA; after a pullback, the SECOND bar whose high exceeds the prior bar's high →
    buy stop 1 tick above that signal bar, stop below its low, target 2R. Mirror (Low 2)."""
    g = g5; cands = defaultdict(list)
    for gi in range(25, len(g.c) - 2):
        if g.k(gi) < 6 or g.k(gi) > 72: continue
        i = g.day(gi)
        for side in (1, -1):
            if (g.c[gi] - E20_5[gi]) * side <= 0 or (E20_5[gi] - E20_5[gi - 3]) * side <= 0: continue
            seg = range(gi - 8, gi + 1)
            pulls = [x for x in seg if ((g.h[x] > g.h[x - 1]) if side == 1 else (g.l[x] < g.l[x - 1]))]
            leg = (g.h[gi - 8:gi].max() > g.h[gi]) if side == 1 else (g.l[gi - 8:gi].min() < g.l[gi])
            if leg and len(pulls) == 2 and pulls[-1] == gi:
                lvl = g.h[gi] + TICK if side == 1 else g.l[gi] - TICK; stp = g.l[gi] - TICK if side == 1 else g.h[gi] + TICK
                f = stop_fill(i, g.next_min(gi), g.next_min(gi) + 5, lvl, side)
                if f: r = abs(f[1] - stp); cands[i].append((f[0], side, stp, f[1] + side * 2 * r, f[1], False))
    return run_seq(cands)
# ---------------------------------------------------------------- ICT
def ict_silver_bullet():
    """Silver Bullet: first FVG formed between 10:00 and 11:00 (1-minute) → limit at the gap's near edge, stop beyond candle 1,
    target 2R."""
    cands = defaultdict(list)
    for i in range(N):
        if not VALID[i]: continue
        for j in range(32, 90):
            if h[i, j - 2] < l[i, j]: side, lvl, stp = 1, l[i, j], l[i, j - 2] - TICK
            elif l[i, j - 2] > h[i, j]: side, lvl, stp = -1, h[i, j], h[i, j - 2] + TICK
            else: continue
            f = limit_fill(i, j + 1, 90, lvl, side)
            if f and (f[1] - stp) * side > 0.5:
                r = abs(f[1] - stp); cands[i].append((f[0], side, stp, f[1] + side * 2 * r, f[1], False))
            break
    return run_seq(cands)
def ict_power_of_3():
    """Power of 3 / AMD: price trades below the 00:00 True Day Open before 10:30 (manipulation) and then a 5-minute bar closes back
    above it → long; stop = low of day; target 2R. Mirror. (Needs the 00:00 open from the 24h frame.)"""
    full = pd.read_pickle(S_PATH + "full1m.pkl"); full = full[~full.index.duplicated()]
    mid = full[(full.index.hour == 0) & (full.index.minute == 0)].open; mid.index = mid.index.normalize().tz_localize(None)
    tdo = mid.reindex(DAYS).values; cands = defaultdict(list); g = g5
    for i in range(N):
        if not VALID[i] or np.isnan(tdo[i]): continue
        for side in (1, -1):
            for k in range(1, 12):
                gi = i * g.nb + k; m = g.next_min(gi)
                swept = (l[i, :m].min() < tdo[i]) if side == 1 else (h[i, :m].max() > tdo[i])
                back = (g.c[gi] > tdo[i] and g.o[gi] <= tdo[i]) if side == 1 else (g.c[gi] < tdo[i] and g.o[gi] >= tdo[i])
                if swept and back:
                    stp = l[i, :m].min() - TICK if side == 1 else h[i, :m].max() + TICK; e = o[i, m]; r = abs(e - stp)
                    cands[i].append((m, side, stp, e + side * 2 * r, None, True)); break
    return run_seq(cands)
def ict_2022():
    """ICT 2022 model: 09:30–11:00, price sweeps the previous day's high/low or the overnight high/low, then displaces the other way
    leaving a 1-minute FVG → limit at the FVG edge, stop at the sweep extreme, target 2R."""
    cands = defaultdict(list)
    for i in range(1, N):
        if not okprev[i]: continue
        lows = [PDL[i], F.onl.values[i]]; highs = [PDH[i], F.onh.values[i]]
        for j in range(2, 90):
            sw_lo = any(l[i, j] < x for x in lows); sw_hi = any(h[i, j] > x for x in highs)
            if not (sw_lo or sw_hi): continue
            side = 1 if sw_lo else -1; ext = l[i, j] if side == 1 else h[i, j]
            for k in range(j + 2, min(j + 30, 120)):
                if side == 1 and h[i, k - 2] < l[i, k]:
                    f = limit_fill(i, k + 1, 150, l[i, k], 1)
                    if f and f[1] - ext > 1: r = f[1] - ext; cands[i].append((f[0], 1, ext - TICK, f[1] + 2 * r, f[1], False))
                    break
                if side == -1 and l[i, k - 2] > h[i, k]:
                    f = limit_fill(i, k + 1, 150, h[i, k], -1)
                    if f and ext - f[1] > 1: r = ext - f[1]; cands[i].append((f[0], -1, ext + TICK, f[1] - 2 * r, f[1], False))
                    break
            break
    return run_seq(cands)
# ---------------------------------------------------------------- Tom DeMark
def demark_td9():
    """TD Sequential setup (15m): 9 consecutive closes below the close 4 bars earlier → buy next bar; stop = lowest low of the
    setup; target 2R (impl). Mirror."""
    g = g15; cands = defaultdict(list); cnt_b = cnt_s = 0
    for gi in range(4, len(g.c) - 1):
        cnt_b = cnt_b + 1 if g.c[gi] < g.c[gi - 4] else 0; cnt_s = cnt_s + 1 if g.c[gi] > g.c[gi - 4] else 0
        if g.k(gi) > 23: continue
        for side, cnt in ((1, cnt_b), (-1, cnt_s)):
            if cnt == 9:
                stp = g.l[gi - 8:gi + 1].min() - TICK if side == 1 else g.h[gi - 8:gi + 1].max() + TICK
                i = g.day(gi); m = g.next_min(gi); e = o[i, m]; r = abs(e - stp)
                cands[i].append((m, side, stp, e + side * 2 * r, None, True))
    return run_seq(cands)
# ---------------------------------------------------------------- Turtles / Seykota (daily swing)
def turtle_20():
    """Turtle System 1: buy a 20-day high break (sell a 20-day low), stop 2 N (20-day ATR), exit a 10-day opposite break. Daily closes."""
    a = atr(DH, DL, DC, 20); rows = []; i = 21
    while i < N - 1:
        side = 1 if DC[i] > DH[i - 20:i].max() else -1 if DC[i] < DL[i - 20:i].min() else 0
        if not side: i += 1; continue
        stp = DC[i] - side * 2 * a[i]; j = i + 1
        while j < N - 1:
            if (side == 1 and (DL[j] <= stp or DC[j] < DL[j - 10:j].min())) or (side == -1 and (DH[j] >= stp or DC[j] > DH[j - 10:j].max())): break
            j += 1
        px = stp if ((side == 1 and DL[j] <= stp) or (side == -1 and DH[j] >= stp)) else DC[j]
        rows.append((j, side * (px - DC[i]) - COST, 2 * a[i])); i = j + 1
    return rows
def seykota_ema():
    """Seykota-style trend following: long when the 15-day EMA is above the 150-day EMA, short when below; flip on cross. Daily."""
    f, s = ema(DC, 15), ema(DC, 150); rows = []; side = 0; e = 0; i0 = 0
    for i in range(151, N):
        want = 1 if f[i] > s[i] else -1
        if want != side:
            if side: rows.append((i, side * (DC[i] - e) - COST, np.nan))
            side, e = want, DC[i]
    return rows
# ---------------------------------------------------------------- Adam Grimes / Trader Dante (failure tests)
def failure_test(g, look, who):
    cands = defaultdict(list)
    for gi in range(look + 1, len(g.c) - 1):
        if g.k(gi) < 2 or g.k(gi) > g.nb - 4: continue
        hi, lo = g.h[gi - look:gi].max(), g.l[gi - look:gi].min(); i = g.day(gi); m = g.next_min(gi)
        if g.h[gi] > hi and g.c[gi] < hi:
            stp = g.h[gi] + TICK; e = o[i, m]; r = stp - e
            if r > 0: cands[i].append((m, -1, stp, e - 2 * r, None, True))
        if g.l[gi] < lo and g.c[gi] > lo:
            stp = g.l[gi] - TICK; e = o[i, m]; r = e - stp
            if r > 0: cands[i].append((m, 1, stp, e + 2 * r, None, True))
    return run_seq(cands)
def grimes_failure(): return failure_test(g5, 20, "Grimes")
def dante_sfp(): return failure_test(g15, 20, "Dante")
# ---------------------------------------------------------------- Brian Shannon / Rayner Teo / FiFi / Umar Ashraf (VWAP & MAs)
def shannon_vwap_pullback():
    """Shannon: price above a rising VWAP, a 5-minute bar dips to VWAP and closes above → long next bar, stop below the bar,
    target 2R. Mirror. Active 10:00–14:00."""
    g = g5; cands = defaultdict(list)
    for i in range(N):
        if not VALID[i]: continue
        vw = vwap_day(i)
        for k in range(6, 54):
            gi = i * g.nb + k; m = g.next_min(gi); vk = vw[m - 1]; vprev = vw[max(m - 31, 0)]
            for side in (1, -1):
                if (vk - vprev) * side <= 0: continue
                touch = (g.l[gi] <= vk < g.c[gi]) if side == 1 else (g.h[gi] >= vk > g.c[gi])
                if touch:
                    stp = g.l[gi] - TICK if side == 1 else g.h[gi] + TICK; e = o[i, m]; r = abs(e - stp)
                    if r > 1: cands[i].append((m, side, stp, e + side * 2 * r, None, True))
    return run_seq(cands)
def teo_pullback():
    """Rayner Teo: trend = price above the 50 EMA on 15-minute bars (continuous); pullback bar touches the 50 EMA and closes above →
    long, stop below the swing low (5 bars), target 2R. Mirror."""
    g = g15; e50 = ema(g.c, 50); cands = defaultdict(list)
    for gi in range(60, len(g.c) - 1):
        if g.k(gi) > 23: continue
        for side in (1, -1):
            if (e50[gi] - e50[gi - 5]) * side <= 0: continue
            touch = (g.l[gi] <= e50[gi] < g.c[gi]) if side == 1 else (g.h[gi] >= e50[gi] > g.c[gi])
            if touch:
                stp = g.l[gi - 4:gi + 1].min() - TICK if side == 1 else g.h[gi - 4:gi + 1].max() + TICK
                i = g.day(gi); m = g.next_min(gi); e = o[i, m]; r = abs(e - stp)
                if r > 1: cands[i].append((m, side, stp, e + side * 2 * r, None, True))
    return run_seq(cands)
def fifi_ema9_vwap():
    """FiFi: 5-minute 9 EMA crosses above VWAP (below for shorts) → enter next bar, stop below the signal bar, target 2R."""
    g = g5; cands = defaultdict(list)
    for i in range(N):
        if not VALID[i]: continue
        vw = vwap_day(i)
        for k in range(3, 72):
            gi = i * g.nb + k; m = g.next_min(gi); v1, v0 = vw[m - 1], vw[m - 6]
            for side in (1, -1):
                if (E9_5[gi] - v1) * side > 0 and (E9_5[gi - 1] - v0) * side <= 0:
                    stp = g.l[gi] - TICK if side == 1 else g.h[gi] + TICK; e = o[i, m]; r = abs(e - stp)
                    if r > 1: cands[i].append((m, side, stp, e + side * 2 * r, None, True))
    return run_seq(cands)
def ashraf_vwap_reclaim():
    """Umar Ashraf: gap-up day, price dips below VWAP in the first hour and a 5-minute bar closes back above it → long,
    stop = low of day, target 2R. Mirror on gap-down days."""
    g = g5; cands = defaultdict(list)
    for i in range(1, N):
        if not okprev[i]: continue
        side = 1 if DO[i] > PDC[i] else -1; vw = vwap_day(i); was = False
        for k in range(1, 12):
            gi = i * g.nb + k; m = g.next_min(gi); vk = vw[m - 1]
            if (g.l[gi] < vk) if side == 1 else (g.h[gi] > vk): was = True
            if was and ((g.c[gi] > vk) if side == 1 else (g.c[gi] < vk)) and k > 1:
                stp = l[i, :m].min() - TICK if side == 1 else h[i, :m].max() + TICK; e = o[i, m]; r = abs(e - stp)
                if r > 1: cands[i].append((m, side, stp, e + side * 2 * r, None, True)); break
    return run_seq(cands)
# ---------------------------------------------------------------- Jim Dalton
def dalton_ib():
    """IB breakout: initial balance = first 60 min; a 5-minute close beyond it → follow; stop at the IB midpoint; target = one IB
    width beyond the IB (Dalton range extension); else close."""
    g = g5; cands = defaultdict(list)
    for i in range(N):
        if not VALID[i]: continue
        hi, lo = h[i, :60].max(), l[i, :60].min(); mid = (hi + lo) / 2; w = hi - lo
        for k in range(12, 66):
            gi = i * g.nb + k; m = g.next_min(gi)
            if g.c[gi] > hi: cands[i].append((m, 1, mid, hi + w, None, True)); break
            if g.c[gi] < lo: cands[i].append((m, -1, mid, lo - w, None, True)); break
    return run_seq(cands)
def value_area(i, pct=0.7, nb=60):
    px, vol = c[i], v[i]; lo_, hi_ = l[i].min(), h[i].max(); edges = np.linspace(lo_, hi_, nb + 1)
    idx = np.clip(np.digitize(px, edges) - 1, 0, nb - 1); hist = np.bincount(idx, weights=vol, minlength=nb)
    poc = int(hist.argmax()); a = b = poc; tot = hist.sum(); s = hist[poc]
    while s < pct * tot and (a > 0 or b < nb - 1):
        up = hist[b + 1] if b < nb - 1 else -1; dn = hist[a - 1] if a > 0 else -1
        if up >= dn: b += 1; s += up
        else: a -= 1; s += dn
    return edges[a], edges[b + 1]
def dalton_80():
    """80 % rule: open outside yesterday's value area, then two consecutive 30-minute periods close inside → trade to the other side
    of the value area; stop beyond the re-entered edge (10 % of VA width); exit at target or close."""
    cands = defaultdict(list)
    for i in range(1, N):
        if not okprev[i]: continue
        val, vah = value_area(i - 1); op = DO[i]
        if not (op > vah or op < val): continue
        side = -1 if op > vah else 1; w = vah - val
        ins = [(val < c[i, (t + 1) * 30 - 1] < vah) for t in range(11)]
        for t in range(1, 10):
            if ins[t] and ins[t - 1]:
                m = (t + 1) * 30; stp = vah + 0.1 * w if side == -1 else val - 0.1 * w; tgt = val if side == -1 else vah
                cands[i].append((m, side, stp, tgt, None, True)); break
    return run_seq(cands)
# ---------------------------------------------------------------- SMB Capital (Bellafiore) / Oliver Velez / Lance Breitstein
def smb_opening_drive():
    """Opening drive: the first 5-minute bar's range > 1.5× its 20-day average and it closes in its top (bottom) 20 % → enter at
    09:35, stop at the bar's other end, target 2R."""
    r0 = h[:, :5].max(1) - l[:, :5].min(1); avg = pd.Series(r0).rolling(20).mean().shift().values; cands = defaultdict(list)
    for i in range(21, N):
        if not VALID[i] or r0[i] < 1.5 * avg[i]: continue
        hi, lo = h[i, :5].max(), l[i, :5].min(); pos = (c[i, 4] - lo) / max(hi - lo, 1e-9)
        side = 1 if pos >= 0.8 else -1 if pos <= 0.2 else 0
        if side: e = o[i, 5]; stp = lo - TICK if side == 1 else hi + TICK; r = abs(e - stp); cands[i].append((5, side, stp, e + side * 2 * r, None, True))
    return run_seq(cands)
def velez_elephant():
    """Velez elephant bar (5m): range > 2× the 20-bar average and body > 70 % of the range → follow next bar, stop at the bar's
    midpoint, target 2R."""
    g = g5; ar = sma(g.h - g.l, 20); cands = defaultdict(list)
    for gi in range(21, len(g.c) - 1):
        if g.k(gi) < 2 or g.k(gi) > 72: continue
        rg = g.h[gi] - g.l[gi]; body = g.c[gi] - g.o[gi]
        if rg > 2 * ar[gi - 1] and abs(body) > 0.7 * rg:
            side = 1 if body > 0 else -1; i = g.day(gi); m = g.next_min(gi); e = o[i, m]; stp = (g.h[gi] + g.l[gi]) / 2; r = abs(e - stp)
            if r > 1 and (e - stp) * side > 0: cands[i].append((m, side, stp, e + side * 2 * r, None, True))
    return run_seq(cands)
def breitstein_capitulation():
    """Lance Breitstein capitulation reversal: price stretched ≥ 1 daily σ below VWAP after a ≥ 0.5 σ drop in 30 min and a 5-minute
    volume spike (≥ 3× the 20-bar average) → long next bar, stop = low − tick, target = VWAP. Mirror."""
    g = g5; av = sma(g.v, 20); cands = defaultdict(list)
    for i in range(N):
        if not VALID[i]: continue
        vw = vwap_day(i); sg = SIG[i] * o[i, 0]
        for k in range(6, 72):
            gi = i * g.nb + k; m = g.next_min(gi)
            if g.v[gi] < 3 * av[gi - 1]: continue
            for side in (1, -1):
                stretch = (vw[m - 1] - g.c[gi]) * side >= sg; drop = (c[i, m - 31] - g.c[gi]) * side >= 0.5 * sg
                if stretch and drop:
                    stp = l[i, m - 30:m].min() - TICK if side == 1 else h[i, m - 30:m].max() + TICK
                    cands[i].append((m, side, stp, vw[m - 1], None, True))
    return run_seq(cands)
# ---------------------------------------------------------------- Bollinger / Wilder / Appel / Kaufman / Bill Williams
def bollinger_mr():
    """Bollinger (5m): close below the lower band (20,2), next bar closes back inside → long, stop = 3-bar low, target = middle band. Mirror."""
    g = g5; m20 = sma(g.c, 20); sd = pd.Series(g.c).rolling(20).std().values; cands = defaultdict(list)
    for gi in range(22, len(g.c) - 1):
        if g.k(gi) < 3 or g.k(gi) > 72: continue
        lo, hi = m20 - 2 * sd, m20 + 2 * sd; i = g.day(gi); m = g.next_min(gi)
        if g.c[gi - 1] < lo[gi - 1] and g.c[gi] > lo[gi]: cands[i].append((m, 1, g.l[gi - 2:gi + 1].min() - TICK, m20[gi], None, True))
        if g.c[gi - 1] > hi[gi - 1] and g.c[gi] < hi[gi]: cands[i].append((m, -1, g.h[gi - 2:gi + 1].max() + TICK, m20[gi], None, True))
    return run_seq(cands)
def wilder_rsi():
    """Wilder RSI(14) on 5m: crosses back above 30 → long (below 70 → short); stop = 10-bar extreme; target 2R (impl)."""
    g = g5; r = rsi(g.c, 14); cands = defaultdict(list)
    for gi in range(15, len(g.c) - 1):
        if g.k(gi) < 3 or g.k(gi) > 72: continue
        i = g.day(gi); m = g.next_min(gi); e = o[i, m]
        if r[gi - 1] < 30 <= r[gi]: stp = g.l[gi - 9:gi + 1].min() - TICK; rr = e - stp; cands[i].append((m, 1, stp, e + 2 * rr, None, True))
        if r[gi - 1] > 70 >= r[gi]: stp = g.h[gi - 9:gi + 1].max() + TICK; rr = stp - e; cands[i].append((m, -1, stp, e - 2 * rr, None, True))
    return run_seq(cands)
def wilder_sar():
    """Parabolic SAR (0.02/0.2) on 15m with ADX(14) > 25: trade each flip; stop = SAR at entry; exit at the opposite flip or close."""
    g = g15; ad, _, _ = adx(g.h, g.l, g.c, 14); n = len(g.c); sar = np.zeros(n); up = True; af = 0.02; ep = g.h[0]; sar[0] = g.l[0]; flips = []
    for x in range(1, n):
        sar[x] = sar[x - 1] + af * (ep - sar[x - 1])
        if up:
            if g.l[x] < sar[x]: up = False; sar[x] = ep; ep = g.l[x]; af = 0.02; flips.append((x, -1))
            elif g.h[x] > ep: ep = g.h[x]; af = min(af + 0.02, 0.2)
        else:
            if g.h[x] > sar[x]: up = True; sar[x] = ep; ep = g.h[x]; af = 0.02; flips.append((x, 1))
            elif g.l[x] < ep: ep = g.l[x]; af = min(af + 0.02, 0.2)
    cands = defaultdict(list)
    for gi, side in flips:
        if g.k(gi) > 23 or ad[gi] <= 25 or gi + 1 >= n: continue
        i = g.day(gi); m = g.next_min(gi); cands[i].append((m, side, sar[gi], None, None, True))
    return run_seq(cands)
def appel_macd():
    """MACD(12,26,9) on 15m, signal-line cross in the direction of the 200 EMA → enter next bar, stop 1.5 ATR, target 2R (impl)."""
    g = g15; mac = ema(g.c, 12) - ema(g.c, 26); sig = ema(mac, 9); e200 = ema(g.c, 200); cands = defaultdict(list)
    for gi in range(201, len(g.c) - 1):
        if g.k(gi) > 23: continue
        for side in (1, -1):
            if (mac[gi] - sig[gi]) * side > 0 and (mac[gi - 1] - sig[gi - 1]) * side <= 0 and (g.c[gi] - e200[gi]) * side > 0:
                i = g.day(gi); m = g.next_min(gi); e = o[i, m]; stp = e - side * 1.5 * ATR15[gi]
                cands[i].append((m, side, stp, e + side * 3 * ATR15[gi], None, True))
    return run_seq(cands)
def kaufman_kama():
    """Kaufman AMA(10,2,30) on 15m: close crosses above a rising KAMA → long until it crosses back (or close); stop 1.5 ATR. Mirror."""
    g = g15; x = g.c; n = 10; er = np.abs(x - np.r_[np.full(n, np.nan), x[:-n]]) / pd.Series(np.abs(np.diff(x, prepend=x[0]))).rolling(n).sum().values
    sc = (np.nan_to_num(er) * (2 / 3 - 2 / 31) + 2 / 31) ** 2; k = np.zeros(len(x)); k[0] = x[0]
    for t in range(1, len(x)): k[t] = k[t - 1] + sc[t] * (x[t] - k[t - 1])
    cands = defaultdict(list)
    for gi in range(31, len(g.c) - 1):
        if g.k(gi) > 23: continue
        for side in (1, -1):
            if (x[gi] - k[gi]) * side > 0 and (x[gi - 1] - k[gi - 1]) * side <= 0 and (k[gi] - k[gi - 2]) * side > 0:
                i = g.day(gi); m = g.next_min(gi); e = o[i, m]
                cands[i].append((m, side, e - side * 1.5 * ATR15[gi], e + side * 3 * ATR15[gi], None, True))
    return run_seq(cands)
def bwilliams_fractal():
    """Bill Williams (15m): price above the Alligator (SMMA 13/8/5) and a confirmed up-fractal → buy stop above the fractal high,
    stop at the Alligator's teeth (SMMA 8), target 2R (impl). Mirror."""
    g = g15; md = (g.h + g.l) / 2
    def smma(x, n): return pd.Series(x).ewm(alpha=1 / n, adjust=False).mean().values
    jaw, teeth, lips = smma(md, 13), smma(md, 8), smma(md, 5); cands = defaultdict(list)
    for gi in range(20, len(g.c) - 1):
        if g.k(gi) > 23 or g.k(gi) < 2: continue
        f = gi - 2; i = g.day(gi)
        for side in (1, -1):
            frac = (g.h[f] == g.h[f - 2:f + 3].max()) if side == 1 else (g.l[f] == g.l[f - 2:f + 3].min())
            align = (g.c[gi] > max(jaw[gi], teeth[gi], lips[gi])) if side == 1 else (g.c[gi] < min(jaw[gi], teeth[gi], lips[gi]))
            if frac and align:
                lvl = g.h[f] + TICK if side == 1 else g.l[f] - TICK; fl = stop_fill(i, g.next_min(gi), g.next_min(gi) + 30, lvl, side)
                if fl and (fl[1] - teeth[gi]) * side > 1: r = abs(fl[1] - teeth[gi]); cands[i].append((fl[0], side, teeth[gi], fl[1] + side * 2 * r, fl[1], False))
    return run_seq(cands)
# ---------------------------------------------------------------- Joe Ross / Rob Hoffman / Steve Nison / Rob Smith
def ross_hook():
    """Ross hook (5m): in an uptrend (20 EMA rising), the first bar that fails to make a new high after a new 10-bar high is the
    hook → buy stop 1 tick above the hook high (next 3 bars), stop at the lowest low since, target 2R. Mirror."""
    g = g5; cands = defaultdict(list)
    for gi in range(12, len(g.c) - 1):
        if g.k(gi) < 4 or g.k(gi) > 72: continue
        i = g.day(gi)
        for side in (1, -1):
            if (E20_5[gi] - E20_5[gi - 3]) * side <= 0: continue
            if side == 1 and g.h[gi - 1] >= g.h[gi - 11:gi - 1].max() and g.h[gi] < g.h[gi - 1]:
                lvl = g.h[gi - 1] + TICK; stp = g.l[gi - 1:gi + 1].min() - TICK
            elif side == -1 and g.l[gi - 1] <= g.l[gi - 11:gi - 1].min() and g.l[gi] > g.l[gi - 1]:
                lvl = g.l[gi - 1] - TICK; stp = g.h[gi - 1:gi + 1].max() + TICK
            else: continue
            f = stop_fill(i, g.next_min(gi), g.next_min(gi) + 15, lvl, side)
            if f: r = abs(f[1] - stp); cands[i].append((f[0], side, stp, f[1] + side * 2 * r, f[1], False))
    return run_seq(cands)
def hoffman_irb():
    """Hoffman Inventory Retracement Bar (5m): 20 EMA rising steeply (≥ 0.1 σ over 5 bars); a bar whose upper wick is ≥ 45 % of its
    range → buy stop above its high (next 5 bars), stop below its low, target 2R (impl: Hoffman scales out). Mirror."""
    g = g5; cands = defaultdict(list)
    for gi in range(25, len(g.c) - 1):
        if g.k(gi) < 4 or g.k(gi) > 72: continue
        i = g.day(gi); sg = SIG[i] * o[i, 0]; rg = max(g.h[gi] - g.l[gi], 1e-9)
        if not np.isfinite(sg): continue
        for side in (1, -1):
            steep = (E20_5[gi] - E20_5[gi - 5]) * side >= 0.1 * sg
            wick = (g.h[gi] - max(g.o[gi], g.c[gi])) / rg >= 0.45 if side == 1 else (min(g.o[gi], g.c[gi]) - g.l[gi]) / rg >= 0.45
            if steep and wick:
                lvl = g.h[gi] + TICK if side == 1 else g.l[gi] - TICK; stp = g.l[gi] - TICK if side == 1 else g.h[gi] + TICK
                f = stop_fill(i, g.next_min(gi), g.next_min(gi) + 25, lvl, side)
                if f: r = abs(f[1] - stp); cands[i].append((f[0], side, stp, f[1] + side * 2 * r, f[1], False))
    return run_seq(cands)
def nison_engulf():
    """Nison: bearish engulfing 15-minute candle within 0.1 σ of yesterday's high → short next bar, stop above it, target 2R. Mirror at PDL."""
    g = g15; cands = defaultdict(list)
    for gi in range(1, len(g.c) - 1):
        k = g.k(gi); i = g.day(gi)
        if k < 1 or k > 23 or not okprev[i]: continue
        sg = SIG[i] * o[i, 0]
        bear = g.c[gi] < g.o[gi] and g.o[gi] >= g.c[gi - 1] and g.c[gi] <= g.o[gi - 1] and g.c[gi - 1] > g.o[gi - 1]
        bull = g.c[gi] > g.o[gi] and g.o[gi] <= g.c[gi - 1] and g.c[gi] >= g.o[gi - 1] and g.c[gi - 1] < g.o[gi - 1]
        m = g.next_min(gi); e = o[i, m]
        if bear and abs(g.h[gi] - PDH[i]) <= 0.1 * sg: stp = g.h[gi] + TICK; r = stp - e; cands[i].append((m, -1, stp, e - 2 * r, None, True))
        if bull and abs(g.l[gi] - PDL[i]) <= 0.1 * sg: stp = g.l[gi] - TICK; r = e - stp; cands[i].append((m, 1, stp, e + 2 * r, None, True))
    return run_seq(cands)
def strat_212():
    """The Strat 2-1-2 continuation (30m): a 2U bar, then an inside bar (1), then price breaks the inside bar's high → long at the
    break, stop at the inside bar's low, target 2R (impl: Strat targets the prior bar high). Mirror with 2D."""
    g = g30; cands = defaultdict(list)
    for gi in range(2, len(g.c) - 1):
        k = g.k(gi)
        if k < 1 or k > 11: continue
        a, b = gi - 1, gi
        inside = g.h[b] <= g.h[a] and g.l[b] >= g.l[a]; i = g.day(gi)
        if not inside: continue
        u = g.h[a] > g.h[a - 1] and g.l[a] >= g.l[a - 1]; d = g.l[a] < g.l[a - 1] and g.h[a] <= g.h[a - 1]
        for side, ok in ((1, u), (-1, d)):
            if not ok: continue
            lvl = g.h[b] + TICK if side == 1 else g.l[b] - TICK; stp = g.l[b] - TICK if side == 1 else g.h[b] + TICK
            f = stop_fill(i, g.next_min(gi), g.next_min(gi) + 30, lvl, side)
            if f: r = abs(f[1] - stp); cands[i].append((f[0], side, stp, f[1] + side * 2 * r, f[1], False))
    return run_seq(cands)
# ---------------------------------------------------------------- Zarattini & Aziz / Gao et al. / Noise area
def zarattini_orb5():
    """Zarattini & Aziz 2023: first 5-minute candle up → long at 09:35 (down → short); stop at the candle's other end; target 10R; else close."""
    cands = defaultdict(list)
    for i in range(N):
        if not VALID[i]: continue
        op, cl = o[i, 0], c[i, 4]
        if cl == op: continue
        side = 1 if cl > op else -1; e = o[i, 5]; stp = l[i, :5].min() - TICK if side == 1 else h[i, :5].max() + TICK; r = abs(e - stp)
        cands[i].append((5, side, stp, e + side * 10 * r, None, True))
    return run_seq(cands)
def gao_momentum():
    """Gao, Han, Li & Zhou: the first half-hour return (prior close → 10:00) predicts the last half-hour → trade 15:30–15:54."""
    rows = []
    for i in range(1, N):
        if not okprev[i]: continue
        side = 1 if c[i, 29] > PDC[i] else -1; r = trade(i, 360, side, None, None)
        if r: rows.append((i, r[0], np.nan))
    return rows
def noise_area():
    """Zarattini, Aziz & Barbon 2024 noise area: first half-hour close outside the band → follow; exit at the close (simplified)."""
    import sys; sys.path.insert(0, os.path.join(H, "../winrate")); import signals as W
    rows = []
    for i, k0, s, _ in W.sig_na_first():
        r = trade(i, k0, s, None, None)
        if r: rows.append((i, r[0], np.nan))
    return rows
# ---------------------------------------------------------------- flexingjoetrades / TTrades / Casper SMC
def joe_orb_ema():
    """flexingjoetrades: 30-minute opening range; a 5-minute close beyond the range AND on the right side of the 5m 20 EMA → enter,
    stop at the other side of the range, target 2R."""
    g = g5; cands = defaultdict(list)
    for i in range(N):
        if not VALID[i]: continue
        hi, lo = h[i, :30].max(), l[i, :30].min()
        for k in range(6, 60):
            gi = i * g.nb + k; m = g.next_min(gi)
            if g.c[gi] > hi and g.c[gi] > E20_5[gi]: e = o[i, m]; r = e - lo; cands[i].append((m, 1, lo - TICK, e + 2 * r, None, True)); break
            if g.c[gi] < lo and g.c[gi] < E20_5[gi]: e = o[i, m]; r = hi - e; cands[i].append((m, -1, hi + TICK, e - 2 * r, None, True)); break
    return run_seq(cands)
def ttrades_fractal():
    """TTrades fractal model (impl): a 60-minute candle sweeps the previous hour's high and closes back below it → in the next hour,
    a 5-minute close below the open of the last up-candle (CISD) → short; stop above the sweep high; target = previous hour's low. Mirror."""
    g60 = G(30); cands = defaultdict(list)   # RTH hours are not aligned to 60; use 30-minute pairs as the HTF candle (impl)
    for i in range(N):
        if not VALID[i]: continue
        H1 = [h[i, t * 60:(t + 1) * 60].max() for t in range(6)]; L1 = [l[i, t * 60:(t + 1) * 60].min() for t in range(6)]
        C1 = [c[i, (t + 1) * 60 - 1] for t in range(6)]
        for t in range(1, 5):
            for side in (-1, 1):
                swept = (H1[t] > H1[t - 1] and C1[t] < H1[t - 1]) if side == -1 else (L1[t] < L1[t - 1] and C1[t] > L1[t - 1])
                if not swept: continue
                ext = H1[t] if side == -1 else L1[t]; tgt = L1[t - 1] if side == -1 else H1[t - 1]
                for m5 in range((t + 1) * 60 + 4, (t + 2) * 60, 5):
                    seg_o = o[i, m5 - 4]; seg_c = c[i, m5]
                    prev = [(o[i, x - 4], c[i, x]) for x in range(m5 - 25, m5 - 4, 5)]
                    ups = [po for po, pc in prev if pc > po] if side == -1 else [po for po, pc in prev if pc < po]
                    if ups and ((seg_c < ups[-1]) if side == -1 else (seg_c > ups[-1])):
                        e = o[i, m5 + 1]
                        if (tgt - e) * side > 0 and (e - ext) * side > 0: cands[i].append((m5 + 1, side, ext + (TICK if side == -1 else -TICK), tgt, None, True))
                        break
    return run_seq(cands)
def casper_ob():
    """Casper SMC (15m): break of structure (close above the last 3-bar pivot high) → limit at the high of the last down candle before
    the move (order block), stop below the OB low, target 2R. Mirror."""
    g = g15; cands = defaultdict(list)
    for gi in range(8, len(g.c) - 1):
        if g.k(gi) > 22 or g.k(gi) < 3: continue
        i = g.day(gi)
        piv_h = [x for x in range(gi - 7, gi - 1) if g.h[x] == g.h[x - 1:x + 2].max()]
        piv_l = [x for x in range(gi - 7, gi - 1) if g.l[x] == g.l[x - 1:x + 2].min()]
        if piv_h and g.c[gi] > g.h[piv_h[-1]] and g.c[gi - 1] <= g.h[piv_h[-1]]:
            ob = next((x for x in range(gi, gi - 8, -1) if g.c[x] < g.o[x]), None)
            if ob is not None:
                f = limit_fill(i, g.next_min(gi), g.next_min(gi) + 90, g.h[ob], 1); stp = g.l[ob] - TICK
                if f and f[1] - stp > 1: r = f[1] - stp; cands[i].append((f[0], 1, stp, f[1] + 2 * r, f[1], False))
        if piv_l and g.c[gi] < g.l[piv_l[-1]] and g.c[gi - 1] >= g.l[piv_l[-1]]:
            ob = next((x for x in range(gi, gi - 8, -1) if g.c[x] > g.o[x]), None)
            if ob is not None:
                f = limit_fill(i, g.next_min(gi), g.next_min(gi) + 90, g.l[ob], -1); stp = g.h[ob] + TICK
                if f and stp - f[1] > 1: r = stp - f[1]; cands[i].append((f[0], -1, stp, f[1] - 2 * r, f[1], False))
    return run_seq(cands)

S_PATH = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
ROSTER = [
    ("Toby Crabel", "ORB stretch", crabel_stretch, "intraday"), ("Toby Crabel", "NR7 + 30m ORB", crabel_nr7, "intraday"),
    ("Larry Williams", "Volatility breakout 0.6×range", williams_volbreak, "intraday"), ("Larry Williams", "OOPS", williams_oops, "intraday"),
    ("Linda Raschke", "Holy Grail (ADX + 20 EMA)", raschke_holy_grail, "intraday"), ("Linda Raschke", "80-20", raschke_8020, "intraday"),
    ("Linda Raschke", "Turtle Soup", raschke_turtle_soup, "intraday"), ("Linda Raschke", "Anti", raschke_anti, "intraday"),
    ("Larry Connors", "RSI(2)", connors_rsi2, "swing"), ("Larry Connors", "Double 7s", connors_double7, "swing"),
    ("Mark Fisher", "ACD", fisher_acd, "intraday"), ("John Carter", "TTM Squeeze", carter_squeeze, "intraday"),
    ("Al Brooks", "High 2 / Low 2", brooks_h2, "intraday"), ("ICT", "Silver Bullet", ict_silver_bullet, "intraday"),
    ("ICT", "Power of 3 (True Day Open)", ict_power_of_3, "intraday"), ("ICT", "2022 model", ict_2022, "intraday"),
    ("Tom DeMark", "TD Sequential 9", demark_td9, "intraday"), ("Richard Dennis (Turtles)", "20-day breakout", turtle_20, "swing"),
    ("Ed Seykota", "EMA 15/150 trend", seykota_ema, "swing"), ("Adam Grimes", "Failure test (5m)", grimes_failure, "intraday"),
    ("Trader Dante", "Swing failure pattern (15m)", dante_sfp, "intraday"), ("Brian Shannon", "VWAP pullback", shannon_vwap_pullback, "intraday"),
    ("Rayner Teo", "50 EMA pullback", teo_pullback, "intraday"), ("FiFi", "9 EMA × VWAP", fifi_ema9_vwap, "intraday"),
    ("Umar Ashraf", "VWAP reclaim on gap days", ashraf_vwap_reclaim, "intraday"), ("Jim Dalton", "Initial balance breakout", dalton_ib, "intraday"),
    ("Jim Dalton", "80 % rule", dalton_80, "intraday"), ("SMB Capital", "Opening drive", smb_opening_drive, "intraday"),
    ("Oliver Velez", "Elephant bar", velez_elephant, "intraday"), ("Lance Breitstein", "Capitulation reversal", breitstein_capitulation, "intraday"),
    ("John Bollinger", "Band re-entry", bollinger_mr, "intraday"), ("J. Welles Wilder", "RSI 30/70", wilder_rsi, "intraday"),
    ("J. Welles Wilder", "Parabolic SAR + ADX", wilder_sar, "intraday"), ("Gerald Appel", "MACD + 200 EMA", appel_macd, "intraday"),
    ("Perry Kaufman", "KAMA cross", kaufman_kama, "intraday"), ("Bill Williams", "Fractal + Alligator", bwilliams_fractal, "intraday"),
    ("Joe Ross", "Ross hook", ross_hook, "intraday"), ("Rob Hoffman", "Inventory retracement bar", hoffman_irb, "intraday"),
    ("Steve Nison", "Engulfing at prior high/low", nison_engulf, "intraday"), ("Rob Smith", "The Strat 2-1-2", strat_212, "intraday"),
    ("Zarattini & Aziz", "5-minute ORB (10R)", zarattini_orb5, "intraday"), ("Gao, Han, Li & Zhou", "Last half-hour momentum", gao_momentum, "intraday"),
    ("Zarattini, Aziz & Barbon", "Noise-area momentum", noise_area, "intraday"), ("flexingjoetrades", "ORB30 + 20 EMA", joe_orb_ema, "intraday"),
    ("TTrades", "Fractal model (sweep + CISD)", ttrades_fractal, "intraday"), ("Casper SMC", "BOS + order block", casper_ob, "intraday"),
]
NOT_TESTABLE = [("Kristjan Kullamägi (Qullamaggie)", "Episodic pivots / breakouts", "single stocks"),
                ("Mark Minervini", "VCP / SEPA", "single stocks"), ("Ross Cameron", "Small-cap momentum", "small-cap stocks"),
                ("William O'Neil", "CAN SLIM", "stocks + fundamentals"), ("Stan Weinstein", "Stage analysis", "weekly stocks"),
                ("Nick Radge", "Weekly momentum rotation", "stock universe"), ("Peter Brandt", "Classical chart patterns", "discretionary multi-week"),
                ("Jesse Livermore", "Pivotal points", "discretionary, not codified")]
