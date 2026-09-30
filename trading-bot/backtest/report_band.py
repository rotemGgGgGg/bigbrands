"""VA band sweep: lower bound, upper bound, grid, plus the 08:00 window — all on the corrected engine."""
import collections
import sys
from concurrent.futures import ProcessPoolExecutor

import report_days as rd
import sp_model as m

DF = None


def init():
    global DF
    DF = m.load(None)


def run(kw):
    r = m.run(DF, m.Params(**kw))
    rs = [t["r"] for t in r.trades]
    by = collections.Counter(t["scenario"] for t in r.trades)
    days = {t["entry_time"].date() for t in r.trades}
    return kw, len(rs), by[1], by[2], by[3], sum(x > 0 for x in rs), sum(rs), days


if __name__ == "__main__":
    df = m.load(None)
    months = (df.index[-1] - df.index[0]).days / 30.4
    base = m.run(df, m.Params())
    by_s = collections.defaultdict(list)
    for s in base.setups:
        by_s[s["time"].date()].append(s)
    trade_days = {t["entry_time"].date() for t in base.trades}
    va_dead = sorted(d for d in base.days if d.weekday() < 5 and d not in trade_days
                     and rd.classify(d, base.days[d], by_s.get(d, []), [])[0].startswith("S."))
    print(f"data {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d} ({months:.1f} months); 'VA never in band' days: {len(va_dead)}\n")

    lows = [0.25, 0.30, 0.35, 0.40, 0.412, 0.45]
    highs = [0.588, 0.65, 0.70, 0.75]
    cfgs = [dict(va_low=lo) for lo in lows] + [dict(va_high=hi) for hi in highs] + \
           [dict(va_low=lo, va_high=hi) for lo in lows for hi in highs] + \
           [dict(win_start=480), dict(win_start=480, va_low=0.30), dict(win_start=480, va_high=0.70)]
    with ProcessPoolExecutor(initializer=init) as ex:
        res = {tuple(sorted(k.items())): v for k, *v in ex.map(run, cfgs)}

    def row(kw, label):
        n, s1, s2, s3, w, R, days = res[tuple(sorted(kw.items()))]
        rescued = sum(1 for d in va_dead if d in days)
        print(f"  {label:18} {n:6} {s1:3} {s2:3} {s3:3} {w:4} {R:+7.2f} {n / months:6.1f}   {rescued:2}/{len(va_dead)}")

    hdr = f"  {'':18} {'trades':>6} {'S1':>3} {'S2':>3} {'S3':>3} {'wins':>4} {'totalR':>7} {'/month':>6}   VA-dead days now traded"
    print("1) LOWER BOUND (upper fixed 0.588)\n" + hdr)
    for lo in lows:
        row(dict(va_low=lo), f"low {lo}")
    print("\n2) UPPER BOUND (lower fixed 0.412)\n" + hdr)
    for hi in highs:
        row(dict(va_high=hi), f"high {hi}")
    print("\n3) GRID — trades / total R   (rows: lower bound, columns: upper bound)")
    print("  low \\ high " + "".join(f"{hi:>16}" for hi in highs))
    for lo in lows:
        cells = []
        for hi in highs:
            n, *_, R, _ = res[tuple(sorted(dict(va_low=lo, va_high=hi).items()))]
            cells.append(f"{n:>3} / {R:+6.2f}R")
        print(f"  {lo:<10} " + "".join(f"{c:>16}" for c in cells))
    print("\n4) 08:00–14:00 WINDOW (corrected engine)\n" + hdr)
    row(dict(win_start=480), "08:00, band as is")
    row(dict(win_start=480, va_low=0.30), "08:00, low 0.30")
    row(dict(win_start=480, va_high=0.70), "08:00, high 0.70")
