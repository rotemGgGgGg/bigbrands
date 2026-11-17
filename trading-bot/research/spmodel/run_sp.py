"""SP Model v8 (backtest/sp_v8.py, rules unchanged) on 2012-2026 Nasdaq-100 1-minute data (HistData NSXUSD CFD, NY time),
resampled to 5-minute bars. Volume: the CFD has none, so each 1-minute bar counts as 1 (a time-at-price / TPO profile)
- an approximation of the futures volume profile the trader uses.
Configs: A = London 00:00-06:00 NY (the model as specified); B = London 02:00-09:30 NY (the user's indicator window).
Reports R per trade, win rate, RR, per year, 2012-19 vs 2020-26, by scenario, and a Lucid-style 50K prop simulation."""
import sys, os, math, collections, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, "../multi")); sys.path.insert(0, os.path.join(H, "../../backtest"))
import mdata, sp_v8 as v
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"


def bars5():
    f = SP + "sp_nq5.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    df = mdata.histdata("NSXUSD"); df = df[~df.index.duplicated()].sort_index()
    df["volume"] = 1.0
    b = df.resample("5min", label="left", closed="left").agg(open=("o", "first"), high=("h", "max"), low=("l", "min"),
                                                            close=("c", "last"), volume=("volume", "sum")).dropna()
    b.index = b.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT"); b = b[b.index.notna()]
    pd.to_pickle(b, f); return b


def stats(tr):
    r = tr.r.values; n = len(r)
    if not n: return dict(n=0)
    w = r[r > 0]; l = r[r < 0]; eq = np.cumsum(r)
    t = r.mean() / r.std() * math.sqrt(n) if r.std() > 0 else 0
    return dict(n=n, per_yr=n / 14.8, win=100 * (r > 0).mean(), rr=w.mean() / -l.mean() if len(l) else np.nan,
                avgR=r.mean(), totR=r.sum(), t=t, maxDD_R=(eq - np.maximum.accumulate(eq)).min())


def prop(tr, risk=250.0):
    """Lucid-like 50K: $3,000 target, $2,000 EOD trailing (locks at +$100), 50% consistency; then funded to a $1,500 payout.
    Fixed $ risk per trade. Started at every 20th trade of 2020-26."""
    x = tr[tr.entry_time.dt.year >= 2020]; pnl = (x.r.values * risk); out = []
    for st in range(0, max(len(pnl) - 20, 1), 20):
        bal = peak = best = 0.0; floor = -2000.0; ph = None
        for i in range(st, len(pnl)):
            bal += pnl[i]; best = max(best, pnl[i]); peak = max(peak, bal); floor = 100.0 if peak >= 2100 else max(floor, peak - 2000)
            if bal <= floor: out.append("fail"); break
            if ph is None and bal >= 3000 and best <= .5 * bal: ph = i; bal = peak = best = 0.0; floor = -2000.0; continue
            if ph is not None and bal >= 1500: out.append("payout"); break
        else: out.append("open")
    c = collections.Counter(out); n = max(len(out), 1)
    return f"payout {100*c['payout']/n:.0f}% | fail {100*c['fail']/n:.0f}% | unfinished {100*c['open']/n:.0f}%"


if __name__ == "__main__":
    df = bars5(); print(f"5-min bars {df.index[0]} -> {df.index[-1]}  ({len(df):,})", flush=True)
    cfgs = {"A London 00:00-06:00": v.Params(check=False),
            "B London 02:00-09:30": v.Params(check=False, ldn_start=120, ldn_end=570, ldn_min_bars=75)}
    pd.set_option("display.width", 220); allr = {}
    for name, p in cfgs.items():
        r = v.run(df, p); tr = pd.DataFrame(r.trades)
        tr["entry_time"] = pd.to_datetime(tr.entry_time, utc=True).dt.tz_convert("America/New_York")
        tr.to_csv(SP + f"sp_trades_{name[0]}.csv", index=False); allr[name] = tr; Y = tr.entry_time.dt.year
        print(f"\n===================== {name}")
        print("ALL      ", {k: round(v_, 2) for k, v_ in stats(tr).items()})
        print("2012-2019", {k: round(v_, 2) for k, v_ in stats(tr[Y <= 2019]).items()})
        print("2020-2026", {k: round(v_, 2) for k, v_ in stats(tr[Y >= 2020]).items()})
        for sc in (1, 2, 3):
            print(f"S{sc}       ", {k: round(v_, 2) for k, v_ in stats(tr[tr.scenario == sc]).items()})
        for lv in (0.5, 0.588):
            print(f"@{lv}    ", {k: round(v_, 2) for k, v_ in stats(tr[tr.level == lv]).items()})
        yy = tr.groupby(Y).r.agg(["count", "sum", lambda s: 100 * (s > 0).mean()]); yy.columns = ["trades", "R", "win%"]
        print("by year:\n", yy.round(1).T.to_string())
        print("exits:", tr.exit.value_counts().to_dict())
        print("prop 50K @ $250 risk/trade (2020-26):", prop(tr), "| @ $400:", prop(tr, 400))
