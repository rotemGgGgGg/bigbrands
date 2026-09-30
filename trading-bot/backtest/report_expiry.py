"""Expiry sweep: trades by scenario, total R, median bars trigger→lock and leg growth trigger→lock."""
import collections
import statistics as st
import sys

import sp_model as m

df = m.load(sys.argv[1] if len(sys.argv) > 1 else None)
print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}\n")
def med(x, f="{:.1f}"):
    return f.format(st.median(x)) if x else "-"


print(f"{'expiry':>6} | {'trades':>6} {'S1':>3} {'S2':>3} {'S3':>3} | {'wins':>4} {'totalR':>7} || S1/S2 locks: {'n':>2} {'bars→lock':>9} {'growth':>7} | S3 locks: {'n':>2} {'bars→lock':>9} {'growth':>7}")
for exp in (0, 6, 8, 10, 12, 16, 24):
    r = m.run(df, m.Params(expiry_bars=exp))
    rs = [t["r"] for t in r.trades]
    by = collections.Counter(t["scenario"] for t in r.trades)
    row = f"{'off' if not exp else exp:>6} | {len(rs):6} {by[1]:3} {by[2]:3} {by[3]:3} | {sum(x > 0 for x in rs):4} {sum(rs):+7.2f} ||"
    for grp in ((1, 2), (3,)):
        locks = [(s, s["lock_hist"][-1]) for s in r.setups if s["scen"] in grp and s.get("lock_hist")]
        bars = [lh[0] - s["trig"] for s, lh in locks]
        growth = [lh[3] / s["init"] for s, lh in locks]
        row += f"{'':13} {len(locks):2} {med(bars):>9} {med(growth, '{:.2f}x'):>7} |" if grp == (1, 2) else f"{'':9} {len(locks):2} {med(bars):>9} {med(growth, '{:.2f}x'):>7}"
    print(row)
