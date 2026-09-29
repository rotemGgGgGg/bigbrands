"""Report: trades by scenario and va_ratio at lock, for each profile range."""
import collections
import re
import sys

import sp_model as m

df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
days = len({t.date() for t in df.index if t.weekday() < 5})
print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}  ({days} weekdays)\n")
for rng in ("leg", "london", "day", "ny"):
    r = m.run(df, m.Params(vp_range=rng))
    f, tr = r.funnel, r.trades
    rs = [t["r"] for t in tr]
    by = collections.Counter(t["scenario"] for t in tr)
    print(f"=== profile range: {rng}")
    print(f"  armed   S1={f['S1_armed']} S2={f['S2_armed']} S3={f['S3_armed']}")
    print(f"  locked  S1={f['S1_locked']} S2={f['S2_locked']} S3={f['S3_locked']}")
    print(f"  deaths  " + ", ".join(f"{k[5:]}={v}" for k, v in sorted(f.items()) if k.startswith("dead_")))
    wins = sum(x > 0 for x in rs)
    print(f"  TRADES  {len(tr)}  (S1={by[1]} S2={by[2]} S3={by[3]})  wins={wins}"
          + (f"  win%={100 * wins / len(rs):.1f}  totalR={sum(rs):+.2f}" if rs else ""))
    locks = [float(x) for x in re.findall(r"S[12] locked @[\d.]+ va=([\d.]+)", "\n".join(r.events))]
    if locks:
        bins = collections.Counter("0.412-0.45" if v < 0.45 else "0.45-0.50" if v < 0.5 else "0.50-0.55" if v < 0.55 else "0.55-0.588" for v in locks)
        print(f"  va_ratio at lock (S1/S2, n={len(locks)}): " + ", ".join(f"{k}: {bins[k]}" for k in ("0.412-0.45", "0.45-0.50", "0.50-0.55", "0.55-0.588")))
    for t in tr:
        va = "  -  " if t["va"] is None else f"{t['va']:.3f}"
        print(f"    {t['entry_time']:%m-%d %H:%M} S{t['scenario']} {t['side']:5} lvl {t['level']:<5} va {va} lock+{t['bars_to_lock']} fill+{t['bars_to_fill']}  leg {t['leg_trigger']:7.2f}  {t['exit']:6} R {t['r']:+.2f}  MFE {t['mfe_r']} MAE {t['mae_r']}")
    print()
