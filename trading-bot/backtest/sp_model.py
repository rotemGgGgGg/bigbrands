"""Python port of pine/sp_model.pine, used to debug the strategy and backtest it
on more history than TradingView loads. Mirrors the Pine logic step by step;
section numbers (§) refer to SP_MODEL_BOT_SPEC.md.

Usage:
    python sp_model.py                      # last 60 days of NQ=F from Yahoo
    python sp_model.py data.csv             # CSV with datetime,open,high,low,close,volume
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

TZ = "America/New_York"
POINT_VALUE = 2.0  # MNQ


@dataclass
class Params:
    risk_usd: float = 250.0
    max_contracts: int = 20
    max_trades: int = 1
    max_fails: int = 3
    va_low: float = 0.412
    expiry_bars: int = 0  # 0 = off
    leg_grow_max: float = 0.0  # 0 = off (the cap was an invented parameter)
    use_leg_filter: bool = False
    leg_min: float = 30.0
    leg_max: float = 400.0
    vp_rows: int = 999
    va_pct: float = 0.70
    vp_range: str = "leg"  # leg | london | day | ny
    vp_anchor: str = "leg"  # leg range only — profile start: leg | a1 | sweep | swing
    vp_offset: int = 0      # bars before the anchor bar (a1 / sweep)
    swing_k: int = 2        # pivot strength for vp_anchor="swing"
    vp_price: str = "anchors"  # leg range only — rows span: anchors (a1..a0) | bars (high/low of the bars, like TradingView FRVP)
    trail_after_fill: bool = False  # False: bracket frozen at lock prices
    ldn_min_bars: int = 60
    check: bool = True  # invariants: fail loudly (InvariantError) instead of producing a wrong trade
    trace: list | None = None  # debug: per-bar state appended while a setup or position is live
    use_s1: bool = True
    use_s2: bool = True
    use_s3: bool = True
    s2_swing_highs: bool = False  # S2 also on the break of an intermediate swing high/low (unconfirmed)
    a0_from_a1: bool = True  # S1: a0 = extreme since the bar of a1, not since the sweep


def fib_price(f1, f0, d, lvl):
    rng = abs(f1 - f0)
    return f0 + rng * lvl if d == -1 else f0 - rng * lvl


def stop_level(lvl):
    return 0.816 if lvl == 0.588 else 0.702


def target_level(lvl):
    return 0.36 if lvl == 0.588 else 0.267


def choose_level(scen, va, va_low):
    if scen == 3:
        return 0.5
    if va is None:
        return 0.0
    if va > 0.588:
        return 0.0
    if va >= 0.5:
        return 0.588
    if va >= va_low:
        return 0.5
    return 0.0


def tick(x):
    return round(x * 4) / 4


def value_area(bars, start, end, lo, hi, rows, pct):
    """Fixed-range volume profile over bars[start..end] and prices [lo, hi] -> (VAH, VAL)."""
    if start is None or hi <= lo:
        return None
    rh = (hi - lo) / rows
    diff = [0.0] * (rows + 1)
    for i in range(start, end + 1):
        bh, bl, bv = bars.high[i], bars.low[i], bars.volume[i]
        if bh > lo and bl < hi:
            i0 = max(0, min(rows - 1, math.floor((bl - lo) / rh)))
            i1 = max(0, min(rows - 1, math.floor((bh - lo) / rh)))
            per = bv / (i1 - i0 + 1)
            diff[i0] += per
            diff[i1 + 1] -= per
    bins, run = [], 0.0
    for k in range(rows):
        run += diff[k]
        bins.append(run)
    tot = sum(bins)
    if tot <= 0:
        return None
    poc = max(range(rows), key=lambda k: (bins[k], -k))
    acc, up, dn = bins[poc], poc, poc
    while acc < tot * pct and (up < rows - 1 or dn > 0):
        v_up = bins[up + 1] if up < rows - 1 else -1.0
        v_dn = bins[dn - 1] if dn > 0 else -1.0
        if v_up >= v_dn:
            up += 1
            acc += v_up
        else:
            dn -= 1
            acc += v_dn
    return lo + (up + 1) * rh, lo + dn * rh


def va_ratio(bars, p, setup, i, day_start, ldn_end, ny_start, ldnH, ldnL):
    """§8 va_ratio, with the profile range switchable (fib leg by default)."""
    f1, f0, d = setup["a1"], setup["a0"], setup["dir"]
    if p.vp_range == "leg":
        start, end, lo, hi = setup["start"], i, min(f1, f0), max(f1, f0)
        if p.vp_anchor in ("a1", "sweep"):
            base = setup["a1bar"] if p.vp_anchor == "a1" else setup["swbar"]
            start = max(0, min(start, base - p.vp_offset))
        elif p.vp_anchor == "swing":
            start = min(start, swing_start(bars, setup["a1bar"], d, p.swing_k))
        if p.vp_price == "bars":
            lo, hi = min(bars.low[start:end + 1]), max(bars.high[start:end + 1])
    elif p.vp_range == "london":
        start, end, lo, hi = day_start, ldn_end, ldnL, ldnH
    else:
        start = day_start if p.vp_range == "day" else ny_start
        end = i
        if start is None:
            return None
        lo, hi = min(bars.low[start:end + 1]), max(bars.high[start:end + 1])
    va = value_area(bars, start, end, lo, hi, p.vp_rows, p.va_pct)
    if va is None:
        return None
    vah, val = va
    rng = abs(f1 - f0)
    return (vah - f0) / rng if d == -1 else (f0 - val) / rng


def swing_start(bars, a1bar, d, k):
    """Last pivot before the 1.0 anchor that started the move into it:
    a swing low before a high (short), a swing high before a low (long)."""
    for j in range(a1bar - k, max(k, a1bar - 150) - 1, -1):
        if j + k >= len(bars.low):
            continue
        if d == -1 and all(bars.low[j] < bars.low[j + o] for o in range(-k, k + 1) if o):
            return j
        if d == 1 and all(bars.high[j] > bars.high[j + o] for o in range(-k, k + 1) if o):
            return j
    return max(0, a1bar - 150)


class InvariantError(AssertionError):
    pass


def _inv(ok, i, bars, msg):
    if not ok:
        raise InvariantError(f"bar {i} {bars.time[i]:%Y-%m-%d %H:%M}: {msg}")


@dataclass
class Bars:
    time: list
    open: list
    high: list
    low: list
    close: list
    volume: list


@dataclass
class Result:
    trades: list = field(default_factory=list)
    funnel: Counter = field(default_factory=Counter)
    events: list = field(default_factory=list)
    setups: list = field(default_factory=list)


def run(df: pd.DataFrame, p: Params = Params()) -> Result:
    b = Bars(list(df.index), list(df.open), list(df.high), list(df.low), list(df.close), list(df.volume))
    res = Result()
    f = res.funnel
    ev = res.events

    def log(i, msg):
        ev.append(f"{b.time[i]:%Y-%m-%d %H:%M} {msg}")

    # day state
    day = None
    ldnH = ldnL = None
    ldnBars = 0
    hiSw = loSw = False
    hiSwBar = loSwBar = None
    hiSwInWin = loSwInWin = False
    hiSinceHi = loSinceHi = loSinceLo = hiSinceLo = None
    hiSinceHiBar = loSinceHiBar = loSinceLoBar = hiSinceLoBar = None
    fails = trades_today = 0
    done_day = False
    s1FailHi = s1FailLo = s2DeadHi = s2DeadLo = s3Dead = False
    lastDeath = -1
    s2 = {}  # per-side S2 state: ref extreme after a pre-open sweep, eligibility, running extreme since the break
    # setup
    setup = None  # dict
    order = None  # working limit placed at previous close
    ref_price = None
    # position
    pos = None
    day_start = ldn_end = ny_start = None

    for i in range(len(b.time)):
        t = b.time[i]
        ny_min = t.hour * 60 + t.minute
        weekday = t.weekday() < 5
        in_london = ny_min < 360
        after_six = ny_min >= 360
        in_win = 570 <= ny_min < 840
        can_place = ny_min + 5 < 840
        at_flatten = ny_min < 840 <= ny_min + 5
        new_day = t.date() != day
        prev_in_win = (not new_day) and i > 0 and (b.time[i - 1].hour * 60 + b.time[i - 1].minute) >= 570
        o, h, l, c = b.open[i], b.high[i], b.low[i], b.close[i]

        if new_day:
            if day is not None and weekday:
                pass
            day = t.date()
            day_start, ldn_end, ny_start = i, None, None
            if pos:  # safety close
                pos = None
            order = None
            ldnH = ldnL = None
            ldnBars = 0
            hiSw = loSw = False
            hiSwBar = loSwBar = None
            hiSwInWin = loSwInWin = False
            setup = None
            ref_price = None
            fails = trades_today = 0
            done_day = False
            s1FailHi = s1FailLo = s2DeadHi = s2DeadLo = s3Dead = False
            lastDeath = -1
            s2 = {side: dict(ref=None, ref_bar=None, swing=None, pull=None, pull_bar=None, elig=False, elig_bar=None,
                             a1=None, a1_bar=None, x=None, x_bar=None, why=None) for side in (1, -1)}
            if weekday:
                f["days"] += 1

        # ── order processing during this bar (orders from previous close) ──
        closed_this_bar = None
        if order is not None and pos is None:
            d = order["dir"]
            filled = (h >= order["price"]) if d == -1 else (l <= order["price"])
            if filled:
                fill = max(o, order["price"]) if d == -1 else min(o, order["price"])
                if p.check:
                    _inv((fill >= order["price"] - 0.25) if d == -1 else (fill <= order["price"] + 0.25), i, b,
                         f"fill {fill} worse than limit {order['price']} by more than a tick")
                    exp = tick(fib_price(setup["a1"], setup["a0"], d, order["level"]))
                    _inv(abs(order["price"] - exp) <= 0.25, i, b,
                         f"limit {order['price']} != fib {order['level']} of current anchors {exp} (a1 {setup['a1']} a0 {setup['a0']})")
                pos = dict(order, entry=fill, a1=setup["a1"], a0=setup["a0"], scen=setup["scen"],
                           bars_to_fill=i - setup["trig"], leg_trig=setup["init"], entry_time=t,
                           stop=order["stop"], tgt=order["tgt"], mfe=0.0, mae=0.0)
                trades_today += 1
                f["fills"] += 1
                setup["outcome"] = "filled"
                setup = None
                order = None
                ref_price = None
                # same-bar exit, pessimistic (§10): stop first
                if (d == -1 and h >= pos["stop"]) or (d == 1 and l <= pos["stop"]):
                    closed_this_bar = ("stop", pos["stop"])
                elif (d == -1 and l <= pos["tgt"]) or (d == 1 and h >= pos["tgt"]):
                    closed_this_bar = ("target", pos["tgt"])
        elif pos is not None:
            d = pos["dir"]
            if d == -1:
                if o >= pos["stop"]:
                    closed_this_bar = ("stop", o)
                elif h >= pos["stop"]:
                    closed_this_bar = ("stop", pos["stop"])
                elif o <= pos["tgt"]:
                    closed_this_bar = ("target", o)
                elif l <= pos["tgt"]:
                    closed_this_bar = ("target", pos["tgt"])
            else:
                if o <= pos["stop"]:
                    closed_this_bar = ("stop", o)
                elif l <= pos["stop"]:
                    closed_this_bar = ("stop", pos["stop"])
                elif o >= pos["tgt"]:
                    closed_this_bar = ("target", o)
                elif h >= pos["tgt"]:
                    closed_this_bar = ("target", pos["tgt"])

        # London range (§3)
        if in_london:
            ldnH = h if ldnH is None else max(ldnH, h)
            ldnL = l if ldnL is None else min(ldnL, l)
            ldnBars += 1
            ldn_end = i
        if ny_start is None and ny_min >= 570:
            ny_start = i
        ldn_valid = ldnH is not None and ldnBars >= p.ldn_min_bars

        # sweeps (§4)
        if after_six and ldn_valid:
            if hiSw:
                new_hi = h > hiSinceHi
                if new_hi:
                    hiSinceHi, hiSinceHiBar = h, i
                if new_hi and p.a0_from_a1:
                    loSinceHi, loSinceHiBar = l, i  # a1 moved: restart a0 from this bar
                elif l < loSinceHi:
                    loSinceHi, loSinceHiBar = l, i
            if loSw:
                new_lo = l < loSinceLo
                if new_lo:
                    loSinceLo, loSinceLoBar = l, i
                if new_lo and p.a0_from_a1:
                    hiSinceLo, hiSinceLoBar = h, i
                elif h > hiSinceLo:
                    hiSinceLo, hiSinceLoBar = h, i
            if not hiSw and h > ldnH:
                hiSw, hiSwBar, hiSwInWin = True, i, in_win
                hiSinceHi, hiSinceHiBar, loSinceHi, loSinceHiBar = h, i, l, i
                f["hi_swept_in_win" if in_win else "hi_swept_outside_win"] += 1
            if not loSw and l < ldnL:
                loSw, loSwBar, loSwInWin = True, i, in_win
                loSinceLo, loSinceLoBar, hiSinceLo, hiSinceLoBar = l, i, h, i
                f["lo_swept_in_win" if in_win else "lo_swept_outside_win"] += 1

        # position: trail, record exits, flatten
        if pos is not None:
            d = pos["dir"]
            pos["a0"] = min(pos["a0"], l) if d == -1 else max(pos["a0"], h)
            risk_pts = abs(pos["stop"] - pos["entry"])
            fav = (pos["entry"] - l) if d == -1 else (h - pos["entry"])
            adv = (h - pos["entry"]) if d == -1 else (pos["entry"] - l)
            pos["mfe"] = max(pos["mfe"], fav / pos["risk_pts"])
            pos["mae"] = max(pos["mae"], adv / pos["risk_pts"])
            if closed_this_bar is None and (at_flatten or ny_min >= 840):
                closed_this_bar = ("14:00", c)
            if closed_this_bar is not None:
                why, px = closed_this_bar
                pnl_pts = (pos["entry"] - px) if d == -1 else (px - pos["entry"])
                r = pnl_pts / pos["risk_pts"]
                res.trades.append(dict(entry_time=pos["entry_time"], exit_time=t, scenario=pos["scen"],
                                       side="LONG" if d == 1 else "SHORT", level=pos["level"], va=pos["va"],
                                       leg_trigger=pos["leg_trig"], leg_exit=abs(pos["a1"] - pos["a0"]),
                                       bars_to_fill=pos["bars_to_fill"], bars_to_lock=pos["bars_to_lock"], exit=why, r=round(r, 3),
                                       mfe_r=round(pos["mfe"], 2), mae_r=round(pos["mae"], 2), qty=pos["qty"]))
                log(i, f"EXIT {why} R={r:.2f}")
                pos = None
                lastDeath = i
                if trades_today >= p.max_trades:
                    done_day = True
            elif p.trail_after_fill:
                lvl = pos["level"]
                pos["stop"] = tick(fib_price(pos["a1"], pos["a0"], d, stop_level(lvl)))
                pos["tgt"] = tick(fib_price(pos["a1"], pos["a0"], d, target_level(lvl)))

        # arm (§5, §6)
        two_bear = i > 0 and c < o and b.close[i - 1] < b.open[i - 1]
        two_bull = i > 0 and c > o and b.close[i - 1] > b.open[i - 1]

        # S2 eligibility. In-window sweep: S1 failing sets it (in the death block below).
        # Pre-open sweep: S1 never arms, so the reference is the post-sweep extreme at the first
        # two-candle pullback after the sweep; S2 opens when price breaks it (optionally: an
        # intermediate swing high/low formed on the way back).
        if s2:
            k = p.swing_k
            for side, swept, sw_in_win, sw_bar, ext, pull in (
                    (1, hiSw, hiSwInWin, hiSwBar, hiSinceHi, two_bear),
                    (-1, loSw, loSwInWin, loSwBar, loSinceLo, two_bull)):
                st2 = s2[side]
                if st2["elig"]:
                    better = (h > st2["x"]) if side == 1 else (l < st2["x"])
                    if better:
                        st2["x"], st2["x_bar"] = (h if side == 1 else l), i
                    continue
                if not swept or sw_in_win:
                    continue
                if st2["ref"] is None:
                    if pull and i - 1 >= sw_bar:
                        st2["ref"] = ext
                        st2["ref_bar"] = hiSinceHiBar if side == 1 else loSinceLoBar
                        rb = st2["ref_bar"]
                        seg = range(rb, i + 1)
                        pb = min(seg, key=lambda q: b.low[q]) if side == 1 else max(seg, key=lambda q: b.high[q])
                        st2["pull"], st2["pull_bar"] = (b.low[pb] if side == 1 else b.high[pb]), pb
                    continue
                against = l if side == 1 else h  # extreme against the S2 direction, since the reference bar
                if st2["pull"] is None or ((against < st2["pull"]) if side == 1 else (against > st2["pull"])):
                    st2["pull"], st2["pull_bar"] = against, i
                j = i - k
                if p.s2_swing_highs and j > st2["ref_bar"] and j - k >= 0:
                    if side == 1 and all(b.high[j] > b.high[j + o2] for o2 in range(-k, k + 1) if o2) and b.high[j] < st2["ref"]:
                        st2["swing"] = b.high[j]
                    if side == -1 and all(b.low[j] < b.low[j + o2] for o2 in range(-k, k + 1) if o2) and b.low[j] > st2["ref"]:
                        st2["swing"] = b.low[j]
                broke_ref = (h > st2["ref"]) if side == 1 else (l < st2["ref"])
                broke_sw = st2["swing"] is not None and ((h > st2["swing"]) if side == 1 else (l < st2["swing"]))
                if broke_ref or broke_sw:
                    # [IMPL-confirm] pre-open: S2's a1 = the pullback extreme between the reference and the break
                    st2.update(elig=True, elig_bar=i, a1=st2["pull"], a1_bar=st2["pull_bar"],
                               x=(h if side == 1 else l), x_bar=i, why="ref" if broke_ref else "swing")
                    f[f"s2_open_{'ref' if broke_ref else 'swing'}"] += 1
        risk_off = done_day or trades_today >= p.max_trades or fails >= p.max_fails
        can_arm = (setup is None and pos is None and not risk_off and in_win and prev_in_win and can_place
                   and ldn_valid and weekday and i - 1 > lastDeath)
        just_armed = False
        if can_arm:
            cand = None
            if hiSw and loSw:
                if p.use_s3 and not s3Dead and hiSwBar != loSwBar and i - 1 >= max(hiSwBar, loSwBar):
                    low_second = loSwBar > hiSwBar
                    if low_second and two_bull:
                        cand = dict(scen=3, dir=-1, side=0, a1=hiSinceHi, a0=loSinceLo, start=min(hiSinceHiBar, loSinceLoBar), a1bar=hiSinceHiBar, swbar=hiSwBar)
                    elif not low_second and two_bear:
                        cand = dict(scen=3, dir=1, side=0, a1=loSinceLo, a0=hiSinceHi, start=min(loSinceLoBar, hiSinceHiBar), a1bar=loSinceLoBar, swbar=loSwBar)
            elif p.use_s1 and hiSw and not loSw and hiSwInWin and not s1FailHi and two_bear and i - 1 >= hiSwBar:
                cand = dict(scen=1, dir=-1, side=1, a1=hiSinceHi, a0=loSinceHi, start=min(hiSinceHiBar, loSinceHiBar), a1bar=hiSinceHiBar, a0bar=loSinceHiBar, swbar=hiSwBar)
            elif p.use_s1 and loSw and not hiSw and loSwInWin and not s1FailLo and two_bull and i - 1 >= loSwBar:
                cand = dict(scen=1, dir=1, side=-1, a1=loSinceLo, a0=hiSinceLo, start=min(loSinceLoBar, hiSinceLoBar), a1bar=loSinceLoBar, a0bar=hiSinceLoBar, swbar=loSwBar)
            elif p.use_s2 and s2[1]["elig"] and not s2DeadHi and two_bull and i - 1 >= s2[1]["elig_bar"]:
                cand = dict(scen=2, dir=1, side=1, a1=s2[1]["a1"], a0=s2[1]["x"], start=min(s2[1]["a1_bar"], s2[1]["x_bar"]), a1bar=s2[1]["a1_bar"], a0bar=s2[1]["x_bar"], swbar=hiSwBar, s2why=s2[1]["why"])
            elif p.use_s2 and s2[-1]["elig"] and not s2DeadLo and two_bear and i - 1 >= s2[-1]["elig_bar"]:
                cand = dict(scen=2, dir=-1, side=-1, a1=s2[-1]["a1"], a0=s2[-1]["x"], start=min(s2[-1]["a1_bar"], s2[-1]["x_bar"]), a1bar=s2[-1]["a1_bar"], a0bar=s2[-1]["x_bar"], swbar=loSwBar, s2why=s2[-1]["why"])
            if cand:
                leg = abs(cand["a1"] - cand["a0"])
                f[f"S{cand['scen']}_triggers"] += 1
                if leg == 0 or (p.use_leg_filter and (leg < p.leg_min or leg > p.leg_max)):
                    f[f"S{cand['scen']}_rejected_leg_{'small' if leg < p.leg_min else 'big'}"] += 1
                    log(i, f"S{cand['scen']} {'LONG' if cand['dir'] == 1 else 'SHORT'} rejected leg={leg:.2f}")
                    lastDeath = i
                else:
                    setup = dict(cand, init=leg, trig=i, frozen=False, locked=False, level=0.0, lock_va=None, lock_bar=None,
                                 live_a0=cand["a0"], live_a0_bar=cand.get("a0bar"), va_frozen=[], va_all=[], refreezes=0, outcome=None, time=t)
                    res.setups.append(setup)
                    order = None
                    ref_price = None
                    just_armed = True
                    f[f"S{cand['scen']}_armed"] += 1
                    log(i, f"S{cand['scen']} {'LONG' if cand['dir'] == 1 else 'SHORT'} armed leg={leg:.2f}")

        # armed: invalidation (§11)
        dead, broke, count_fail, why = False, False, True, ""
        if setup is not None and not just_armed:
            d = setup["dir"]
            if (h > setup["a1"]) if d == -1 else (l < setup["a1"]):
                dead, broke, why = True, True, "1.0 broken"
            elif setup["locked"] and order is None and ((h >= setup["entry"]) if d == -1 else (l <= setup["entry"])):
                dead, why = True, "entry touched, no fill"
            elif setup["scen"] != 3 and hiSw and loSw:
                dead, count_fail, why = True, False, "both swept -> S3"
            elif p.expiry_bars and i - setup["trig"] >= p.expiry_bars:
                dead, why = True, "expired"
            elif not can_place:
                dead, count_fail, why = True, False, "14:00"
            if not dead:
                prev = setup["live_a0"]
                setup["extending"] = (l < prev) if d == -1 else (h > prev)
                setup["live_a0"] = min(prev, l) if d == -1 else max(prev, h)
                if setup["extending"]:
                    setup["live_a0_bar"] = i
                if setup["extending"] and setup["frozen"]:
                    # new extreme: the retracement was false — unlock and re-anchor
                    setup.update(frozen=False, locked=False, level=0.0, lock_va=None, lock_bar=None)
                    setup["refreezes"] += 1
                    f["unfrozen_new_extreme"] += 1
                if not setup["frozen"]:
                    setup["a0"] = setup["live_a0"]
                if p.leg_grow_max and abs(setup["a1"] - setup["live_a0"]) > p.leg_grow_max * setup["init"]:
                    dead, why = True, "leg grew"
        if setup is not None and just_armed:
            d = setup["dir"]
            setup["extending"] = (l <= setup["a0"]) if d == -1 else (h >= setup["a0"])

        if p.check and setup is not None:
            _inv(setup["a1"] == setup.setdefault("a1_at_arm", setup["a1"]), i, b, f"a1 moved: {setup['a1_at_arm']} -> {setup['a1']}")
            leg_now = (setup["a1"] - setup["a0"]) if setup["dir"] == -1 else (setup["a0"] - setup["a1"])
            _inv(leg_now > 0, i, b, f"leg not positive: a1 {setup['a1']} a0 {setup['a0']} dir {setup['dir']}")
            if setup["frozen"]:
                _inv(setup["a0"] == setup.setdefault("a0_at_freeze", setup["a0"]), i, b, f"a0 moved while frozen: {setup['a0_at_freeze']} -> {setup['a0']}")
            else:
                setup.pop("a0_at_freeze", None)

        # place / update the limit (§9)
        if setup is not None and not dead:
            d = setup["dir"]
            # STEP 1: freeze the anchors on the first bar that does not extend the leg
            if not setup["frozen"] and not setup["extending"]:
                setup["frozen"] = True
                setup.setdefault("freeze_bars", []).append(i)
                f[f"S{setup['scen']}_frozen"] += 1
            # STEP 2: keep watching the value area (profile includes the retracement bars)
            va = None if setup["scen"] == 3 else va_ratio(b, p, setup, i, day_start, ldn_end, ny_start, ldnH, ldnL)
            if va is not None:
                setup["va_all"].append(va)
                if setup["frozen"]:
                    setup["va_frozen"].append(va)
            if setup["frozen"] and not setup["locked"]:
                lvl = choose_level(setup["scen"], va, p.va_low)
                if lvl > 0:  # the level set never changes while the anchors stay frozen
                    setup.update(locked=True, level=lvl, lock_va=va, lock_bar=i,
                                 entry=tick(fib_price(setup["a1"], setup["a0"], d, lvl)))
                    setup.setdefault("lock_hist", []).append((i, lvl, va, abs(setup["a1"] - setup["a0"])))
                    f[f"S{setup['scen']}_locked"] += 1
                    log(i, f"S{setup['scen']} locked @{lvl} va={va}")
            order = None
            if setup["locked"]:
                lvl, va = setup["level"], setup["lock_va"]
                eP = tick(fib_price(setup["a1"], setup["a0"], d, lvl))
                sP = tick(fib_price(setup["a1"], setup["a0"], d, stop_level(lvl)))
                tP = tick(fib_price(setup["a1"], setup["a0"], d, target_level(lvl)))
                if (c >= eP) if d == -1 else (c <= eP):
                    dead, why = True, "entry touched, no fill"  # closed through the entry before an order could work
                else:
                    rp = abs(sP - eP)
                    qty = min(math.floor(p.risk_usd / (rp * POINT_VALUE)), p.max_contracts) if rp > 0 else 0
                    if p.check:
                        _inv((tP < eP < sP) if d == -1 else (sP < eP < tP), i, b, f"bracket on wrong side: stop {sP} entry {eP} target {tP} dir {d}")
                        _inv(eP == setup["entry"], i, b, f"order entry {eP} != locked entry {setup['entry']}")
                    if qty >= 1:
                        order = dict(dir=d, price=eP, stop=sP, tgt=tP, qty=qty, level=lvl, va=va, risk_pts=rp, bars_to_lock=setup['lock_bar'] - setup['trig'])
                        f["orders_placed"] += 1
                    else:
                        f["skipped_size"] += 1

        if dead:
            setup["outcome"] = why
            f[f"dead_{why}"] += 1
            log(i, f"S{setup['scen']} dead: {why}")
            if count_fail:
                fails += 1
            if broke:
                if setup["scen"] == 1:
                    if setup["side"] == 1:
                        s1FailHi = True
                        s2[1].update(elig=True, elig_bar=i, a1=setup["a0"], a1_bar=setup["live_a0_bar"], x=hiSinceHi, x_bar=hiSinceHiBar, why="S1 failed")
                    else:
                        s1FailLo = True
                        s2[-1].update(elig=True, elig_bar=i, a1=setup["a0"], a1_bar=setup["live_a0_bar"], x=loSinceLo, x_bar=loSinceLoBar, why="S1 failed")
                elif setup["scen"] == 2:
                    if setup["side"] == 1:
                        s2DeadHi = True
                    else:
                        s2DeadLo = True
                else:
                    s3Dead = True
            lastDeath = i
            setup = None
            order = None
            ref_price = None

        if p.trace is not None and (setup is not None or pos is not None or dead or closed_this_bar):
            src = setup if setup is not None else {}
            p.trace.append(dict(i=i, t=t, o=o, h=h, l=l, c=c, scen=src.get("scen"), a1=src.get("a1"), a0=src.get("a0"),
                                live_a0=src.get("live_a0"), extending=src.get("extending"), frozen=src.get("frozen"),
                                locked=src.get("locked"), level=src.get("level"), entry=src.get("entry"),
                                order=None if order is None else order["price"], pos=None if pos is None else dict(entry=pos["entry"], stop=pos["stop"], tgt=pos["tgt"], a1=pos["a1"], a0=pos["a0"]),
                                dead=why if dead else None, closed=closed_this_bar))

    return res


def load(path: str | None) -> pd.DataFrame:
    if path:
        df = pd.read_csv(path, parse_dates=[0], index_col=0)
        df.columns = [c.lower() for c in df.columns]
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        return df.tz_convert(TZ)[["open", "high", "low", "close", "volume"]]
    import yfinance as yf

    d = yf.download("NQ=F", period="60d", interval="5m", prepost=True, progress=False, auto_adjust=False)
    d.columns = [c[0].lower() for c in d.columns]
    return d.tz_convert(TZ)[["open", "high", "low", "close", "volume"]]


if __name__ == "__main__":
    df = load(sys.argv[1] if len(sys.argv) > 1 else None)
    res = run(df)
    print(f"bars {len(df)}  {df.index[0]} → {df.index[-1]}\n")
    print("FUNNEL")
    for k, v in sorted(res.funnel.items()):
        print(f"  {k:32s} {v}")
    print("\nTRADES")
    for t in res.trades:
        print(" ", t)
    if res.trades:
        rs = [t["r"] for t in res.trades]
        wins = sum(r > 0 for r in rs)
        print(f"\n  n={len(rs)}  win%={100 * wins / len(rs):.1f}  totalR={sum(rs):.2f}")
