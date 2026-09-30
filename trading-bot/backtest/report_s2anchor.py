"""S2 anchor_1 change: before (trigger-candle wick) vs after (S1's anchor_0 / pre-open pullback extreme)."""
import collections
import importlib.util
import sys

import sp_model as m

df = m.load(None)
spec = importlib.util.spec_from_file_location("prev", sys.argv[1])
prev = importlib.util.module_from_spec(spec)
sys.modules["prev"] = prev
spec.loader.exec_module(prev)

print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}\n")
out = {}
for name, mod in (("before: S2 1.0 = trigger-candle wick", prev), ("after:  S2 1.0 = S1's anchor_0", m)):
    r = mod.run(df, mod.Params())
    out[name] = r
    rs = [t["r"] for t in r.trades]
    by = collections.Counter(t["scenario"] for t in r.trades)
    rby = collections.defaultdict(float)
    for t in r.trades:
        rby[t["scenario"]] += t["r"]
    s2 = [s for s in r.setups if s["scen"] == 2]
    s2f = [s for s in s2 if s["outcome"] == "filled"]
    ends = collections.Counter(s["outcome"] for s in s2)
    print(f"=== {name}")
    print(f"  trades {len(rs)} (S1={by[1]} S2={by[2]} S3={by[3]})  wins {sum(x > 0 for x in rs)}  totalR {sum(rs):+.2f}   R: S1 {rby[1]:+.2f} S2 {rby[2]:+.2f} S3 {rby[3]:+.2f}")
    print(f"  S2 setups armed {len(s2)}, filled {len(s2f)}   ends: {dict(ends)}")
    legs = sorted(s["init"] for s in s2)
    if legs:
        print(f"  S2 leg at trigger: median {legs[len(legs) // 2]:.1f}  min {legs[0]:.1f}  max {legs[-1]:.1f}")
    for t in r.trades:
        if t["scenario"] == 2:
            print(f"    S2 trade {t['entry_time']:%m-%d %H:%M} {t['side']} lvl {t['level']} va {t['va']:.3f} leg {t['leg_trigger']:.1f} {t['exit']} R {t['r']:+.2f}")
    print()

print("Sep 3 S2 under the new rule:")
for s in out["after:  S2 1.0 = S1's anchor_0"].setups:
    if f"{s['time']:%Y-%m-%d}" == "2026-09-03" and s["scen"] == 2:
        print(f"  armed {s['time']:%H:%M}  a1 {s['a1']:.2f}  a0 {s['a0']:.2f}  leg {abs(s['a1'] - s['a0']):.2f}  "
              f"0.5 = {s['a0'] - abs(s['a1'] - s['a0']) * 0.5:.2f}  locked {'yes' if s.get('lock_hist') else 'no'}  → {s['outcome']}")
