"""Step 1: one row per weekday — London range, sweeps, setups and what ended them — then dead days grouped by cause."""
import collections
import sys

import sp_model as m


def minutes(t):
    return t.hour * 60 + t.minute


def classify(d, ds, setups, trades):
    """Why did this day produce no trade? Returns (cause, detail)."""
    if trades:
        return "TRADE", ""
    if not ds["ldn_valid"]:
        return "A. London range missing", ""
    hs, ls = ds["hi_sw"], ds["lo_sw"]
    hw = hs is not None and minutes(hs) < 840
    lw = ls is not None and minutes(ls) < 840
    if setups:
        ends = collections.Counter(s["outcome"] for s in setups)
        locked = any(s.get("lock_hist") for s in setups)
        top = ends.most_common(1)[0][0]
        if not locked:
            return f"S. setups armed, none ever locked (va never in band / S3 never froze) — last end: {setups[-1]['outcome']}", dict(ends)
        return f"L. setup locked but never filled — {setups[-1]['outcome']}", dict(ends)
    if not hw and not lw:
        return "B. no London level swept before 14:00", ""
    if hw and lw and minutes(max(hs, ls)) >= 570 or (hw and lw):
        return "C. both swept, no two-candle trigger against the second sweep in window", ""
    side = "hi" if hw else "lo"
    in_win = ds["hi_in_win"] if side == "hi" else ds["lo_in_win"]
    if in_win:
        return "D. one side swept in window, no S1 trigger in window", ""
    ref = ds["s2_ref_hi"] if side == "hi" else ds["s2_ref_lo"]
    elig = ds["s2_elig_hi"] if side == "hi" else ds["s2_elig_lo"]
    if ref is None:
        return "E. pre-open sweep, one side: no two-candle pullback after the sweep → no S2 reference", ""
    if elig is None:
        return "F. pre-open sweep, one side: S2 reference never broken", ""
    if minutes(elig) >= 840:
        return "G. pre-open sweep: S2 reference broken after 14:00", ""
    return "H. S2 opened, but no two-candle trigger in window", ""


if __name__ == "__main__":
    df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
    r = m.run(df, m.Params())
    by_day_s = collections.defaultdict(list)
    for s in r.setups:
        by_day_s[s["time"].date()].append(s)
    by_day_t = collections.defaultdict(list)
    for t in r.trades:
        by_day_t[t["entry_time"].date()].append(t)
    days = sorted(d for d in r.days if d.weekday() < 5)
    f = lambda t: "—" if t is None else f"{t:%H:%M}"
    print(f"{'date':10} {'dow':3} {'London H':>9} {'London L':>9} {'hi swept':>8} {'lo swept':>8} | setups (time S# dir → end) | trade")
    causes = collections.Counter()
    detail = collections.defaultdict(list)
    for d in days:
        ds = r.days[d]
        st = by_day_s.get(d, [])
        tr = by_day_t.get(d, [])
        cause, _ = classify(d, ds, st, tr)
        causes[cause] += 1
        detail[cause].append(d)
        stxt = "; ".join(f"{s['time']:%H:%M} S{s['scen']}{'L' if s['dir'] == 1 else 'S'}→{s['outcome']}" for s in st) or "—"
        ttxt = ", ".join(f"S{t['scenario']} {t['r']:+.2f}R" for t in tr) or cause
        print(f"{d} {d:%a} {ds['ldnH'] or 0:9.2f} {ds['ldnL'] or 0:9.2f} {f(ds['hi_sw']):>8} {f(ds['lo_sw']):>8} | {stxt} | {ttxt}")
    print(f"\n{len(days)} weekdays, {len(r.trades)} trades on {len([d for d in days if by_day_t.get(d)])} days\n")
    print("DAYS WITHOUT A TRADE, BY CAUSE")
    for c, n in causes.most_common():
        if c != "TRADE":
            print(f"  {n:2}  {c}")
    ends = collections.Counter((s["scen"], s["outcome"]) for s in r.setups)
    print("\nALL SETUP ENDINGS (scenario, outcome): count")
    for (sc, o), n in sorted(ends.items(), key=lambda x: -x[1]):
        print(f"  S{sc} {o:26} {n}")
