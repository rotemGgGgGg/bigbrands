"""Bar-by-bar dump of one day in v7: sweeps, S2 reference/pullback, setup anchors, value area, live limit."""
import sys

import sp_v7 as v

DAY = sys.argv[1] if len(sys.argv) > 1 else "2026-08-10"
df = v.load(None)
tr = []
r = v.run(df, v.Params(trace=tr))
T = list(df.index)
rows = [x for x in tr if f"{x['t']:%Y-%m-%d}" == DAY]
d = df[df.index.strftime("%Y-%m-%d") == DAY]
ldn = d.between_time("00:00", "05:55")
print(f"{DAY}: London high {ldn.high.max():.2f}  London low {ldn.low.min():.2f}")
for e in r.events:
    if e.startswith(DAY):
        print("  event:", e)
f = lambda x: "        -" if x is None else f"{x:9.2f}"
print(f"\n{'time':5} {'O':>9} {'H':>9} {'L':>9} {'C':>9} | {'S2 ref':>9} {'pull':>9} elig | setup {'a1':>9} {'a1@':>5} {'a0':>9} {'leg':>7} {'va':>6} | limit")
for x in rows:
    if x["t"].hour < 6 or x["t"].hour >= 14:
        continue
    s2 = x["s2"][-1] if x["sw"][-1] is not None else x["s2"][1]
    st = x["setup"]
    a1bar = "" if not st else f"{T[st['a1_bar']]:%H:%M}"
    leg = "" if not st else f"{abs(st['a1'] - st['a0']):7.2f}"
    va = "" if not st or st.get("last_va") is None else f"{st['last_va']:.3f}"
    od = x["order"]
    otxt = "" if not od else f"{'SELL' if od['d'] == -1 else 'BUY'} {od['entry']:.2f} @{od['level']} stop {od['stop']:.2f} tgt {od['tgt']:.2f}"
    print(f"{x['t']:%H:%M} {x['o']:9.2f} {x['h']:9.2f} {x['l']:9.2f} {x['c']:9.2f} | {f(s2['ref'])} {f(s2['pull'])} {'Y' if s2['elig'] else 'n':>4} | "
          f"{('S' + str(st['scen']) + ('L' if st['d'] == 1 else 'S')) if st else '    ':5} {f(st['a1'] if st else None)} {a1bar:>5} {f(st['a0'] if st else None)} {leg:>7} {va:>6} | {otxt}"
          + (f"  IN POSITION @{x['pos']:.2f}" if x["pos"] else ""))
    if x["t"].hour == 10 and x["t"].minute >= 30:
        break
