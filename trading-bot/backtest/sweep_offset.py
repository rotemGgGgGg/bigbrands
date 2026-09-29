"""Sweep the volume-profile start: N bars before the 1.0 anchor bar / the sweep bar, plus the swing-low anchor."""
import collections
import sys
from concurrent.futures import ProcessPoolExecutor

import sp_model as m

DF = None


def init(path):
    global DF
    DF = m.load(path)


def band(x):
    return 0.412 <= x <= 0.588


def one(cfg):
    anchor, n, k, price = cfg
    r = m.run(DF, m.Params(vp_range="leg", vp_anchor=anchor, vp_offset=n, swing_k=k, vp_price=price))
    s12 = [s for s in r.setups if s["scen"] in (1, 2)]
    reach = [s for s in s12 if any(band(v) for v in s["va_frozen"])]
    by = collections.Counter(t["scenario"] for t in r.trades)
    rs = [t["r"] for t in r.trades]
    s1r = sum(t["r"] for t in r.trades if t["scenario"] in (1, 2))
    return cfg, len(s12), len(reach), sum(1 for s in reach if s["scen"] == 1), by, len(rs), sum(x > 0 for x in rs), sum(rs), s1r


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '-' else None
    df = m.load(path)
    months = (df.index[-1] - df.index[0]).days / 30.4
    price = sys.argv[2] if len(sys.argv) > 2 else "anchors"
    cfgs = [(a, n, 2, price) for a in ("a1", "sweep") for n in range(21)] + [("swing", 0, k, price) for k in (1, 2, 3)]
    print(f"profile rows span: {price}")
    with ProcessPoolExecutor(initializer=init, initargs=(path,)) as ex:
        res = list(ex.map(one, cfgs))
    print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}  ({months:.1f} months)\n")
    print(f"{'anchor':7} {'N/k':>3} | {'S1/S2 armed':>11} {'reached band':>12} {'(S1)':>5} | {'trades':>6} {'S1':>3} {'S2':>3} {'S3':>3} | {'wins':>4} {'totalR':>7} {'S1+S2 R':>8} | {'S1/mo':>5}")
    last = None
    for (anchor, n, k, _), armed, reach, reach1, by, nt, w, tr, s12r in res:
        if last and last != anchor:
            print()
        last = anchor
        print(f"{anchor:7} {n if anchor != 'swing' else k:>3} | {armed:>11} {reach:>12} {reach1:>5} | {nt:>6} {by[1]:>3} {by[2]:>3} {by[3]:>3} | {w:>4} {tr:>+7.2f} {s12r:>+8.2f} | {by[1] / months:>5.1f}")
