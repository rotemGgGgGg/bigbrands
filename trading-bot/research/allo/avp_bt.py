"""AVP Zones (decoded) backtest on Databento NQ 1-minute data, 2011-2026, with our gates.

Blue zone for session D = [C - H, C + H], C = close of session D-1 (17:00 NY). Signals on 5-minute RTH bars
(the seller: "use the 5 minute, RTH is best"), his raw mechanic:
  price is on one side of the zone (last close outside it) -> a candle pops INTO the zone -> an OPPOSING candle closes
  back out on the original side -> enter at that close. Stop = far side of the zone + 2 ticks. Target = T x R.
  Flat at 16:00. One trade per zone per day (flip ON allows one more, in the other direction, after a stop).
  void ON: the touch is cancelled if price traded beyond the far side before the counter-close (re-arms on a close outside).
Exits are walked on 1-minute bars (stop first if both are hit in the same minute). Cost: 1 NQ point per round trip.
Choose settings on 2011-2019 only; 2020-2026 is judged once. Placebo: same rules on randomly shifted zones.

    python allo/avp_bt.py            # grid on 2011-19, best + top-5 judged on 2020-26, placebo, years, recent trades
"""
import os, sys, itertools, numpy as np, pandas as pd

DATA = os.path.join(os.path.expanduser(os.environ.get("EDGE_DATA", "~/edge-data")), "")
COST, TICK = 1.0, 0.25


def sessions():
    z = np.load(DATA + "databento/NQ.npz")
    t = pd.to_datetime(z["t"] * 60, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
    df = pd.DataFrame({k: z[k] for k in "ohlc"}, index=t)
    df["sess"] = (df.index + pd.Timedelta(hours=6)).normalize()
    out, prev_close = [], None
    for d, g in df.groupby("sess"):
        m = g.index.hour * 60 + g.index.minute
        r = g[(m >= 570) & (m < 960)]
        if prev_close is not None and len(r) >= 300 and d.weekday() < 5:
            idx = pd.date_range(d + pd.Timedelta(minutes=570), periods=390, freq="1min")
            r = r.reindex(idx); r["c"] = r.c.ffill().bfill()
            for k in "ohl": r[k] = r[k].fillna(r.c)
            o1, h1, l1, c1 = (r[k].values for k in "ohlc")
            o5, c5 = o1[::5], c1[4::5]; h5 = h1.reshape(78, 5).max(1); l5 = l1.reshape(78, 5).min(1)
            out.append(dict(d=d, C=prev_close, rng=prev_rng, o5=o5, h5=h5, l5=l5, c5=c5, h1=h1, l1=l1, c1=c1))
        prev_close = g.c.iloc[-1]; prev_rng = g.h.max() - g.l.min()
    return out


def run_day(s, C, H, T, void, flip, same_bar):
    lo, hi = C - H, C + H; o, h, l, c = s["o5"], s["h5"], s["l5"], s["c5"]
    side = -1 if c[0] < lo else (1 if c[0] > hi else 0)               # -1: price below the zone (look for shorts)
    touch_bar = None; trades = []; busy_until = 0; last = None           # last = (direction, stopped?) of the first trade
    for i in range(1, 78):
        if side == -1:
            if h[i] >= lo and touch_bar is None: touch_bar = i           # a candle pops into the zone
            if void and h[i] > hi + TICK: touch_bar = None
            sig = touch_bar is not None and c[i] < lo and c[i] < o[i]    # opposing candle closes back under
            d = -1
        elif side == 1:
            if l[i] <= hi and touch_bar is None: touch_bar = i
            if void and l[i] < lo - TICK: touch_bar = None
            sig = touch_bar is not None and c[i] > hi and c[i] > o[i]
            d = 1
        else:
            sig = False; d = 0
        if sig and not same_bar and touch_bar == i: sig = False          # pop-in and counter-close on two candles
        allowed = last is None or (flip and last[1] and d == -last[0] and len(trades) == 1)
        if sig and i >= busy_until and i < 77 and allowed:
            e = c[i]; stop = (hi + 2 * TICK) if d == -1 else (lo - 2 * TICK); R = abs(e - stop)
            tgt = e + d * T * R; res = None; j = 390
            for j in range((i + 1) * 5, 390):
                if (d == -1 and s["h1"][j] >= stop) or (d == 1 and s["l1"][j] <= stop): res = -1.0; break
                if (d == -1 and s["l1"][j] <= tgt) or (d == 1 and s["h1"][j] >= tgt): res = T; break
            if res is None: res = d * (s["c1"][-1] - e) / R
            trades.append((s["d"], i, d, e, stop, R, res - COST / R, res == -1.0))
            last = (d, res == -1.0) if last is None else last
            busy_until = j // 5 + 1; touch_bar = None
        if c[i] < lo:
            if side != -1: touch_bar = None
            side = -1
        elif c[i] > hi:
            if side != 1: touch_bar = None
            side = 1
    return trades


def run(S, H, T, void, flip, same_bar, shift=None, rng=None):
    tr = []
    for s in S:
        C = s["C"]
        if shift is not None:
            off = 0
            while abs(off) < 4 * H: off = rng.uniform(-1, 1) * max(s["rng"], 8 * H)
            C = C + off
        tr += run_day(s, C, H, T, void, flip, same_bar)
    return tr


def stat(tr, a=None, b=None):
    r = np.array([x[6] for x in tr if (a is None or x[0].year >= a) and (b is None or x[0].year <= b)])
    if len(r) < 3: return dict(n=len(r), avg=np.nan, t=np.nan, win=np.nan)
    return dict(n=len(r), avg=r.mean(), t=r.mean() / r.std(ddof=1) * np.sqrt(len(r)), win=(r > 0).mean() * 100)


if __name__ == "__main__":
    S = sessions(); print(f"{len(S)} RTH sessions {S[0]['d'].date()} .. {S[-1]['d'].date()}", flush=True)
    grid = list(itertools.product((25, 35, 45), (1.5, 2.0, 3.0), (0, 1), (0, 1), (0, 1)))
    rows = []
    for H, T, void, flip, sb in grid:
        tr = run(S, H, T, void, flip, sb); a, b = stat(tr, None, 2019), stat(tr, 2020, None)
        rows.append((a["avg"] if a["n"] >= 200 else -9, H, T, void, flip, sb, a, b, tr))
    rows.sort(key=lambda r: -r[0])
    print("\nTOP 5 by 2011-2019 avg R (chosen in-sample) -> judged on 2020-2026")
    print(" H   T   void flip 2bar |  IS n   avgR    t   win% |  OOS n   avgR    t   win%")
    for r in rows[:5]:
        _, H, T, v, f, sb, a, b, _ = r
        print(f"{H:3d} {T:3.1f}   {v}    {f}    {1 - sb}  | {a['n']:5d} {a['avg']:+.3f} {a['t']:5.2f} {a['win']:5.1f} | "
              f"{b['n']:5d} {b['avg']:+.3f} {b['t']:5.2f} {b['win']:5.1f}")
    _, H, T, v, f, sb, a, b, tr = rows[0]
    print(f"\nCHOSEN: H={H} T={T} void={v} flip={f} same_bar={sb}")
    print("year  n   avgR   win%")
    for y in range(S[0]["d"].year, S[-1]["d"].year + 1):
        st = stat(tr, y, y)
        if st["n"]: print(f"{y} {st['n']:4d} {st['avg']:+.3f} {st['win']:5.1f}")
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    rng = np.random.default_rng(7); oos = [x for x in S if x["d"].year >= 2020]; pl = []
    for k in range(runs):
        st = stat(run(oos, H, T, v, f, sb, shift=True, rng=rng)); pl.append(st["avg"])
    pl = np.array(pl); p = (np.sum(pl >= b["avg"]) + 1) / (len(pl) + 1)
    print(f"\nPLACEBO 2020-26 (random zones, {runs} runs): mean {np.nanmean(pl):+.3f}R  95th pct {np.nanpercentile(pl, 95):+.3f}R"
          f"  real {b['avg']:+.3f}R  p = {p:.3f}")
    print("\nrecent trades (compare with his 23): date  time(NY)  side  entry  stop  R  result")
    for x in tr:
        if x[0] >= pd.Timestamp("2026-10-01"):
            hh, mm = divmod(570 + 5 * x[1] + 5, 60)
            print(f"  {x[0].date()} {hh:02d}:{mm:02d} {'L' if x[2] == 1 else 'S'} {x[3]:9.2f} {x[4]:9.2f} {x[5]:6.1f} {x[6]:+.2f}")
