"""v4 report: trades by scenario + minimum va_ratio per S1/S2 setup."""
import collections
import sys

import sp_model as m

df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
for rng in ("leg", "london", "day", "ny"):
    r = m.run(df, m.Params(vp_range=rng))
    tr, rs = r.trades, [t["r"] for t in r.trades]
    by = collections.Counter(t["scenario"] for t in tr)
    w = sum(x > 0 for x in rs)
    print(f"=== profile {rng}: trades {len(tr)} (S1={by[1]} S2={by[2]} S3={by[3]}) wins {w}"
          + (f"  win% {100 * w / len(rs):.1f}  totalR {sum(rs):+.2f}" if rs else ""))
    if rng != "leg":
        continue
    for t in tr:
        va = "  -  " if t["va"] is None else f"{t['va']:.3f}"
        print(f"    {t['entry_time']:%m-%d %H:%M} S{t['scenario']} {t['side']:5} lvl {t['level']:<5} va {va} lock+{t['bars_to_lock']} fill+{t['bars_to_fill']} {t['exit']:6} R {t['r']:+.2f}")
    print("\n  S1/S2 setups — min va_ratio (frozen bars / all bars), bars, re-anchors, outcome")
    mins = []
    for s in r.setups:
        if s["scen"] == 3:
            continue
        vf, va = s["va_frozen"], s["va_all"]
        mf = min(vf) if vf else None
        mins.append(mf if mf is not None else (min(va) if va else None))
        print(f"    {s['time']:%m-%d %H:%M} S{s['scen']} {'LONG ' if s['dir'] == 1 else 'SHORT'} "
              f"min frozen {'  n/a' if mf is None else f'{mf:.3f}'}  min all {min(va) if va else float('nan'):.3f}  "
              f"bars {len(va):2d}  re-anchor {s['refreezes']}  → {s['outcome']}")
    ok = [x for x in mins if x is not None]
    print(f"\n  S1/S2 setups: {len(ok)}   min<0.588: {sum(x <= 0.588 for x in ok)}   min<0.70: {sum(x < 0.70 for x in ok)}   median of mins: {sorted(ok)[len(ok) // 2]:.3f}\n")
