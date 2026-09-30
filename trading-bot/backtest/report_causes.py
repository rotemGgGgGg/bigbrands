"""Step 2: each candidate cause tested alone against the baseline."""
import collections
import sys

import sp_model as m

df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
months = (df.index[-1] - df.index[0]).days / 30.4
tests = [
    ("baseline (v6.1 rules)", {}),
    ("[IMPL] lock bar closed through entry → place limit anyway", dict(t_place_through=True)),
    ("[IMPL] first trigger candle may close before 09:30", dict(t_trigger_preopen=True)),
    ("[IMPL] re-trigger may reuse the bar a setup died on", dict(t_retrigger_overlap=True)),
    ("[diagnostic, unstated] new trigger replaces an unlocked setup", dict(replace_unlocked=True)),
]
print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}  ({months:.1f} months)\n")
print(f"{'test':62} {'trades':>6} {'S1':>3} {'S2':>3} {'S3':>3} {'wins':>4} {'totalR':>7} {'/month':>6}")
for name, kw in tests:
    r = m.run(df, m.Params(**kw))
    rs = [t["r"] for t in r.trades]
    by = collections.Counter(t["scenario"] for t in r.trades)
    print(f"{name:62} {len(rs):6} {by[1]:3} {by[2]:3} {by[3]:3} {sum(x > 0 for x in rs):4} {sum(rs):+7.2f} {len(rs) / months:6.1f}")
