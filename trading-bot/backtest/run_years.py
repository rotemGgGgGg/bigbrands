"""Multi-year backtest of SP Model v7 on a local file.

    python run_years.py MNQ_1min.txt                       # NinjaTrader export, NinjaTrader set to New York time
    python run_years.py MNQ_1min.txt --tz Asia/Jerusalem   # NinjaTrader set to Israel time
    python run_years.py data.csv --out trades.csv

Prints overall, per-year and per-scenario results and writes every trade to a CSV.
"""
import argparse
import collections
import os

import pandas as pd

import sp_v8 as v


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


def load_many(paths, tz, stamp):
    """One file as is. Several (one per contract, e.g. MNQ MAR26 / JUN26 / ...): each New York day comes from the
    contract that traded the most that day — the front month — so the roll needs no price adjustment."""
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith((".txt", ".csv")))
        else:
            files.append(p)
    if len(files) == 1:
        return v.load(files[0], tz=tz, stamp=stamp)
    frames = []
    for f in files:
        d = v.load(f, tz=tz, stamp=stamp)
        print(f"  {os.path.basename(f)}: {d.index[0]:%Y-%m-%d} → {d.index[-1]:%Y-%m-%d}")
        frames.append(d)
    vol = pd.concat([d["volume"].groupby(d.index.date).sum().rename(i) for i, d in enumerate(frames)], axis=1).fillna(0)
    pick = vol.idxmax(axis=1)
    parts = [frames[i][pd.Index(frames[i].index.date).isin(list(pick[pick == i].index))] for i in range(len(frames))]
    return pd.concat(parts).sort_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="one file, several contract files, or a folder of them")
    ap.add_argument("--tz", default="America/New_York", help="time zone of the file's timestamps (if they have no offset)")
    ap.add_argument("--stamp", default="auto", choices=["auto", "open", "close"], help="timestamp marks the bar's open or close")
    ap.add_argument("--out", default="trades_v8.csv")
    a = ap.parse_args()

    df = load_many(a.files, a.tz, a.stamp)
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
