"""Final numbers for the level-6 survivor(s): per-year with 1 MNQ ($2/pt), win rate, R:R, holding days, plus a causality
check (future days scrambled -> every past trade unchanged) and Lucid 50K Flex days (target $3,000, $2,000 EOD trailing)."""
import copy, numpy as np, pandas as pd
import pdata, engine as E, strats as T
D = pdata.load(); YR = D["days"].year.values; RET = E.day_returns(D)
L = pd.read_csv("levels.csv")
for sid in L[L.level >= 6].sid:
    r = T.REG[sid - 1]; _, hold, mode = r["fn"](D, 1.0)
    net, g, dpn, st = E.daily_eval(hold, RET[mode], mode, D["do"])
    y = YR[st]; usd = net * 2
    runs = np.diff(np.r_[0, np.nonzero(np.diff(np.r_[0, (hold != 0).astype(int), 0]))[0]])[1::2]
    print(f"\n#{sid} {r['name']} — {r['src']}")
    print(f"trades {len(net)} ({len(net)/14.8:.1f}/yr) | win {100*(net>0).mean():.1f}% | R:R {net[net>0].mean()/-net[net<=0].mean():.2f} | avg hold {runs.mean():.1f} days | avg ${usd.mean():.0f}/trade 1 MNQ")
    t = pd.DataFrame(dict(y=y, usd=usd)).groupby("y").agg(trades=("usd", "size"), usd=("usd", "sum"), win=("usd", lambda x: round(100 * (x > 0).mean())))
    t["pct_of_50k"] = (100 * t.usd / 50000).round(1); print(t.round(0).to_string())
    # causality
    rng = np.random.default_rng(1); bad = 0
    for k in rng.choice(len(st) - 3, 30, replace=False):
        d = st[k] + 1; D2 = copy.deepcopy(D)
        for key in ("do", "dh", "dl", "dc"): D2[key][d + 15:] *= rng.uniform(.8, 1.2, len(D2[key]) - d - 15)
        _, h2, _ = r["fn"](D2, 1.0); bad += int(not np.array_equal(h2[:d + 1], hold[:d + 1], equal_nan=True))
    print("future-scramble mismatches:", bad, "/ 30")
    # Lucid 50K Flex eval with 1 MNQ, every calendar trading day counted, start at each year's first day
    eq = pd.Series(dpn * 2, index=D["days"])
    for y0 in range(2012, 2027):
        s = eq[eq.index.year >= y0].cumsum(); peak = s.cummax().clip(lower=0); ok = (s >= 3000); bust = (s <= peak - 2000)
        i_ok = ok.values.argmax() if ok.any() else None; i_b = bust.values.argmax() if bust.any() else None
        res = "funded day %d" % (i_ok + 1) if i_ok is not None and (i_b is None or i_ok < i_b) else ("BLOWN day %d" % (i_b + 1) if i_b is not None else "not reached")
        print(y0, res)
