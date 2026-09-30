"""Scenario ablation: all on vs S3 off vs S3 only, R per scenario, plus a sanity check on sample size."""
import collections
import math
import sys

import sp_model as m

df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}\n")
cfgs = [("all three (baseline)", dict()), ("S1 + S2 only (S3 off)", dict(use_s3=False)), ("S3 only", dict(use_s1=False, use_s2=False))]
res = {}
print(f"{'config':24} {'trades':>6} {'wins':>4} {'win%':>6} {'totalR':>7} {'avgR':>6} {'maxDD R':>7} | R per scenario (n, wins, R)")
for name, kw in cfgs:
    r = m.run(df, m.Params(**kw))
    rs = [t["r"] for t in r.trades]
    eq, peak, dd = 0.0, 0.0, 0.0
    for x in rs:
        eq += x; peak = max(peak, eq); dd = max(dd, peak - eq)
    per = collections.defaultdict(list)
    for t in r.trades:
        per[t["scenario"]].append(t["r"])
    w = sum(x > 0 for x in rs)
    parts = [f"S{k}: {len(v)}, {sum(x > 0 for x in v)}, {sum(v):+.2f}" for k, v in sorted(per.items())]
    print(f"{name:24} {len(rs):6} {w:4} {100 * w / len(rs) if rs else 0:6.1f} {sum(rs):+7.2f} {(sum(rs) / len(rs) if rs else 0):+6.2f} {dd:7.2f} | " + " | ".join(parts))
    res[name] = r

print("\nTrades that differ between 'all three' and 'S3 off':")
a = {(t["entry_time"], t["scenario"]) for t in res["all three (baseline)"].trades}
b = {(t["entry_time"], t["scenario"]) for t in res["S1 + S2 only (S3 off)"].trades}
for t in res["all three (baseline)"].trades:
    if (t["entry_time"], t["scenario"]) not in b:
        print(f"  only with S3 on : {t['entry_time']:%m-%d %H:%M} S{t['scenario']} {t['side']} R {t['r']:+.2f}")
for t in res["S1 + S2 only (S3 off)"].trades:
    if (t["entry_time"], t["scenario"]) not in a:
        print(f"  only with S3 off: {t['entry_time']:%m-%d %H:%M} S{t['scenario']} {t['side']} R {t['r']:+.2f}")


def p_at_least(k, n, p):
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


print("\nHow much can these samples say? (chance of the observed wins or better if the true win rate were only breakeven)")
for label, k, n, be in (("S1+S2, backtester", None, None, 0.48), ("S1+S2, TradingView 3/3", 3, 3, 0.48), ("S3, TradingView 3/7", 3, 7, 0.465)):
    if k is None:
        v = [t["r"] for t in res["S1 + S2 only (S3 off)"].trades]
        k, n = sum(x > 0 for x in v), len(v)
    print(f"  {label:26} {k}/{n} wins → P(≥{k} wins | breakeven {be:.0%}) = {p_at_least(k, n, be):.2f}")
