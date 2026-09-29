"""a0-from-a1 fix: trades by scenario, leg sizes and va_ratio distribution, before vs after, v3 and v4."""
import collections
import statistics as st
import sys

import sp_model as v4
import sp_model_v3 as v3

df = v4.load(sys.argv[1] if len(sys.argv) > 1 else None)
months = (df.index[-1] - df.index[0]).days / 30.4
print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d} ({months:.1f} months)\n")


def legs_from_events(r):
    out = collections.defaultdict(list)
    for e in r.events:
        if " armed leg=" in e or " rejected leg=" in e:
            scen = e.split()[2]
            out[scen].append(float(e.rsplit("leg=", 1)[1]))
    return out


print("TRADES BY SCENARIO")
print(f"  {'version':6} {'a0 from':8} {'trades':>6} {'S1':>3} {'S2':>3} {'S3':>3} {'wins':>4} {'win%':>6} {'totalR':>7} {'S1 R':>6}  {'S1/mo':>5}")
runs = {}
for name, mod in (("v3", v3), ("v4", v4)):
    for fix in (False, True):
        r = mod.run(df, mod.Params(a0_from_a1=fix))
        runs[(name, fix)] = r
        rs = [t["r"] for t in r.trades]
        by = collections.Counter(t["scenario"] for t in r.trades)
        w = sum(x > 0 for x in rs)
        s1r = sum(t["r"] for t in r.trades if t["scenario"] == 1)
        print(f"  {name:6} {'a1 bar' if fix else 'sweep':8} {len(rs):6} {by[1]:3} {by[2]:3} {by[3]:3} {w:4} "
              f"{(100 * w / len(rs) if rs else 0):6.1f} {sum(rs):+7.2f} {s1r:+6.2f}  {by[1] / months:5.1f}")

print("\nLEG SIZE AT TRIGGER (points), every trigger incl. re-triggers — v4")
for fix in (False, True):
    L = legs_from_events(runs[("v4", fix)])
    parts = [f"{k} n={len(v)} median={st.median(v):.1f}" for k, v in sorted(L.items())]
    print(f"  a0 from {'a1 bar' if fix else 'sweep '}: " + " | ".join(parts))

for fix in (False, True):
    r = runs[("v4", fix)]
    print(f"\nVA_RATIO — v4, a0 from {'a1 bar' if fix else 'sweep'}")
    s12 = [s for s in r.setups if s["scen"] in (1, 2)]
    allv = [v for s in s12 for v in s["va_frozen"]]
    bins = [(-9, 0.412, "<0.412"), (0.412, 0.5, "0.412-0.5"), (0.5, 0.588, "0.5-0.588"), (0.588, 0.7, "0.588-0.7"), (0.7, 0.85, "0.7-0.85"), (0.85, 9, ">0.85")]
    hist = {lab: sum(lo <= v < hi for v in allv) for lo, hi, lab in bins}
    print(f"  S1/S2 per-bar (frozen bars, n={len(allv)}): " + ", ".join(f"{k} {v}" for k, v in hist.items()))
    locks = [s["lock_va"] for s in s12 if s["lock_va"] is not None]
    print(f"  S1/S2 setups {len(s12)} | reached band {sum(1 for s in s12 if any(0.412 <= v <= 0.588 for v in s['va_frozen']))} | locked {len(locks)} "
          f"| va at lock: {', '.join(f'{v:.3f}' for v in sorted(locks)) or '-'}")
    print(f"  {'armed':11} {'setup':9} {'leg':>7} {'min va':>7}  outcome")
    for s in s12:
        mv = min(s["va_frozen"]) if s["va_frozen"] else None
        print(f"  {s['time']:%m-%d %H:%M} S{s['scen']} {'LONG ' if s['dir'] == 1 else 'SHORT'} {s['init']:7.2f} {'   n/a' if mv is None else f'{mv:7.3f}'}  {s['outcome']}")

print("\nTRADES — v4, a0 from a1 bar")
for t in runs[("v4", True)].trades:
    va = "  -  " if t["va"] is None else f"{t['va']:.3f}"
    print(f"  {t['entry_time']:%m-%d %H:%M} S{t['scenario']} {t['side']:5} lvl {t['level']:<5} va {va} leg {t['leg_trigger']:7.2f} {t['exit']:6} R {t['r']:+.2f}")
