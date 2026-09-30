"""SP Model v8 — rewritten from ../TRADER_BRAIN.md (rules as of v7.5). Mirrors pine/sp_model_v8.pine.

Every bar is evaluated at its close. An order placed at a close works during the next bar; fills and exits inside
a bar follow TradingView's broker emulator (open → nearer extreme → other extreme → close).

Each London level is a `Side` (+1 = London high, -1 = London low). A side carries its sweep, the extreme made
since the sweep, S1's failure flag and the S2 round machine. S1 trades against the sweep, S2 with it.

Usage:
    python sp_v8.py              # last 60 days of NQ=F from Yahoo
    python sp_v8.py data.csv     # NinjaTrader / TradingView / CSV export (see data.py)
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

TZ = "America/New_York"
TICK = 0.25
LEVELS = {0.5: (0.702, 0.267), 0.588: (0.816, 0.36)}   # entry → (stop, target)   [T]
LDN_END, WIN_START, WIN_END = 360, 570, 840              # 06:00, 09:30, 14:00 in minutes (NY)


@dataclass
class Params:
    va_floor: float = 0.41          # [T] below → no trade
    va_mid: float = 0.5             # [T] 0.41–0.5 → 0.5 entry; 0.5–0.588 → 0.588 entry
    va_ceiling: float = 0.588       # [T] above → no trade
    vp_rows: int = 999              # [T]
    va_pct: float = 0.70            # [T]
    max_fails: int = 3              # [T] three 1.0 breaks end the session
    dead_waits_highest: bool = True  # [T by example, OPEN] a cancelled S2 round waits for the most extreme swing
    use_s1: bool = True
    use_s2: bool = True
    use_s3: bool = True
    ldn_min_bars: int = 60          # [IMPL] London range needs ≥ 60 of its 72 bars
    qty: int = 1                    # [IMPL] fixed size
    check: bool = True              # invariants raise InvariantError


class InvariantError(AssertionError):
    pass


# ── pure helpers ──────────────────────────────────────────────────────────
def tick(x):
    """Nearest tick, ties up — like Pine's math.round_to_mintick."""
    return math.floor(x / TICK + 0.5 + 1e-9) * TICK


def fib(a1, a0, d, lvl):
    """1.0 = a1 (where the move started), 0 = a0 (where it got to). d = 1 long, -1 short."""
    rng = abs(a1 - a0)
    return a0 + rng * lvl if d == -1 else a0 - rng * lvl


def beyond(x, lvl, sign):
    """Strictly beyond `lvl` in the direction `sign` (+1 above, -1 below)."""
    return x > lvl if sign == 1 else x < lvl


def choose_level(scen, va, p):
    if scen == 3:
        return 0.5                                          # [T] S3: 0.5 only, no value area
    if va is None or va > p.va_ceiling or va < p.va_floor:
        return 0.0
    return 0.588 if va >= p.va_mid else 0.5


def value_area(H, L, V, start, end, lo, hi, rows, pct):
    """Fixed-range volume profile over bars [start, end] and prices [lo, hi] → (VAH, VAL)."""
    if hi <= lo:
        return None
    rh = (hi - lo) / rows
    diff = [0.0] * (rows + 1)
    for i in range(start, end + 1):
        if H[i] > lo and L[i] < hi:
            i0 = max(0, min(rows - 1, math.floor((L[i] - lo) / rh)))
            i1 = max(0, min(rows - 1, math.floor((H[i] - lo) / rh)))
            per = V[i] / (i1 - i0 + 1)
            diff[i0] += per
            diff[i1 + 1] -= per
    bins, run, tot, poc, pocv = [], 0.0, 0.0, 0, -1.0
    for k in range(rows):
        run += diff[k]
        bins.append(run)
        tot += run
        if run > pocv:
            pocv, poc = run, k
    if tot <= 0:
        return None
    acc, up, dn = bins[poc], poc, poc
    while acc < tot * pct and (up < rows - 1 or dn > 0):
        vu = bins[up + 1] if up < rows - 1 else -1.0
        vd = bins[dn - 1] if dn > 0 else -1.0
        if vu >= vd:
            up, acc = up + 1, acc + vu
        else:
            dn, acc = dn - 1, acc + vd
    return lo + (up + 1) * rh, lo + dn * rh


def walk_bar(o, h, l, c, d, entry=None, stop=None, tgt=None, in_pos=False):
    """TradingView broker emulator. Returns (fill | None, (reason, price) | None)."""
    fill = None
    if not in_pos and entry is not None and ((o <= entry) if d == 1 else (o >= entry)):
        fill, in_pos = o, True                              # gap through the limit: filled at the open
    if in_pos:
        if (o <= stop) if d == 1 else (o >= stop):
            return fill, ("stop", o)
        if (o >= tgt) if d == 1 else (o <= tgt):
            return fill, ("target", o)
    path = [o, h, l, c] if (h - o) <= (o - l) else [o, l, h, c]
    cur = o
    for nxt in path[1:]:
        while True:
            up = nxt > cur
            lv = []
            if not in_pos and entry is not None and up == (d == -1):
                lv.append(("entry", entry))
            if in_pos:
                lv.append(("stop", stop) if up == (d == -1) else ("target", tgt))
            hit = [(n, x) for n, x in lv if (cur < x <= nxt if up else nxt <= x < cur)]
            if not hit:
                break
            n, x = min(hit, key=lambda z: abs(z[1] - cur))
            if n == "entry":
                fill, in_pos, cur = x, True, x
                continue
            return fill, (n, x)
        cur = nxt
    return fill, None


# ── state ─────────────────────────────────────────────────────────────────
@dataclass
class Side:
    """One London level. sign +1 = the high (S1 short / S2 long), -1 = the low (S1 long / S2 short)."""
    sign: int
    sweep_bar: int | None = None
    sweep_in_window: bool = False
    ext: float | None = None            # extreme since the sweep (the consumed level's new reference)
    ext_bar: int | None = None
    s1_failed: bool = False
    # S2 rounds
    ref: float | None = None            # pre-open sweep: post-sweep extreme at the first two-candle pullback
    s2_open: bool = False
    round: int = 0                      # +1 on every break
    break_bar: int | None = None
    level: float | None = None          # the level this round broke
    cancelled: bool = False             # price came back through `level` before the trigger
    used: int = 0                       # round that already produced its setup
    swing: float | None = None          # swing to break for the next round

    @property
    def name(self):
        return "LONG" if self.sign == 1 else "SHORT"   # S2 direction on this side

    def open_round(self, i, level):
        self.s2_open, self.break_bar, self.level = True, i, level
        self.round += 1
        self.swing, self.cancelled = None, False


@dataclass
class Day:
    ldn_hi: float | None = None
    ldn_lo: float | None = None
    ldn_n: int = 0
    sides: dict = field(default_factory=lambda: {1: Side(1), -1: Side(-1)})
    s3_dead: bool = False
    fails: int = 0
    trades: int = 0
    capped: bool = False


@dataclass
class Result:
    trades: list = field(default_factory=list)
    setups: list = field(default_factory=list)
    events: list = field(default_factory=list)
    funnel: Counter = field(default_factory=Counter)


# ── the model ─────────────────────────────────────────────────────────────
def run(df: pd.DataFrame, p: Params = Params()) -> Result:
    T = list(df.index)
    O, H, L, C, V = (list(df[k]) for k in ("open", "high", "low", "close", "volume"))
    res = Result()
    day, D = None, Day()
    setup = order = pos = None

    def log(i, msg):
        res.events.append(f"{T[i]:%Y-%m-%d %H:%M} {msg}")

    def check(ok, i, msg):
        if p.check and not ok:
            raise InvariantError(f"{T[i]:%Y-%m-%d %H:%M}: {msg}")

    def extreme_since(bar, i, d):
        """fib 0 counts forward from the 1.0 bar only [T]; ties keep the earliest bar."""
        if d == -1:
            k = min(range(bar, i + 1), key=lambda q: (L[q], q))
            return L[k], k
        k = max(range(bar, i + 1), key=lambda q: (H[q], -q))
        return H[k], k

    def end_setup(i, why, broke=False):
        nonlocal setup, order
        s = setup
        s["outcome"] = why
        res.funnel[f"S{s['scen']} {why}"] += 1
        log(i, f"S{s['scen']} {'LONG' if s['d'] == 1 else 'SHORT'} dead: {why}")
        if broke:                                           # a 1.0 break is a failed setup [T]
            if s["scen"] == 1:                              # S1 broke its 1.0 → S2 opens on that side [T]
                sd = D.sides[s["side"]]
                sd.s1_failed = True
                sd.open_round(i, s["a1"])
            elif s["scen"] == 3:
                D.s3_dead = True                            # [IMPL]
            D.fails += 1
            if D.fails >= p.max_fails:
                D.capped = True
                log(i, f"{p.max_fails} failed setups — stop for the session")
        setup = order = None

    for i in range(len(T)):
        t = T[i]
        mn = t.hour * 60 + t.minute                         # bar OPEN time, NY
        o, h, l, c = O[i], H[i], L[i], C[i]
        closed = None

        # 1 ── the order placed at the previous close works during this bar
        if order is not None and pos is None:
            d = order["d"]
            fill, closed = walk_bar(o, h, l, c, d, entry=order["entry"], stop=order["stop"], tgt=order["tgt"])
            if fill is not None:
                check((fill <= order["entry"]) if d == 1 else (fill >= order["entry"]), i,
                      f"fill {fill} worse than limit {order['entry']}")
                pos = dict(order, fill=fill, time=t, scen=setup["scen"], a1=setup["a1"], a0=setup["a0"])
                D.trades += 1                               # the first fill ends the day [T]
                setup["outcome"] = "filled"
                setup = order = None
        elif pos is not None:
            _, closed = walk_bar(o, h, l, c, pos["d"], stop=pos["stop"], tgt=pos["tgt"], in_pos=True)

        # 2 ── new day at 00:00 NY
        if t.date() != day:
            if pos is not None and closed is None:
                closed = ("day reset", c)
            day, D = t.date(), Day()
            setup = order = None

        # 3 ── London range 00:00–06:00 [T]
        if mn < LDN_END:
            D.ldn_hi = h if D.ldn_hi is None else max(D.ldn_hi, h)
            D.ldn_lo = l if D.ldn_lo is None else min(D.ldn_lo, l)
            D.ldn_n += 1
        valid = D.ldn_hi is not None and D.ldn_n >= p.ldn_min_bars
        in_win = WIN_START <= mn < WIN_END

        # 4 ── sweeps from 06:00: wick, exact touch counts, each level consumed once [T]
        if mn >= LDN_END and valid:
            for sd, px, lvl in ((D.sides[1], h, D.ldn_hi), (D.sides[-1], l, D.ldn_lo)):
                if sd.sweep_bar is not None:
                    if beyond(px, sd.ext, sd.sign):
                        sd.ext, sd.ext_bar = px, i
                elif px == lvl or beyond(px, lvl, sd.sign):
                    sd.sweep_bar, sd.sweep_in_window, sd.ext, sd.ext_bar = i, in_win, px, i
                    log(i, f"London {'high' if sd.sign == 1 else 'low'} swept")

        # 5 ── position: flat at 14:00 [T]; record the trade
        if pos is not None and closed is None and mn + 5 >= WIN_END:
            closed = ("14:00", c)
        if pos is not None and closed is not None:
            why, px = closed
            d = pos["d"]
            r = ((px - pos["fill"]) if d == 1 else (pos["fill"] - px)) / abs(pos["stop"] - pos["entry"])
            res.trades.append(dict(entry_time=pos["time"], exit_time=t, scenario=pos["scen"], side="LONG" if d == 1 else "SHORT",
                                   level=pos["level"], va=pos["va"], entry=pos["entry"], fill=pos["fill"], stop=pos["stop"],
                                   target=pos["tgt"], a1=pos["a1"], a0=pos["a0"], exit=why, exit_price=px, r=round(r, 3)))
            log(i, f"EXIT {why} R={r:+.2f}")
            pos = None

        # 6 ── armed setup: 1.0 break (wick, strictly beyond) → dead; 14:00 → dead; else fib 0 extends [T]
        if setup is not None:
            s = setup
            if beyond(h if s["d"] == -1 else l, s["a1"], -s["d"]):
                end_setup(i, "1.0 broken", broke=True)
            elif mn + 5 >= WIN_END:
                end_setup(i, "14:00")
            elif beyond(l if s["d"] == -1 else h, s["a0"], s["d"]):
                s["a0"], s["a0_bar"] = (l if s["d"] == -1 else h), i

        same_day = i > 0 and T[i - 1].date() == t.date()
        two_bull = same_day and c >= o and C[i - 1] >= O[i - 1]          # doji counts both ways [T]
        two_bear = same_day and c <= o and C[i - 1] <= O[i - 1]

        # 7 ── S2 rounds [T]: opened by S1's 1.0 break (step 6), by a pre-open sweep's reference break, or by a
        #      break of the 3-bar swing formed after the last break. A wick back through the broken level before
        #      the round's trigger cancels it (v7.5); a cancelled round waits for the most extreme swing since.
        if valid:
            for sd, pullback in ((D.sides[1], two_bear), (D.sides[-1], two_bull)):
                if sd.sweep_bar is None:
                    continue
                toward = h if sd.sign == 1 else l            # price in the S2 direction
                back = l if sd.sign == 1 else h
                if sd.s2_open:
                    if not sd.cancelled and sd.round != sd.used and i > sd.break_bar and beyond(back, sd.level, -sd.sign):
                        sd.cancelled = True
                        log(i, f"S2 {sd.name} round {sd.round} dead (back through {sd.level})")
                    j = i - 1                                # 3-bar pivot at j, formed after the break
                    if j > sd.break_bar and T[j - 1].date() == t.date():
                        pj, pa, pb = (H[j], H[j - 1], H[i]) if sd.sign == 1 else (L[j], L[j - 1], L[i])
                        if beyond(pj, pa, sd.sign) and beyond(pj, pb, sd.sign):
                            if p.dead_waits_highest and sd.cancelled and sd.swing is not None:
                                sd.swing = max(sd.swing, pj) if sd.sign == 1 else min(sd.swing, pj)
                            else:
                                sd.swing = pj
                    if sd.swing is not None and beyond(toward, sd.swing, sd.sign):
                        sd.open_round(i, sd.swing)
                        log(i, f"S2 {sd.name} re-opens (swing {sd.level} broken, round {sd.round})")
                elif not sd.sweep_in_window:                 # pre-open sweep: reference = first two-candle pullback
                    if sd.ref is None:
                        if pullback and i - 1 >= sd.sweep_bar:
                            sd.ref = sd.ext
                    elif beyond(toward, sd.ref, sd.sign):
                        sd.open_round(i, sd.ref)
                        log(i, f"S2 {sd.name} opens (pre-open reference broken)")

        # 8 ── triggers: second candle closes 09:30–14:00 [T]; not after a fill or the 3-fail cap
        if valid and pos is None and D.trades == 0 and not D.capped and WIN_START <= mn + 5 < WIN_END:
            cand = None
            hi_sd, lo_sd = D.sides[1], D.sides[-1]
            if hi_sd.sweep_bar is not None and lo_sd.sweep_bar is not None:
                # both taken → S3 only, against the second sweep; 1.0 = first sweep's extreme [T]
                if p.use_s3 and not D.s3_dead and hi_sd.sweep_bar != lo_sd.sweep_bar \
                        and i - 1 >= max(hi_sd.sweep_bar, lo_sd.sweep_bar):
                    if lo_sd.sweep_bar > hi_sd.sweep_bar and two_bull:
                        cand = dict(scen=3, d=-1, side=0, a1=hi_sd.ext, a1_bar=hi_sd.ext_bar)
                    elif hi_sd.sweep_bar > lo_sd.sweep_bar and two_bear:
                        cand = dict(scen=3, d=1, side=0, a1=lo_sd.ext, a1_bar=lo_sd.ext_bar)
            else:
                for sd in (hi_sd, lo_sd):
                    if sd.sweep_bar is None or cand:
                        continue
                    s1_trig = two_bear if sd.sign == 1 else two_bull
                    s2_trig = two_bull if sd.sign == 1 else two_bear
                    if p.use_s1 and sd.sweep_in_window and not sd.s1_failed and s1_trig and i - 1 >= sd.sweep_bar:
                        # S1 SHORT: highest point since the sweep; S1 LONG: low of the first trigger candle [T]
                        a1, a1_bar = (sd.ext, sd.ext_bar) if sd.sign == 1 else (L[i - 1], i - 1)
                        cand = dict(scen=1, d=-sd.sign, side=sd.sign, a1=a1, a1_bar=a1_bar)
                    elif p.use_s2 and sd.s2_open and not sd.cancelled and sd.round != sd.used \
                            and s2_trig and i >= sd.break_bar:
                        # S2: the far extreme of the first trigger candle [T]; the pair may start before the break [IMPL]
                        a1 = L[i - 1] if sd.sign == 1 else H[i - 1]
                        cand = dict(scen=2, d=sd.sign, side=sd.sign, a1=a1, a1_bar=i - 1, round=sd.round)
            # [IMPL] the second candle already traded beyond the first candle's extreme → 1.0 broken, no setup
            if cand is not None and cand["a1_bar"] == i - 1 and beyond(h if cand["d"] == -1 else l, cand["a1"], -cand["d"]):
                res.funnel[f"S{cand['scen']} trigger broke its own 1.0"] += 1
                cand = None
            # [IMPL] a later trigger of the same scenario, direction and round keeps the first anchor
            if cand is not None and not (setup is not None and setup["scen"] == cand["scen"] and setup["d"] == cand["d"]
                                         and setup.get("round") == cand.get("round")):
                a0, a0_bar = extreme_since(cand["a1_bar"], i, cand["d"])
                leg = abs(cand["a1"] - a0)
                if leg > 0:
                    if setup is not None:
                        setup["outcome"] = "replaced"
                        res.funnel[f"S{setup['scen']} replaced"] += 1
                    if cand["scen"] == 2:
                        D.sides[cand["side"]].used = cand["round"]      # one setup per round [IMPL]
                    setup = dict(cand, a0=a0, a0_bar=a0_bar, time=t, trig_bar=i, leg_trig=leg, a1_at_arm=cand["a1"], outcome=None)
                    res.setups.append(setup)
                    order = None
                    log(i, f"S{cand['scen']} {'LONG' if cand['d'] == 1 else 'SHORT'} armed a1 {cand['a1']} a0 {a0} leg {leg:.2f}")

        # 9 ── place / move the limit; fills only 09:30–14:00 [T], last placement at the 13:50 close [IMPL]
        order = None
        if setup is not None and pos is None and WIN_START - 5 <= mn and mn + 5 < WIN_END:
            s = setup
            check(s["a1"] == s["a1_at_arm"], i, "a1 moved after it was set")
            va = None
            if s["scen"] != 3:
                lo, hi = min(s["a1"], s["a0"]), max(s["a1"], s["a0"])
                vv = value_area(H, L, V, s["a1_bar"], i, lo, hi, p.vp_rows, p.va_pct)
                if vv is not None:
                    vah, val = vv
                    va = (vah - s["a0"]) / (hi - lo) if s["d"] == -1 else (s["a0"] - val) / (hi - lo)
            s["last_va"] = va
            lvl = choose_level(s["scen"], va, p)
            if lvl > 0:
                sl, tl = LEVELS[lvl]
                e, st, tg = (tick(fib(s["a1"], s["a0"], s["d"], x)) for x in (lvl, sl, tl))
                check((tg < e < st) if s["d"] == -1 else (st < e < tg), i, f"bracket on wrong side {st} {e} {tg}")
                if not ((c >= e) if s["d"] == -1 else (c <= e)):   # [IMPL] a limit through the market is not placed
                    order = dict(d=s["d"], entry=e, stop=st, tgt=tg, level=lvl, va=va, qty=p.qty)
    return res


def load(path: str | None = None, tz: str = TZ, stamp: str = "auto") -> pd.DataFrame:
    """A local file (NinjaTrader export, TradingView export or CSV — see data.py), or 60 days of Yahoo NQ."""
    if path:
        from data import load_file
        return load_file(path, tz=tz, stamp=stamp)
    import yfinance as yf

    d = yf.download("NQ=F", period="60d", interval="5m", prepost=True, progress=False, auto_adjust=False)
    d.columns = [c[0].lower() for c in d.columns]
    return d.tz_convert(TZ)[["open", "high", "low", "close", "volume"]]


if __name__ == "__main__":
    df = load(sys.argv[1] if len(sys.argv) > 1 else None)
    r = run(df)
    months = (df.index[-1] - df.index[0]).days / 30.4
    by = Counter(t["scenario"] for t in r.trades)
    rs = [t["r"] for t in r.trades]
    print(f"{df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d} ({months:.1f} months)")
    print(f"trades {len(rs)} (S1={by[1]} S2={by[2]} S3={by[3]}) wins {sum(x > 0 for x in rs)} totalR {sum(rs):+.2f} "
          f"({len(rs) / months:.1f}/month)")
    for t in r.trades:
        va = "  -  " if t["va"] is None else f"{t['va']:.3f}"
        print(f"  {t['entry_time']:%Y-%m-%d %H:%M} S{t['scenario']} {t['side']:5} @{t['level']:<5} va {va} "
              f"entry {t['entry']:.2f} stop {t['stop']:.2f} tgt {t['target']:.2f} → {t['exit']:9} {t['exit_price']:.2f}  R {t['r']:+.2f}")
    print("setup endings:", dict(r.funnel))
