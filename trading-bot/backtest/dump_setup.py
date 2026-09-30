"""Bar-by-bar dump of every setup on one day: anchors, fib prices, freeze/lock state and the live limit."""
import sys

import sp_model as m

DAY = sys.argv[1] if len(sys.argv) > 1 else "2026-09-03"
df = m.load(None)
tr = []
m.run(df, m.Params(trace=tr))
fmt = lambda x: "      -  " if x is None else f"{x:9.2f}"
print(f"{'time':5} {'H':>9} {'L':>9} | {'S':1} {'a1':>9} {'a0':>9} {'leg':>7} {'0.5':>9} {'0.588':>9} {'ext':>3} {'frz':>3} {'lock':>4} {'lvl':>5} {'lockedEntry':>11} {'limit':>9} | event")
for x in tr:
    if f"{x['t']:%Y-%m-%d}" != DAY:
        continue
    ev = []
    if x["dead"]:
        ev.append("DEAD: " + x["dead"])
    if x["closed"]:
        ev.append(f"EXIT {x['closed'][0]} @{x['closed'][1]:.2f}")
    if x["pos"] and not x["scen"]:
        pz = x["pos"]
        ev.append(f"IN POS entry {pz['entry']:.2f} stop {pz['stop']:.2f} tgt {pz['tgt']:.2f} (a1 {pz['a1']:.2f} a0 {pz['a0']:.2f})")
    a1, a0 = x["a1"], x["a0"]
    leg = None if a1 is None else abs(a1 - a0)
    f05 = f0588 = None
    if a1 is not None:
        d = 1 if a0 > a1 else -1
        f05 = a0 - leg * 0.5 if d == 1 else a0 + leg * 0.5
        f0588 = a0 - leg * 0.588 if d == 1 else a0 + leg * 0.588
    yn = lambda b: "" if b is None else ("Y" if b else "n")
    print(f"{x['t']:%H:%M} {x['h']:9.2f} {x['l']:9.2f} | {x['scen'] or ' '} {fmt(a1)} {fmt(a0)} {('      -' if leg is None else f'{leg:7.2f}')} {fmt(f05)} {fmt(f0588)} "
          f"{yn(x['extending']):>3} {yn(x['frozen']):>3} {yn(x['locked']):>4} {(x['level'] or 0):5} {fmt(x['entry']):>11} {fmt(x['order'])} | {'; '.join(ev)}")
d = df[df.index.strftime("%Y-%m-%d") == DAY]
w = d.between_time("06:00", "13:55")
print(f"\nday low 06:00-14:00: {w.low.min():.2f} at {w.low.idxmin():%H:%M}   day high: {w.high.max():.2f} at {w.high.idxmax():%H:%M}")
print(f"bars with a low within 15 pts of 29,240: " + ", ".join(f"{t:%H:%M} ({v:.2f})" for t, v in w.low.items() if abs(v - 29240) <= 15))
