"""Alternative chart constructions built from 1-minute RTH bars, each with its own signal generators.
Every event = (i, m, side, struct_stop_pts): the pattern is COMPLETE at the close of minute m, entry at the open of m+1.
struct_stop_pts = distance from the m+1 open to the chart's own invalidation level (nan if none)."""
import numpy as np, pandas as pd
from core import o, h, l, c, v, N, SIG, VALID, LAST

def _ev(rows): return pd.DataFrame(rows, columns=["i", "m", "side", "sstop"])

def _stop(i, m, side, inval):
    e = o[i, m + 1]; d = (e - inval) * side
    return d if d > 0.5 else np.nan

# ---------------- 1. Renko (close-based, box = k·σ·price, reset daily)
def renko(i, box):
    bricks = []                     # (minute completed, direction, brick_close)
    base = o[i, 0]; d0 = 0
    for m in range(LAST):
        x = c[i, m]
        while True:
            if d0 >= 0 and x >= base + box: base += box; d0 = 1; bricks.append((m, 1, base))
            elif d0 <= 0 and x <= base - box: base -= box; d0 = -1; bricks.append((m, -1, base))
            elif d0 == 1 and x <= base - 2 * box: base -= 2 * box; d0 = -1; bricks.append((m, -1, base))
            elif d0 == -1 and x >= base + 2 * box: base += 2 * box; d0 = 1; bricks.append((m, 1, base))
            else: break
    return bricks

def gen_renko(k, run, mode):
    """mode 'rev_follow': after ≥run bricks one way, first opposite brick → trade the new direction.
       mode 'rev_fade' : same trigger, fade it (bet the trend resumes).
       mode 'pullback' : trend of ≥run bricks, then exactly 1 opposite brick, then trend brick → follow trend."""
    rows = []
    for i in range(N):
        if not VALID[i]: continue
        box = k * SIG[i] * o[i, 0]
        b = renko(i, box)
        for t in range(run, len(b)):
            m, d, px = b[t]
            if m >= 360: break
            prev = [x[1] for x in b[t - run:t]]
            if mode in ("rev_follow", "rev_fade") and all(p == -d for p in prev):
                side = d if mode == "rev_follow" else -d
                inval = px - d * 2 * box if side == d else px + d * box
                rows.append((i, m, side, _stop(i, m, side, inval)))
            if mode == "pullback" and t >= run + 1 and b[t - 1][1] == -d and all(x[1] == d for x in b[t - run - 1:t - 1]):
                rows.append((i, m, d, _stop(i, m, d, b[t - 1][2] - d * box)))
    return _ev(rows)

# ---------------- 2. Heikin-Ashi on n-minute bars
def ha(i, n):
    k = 390 // n
    O = o[i, ::n][:k]; Hh = h[i, :k * n].reshape(k, n).max(1); Ll = l[i, :k * n].reshape(k, n).min(1); C = c[i, n - 1::n][:k]
    hc = (O + Hh + Ll + C) / 4; ho = np.empty(k); ho[0] = (O[0] + C[0]) / 2
    for t in range(1, k): ho[t] = (ho[t - 1] + hc[t - 1]) / 2
    hh = np.maximum(Hh, np.maximum(ho, hc)); hl = np.minimum(Ll, np.minimum(ho, hc))
    return ho, hh, hl, hc

def gen_ha(n, run, mode):
    """'flip_follow': after ≥run same-colour HA bars, first opposite colour bar with NO wick on the trend side → follow it.
       'strong_cont': run of ≥run bars of one colour, all without opposing wick → follow (continuation)."""
    rows = []
    for i in range(N):
        if not VALID[i]: continue
        ho, hh, hl, hc = ha(i, n)
        col = np.sign(hc - ho)
        for t in range(run, len(hc)):
            m = (t + 1) * n - 1
            if m >= 360: break
            if mode == "flip_follow" and col[t] != 0 and all(col[t - run:t] == -col[t]):
                nowick = (hl[t] >= min(ho[t], hc[t]) - 1e-9) if col[t] > 0 else (hh[t] <= max(ho[t], hc[t]) + 1e-9)
                if nowick: rows.append((i, m, int(col[t]), _stop(i, m, int(col[t]), hl[t] if col[t] > 0 else hh[t])))
            if mode == "strong_cont" and col[t] != 0 and all(col[t - run + 1:t + 1] == col[t]):
                ok = all((hl[x] >= min(ho[x], hc[x]) - 1e-9) if col[t] > 0 else (hh[x] <= max(ho[x], hc[x]) + 1e-9) for x in range(t - run + 1, t + 1))
                if ok and (t == run or col[t - run] != col[t]):
                    rows.append((i, m, int(col[t]), _stop(i, m, int(col[t]), hl[t] if col[t] > 0 else hh[t])))
    return _ev(rows)

# ---------------- 3. Range bars (each bar spans exactly r points of range)
def range_bars(i, r):
    bars = []; hi = lo = o[i, 0]; op = o[i, 0]
    for m in range(LAST):
        hi = max(hi, h[i, m]); lo = min(lo, l[i, m])
        if hi - lo >= r:
            cl = c[i, m]; bars.append((m, op, hi, lo, cl)); op = cl; hi = lo = cl
    return bars

def gen_range(k, run, mode):
    """'exhaust_fade': ≥run consecutive same-direction range bars, then a bar closing opposite past the prior bar's open → follow reversal.
       'three_push': three consecutive higher highs/lower lows with shrinking bodies → fade."""
    rows = []
    for i in range(N):
        if not VALID[i]: continue
        b = range_bars(i, k * SIG[i] * o[i, 0])
        dirs = [np.sign(x[4] - x[1]) for x in b]
        for t in range(run + 1, len(b)):
            m = b[t][0]
            if m >= 360: break
            if mode == "exhaust_fade" and all(dd == -dirs[t] for dd in dirs[t - run:t]) and dirs[t] != 0:
                if (dirs[t] > 0 and b[t][4] > b[t - 1][1]) or (dirs[t] < 0 and b[t][4] < b[t - 1][1]):
                    side = int(dirs[t]); rows.append((i, m, side, _stop(i, m, side, b[t][3] if side > 0 else b[t][2])))
            if mode == "three_push" and t >= 3:
                x1, x2, x3 = b[t - 2], b[t - 1], b[t]
                bod = [abs(x[4] - x[1]) for x in (x1, x2, x3)]
                if x3[2] > x2[2] > x1[2] and bod[2] < bod[1] < bod[0]:
                    rows.append((i, m, -1, _stop(i, m, -1, x3[2])))
                if x3[3] < x2[3] < x1[3] and bod[2] < bod[1] < bod[0]:
                    rows.append((i, m, 1, _stop(i, m, 1, x3[3])))
    return _ev(rows)

# ---------------- 4. Volume bars (each bar = 1/q of yesterday's RTH volume) — absorption
def gen_volbars(q, z, mode):
    """Volume clock. 'absorb_fade': a volume bar whose range is < z × median range of the previous 10 volume bars,
       arriving after the last 3 volume bars all moved one way → fade that move (passive absorption).
       'ignite_follow': range > z × median and close at its extreme → follow."""
    rows = []
    for i in range(1, N):
        if not VALID[i]: continue
        unit = v[i - 1].sum() / q
        if unit <= 0: continue
        bars = []; acc = 0; op = o[i, 0]; hi = -1e18; lo = 1e18
        for m in range(LAST):
            acc += v[i, m]; hi = max(hi, h[i, m]); lo = min(lo, l[i, m])
            if acc >= unit:
                bars.append((m, op, hi, lo, c[i, m])); acc = 0; op = c[i, m]; hi = -1e18; lo = 1e18
        for t in range(10, len(bars)):
            m, bo, bh, bl, bc = bars[t]
            if m >= 360: break
            rngs = [x[2] - x[3] for x in bars[t - 10:t]]; med = np.median(rngs); rg = bh - bl
            mv = [np.sign(x[4] - x[1]) for x in bars[t - 3:t]]
            if mode == "absorb_fade" and rg < z * med and abs(sum(mv)) == 3:
                side = -int(mv[0]); inval = bh if side < 0 else bl
                rows.append((i, m, side, _stop(i, m, side, inval + (0 if side < 0 else 0))))
            if mode == "ignite_follow" and rg > z * med:
                if bc >= bh - 0.1 * rg: rows.append((i, m, 1, _stop(i, m, 1, bl)))
                elif bc <= bl + 0.1 * rg: rows.append((i, m, -1, _stop(i, m, -1, bh)))
    return _ev(rows)

# ---------------- 5. Market profile of the previous RTH day (volume-at-price from 1-minute closes)
def value_area(i, pct=0.7, nb=60):
    px, vol = c[i], v[i]
    lo_, hi_ = l[i].min(), h[i].max()
    edges = np.linspace(lo_, hi_, nb + 1); idx = np.clip(np.digitize(px, edges) - 1, 0, nb - 1)
    hist = np.bincount(idx, weights=vol, minlength=nb)
    poc = int(hist.argmax()); a = b = poc; tot = hist.sum(); s = hist[poc]
    while s < pct * tot and (a > 0 or b < nb - 1):
        up = hist[b + 1] if b < nb - 1 else -1; dn = hist[a - 1] if a > 0 else -1
        if up >= dn: b += 1; s += up
        else: a -= 1; s += dn
    return edges[a], edges[b + 1], (edges[poc] + edges[poc + 1]) / 2

def gen_profile(mode, accept_min):
    """'eighty': open outside yesterday's value area, then price is accepted back inside for accept_min consecutive
       minutes (closes inside) → trade toward the other side of the VA (Dalton 80 % rule). Stop beyond the VA edge re-entered.
       'reject': open inside VA, price breaks out then returns inside within accept_min minutes → fade the break."""
    rows = []
    for i in range(1, N):
        if not VALID[i] or D_roll[i]: continue
        val, vah, poc = value_area(i - 1)
        op = o[i, 0]
        if mode == "eighty" and (op > vah or op < val):
            side = -1 if op > vah else 1; edge = vah if side == -1 else val
            inside = (c[i] < vah) & (c[i] > val)
            run = 0
            for m in range(0, 300):
                run = run + 1 if inside[m] else 0
                if run >= accept_min:
                    rows.append((i, m, side, _stop(i, m, side, edge + (-side) * 0.0 + (-side) * 0.1 * (vah - val)))); break
        if mode == "reject" and val < op < vah:
            for m in range(5, 300):
                if h[i, m] > vah + 0.05 * (vah - val):
                    back = next((x for x in range(m + 1, min(m + 1 + accept_min, 300)) if c[i, x] < vah), None)
                    if back is not None: rows.append((i, back, -1, _stop(i, back, -1, h[i, m:back + 1].max())))
                    break
                if l[i, m] < val - 0.05 * (vah - val):
                    back = next((x for x in range(m + 1, min(m + 1 + accept_min, 300)) if c[i, x] > val), None)
                    if back is not None: rows.append((i, back, 1, _stop(i, back, 1, l[i, m:back + 1].min())))
                    break
    return _ev(rows)

# ---------------- 6. Point & Figure (box b, 3-box reversal) on 1-minute closes
def gen_pnf(k, mode):
    """'double_break': X column exceeds the previous X column top (double-top buy) / O below previous O (double-bottom sell) → follow.
       'triple_break': exceeds the two previous same-type column extremes (equal tops) → follow. Stop = 3-box reversal level."""
    rows = []
    for i in range(N):
        if not VALID[i]: continue
        box = k * SIG[i] * o[i, 0]; cols = []      # [dir, top, bottom]
        cur = None; fired = set()
        for m in range(LAST):
            x = c[i, m]
            if cur is None:
                cur = [1, x, x] if x >= o[i, 0] else [-1, x, x]; continue
            if cur[0] == 1:
                if x >= cur[1] + box: cur[1] = cur[1] + box * np.floor((x - cur[1]) / box)
                elif x <= cur[1] - 3 * box: cols.append(cur); cur = [-1, cur[1] - box, cur[1] - box * np.floor((cur[1] - x) / box)]
            else:
                if x <= cur[2] - box: cur[2] = cur[2] - box * np.floor((cur[2] - x) / box)
                elif x >= cur[2] + 3 * box: cols.append(cur); cur = [1, cur[2] + box * np.floor((x - cur[2]) / box), cur[2] + box]
            if m >= 360: continue
            same = [cc for cc in cols if cc[0] == cur[0]]
            need = 1 if mode == "double_break" else 2
            if len(same) >= need and (len(cols), cur[0]) not in fired:
                if cur[0] == 1 and all(cur[1] > cc[1] for cc in same[-need:]):
                    if need == 1 or abs(same[-1][1] - same[-2][1]) <= box:
                        fired.add((len(cols), 1)); rows.append((i, m, 1, _stop(i, m, 1, cur[1] - 3 * box)))
                if cur[0] == -1 and all(cur[2] < cc[2] for cc in same[-need:]):
                    if need == 1 or abs(same[-1][2] - same[-2][2]) <= box:
                        fired.add((len(cols), -1)); rows.append((i, m, -1, _stop(i, m, -1, cur[2] + 3 * box)))
    return _ev(rows)

# ---------------- 7. Three-line break on n-minute closes
def gen_tlb(n, run):
    """After ≥run consecutive lines one way, a reversal line (close beyond the extreme of the last 3 lines) → follow the reversal."""
    rows = []
    for i in range(N):
        if not VALID[i]: continue
        C = c[i, n - 1::n][:390 // n]; lines = []   # (dir, lo, hi, minute)
        last = o[i, 0]; lines.append((0, min(last, C[0]), max(last, C[0]), n - 1))
        for t in range(1, len(C)):
            m = (t + 1) * n - 1; x = C[t]; d, lo_, hi_, _ = lines[-1]
            recent = lines[-3:]
            if x > hi_ and (d >= 0 or x > max(r[2] for r in recent)):
                rev = d == -1; lines.append((1, hi_, x, m))
            elif x < lo_ and (d <= 0 or x < min(r[1] for r in recent)):
                rev = d == 1; lines.append((-1, x, lo_, m))
            else: continue
            if m >= 360: break
            if rev and len(lines) > run + 1 and all(r[0] == -lines[-1][0] for r in lines[-run - 1:-1]):
                s = lines[-1][0]; rows.append((i, m, s, _stop(i, m, s, lines[-1][1] if s > 0 else lines[-1][2])))
    return _ev(rows)

# ---------------- 8. Approximate delta (close-location × volume) divergence — NOT true order flow
def gen_delta(n, look):
    """On n-minute bars: price makes a new `look`-bar high while cumulative approx-delta does not (or vice versa) → fade."""
    rows = []
    for i in range(N):
        if not VALID[i]: continue
        k = 390 // n
        Hh = h[i, :k * n].reshape(k, n).max(1); Ll = l[i, :k * n].reshape(k, n).min(1)
        rng = np.maximum(h[i] - l[i], 1e-9); clv = ((c[i] - l[i]) - (h[i] - c[i])) / rng
        dl = (clv * v[i])[:k * n].reshape(k, n).sum(1); cd = np.cumsum(dl)
        for t in range(look, k):
            m = (t + 1) * n - 1
            if m >= 360: break
            if Hh[t] > Hh[t - look:t].max() and cd[t] < cd[t - look:t].max():
                rows.append((i, m, -1, _stop(i, m, -1, Hh[t])))
            if Ll[t] < Ll[t - look:t].min() and cd[t] > cd[t - look:t].min():
                rows.append((i, m, 1, _stop(i, m, 1, Ll[t])))
    return _ev(rows)

# ---------------- 9. Permutation entropy regime (order-pattern complexity of 1-minute returns)
def perm_entropy(x, d=3):
    if len(x) < d + 5: return np.nan
    pats = np.array([np.argsort(x[t:t + d]) @ (d ** np.arange(d)) for t in range(len(x) - d + 1)])
    p = np.bincount(pats) ; p = p[p > 0] / p.sum()
    return -(p * np.log(p)).sum() / np.log(6)

def gen_entropy(win, thr, mode):
    """Every 15 minutes: entropy of the last `win` 1-minute closes. Low entropy (< thr) = orderly market →
       'follow' the last-window direction, or 'fade' it."""
    rows = []
    for i in range(N):
        if not VALID[i]: continue
        for m in range(win, 360, 15):
            x = c[i, m - win + 1:m + 1]; pe = perm_entropy(x)
            if pe < thr:
                d = int(np.sign(x[-1] - x[0]))
                if d == 0: continue
                side = d if mode == "follow" else -d
                ext = x.min() if side == 1 else x.max()
                rows.append((i, m, side, _stop(i, m, side, l[i, m - win + 1:m + 1].min() if side == 1 else h[i, m - win + 1:m + 1].max())))
    return _ev(rows)

import core as _core
D_roll = _core.D.roll
