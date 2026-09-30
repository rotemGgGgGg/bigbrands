"""Pre-open sweep rule: before vs after, S2 swing-high toggle off vs on."""
import collections
import datetime as dt
import importlib.util
import sys

import sp_model as m

prev_path = sys.argv[1] if len(sys.argv) > 1 else None
DEAD = [dt.date(2026, 9, d) for d in (9, 10, 11, 16, 17, 18, 21, 23)]
df = m.load(None)
weekdays = sorted({t.date() for t in df.index if t.weekday() < 5})

runs = []
if prev_path:
    spec = importlib.util.spec_from_file_location("prev", prev_path)
    prev = importlib.util.module_from_spec(spec)
    sys.modules["prev"] = prev
    spec.loader.exec_module(prev)
    runs.append(("before (S2 only after S1 fails)", prev.run(df, prev.Params())))
runs.append(("after, swing-high toggle OFF", m.run(df, m.Params(s2_swing_highs=False))))
runs.append(("after, swing-high toggle ON", m.run(df, m.Params(s2_swing_highs=True))))

print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d} ({len(weekdays)} weekdays)\n")
for name, r in runs:
    rs = [t["r"] for t in r.trades]
    by = collections.Counter(t["scenario"] for t in r.trades)
    rby = collections.defaultdict(float)
    for t in r.trades:
        rby[t["scenario"]] += t["r"]
    days_with_setup = {s["time"].date() for s in r.setups}
    dead_now = [d for d in DEAD if d in days_with_setup]
    armed = collections.Counter(s["scen"] for s in r.setups)
    print(f"=== {name}")
    print(f"  trades {len(rs)}  S1={by[1]} S2={by[2]} S3={by[3]}  wins {sum(x > 0 for x in rs)}  totalR {sum(rs):+.2f}"
          f"   (R by scenario: S1 {rby[1]:+.2f}, S2 {rby[2]:+.2f}, S3 {rby[3]:+.2f})")
    print(f"  setups armed: S1={armed[1]} S2={armed[2]} S3={armed[3]}   days with ≥1 setup: {len(days_with_setup)}/{len(weekdays)}")
    print(f"  previously-dead days (Sep 9,10,11,16,17,18,21,23) with a setup now: {len(dead_now)}/8  {[d.strftime('%m-%d') for d in dead_now]}")
    for s in r.setups:
        if s["time"].date() in DEAD:
            print(f"      {s['time']:%m-%d %H:%M} S{s['scen']} {'LONG ' if s['dir'] == 1 else 'SHORT'} leg {s['init']:7.2f} "
                  f"opened by {s.get('s2why', '-'):9} locked {'yes' if s.get('lock_hist') else 'no ':3}  → {s['outcome']}")
    s2t = [t for t in r.trades if t["scenario"] == 2]
    for t in s2t:
        print(f"    S2 trade {t['entry_time']:%m-%d %H:%M} {t['side']} lvl {t['level']} va {t['va']:.3f} leg {t['leg_trigger']:.1f} {t['exit']} R {t['r']:+.2f}")
    print()
