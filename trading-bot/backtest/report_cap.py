"""Leg-growth cap sweep + S1/S2 timeline (trigger → freeze → band → lock → fill)."""
import collections
import statistics as st
import sys

import sp_model as m

df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
idx = {t: k for k, t in enumerate(df.index)}
months = (df.index[-1] - df.index[0]).days / 30.4
print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d} ({months:.1f} months)\n")
print(f"{'cap':>5} | {'trades':>6} {'S1':>3} {'S2':>3} {'S3':>3} | {'wins':>4} {'totalR':>7} | S1/S2: setups, reached band, locked, filled | median bars trig→lock (S1/S2)")
runs = {}
for cap in (0.0, 2.5, 3.0, 4.0, 5.0):
    r = m.run(df, m.Params(leg_grow_max=cap))
    runs[cap] = r
    rs = [t["r"] for t in r.trades]
    by = collections.Counter(t["scenario"] for t in r.trades)
    s12 = [s for s in r.setups if s["scen"] in (1, 2)]
    reach = sum(1 for s in s12 if any(0.412 <= v <= 0.588 for v in s["va_frozen"]))
    locks = [s["lock_bar"] - s["trig"] for s in s12 if s["lock_bar"] is not None]
    filled = sum(1 for s in s12 if s["outcome"] == "filled")
    print(f"{'off' if not cap else f'{cap}x':>5} | {len(rs):6} {by[1]:3} {by[2]:3} {by[3]:3} | {sum(x > 0 for x in rs):4} {sum(rs):+7.2f} | "
          f"{len(s12):3} {reach:3} {len(locks):3} {filled:3} | {st.median(locks) if locks else '-'}  {sorted(locks)}")

r = runs[0.0]
print("\nS1/S2 TIMELINE, cap off — bars counted from the trigger bar (Feb 16 benchmark: freeze +4, lock +4, fill +6)")
print(f"{'armed':11} {'setup':9} {'leg@trig':>8} {'leg@frz':>8} {'freeze bars':>18} {'re-anc':>6} {'1st band':>8} {'lock':>5} {'va@lock':>7}  outcome")
for s in r.setups:
    if s["scen"] not in (1, 2):
        continue
    t0 = s["trig"]
    fz = [b - t0 for b in s.get("freeze_bars", [])]
    # first in-band bar while frozen: va_frozen aligns with frozen bars in order; recompute via freeze-bar-independent scan
    band = None
    k = 0
    lock = None if s["lock_bar"] is None else s["lock_bar"] - t0
    leg_fz = abs(s["a1"] - s["a0"])
    vm = f"{s['lock_va']:.3f}" if s["lock_va"] is not None else "   -  "
    first_band = next((j for j, v in enumerate(s["va_frozen"]) if 0.412 <= v <= 0.588), None)
    print(f"{s['time']:%m-%d %H:%M} S{s['scen']} {'LONG ' if s['dir'] == 1 else 'SHORT'} {s['init']:8.1f} {leg_fz:8.1f} {str(fz[:6]):>18} {s['refreezes']:6} "
          f"{'-' if first_band is None else '#' + str(first_band + 1):>8} {'-' if lock is None else '+' + str(lock):>5} {vm:>7}  {s['outcome']}")
