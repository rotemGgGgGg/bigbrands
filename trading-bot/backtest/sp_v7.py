"""SP Model v7 — written from scratch against the trader-confirmed spec (see ../SPEC_V7.md).

Mirrors pine/sp_model_v7.pine step for step. Every bar is evaluated at its close; orders placed at a
close work during the next bar; fills and exits inside a bar follow TradingView's broker emulator path.

Usage:
    python sp_v7.py              # last 60 days of NQ=F from Yahoo
    python sp_v7.py data.csv     # datetime,open,high,low,close,volume (bar OPEN time, with offset or UTC)
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

TZ = "America/New_York"
TICK = 0.25


@dataclass
class Params:
    va_floor: float = 0.41      # below → no trade
    va_mid: float = 0.5         # 0.41–0.5 → limit at 0.5; 0.5–0.588 → limit at 0.588
    va_ceiling: float = 0.588   # above → no trade
    vp_rows: int = 999
    va_pct: float = 0.70
    ldn_min_bars: int = 60      # [IMPL] London range counts as formed with ≥60 of its 72 bars
    qty: int = 1                # [IMPL] fixed size — the spec does not size; keeps the trade list size-independent
    use_s1: bool = True
    use_s2: bool = True
    use_s3: bool = True
    check: bool = True          # invariants raise InvariantError
    trace: list | None = None   # debug: per-bar state


# ── helpers ────────────────────────────────────────────────────────────────
def tick(x):
    """Nearest tick, ties rounded up — like Pine's math.round_to_mintick (Python's round() would round ties to even)."""
    return math.floor(x / TICK + 0.5 + 1e-9) * TICK


def fib(a1, a0, d, lvl):
    """1.0 = a1 (where the move started), 0 = a0 (where it got to). d: 1 long, -1 short."""
    rng = abs(a1 - a0)
    return a0 + rng * lvl if d == -1 else a0 - rng * lvl


LEVELS = {0.5: (0.702, 0.267), 0.588: (0.816, 0.36)}  # entry → (stop, target)


def choose_level(scen, va, p):
    if scen == 3:
        return 0.5
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
            up += 1
            acc += vu
        else:
            dn -= 1
            acc += vd
    return lo + (up + 1) * rh, lo + dn * rh


def walk_bar(o, h, l, c, d, entry=None, stop=None, tgt=None, in_pos=False):
    """TradingView broker emulator: open → nearer extreme → other extreme → close.
    Returns (fill | None, (reason, price) | None)."""
    fill = None
    if not in_pos and entry is not None and ((o <= entry) if d == 1 else (o >= entry)):
        fill, in_pos = o, True
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


class InvariantError(AssertionError):
    pass


@dataclass
class Result:
    trades: list = field(default_factory=list)
    setups: list = field(default_factory=list)
    events: list = field(default_factory=list)
    funnel: Counter = field(default_factory=Counter)


# ── the model ──────────────────────────────────────────────────────────────
def run(df: pd.DataFrame, p: Params = Params()) -> Result:
    T = list(df.index)
    O, H, L, C, V = (list(df[k]) for k in ("open", "high", "low", "close", "volume"))
    res = Result()

    def inv(ok, i, msg):
        if p.check and not ok:
            raise InvariantError(f"{T[i]:%Y-%m-%d %H:%M}: {msg}")

    def log(i, msg):
        res.events.append(f"{T[i]:%Y-%m-%d %H:%M} {msg}")

    day = None
    order = None   # limit working during the next bar: dict(d, entry, stop, tgt, level, va)
    pos = None
    S = None       # day state
    setup = None

    def new_day_state():
        return dict(ldnH=None, ldnL=None, ldnN=0,
                    sw={1: None, -1: None},          # sweep bar per side (1 = London high, -1 = London low)
                    sw_win={1: False, -1: False},
                    ext={1: None, -1: None},         # extreme since that side's sweep (high for 1, low for -1)
                    ext_bar={1: None, -1: None},
                    s1_fail={1: False, -1: False},
                    s2_dead={1: False, -1: False},
                    s3_dead=False,
                    s2={side: dict(ref=None, ref_bar=None, pull=None, pull_bar=None, elig=False, elig_bar=None,
                                   a1=None, a1_bar=None) for side in (1, -1)},
                    trades=0)

    def extreme_since(bar, i, d):
        """fib 0 counts forward from the 1.0 bar: short → lowest low, long → highest high over [bar, i]."""
        if d == -1:
            k = min(range(bar, i + 1), key=lambda q: (L[q], q))
            return L[k], k
        k = max(range(bar, i + 1), key=lambda q: (H[q], -q))
        return H[k], k

    def kill(i, why, broke=False):
        nonlocal setup, order
        s = setup
        s["outcome"] = why
        res.funnel[f"S{s['scen']} {why}"] += 1
        log(i, f"S{s['scen']} {'LONG' if s['d'] == 1 else 'SHORT'} dead: {why}")
        if broke:
            if s["scen"] == 1:
                side = s["side"]
                S["s1_fail"][side] = True
                # S2 inherits S1's anchor_0 as its anchor_1
                S["s2"][side].update(elig=True, elig_bar=i, a1=s["a0"], a1_bar=s["a0_bar"])
            elif s["scen"] == 2:
                S["s2_dead"][s["side"]] = True     # [IMPL] carried over from v6
            else:
                S["s3_dead"] = True                # [IMPL] carried over from v6
        setup, order = None, None

    for i in range(len(T)):
        t = T[i]
        mn = t.hour * 60 + t.minute                 # bar OPEN time, NY
        o, h, l, c = O[i], H[i], L[i], C[i]
        closed = None

        # 1 ── orders from the previous close work during this bar
        if order is not None and pos is None:
            d = order["d"]
            fill, ex = walk_bar(o, h, l, c, d, entry=order["entry"], stop=order["stop"], tgt=order["tgt"])
            if fill is not None:
                inv((fill <= order["entry"]) if d == 1 else (fill >= order["entry"]), i, f"fill {fill} worse than limit {order['entry']}")
                pos = dict(order, fill=fill, time=t, scen=setup["scen"], a1=setup["a1"], a0=setup["a0"],
                           trig=setup["time"])
                S["trades"] += 1
                setup["outcome"] = "filled"
                setup, order = None, None
                closed = ex
        elif pos is not None:
            _, closed = walk_bar(o, h, l, c, pos["d"], stop=pos["stop"], tgt=pos["tgt"], in_pos=True)

        # 2 ── new day at 00:00 NY
        if t.date() != day:
            if pos is not None and closed is None:
                closed = ("day reset", c)
            day = t.date()
            S = new_day_state()
            setup, order = None, None

        # 3 ── London range 00:00–06:00
        if mn < 360:
            S["ldnH"] = h if S["ldnH"] is None else max(S["ldnH"], h)
            S["ldnL"] = l if S["ldnL"] is None else min(S["ldnL"], l)
            S["ldnN"] += 1
        valid = S["ldnH"] is not None and S["ldnN"] >= p.ldn_min_bars
        in_win = 570 <= mn < 840

        # 4 ── sweeps from 06:00 (wick, exact touch counts; a level is consumed once)
        if mn >= 360 and valid:
            for side, px, lvl in ((1, h, S["ldnH"]), (-1, l, S["ldnL"])):
                if S["sw"][side] is not None:
                    if (px > S["ext"][side]) if side == 1 else (px < S["ext"][side]):
                        S["ext"][side], S["ext_bar"][side] = px, i
                elif (px >= lvl) if side == 1 else (px <= lvl):
                    S["sw"][side], S["sw_win"][side] = i, in_win
                    S["ext"][side], S["ext_bar"][side] = px, i
                    log(i, f"London {'high' if side == 1 else 'low'} swept")

        # 5 ── position: flat at 14:00, record the trade
        if pos is not None and closed is None and (mn + 5 >= 840):
            closed = ("14:00", c)
        if pos is not None and closed is not None:
            why, px = closed
            d = pos["d"]
            risk = abs(pos["stop"] - pos["entry"])
            r = ((px - pos["fill"]) if d == 1 else (pos["fill"] - px)) / risk
            res.trades.append(dict(entry_time=pos["time"], exit_time=t, scenario=pos["scen"], side="LONG" if d == 1 else "SHORT",
                                   level=pos["level"], va=pos["va"], entry=pos["entry"], fill=pos["fill"], stop=pos["stop"],
                                   target=pos["tgt"], a1=pos["a1"], a0=pos["a0"], exit=why, exit_price=px, r=round(r, 3)))
            log(i, f"EXIT {why} R={r:+.2f}")
            pos = None

        # 6 ── armed setup: 1.0 break → dead; otherwise fib 0 extends
        if setup is not None:
            s = setup
            if (h > s["a1"]) if s["d"] == -1 else (l < s["a1"]):
                kill(i, "1.0 broken", broke=True)
            elif mn + 5 >= 840:
                kill(i, "14:00")
            else:
                if (l < s["a0"]) if s["d"] == -1 else (h > s["a0"]):
                    s["a0"], s["a0_bar"] = (l if s["d"] == -1 else h), i

        two_bull = i > 0 and T[i - 1].date() == t.date() and c >= o and C[i - 1] >= O[i - 1]   # doji counts both ways
        two_bear = i > 0 and T[i - 1].date() == t.date() and c <= o and C[i - 1] <= O[i - 1]

        # 7 ── S2 eligibility after a pre-open sweep: reference = post-sweep extreme at the first
        #      two-candle pullback; S2 opens when price breaks it; S2's 1.0 = the pullback extreme [IMPL-confirm]
        if valid:
            for side, pull in ((1, two_bear), (-1, two_bull)):
                st = S["s2"][side]
                swb = S["sw"][side]
                if swb is None or S["sw_win"][side] or st["elig"]:
                    continue
                if st["ref"] is None:
                    if pull and i - 1 >= swb:
                        st["ref"], st["ref_bar"] = S["ext"][side], S["ext_bar"][side]
                        v, k = extreme_since(st["ref_bar"], i, -side)
                        st["pull"], st["pull_bar"] = v, k
                    continue
                if (l < st["pull"]) if side == 1 else (h > st["pull"]):
                    st["pull"], st["pull_bar"] = (l if side == 1 else h), i
                if (h > st["ref"]) if side == 1 else (l < st["ref"]):
                    st.update(elig=True, elig_bar=i, a1=st["pull"], a1_bar=st["pull_bar"])
                    log(i, f"S2 {'LONG' if side == 1 else 'SHORT'} opens (pre-open reference broken)")

        # 8 ── triggers: from 06:00 to 14:00; a new setup replaces an armed, unfilled one
        if valid and pos is None and S["trades"] == 0 and 360 <= mn and mn + 5 < 840:
            cand = None
            hs, ls = S["sw"][1], S["sw"][-1]
            if hs is not None and ls is not None:          # both sides taken → S3 only
                if p.use_s3 and not S["s3_dead"] and hs != ls and i - 1 >= max(hs, ls):
                    if ls > hs and two_bull:               # low swept second → SHORT
                        cand = dict(scen=3, d=-1, side=0, a1=S["ext"][1], a1_bar=S["ext_bar"][1])
                    elif hs > ls and two_bear:             # high swept second → LONG
                        cand = dict(scen=3, d=1, side=0, a1=S["ext"][-1], a1_bar=S["ext_bar"][-1])
            else:
                for side in (1, -1):
                    swb = S["sw"][side]
                    if swb is None or cand:
                        continue
                    trig_s1 = two_bear if side == 1 else two_bull
                    trig_s2 = two_bull if side == 1 else two_bear
                    if p.use_s1 and S["sw_win"][side] and not S["s1_fail"][side] and trig_s1 and i - 1 >= swb:
                        cand = dict(scen=1, d=-side, side=side, a1=S["ext"][side], a1_bar=S["ext_bar"][side])
                    elif p.use_s2 and S["s2"][side]["elig"] and not S["s2_dead"][side] and trig_s2 and i - 1 >= S["s2"][side]["elig_bar"]:
                        st = S["s2"][side]
                        cand = dict(scen=2, d=side, side=side, a1=st["a1"], a1_bar=st["a1_bar"])
            if cand is not None:
                same = setup is not None and all(setup[k] == cand[k] for k in ("scen", "d", "a1", "a1_bar"))
                if not same:
                    a0, a0_bar = extreme_since(cand["a1_bar"], i, cand["d"])
                    leg = abs(cand["a1"] - a0)
                    if leg > 0:
                        if setup is not None:
                            setup["outcome"] = "replaced"
                            res.funnel[f"S{setup['scen']} replaced"] += 1
                        setup = dict(cand, a0=a0, a0_bar=a0_bar, time=t, trig_bar=i, leg_trig=leg, outcome=None)
                        res.setups.append(setup)
                        order = None
                        log(i, f"S{cand['scen']} {'LONG' if cand['d'] == 1 else 'SHORT'} armed a1 {cand['a1']} a0 {a0} leg {leg:.2f}")

        # 9 ── place / move the limit (fill possible 09:30–14:00)
        order = None
        if setup is not None and pos is None and 565 <= mn and mn + 5 < 840:
            s = setup
            inv(s["a1"] == s.setdefault("a1_at_arm", s["a1"]), i, "a1 moved after it was set")
            va = None
            if s["scen"] != 3:
                lo, hi = min(s["a1"], s["a0"]), max(s["a1"], s["a0"])
                vv = value_area(H, L, V, s["a1_bar"], i, lo, hi, p.vp_rows, p.va_pct)
                if vv is not None:
                    vah, val = vv
                    va = (vah - s["a0"]) / (hi - lo) if s["d"] == -1 else (s["a0"] - val) / (hi - lo)
            lvl = choose_level(s["scen"], va, p)
            s["last_va"] = va
            if lvl > 0:
                sl, tl = LEVELS[lvl]
                e, st_, tg = (tick(fib(s["a1"], s["a0"], s["d"], x)) for x in (lvl, sl, tl))
                inv((tg < e < st_) if s["d"] == -1 else (st_ < e < tg), i, f"bracket on wrong side {st_} {e} {tg}")
                through = (c >= e) if s["d"] == -1 else (c <= e)   # [IMPL] a limit through the market is not placed
                if not through:
                    order = dict(d=s["d"], entry=e, stop=st_, tgt=tg, level=lvl, va=va, qty=p.qty)
        if p.trace is not None:
            p.trace.append(dict(t=t, o=o, h=h, l=l, c=c, sw=dict(S["sw"]), s2={k: dict(v) for k, v in S["s2"].items()},
                                setup=None if setup is None else {k: setup.get(k) for k in ("scen", "d", "a1", "a1_bar", "a0", "a0_bar", "last_va")},
                                order=None if order is None else dict(order), pos=None if pos is None else pos["entry"]))
    return res


def load(path: str | None = None) -> pd.DataFrame:
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
