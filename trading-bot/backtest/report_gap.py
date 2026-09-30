"""Setup-level log and per-day funnel for a date window (default Sep 3 – Sep 25, 2026)."""
import collections
import datetime as dt
import sys

import sp_model as m

START, END = dt.date(2026, 9, 3), dt.date(2026, 9, 25)
df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
r = m.run(df, m.Params())


def band_dist(v):
    return 0.0 if 0.412 <= v <= 0.588 else min(abs(v - 0.412), abs(v - 0.588))


print("SETUP LOG — every setup that armed")
print(f"{'date':10} {'time':5} {'setup':9} {'leg@trig':>8} {'locked':>6} {'va (lock / closest)':>20} {'re-anc':>6}  ended by")
per_day = collections.defaultdict(list)
for s in r.setups:
    d = s["time"].date()
    if not START <= d <= END:
        continue
    per_day[d].append(s)
    lh = s.get("lock_hist")
    if s["scen"] == 3:
        vtxt = "n/a (S3)"
    elif lh:
        vtxt = f"{lh[-1][2]:.3f} at lock"
    else:
        vals = s["va_frozen"] or s["va_all"]
        vtxt = f"{min(vals, key=band_dist):.3f} closest" if vals else "never frozen"
    print(f"{d} {s['time']:%H:%M} S{s['scen']} {'LONG ' if s['dir'] == 1 else 'SHORT'} {s['init']:8.2f} {'yes' if lh else 'no':>6} {vtxt:>20} {s['refreezes']:6}  {s['outcome']}")

# rejected triggers (leg == 0) and trades in the window
rej = [e for e in r.events if "rejected" in e and START <= dt.date.fromisoformat(e[:10]) <= END]
trd = [t for t in r.trades if START <= t["entry_time"].date() <= END]
print(f"\nrejected triggers in window: {len(rej)}   trades in window: {len(trd)}")
for t in trd:
    print(f"  trade {t['entry_time']:%m-%d %H:%M} S{t['scenario']} {t['side']} R {t['r']:+.2f}")

print("\nPER-DAY FUNNEL — why a day did or did not produce a setup (times NY, window 09:30–14:00)")
print(f"{'date':10} {'dow':3} {'London H / L':>21} {'high swept':>11} {'low swept':>11}  {'setups':>6}  note")
for day, g in df.groupby(df.index.date):
    if not START <= day <= END or day.weekday() >= 5:
        continue
    ldn = g.between_time("00:00", "05:55")
    if len(ldn) < 60:
        print(f"{day} {day:%a} {'London range missing':>21}"); continue
    H, L = ldn.high.max(), ldn.low.min()
    after = g.between_time("06:00", "23:55")
    hs = after[after.high > H].index.min()
    ls = after[after.low < L].index.min()
    fmt = lambda x: "—" if x is None or x != x else f"{x:%H:%M}"
    inwin = lambda x: x is not None and x == x and (9 * 60 + 30) <= x.hour * 60 + x.minute < 14 * 60
    n = len(per_day.get(day, []))
    both_pre = (hs == hs and ls == ls and hs is not None and ls is not None and max(hs, ls).hour * 60 + max(hs, ls).minute < 570)
    if n:
        note = ", ".join(f"S{s['scen']}→{s['outcome']}" for s in per_day[day])
    elif not inwin(hs) and not inwin(ls) and not both_pre:
        note = "no London level swept inside 09:30–14:00 → no S1; not both swept → no S3"
    elif both_pre or (hs == hs and ls == ls):
        note = "both swept, but no two-candle trigger against the second sweep in window"
    else:
        note = "one level swept in window, but no two-candle trigger against it in window"
    print(f"{day} {day:%a} {H:10.2f} / {L:9.2f} {fmt(hs):>11} {fmt(ls):>11}  {n:6}  {note}")
