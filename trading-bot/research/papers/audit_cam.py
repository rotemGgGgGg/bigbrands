"""Audit of the Camarilla H3/L3 fades (the only intraday survivors): yearly, gap-at-open fills, stricter fills, worse costs,
and a future-scramble causality check (bars after each day's exit minute and all later days are replaced by noise)."""
import numpy as np, pandas as pd, copy
import pdata, engine as E, strats as T
D = pdata.load(); YR = D["days"].year.values
def run(sid, D=D, cx=1.0, s=1.0): return E.intraday_trades(D, T.REG[sid - 1]["fn"](D, s)[1], cx)
for sid in (110, 111):
    Tr = run(sid); nm = T.REG[sid - 1]["name"]; y = YR[Tr["d"]]
    print("\n", nm, "| trades", len(y), "| win %.1f" % (100 * (Tr["net"] > 0).mean()))
    g = pd.DataFrame(dict(y=y, net=Tr["net"], fm=Tr["fm"])).groupby("y").agg(n=("net", "size"), pts=("net", "sum"), win=("net", lambda x: 100 * (x > 0).mean()))
    print(g.round(1).T.to_string())
    at_open = Tr["fm"] == 0; print("filled at 09:30 open (gap beyond level): %d trades, net %.0f | rest %.0f" % (at_open.sum(), Tr["net"][at_open].sum(), Tr["net"][~at_open].sum()))
    for cx in (2.0, 3.0): print(f"costs x{cx}: net {run(sid, cx=cx)['net'].sum():.0f}")
    for s in (0.75, 1.25): print(f"multiplier x{s}: net {run(sid, s=s)['net'].sum():.0f}")
    # stricter: limit needs 1 full point through, fill exactly at level, no better-than-level fills
    E.TICK = 1.0; t2 = run(sid); E.TICK = 0.25; print(f"limit/target need 1 pt through: net {t2['net'].sum():.0f}, n {len(t2['net'])}")
# causality: scramble everything after day k's exit minute and all later days -> trades up to day k must be identical
rng = np.random.default_rng(0)
for sid in (110, 111):
    Tr = run(sid); bad = 0
    for k in rng.choice(len(Tr["d"]) - 5, 40, replace=False):
        d = Tr["d"][k]; D2 = copy.deepcopy(D)
        for key in ("o", "h", "l", "c"): D2[key][d + 1:] = D2[key][d + 1:] * rng.uniform(.9, 1.1)
        D2["dh"][d + 1:] = D2["h"][d + 1:].max(1); D2["dl"][d + 1:] = D2["l"][d + 1:].min(1); D2["dc"][d + 1:] = D2["c"][d + 1:, -1]; D2["do"][d + 1:] = D2["o"][d + 1:, 0]
        T2 = run(sid, D2); j = np.nonzero(T2["d"] == d)[0]
        if len(j) == 0 or abs(T2["net"][j[0]] - Tr["net"][k]) > 1e-9: bad += 1
    print(T.REG[sid - 1]["name"], "future-scramble mismatches:", bad, "/ 40")
