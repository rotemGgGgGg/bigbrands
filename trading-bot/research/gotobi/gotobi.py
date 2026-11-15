"""Gotobi Tokyo-fix reversal (Ito & Yamada 2017), tested on Dukascopy USDJPY 1-minute, 2012-2026.
Rules as published: on Gotobi days (5,10,15,20,25,30/last day of Feb; weekend or Japanese holiday -> previous Japanese business day)
SELL USDJPY at 09:55 Tokyo (00:55 UTC), exit 10:20 Tokyo or stop 0.15%. Costs: 1.0 bp round trip (about 1.5 pips).
Checks: Gotobi vs non-Gotobi control, the other 'digit' placebos (days ending 1/6, 2/7, 3/8, 4/9), per year, the vendor's
window Sep 2016-Aug 2026, a parameter neighbourhood, the pre-fix long leg, and a combination with our existing portfolio."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi"))
import mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
COST = 1.0


def jp_holidays(y0=2011, y1=2027):
    """Japanese public + bank holidays (Dec 31 - Jan 3), with substitute and sandwiched 'citizen' holidays."""
    hs = set()
    def nth_mon(y, m, n):
        d = pd.Timestamp(y, m, 1); d += pd.Timedelta(days=(0 - d.weekday()) % 7); return d + pd.Timedelta(weeks=n - 1)
    for y in range(y0, y1 + 1):
        T = lambda m, d: pd.Timestamp(y, m, d)
        h = {T(1, 1), T(1, 2), T(1, 3), T(12, 31), nth_mon(y, 1, 2), T(2, 11), T(4, 29), T(5, 3), T(5, 4), T(5, 5), nth_mon(y, 9, 3),
             T(11, 3), T(11, 23)}
        h.add(T(3, int(20.8431 + 0.242194 * (y - 1980) - int((y - 1980) / 4))))
        h.add(T(9, int(23.2488 + 0.242194 * (y - 1980) - int((y - 1980) / 4))))
        if y <= 2018: h.add(T(12, 23))
        if y >= 2020: h.add(T(2, 23))
        if y == 2019: h |= {T(4, 30), T(5, 1), T(5, 2), T(10, 22)}
        if y == 2020: h |= {T(7, 23), T(7, 24), T(8, 10)}
        elif y == 2021: h |= {T(7, 22), T(7, 23), T(8, 9)}
        else:
            h.add(nth_mon(y, 7, 3)); h.add(nth_mon(y, 10, 2))
            if y >= 2016: h.add(T(8, 11))
        # substitute holiday: a holiday on Sunday -> next non-holiday day
        for d in sorted(h):
            if d.weekday() == 6:
                s = d + pd.Timedelta(days=1)
                while s in h: s += pd.Timedelta(days=1)
                h.add(s)
        # citizen's holiday: weekday sandwiched between two holidays
        for d in sorted(h):
            m = d + pd.Timedelta(days=1)
            if m not in h and (m + pd.Timedelta(days=1)) in h and m.weekday() < 5: h.add(m)
        hs |= h
    return hs


HOL = jp_holidays()
def is_bd(d): return d.weekday() < 5 and d not in HOL


def trade_days(digits=(5, 0), y0=2012, y1=2026):
    """Gotobi-style days for a digit pair; weekends/holidays roll to the previous Japanese business day."""
    out = set()
    for d in pd.date_range(f"{y0}-01-01", f"{y1}-12-31"):
        last = (d + pd.Timedelta(days=1)).day == 1
        hit = d.day % 10 in digits and d.day != 31
        if digits == (5, 0) and d.month == 2 and last and d.day not in (5, 10, 15, 20, 25): hit = True   # last day of Feb
        if digits == (5, 0) and d.month == 2 and d.day == 30: hit = False
        if not hit: continue
        while not is_bd(d): d -= pd.Timedelta(days=1)
        out.add(d)
    return sorted(out)


def load():
    f = SP + "gotobi_usdjpy.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    z = np.load(mdata.DK + "USDJPY.npz"); t = pd.to_datetime(z["t"] * 60, unit="s")              # UTC, naive
    df = pd.DataFrame({k: z[k] for k in "ohlc"}, index=t); df = df[~df.index.duplicated()].sort_index()
    df = df[(df.index.hour < 3)]                                                                 # 00:00-02:59 UTC = 09:00-11:59 Tokyo
    G = {}
    for d, g in df.groupby(df.index.normalize()):
        m = g.index.hour * 60 + g.index.minute; x = g.set_index(m).reindex(range(180))
        if x.c.notna().sum() < 120: continue
        x["c"] = x.c.ffill().bfill()
        for k in "ohl": x[k] = x[k].fillna(x.c)
        G[d] = x[list("ohlc")].values.T
    pd.to_pickle(G, f); return G


def run(G, days, side=-1, ent=55, ex=80, stop=0.15):
    """minutes after 09:00 Tokyo (00:00 UTC). Entry at open of 'ent', exit at open of 'ex' or stop (stop % of entry)."""
    out = {}
    for d in days:
        a = G.get(d)
        if a is None: continue
        o, h, l, c = a; e = o[ent]; px = o[ex]
        if stop:
            sl = e * (1 - side * stop / 100); seg = h[ent:ex] if side < 0 else l[ent:ex]
            hit = np.nonzero(seg >= sl)[0] if side < 0 else np.nonzero(seg <= sl)[0]
            if len(hit): px = sl
        out[d] = side * (px - e) / e * 1e4 - COST
    return pd.Series(out, dtype=float)


def st(s):
    t = s.mean() / s.std() * math.sqrt(len(s)) if len(s) > 2 else 0
    pf = s[s > 0].sum() / -s[s < 0].sum()
    return f"n {len(s):4d} | mean {s.mean():5.2f}bp | t {t:5.2f} | win {100*(s>0).mean():4.1f}% | PF {pf:4.2f} | sum {s.sum():7.0f}bp"


if __name__ == "__main__":
    G = load(); allbd = [d for d in G if is_bd(d)]
    got = trade_days(); gset = set(got)
    non = [d for d in allbd if d not in gset]
    print("=== Published rules: sell 09:55 -> 10:20 Tokyo, stop 0.15%, cost 1bp")
    g = run(G, got); n = run(G, non)
    print("Gotobi        ", st(g)); print("non-Gotobi    ", st(n))
    v0, v1 = pd.Timestamp("2016-09-01"), pd.Timestamp("2026-08-31")
    print("vendor window Gotobi", st(g[(g.index >= v0) & (g.index <= v1)]))
    print("2012-2016-08 (before their window)", st(g[g.index < v0]))
    print("\nper year (sum bp):", g.groupby(g.index.year).sum().round(0).to_dict())
    print("\n=== Placebo digits (same rules on days ending in other digit pairs)")
    for dg in [(1, 6), (2, 7), (3, 8), (4, 9)]:
        print(f"digits {dg}", st(run(G, trade_days(dg))))
    print("\n=== Neighbourhood (Gotobi; IS 2012-19 / OOS 2020-26 mean bp and t)")
    rows = []
    for ent, ex, stop in itertools.product((50, 54, 55, 56, 60), (65, 70, 80, 90, 115), (None, 0.1, 0.15, 0.25)):
        if ex <= ent: continue
        s = run(G, got, -1, ent, ex, stop); Y = s.index.year; I, O = s[Y <= 2019], s[Y >= 2020]
        rows.append(dict(ent=f"09:{ent:02d}", ex=f"{9 + ex // 60}:{ex % 60:02d}", stop=stop, IS=I.mean(), IS_t=I.mean() / I.std() * math.sqrt(len(I)),
                         OOS=O.mean(), OOS_t=O.mean() / O.std() * math.sqrt(len(O)), win=100 * (s > 0).mean()))
    R = pd.DataFrame(rows); print(R.round(2).to_string(index=False))
    print(f"variants positive OOS: {(R.OOS > 0).sum()}/{len(R)}, OOS t>=2: {(R.OOS_t >= 2).sum()}")
    print("\n=== Pre-fix leg (long 09:00/09:30 -> 09:55) Gotobi vs non-Gotobi")
    for e0 in (0, 30):
        print(f"long 09:{e0:02d}-09:55 Gotobi", st(run(G, got, 1, e0, 55, None)), "| non", st(run(G, non, 1, e0, 55, None)))
    pd.to_pickle(g, SP + "gotobi_series.pkl")
