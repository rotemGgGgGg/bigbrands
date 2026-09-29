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
    expiry_bars: int = 12
    leg_grow_max: float = 1.5
    leg_min: float = 30.0
    leg_max: float = 150.0
    vp_rows: int = 999
    va_pct: float = 0.70
    ldn_min_bars: int = 60
    kill_on_touch_no_order: bool = True  # README [IMPL] #3


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


def va_ratio(bars, start, end, f1, f0, d, rows, pct):
    lo, hi = min(f1, f0), max(f1, f0)
    if hi <= lo:
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
    vah, val = lo + (up + 1) * rh, lo + dn * rh
    return (vah - f0) / (hi - lo) if d == -1 else (f0 - val) / (hi - lo)


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
    # setup
    setup = None  # dict
    order = None  # working limit placed at previous close
    ref_price = None
    # position
    pos = None

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
            if weekday:
                f["days"] += 1

        # ── order processing during this bar (orders from previous close) ──
        closed_this_bar = None
        if order is not None and pos is None:
            d = order["dir"]
            filled = (h >= order["price"]) if d == -1 else (l <= order["price"])
            if filled:
                fill = max(o, order["price"]) if d == -1 else min(o, order["price"])
                pos = dict(order, entry=fill, a1=setup["a1"], a0=setup["a0"], scen=setup["scen"],
                           bars_to_fill=i - setup["trig"], leg_trig=setup["init"], entry_time=t,
                           stop=order["stop"], tgt=order["tgt"], mfe=0.0, mae=0.0)
                trades_today += 1
                f["fills"] += 1
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
        ldn_valid = ldnH is not None and ldnBars >= p.ldn_min_bars

        # sweeps (§4)
        if after_six and ldn_valid:
            if hiSw:
                if h > hiSinceHi:
                    hiSinceHi, hiSinceHiBar = h, i
                if l < loSinceHi:
                    loSinceHi, loSinceHiBar = l, i
            if loSw:
                if l < loSinceLo:
                    loSinceLo, loSinceLoBar = l, i
                if h > hiSinceLo:
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
                                       bars_to_fill=pos["bars_to_fill"], exit=why, r=round(r, 3),
                                       mfe_r=round(pos["mfe"], 2), mae_r=round(pos["mae"], 2), qty=pos["qty"]))
                log(i, f"EXIT {why} R={r:.2f}")
                pos = None
                lastDeath = i
                if trades_today >= p.max_trades:
                    done_day = True
            else:
                lvl = pos["level"]
                pos["stop"] = tick(fib_price(pos["a1"], pos["a0"], d, stop_level(lvl)))
                pos["tgt"] = tick(fib_price(pos["a1"], pos["a0"], d, target_level(lvl)))

        # arm (§5, §6)
        two_bear = i > 0 and c < o and b.close[i - 1] < b.open[i - 1]
        two_bull = i > 0 and c > o and b.close[i - 1] > b.open[i - 1]
        risk_off = done_day or trades_today >= p.max_trades or fails >= p.max_fails
        can_arm = (setup is None and pos is None and not risk_off and in_win and prev_in_win and can_place
                   and ldn_valid and weekday and i - 1 > lastDeath)
        just_armed = False
        if can_arm:
            cand = None
            if hiSw and not loSw and hiSwInWin and not s1FailHi and two_bear and i - 1 >= hiSwBar:
                cand = dict(scen=1, dir=-1, side=1, a1=hiSinceHi, a0=loSinceHi, start=min(hiSinceHiBar, loSinceHiBar))
            elif loSw and not hiSw and loSwInWin and not s1FailLo and two_bull and i - 1 >= loSwBar:
                cand = dict(scen=1, dir=1, side=-1, a1=loSinceLo, a0=hiSinceLo, start=min(loSinceLoBar, hiSinceLoBar))
            elif s1FailHi and not s2DeadHi and two_bull:
                cand = dict(scen=2, dir=1, side=1, a1=b.low[i - 1], a0=hiSinceHi, start=min(i - 1, hiSinceHiBar))
            elif s1FailLo and not s2DeadLo and two_bear:
                cand = dict(scen=2, dir=-1, side=-1, a1=b.high[i - 1], a0=loSinceLo, start=min(i - 1, loSinceLoBar))
            elif hiSw and loSw and not s3Dead and hiSwBar != loSwBar and i - 1 >= max(hiSwBar, loSwBar):
                low_second = loSwBar > hiSwBar
                if low_second and two_bull:
                    cand = dict(scen=3, dir=-1, side=0, a1=hiSinceHi, a0=loSinceLo, start=min(hiSinceHiBar, loSinceLoBar))
                elif not low_second and two_bear:
                    cand = dict(scen=3, dir=1, side=0, a1=loSinceLo, a0=hiSinceHi, start=min(loSinceLoBar, hiSinceHiBar))
            if cand:
                leg = abs(cand["a1"] - cand["a0"])
                f[f"S{cand['scen']}_triggers"] += 1
                if leg == 0 or leg < p.leg_min or leg > p.leg_max:
                    f[f"S{cand['scen']}_rejected_leg_{'small' if leg < p.leg_min else 'big'}"] += 1
                    log(i, f"S{cand['scen']} {'LONG' if cand['dir'] == 1 else 'SHORT'} rejected leg={leg:.2f}")
                    lastDeath = i
                else:
                    setup = dict(cand, init=leg, trig=i)
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
            elif p.kill_on_touch_no_order and order is None and ref_price is not None and ((h >= ref_price) if d == -1 else (l <= ref_price)):
                dead, why = True, "entry touched, no order"
            elif i - setup["trig"] >= p.expiry_bars:
                dead, why = True, "expired"
            elif not can_place:
                dead, count_fail, why = True, False, "14:00"
            if not dead:
                setup["a0"] = min(setup["a0"], l) if d == -1 else max(setup["a0"], h)
                if abs(setup["a1"] - setup["a0"]) > p.leg_grow_max * setup["init"]:
                    dead, why = True, "leg grew"

        # place / update the limit (§9)
        if setup is not None and not dead:
            d = setup["dir"]
            va = None if setup["scen"] == 3 else va_ratio(b, setup["start"], i, setup["a1"], setup["a0"], d, p.vp_rows, p.va_pct)
            if va is not None:
                f["va_samples"] += 1
                band = ">0.588" if va > 0.588 else "0.5-0.588" if va >= 0.5 else "0.412-0.5" if va >= p.va_low else "<0.412"
                f[f"va_{band}"] += 1
            lvl = choose_level(setup["scen"], va, p.va_low)
            order = None
            ref_price = tick(fib_price(setup["a1"], setup["a0"], d, 0.5))
            if lvl > 0:
                eP = tick(fib_price(setup["a1"], setup["a0"], d, lvl))
                sP = tick(fib_price(setup["a1"], setup["a0"], d, stop_level(lvl)))
                tP = tick(fib_price(setup["a1"], setup["a0"], d, target_level(lvl)))
                if (c >= eP) if d == -1 else (c <= eP):
                    dead, why = True, "price past entry"
                else:
                    rp = abs(sP - eP)
                    qty = min(math.floor(p.risk_usd / (rp * POINT_VALUE)), p.max_contracts) if rp > 0 else 0
                    if qty >= 1:
                        order = dict(dir=d, price=eP, stop=sP, tgt=tP, qty=qty, level=lvl, va=va, risk_pts=rp)
                        f["orders_placed"] += 1
                    else:
                        f["skipped_size"] += 1

        if dead:
            f[f"dead_{why}"] += 1
            log(i, f"S{setup['scen']} dead: {why}")
            if count_fail:
                fails += 1
            if broke:
                if setup["scen"] == 1:
                    if setup["side"] == 1:
                        s1FailHi = True
                    else:
                        s1FailLo = True
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
