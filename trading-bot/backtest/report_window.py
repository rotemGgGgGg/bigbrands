"""Step 3 (diagnostic): trading window 09:30–14:00 vs 09:30–16:00 vs 08:00–14:00, and how close the 14:00 deaths were to filling."""
import collections
import sys

import sp_model as m

df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
months = (df.index[-1] - df.index[0]).days / 30.4
print(f"{'window':12} {'trades':>6} {'S1':>3} {'S2':>3} {'S3':>3} {'wins':>4} {'totalR':>7} {'/month':>6}")
for name, ws, we in (("09:30–14:00", 570, 840), ("09:30–16:00", 570, 960), ("08:00–14:00", 480, 840)):
    r = m.run(df, m.Params(win_start=ws, win_end=we))
    rs = [t["r"] for t in r.trades]
    by = collections.Counter(t["scenario"] for t in r.trades)
    print(f"{name:12} {len(rs):6} {by[1]:3} {by[2]:3} {by[3]:3} {sum(x > 0 for x in rs):4} {sum(rs):+7.2f} {len(rs) / months:6.1f}")

# Setups that died at 14:00 while locked (limit live): would the limit have filled after 14:00, and how soon?
r = m.run(df, m.Params())
H, L, T = list(df.high), list(df.low), list(df.index)
rows = []
for s in r.setups:
    if s["outcome"] != "14:00" or not s.get("lock_hist"):
        continue
    if not s["locked"]:
        rows.append((s, None, "unlocked at 14:00 (re-anchored)"))
        continue
    d, e = s["dir"], s["entry"]
    day = s["time"].date()
    k = next(j for j, t in enumerate(T) if t.date() == day and t.hour * 60 + t.minute >= 840)
    n = None
    for j in range(k, len(T)):
        if T[j].date() != day or T[j].hour * 60 + T[j].minute >= 960:
            break
        if (H[j] >= e) if d == -1 else (L[j] <= e):
            n = j - k + 1
            break
    rows.append((s, n, "" if n else "not reached by 16:00"))
print(f"\nsetups that died at 14:00 with a level locked: {len(rows)}")
for s, n, note in rows:
    print(f"  {s['time']:%m-%d %H:%M} S{s['scen']} {'LONG ' if s['dir'] == 1 else 'SHORT'} entry {s.get('entry') or 0:9.2f}  "
          + (f"filled {n} bar(s) after 14:00" if n else note))
ns = [n for _, n, _ in rows if n]
for N in (1, 3, 6, 12, 24):
    print(f"  within {N:2} bars of 14:00: {sum(1 for x in ns if x <= N)}")
