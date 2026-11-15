"""The video's full Gotobi version ('GotobiFixALL', inputs read from its MT5 report screenshot):
  LONG  from 18:00 UTC the evening before the Gotobi date (03:00 Tokyo) to the 09:55 Tokyo fix (00:55 UTC)
  SHORT from the fix for 35 minutes (exit 01:30 UTC = 10:30 Tokyo). No stop (StopPips=0).
  NoLongMonday (the long would span the weekend), NoLongEOM (no long leg on the month-end Gotobi day). 1 lot each pair.
  Pairs: USDJPY, EURJPY, GBPJPY. Vendor shows 2018-01-01 .. 2026-11-06: 605 Gotobi days, +$83,888, PF 1.71, worst DD -$9,893.
Tests here: replicate on Dukascopy 1-min; 2012-2017 = data the vendor did not show (true out-of-sample for their parameters);
each leg and pair separately; a parameter neighbourhood (chosen on 2012-19, judged on 2020-26)."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi")); sys.path.insert(0, H)
import mdata
from gotobi import trade_days, is_bd, jp_holidays
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
COST = {"USDJPY": 1.0, "EURJPY": 1.2, "GBPJPY": 1.4}            # bp round trip per leg (spread + commission, raw account)
W0 = 18 * 60                                                      # window: 18:00 UTC previous day .. 02:00 UTC (480 min)


def load(sym):
    f = SP + f"gfull_{sym}.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    z = np.load(mdata.DK + sym + ".npz"); t = pd.to_datetime(z["t"] * 60, unit="s")
    df = pd.DataFrame({k: z[k] for k in "ohlc"}, index=t); df = df[~df.index.duplicated()].sort_index()
    sh = df.index + pd.Timedelta(minutes=360)                     # 18:00 UTC -> 00:00 of the Tokyo trade date
    m = sh.hour * 60 + sh.minute; df = df[m < 480]; sh = sh[m < 480]; m = m[m < 480]
    G = {}
    for d, idx in pd.Series(np.arange(len(df)), index=sh.normalize()).groupby(level=0):
        x = df.iloc[idx.values].set_index(m[idx.values]).reindex(range(480))
        if x.c.notna().sum() < 200: continue
        x["c"] = x.c.ffill().bfill()
        for k in "ohl": x[k] = x[k].fillna(x.c)
        G[d] = x[list("ohlc")].values.T
    pd.to_pickle(G, f); return G


def eom_gotobi(d):
    """the month-end Gotobi (30th, or last day of Feb), after rolling back"""
    return d.day >= 26 or (d.month == 2 and d.day >= 24)


def run(sym, days, long_start=0, fix=415, short_min=35, stop_bp=None, legs=("L", "S"), no_long_mon=True, no_long_eom=True):
    G = load(sym); c = COST[sym]; rows = {}
    for d in days:
        a = G.get(d)
        if a is None: continue
        o, h, l, cl = a; pnl = 0.0; n = 0
        if "L" in legs and not (no_long_mon and d.weekday() == 0) and not (no_long_eom and eom_gotobi(d)):
            e, x = o[long_start], o[fix]
            if stop_bp:
                hit = np.nonzero(l[long_start:fix] <= e * (1 - stop_bp / 1e4))[0]
                if len(hit): x = e * (1 - stop_bp / 1e4)
            pnl += (x - e) / e * 1e4 - c; n += 1
        if "S" in legs:
            e, x = o[fix], o[fix + short_min]
            if stop_bp:
                hit = np.nonzero(h[fix:fix + short_min] >= e * (1 + stop_bp / 1e4))[0]
                if len(hit): x = e * (1 + stop_bp / 1e4)
            pnl += -(x - e) / e * 1e4 - c; n += 1
        if n: rows[d] = pnl
    return pd.Series(rows, dtype=float)


def usd_per_lot_bp(sym, d):
    """USD value of 1 bp move on 1 lot (100k base). For XXXJPY: 1e5 * price * 1e-4 JPY / USDJPY."""
    return None


def stats(s, label):
    if not len(s): return f"{label}: no data"
    t = s.mean() / s.std() * math.sqrt(len(s)); pf = s[s > 0].sum() / -s[s < 0].sum(); cs = s.cumsum()
    return (f"{label:34s} n {len(s):4d} | {s.mean():5.2f} bp/day | t {t:5.2f} | win {100*(s>0).mean():4.1f}% | PF {pf:4.2f} | "
            f"sum {s.sum():6.0f} bp | maxDD {(cs-cs.cummax()).min():6.0f} bp")


if __name__ == "__main__":
    pairs = [p for p in sys.argv[1:] or ["USDJPY", "EURJPY", "GBPJPY"] if os.path.exists(mdata.DK + p + ".npz")]
    days = trade_days(y0=2012, y1=2026); ctrl = [d for d in pd.bdate_range("2012-01-01", "2026-11-06") if is_bd(d) and d not in set(days)]
    V0, V1 = pd.Timestamp("2018-01-01"), pd.Timestamp("2026-11-06")
    allp = {}
    for p in pairs:
        s = run(p, days); allp[p] = s; c = run(p, ctrl)
        print(f"\n===== {p} (vendor rules)")
        print(stats(s[(s.index >= V0) & (s.index <= V1)], "vendor window 2018-2026"))
        print(stats(s[s.index < V0], "2012-2017 (not shown by vendor)"))
        print(stats(c[(c.index >= V0)], "control: non-Gotobi days 2018-26"))
        print(stats(run(p, days, legs=("L",)), "long leg only 2012-26"), "\n" + stats(run(p, days, legs=("S",)), "short leg only 2012-26"))
        print("per year bp:", s.groupby(s.index.year).sum().round(0).astype(int).to_dict())
    if len(allp) > 1:
        P = pd.DataFrame(allp).fillna(0); tot = P.mean(1)
        print("\n===== all pairs, equal weight (bp of each position, averaged)")
        print(stats(tot[tot.index >= V0], "vendor window 2018-2026")); print(stats(tot[tot.index < V0], "2012-2017"))
        print("per year:", tot.groupby(tot.index.year).sum().round(0).astype(int).to_dict())
        pd.to_pickle(P, SP + "gfull_pairs.pkl")
    # neighbourhood on USDJPY-style grid for every pair: choose on 2012-19, judge on 2020-26
    print("\n===== neighbourhood (all pairs averaged): long start, short length, stop, legs")
    rows = []
    for ls, sm, stp, lg in itertools.product((0, 180, 360), (20, 25, 35, 60), (None, 30), (("L", "S"), ("L",), ("S",))):
        P = pd.DataFrame({p: run(p, days, long_start=ls, short_min=sm, stop_bp=stp, legs=lg) for p in pairs}).fillna(0).mean(1)
        Y = P.index.year; I, O = P[Y <= 2019], P[Y >= 2020]
        rows.append(dict(long_from=f"{(18 + ls // 60) % 24:02d}:00UTC", short_min=sm, stop_bp=stp, legs="+".join(lg),
                         IS=I.mean(), IS_t=I.mean() / I.std() * math.sqrt(len(I)), OOS=O.mean(), OOS_t=O.mean() / O.std() * math.sqrt(len(O))))
    R = pd.DataFrame(rows).sort_values("IS_t", ascending=False); pd.set_option("display.width", 200)
    print(R.round(2).to_string(index=False)); R.to_csv(SP + "gfull_grid.csv", index=False)
