"""Multi-year backtest of SP Model v7 on a local file.

    python run_years.py MNQ_1min.txt                       # NinjaTrader export, NinjaTrader set to New York time
    python run_years.py MNQ_1min.txt --tz Asia/Jerusalem   # NinjaTrader set to Israel time
    python run_years.py data.csv --out trades.csv

Prints overall, per-year and per-scenario results and writes every trade to a CSV.
"""
import argparse
import collections

import pandas as pd

import sp_v7 as v


def stats(rs):
    n = len(rs)
    w = sum(r > 0 for r in rs)
    eq = peak = dd = 0.0
    streak = worst = 0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
        streak = streak + 1 if r < 0 else 0
        worst = max(worst, streak)
    return n, w, (100 * w / n if n else 0.0), sum(rs), dd, worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--tz", default="America/New_York", help="time zone of the file's timestamps (if they have no offset)")
    ap.add_argument("--stamp", default="auto", choices=["auto", "open", "close"], help="timestamp marks the bar's open or close")
    ap.add_argument("--out", default="trades_v7.csv")
    a = ap.parse_args()

    df = v.load(a.file, tz=a.tz, stamp=a.stamp)
    days = df.index.normalize().nunique()
    months = max((df.index[-1] - df.index[0]).days / 30.4, 1e-9)
    print(f"data: {df.index[0]:%Y-%m-%d %H:%M} → {df.index[-1]:%Y-%m-%d %H:%M} NY  |  {len(df):,} five-minute bars, {days} days")

    r = v.run(df, v.Params())
    tr = r.trades
    rs = [t["r"] for t in tr]
    n, w, wr, tot, dd, streak = stats(rs)
    print(f"\nALL      trades {n}  ({n / months:.1f}/month)  win {wr:.1f}%  total {tot:+.2f}R  avg {(tot / n if n else 0):+.3f}R  "
          f"max drawdown {dd:.2f}R  worst losing streak {streak}")
    print("         breakeven win rate: 46.5% for 0.5 entries (1.15R), 50% for 0.588 entries (1.00R)")

    print(f"\n{'scenario':8} {'trades':>6} {'win%':>6} {'total R':>8} {'avg R':>7}")
    for sc in (1, 2, 3):
        x = [t["r"] for t in tr if t["scenario"] == sc]
        n, w, wr, tot, _, _ = stats(x)
        print(f"S{sc:<7} {n:6} {wr:6.1f} {tot:+8.2f} {(tot / n if n else 0):+7.3f}")
    for lvl in (0.5, 0.588):
        x = [t["r"] for t in tr if t["level"] == lvl]
        n, w, wr, tot, _, _ = stats(x)
        print(f"@{lvl:<7} {n:6} {wr:6.1f} {tot:+8.2f} {(tot / n if n else 0):+7.3f}")

    print(f"\n{'year':6} {'trades':>6} {'/month':>6} {'win%':>6} {'total R':>8} {'max DD R':>8}")
    by_year = collections.defaultdict(list)
    for t in tr:
        by_year[t["entry_time"].year].append(t["r"])
    for y in sorted(by_year):
        x = by_year[y]
        n, w, wr, tot, dd, _ = stats(x)
        span = df[df.index.year == y]
        mo = max((span.index[-1] - span.index[0]).days / 30.4, 1e-9)
        print(f"{y:<6} {n:6} {n / mo:6.1f} {wr:6.1f} {tot:+8.2f} {dd:8.2f}")

    pd.DataFrame(tr).to_csv(a.out, index=False)
    print(f"\n{len(tr)} trades written to {a.out}")
    ends = collections.Counter()
    for s in r.setups:
        ends[f"S{s['scen']} {s['outcome']}"] += 1
    print("setup endings:", dict(sorted(ends.items())))


if __name__ == "__main__":
    main()
