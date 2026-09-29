"""v3 vs v4 trades, and minimum va_ratio per S1/S2 setup on the fib-leg and London profiles.

The London figure is computed on the same setups as the fib-leg run (shadow calculation),
so the two columns are directly comparable.
"""
import collections
import dataclasses
import sys

import sp_model as v4
import sp_model_v3 as v3

df = v4.load(sys.argv[1] if len(sys.argv) > 1 else None)
print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}\n")

print("1) TRADES BY SCENARIO")
print(f"   {'version':8} {'profile':7} {'trades':>6} {'S1':>3} {'S2':>3} {'S3':>3} {'wins':>5} {'win%':>6} {'totalR':>7}")
for name, mod in (("v3", v3), ("v4", v4)):
    for rng in ("leg", "london"):
        r = mod.run(df, mod.Params(vp_range=rng))
        rs = [t["r"] for t in r.trades]
        by = collections.Counter(t["scenario"] for t in r.trades)
        w = sum(x > 0 for x in rs)
        wr = f"{100 * w / len(rs):.1f}" if rs else "-"
        print(f"   {name:8} {rng:7} {len(rs):6} {by[1]:3} {by[2]:3} {by[3]:3} {w:5} {wr:>6} {sum(rs):+7.2f}")

# Shadow: every time the fib-leg run computes va_ratio, also compute it on the London range.
orig = v4.va_ratio


def shadow(bars, p, setup, i, *rest):
    va = orig(bars, p, setup, i, *rest)
    ldn = orig(bars, dataclasses.replace(p, vp_range="london"), setup, i, *rest)
    if ldn is not None:
        setup.setdefault("ldn_all", []).append(ldn)
        if setup["frozen"]:
            setup.setdefault("ldn_frozen", []).append(ldn)
    return va


v4.va_ratio = shadow
r = v4.run(df, v4.Params(vp_range="leg"))
v4.va_ratio = orig


def mn(xs):
    return min(xs) if xs else None


def f(x):
    return "  n/a" if x is None else f"{x:.3f}"


def band(x):
    return x is not None and 0.412 <= x <= 0.588


print("\n2+3) EVERY S1/S2 SETUP (v4, fib-leg run) — minimum va_ratio over its life")
print("     'all' = every bar while armed; 'frozen' = only bars after the anchors froze; * = min reached the 0.412–0.588 band")
print(f"   {'armed':11} {'scen':9} {'bars':>4} {'re-anc':>6}  {'LEG all':>8} {'LEG frz':>8}  {'LDN all':>8} {'LDN frz':>8}  outcome")
rows = []
for s in r.setups:
    if s["scen"] == 3:
        continue
    la, lf = mn(s["va_all"]), mn(s["va_frozen"])
    da, dfz = mn(s.get("ldn_all", [])), mn(s.get("ldn_frozen", []))
    rows.append((la, lf, da, dfz))
    star = lambda x: ("*" if band(x) else " ")
    print(f"   {s['time']:%m-%d %H:%M} S{s['scen']} {'LONG ' if s['dir'] == 1 else 'SHORT'}  {len(s['va_all']):4} {s['refreezes']:6}  "
          f"{f(la)}{star(la)}  {f(lf)}{star(lf)}   {f(da)}{star(da)}  {f(dfz)}{star(dfz)}  {s['outcome']}")

n = len(rows)
cnt = lambda k, test: sum(1 for row in rows if row[k] is not None and test(row[k]))
print(f"\n   S1/S2 setups: {n}")
for k, label in ((0, "LEG all"), (1, "LEG frozen"), (2, "LDN all"), (3, "LDN frozen")):
    print(f"   {label:11} min in band: {cnt(k, band):2}   min < 0.70: {cnt(k, lambda x: x < 0.70):2}   min > 0.588: {cnt(k, lambda x: x > 0.588):2}   min < 0.412: {cnt(k, lambda x: x < 0.412):2}")
only_ldn = sum(1 for la, lf, da, dfz in rows if band(dfz) and not band(lf))
print(f"\n   setups where London (frozen) reaches the band but the fib leg (frozen) does not: {only_ldn}")
