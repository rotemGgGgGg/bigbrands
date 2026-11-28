"""AVP Zones (decoded) - EVERYTHING: all zone types, targets and trading-hour windows, chosen on 2011-19, judged on 2020-26.

Zone sets per session D:
  blue   : close of session D-1 +/- H
  past   : closes of D-1, D-2, D-3 +/- H                ("Past days' zones")
  ladder : VWAP(D-1 at 16:00) +/- k*S, k = 1..3, S = 1.10 x mean VWAP-sigma of the last 3 sessions, half-height 0.1*S
  all    : past + ladder
Signal (his raw mechanic): price on one side of a zone, a candle pops into it, a later OPPOSING candle closes back out
-> enter at that close; stop = far side + 2 ticks. One position at a time; one trade per zone (flip: one more, opposite
way, after a stop). Targets: 2R, 3R, or "next zone" (nearest zone edge beyond the entry, at least 1R; else 2R).
Windows (signals and exits; flat at the window end): RTH 09:30-16:00, NY AM 09:30-12:00, NY PM 12:00-16:00,
London 03:00-09:30, Asia 18:00-03:00, All 18:00-17:00. 5-minute signals, 1-minute exits, cost 1 NQ point.

    python allo/avp_bt2.py          (~10-20 minutes)
"""
import os, sys, itertools, numpy as np, pandas as pd

DATA = os.path.join(os.path.expanduser(os.environ.get("EDGE_DATA", "~/edge-data")), "")
COST, TICK, N = 1.0, 0.25, 1380                                         # minutes 18:00 -> 17:00
WIN = {"RTH": (930, 1320), "AM": (930, 1080), "PM": (1080, 1320), "London": (540, 930), "Asia": (0, 540), "All": (0, 1380)}


def sessions():
    z = np.load(DATA + "databento/NQ.npz")
    t = pd.to_datetime(z["t"] * 60, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
    df = pd.DataFrame({k: z[k] for k in "ohlcv"}, index=t)
    df["sess"] = (df.index + pd.Timedelta(hours=6)).normalize()
    S, closes, vw16, sg16 = [], [], [], []
    for d, g in df.groupby("sess"):
        if len(g) < 600: continue
        start = d - pd.Timedelta(hours=6)
        r = g.reindex(pd.date_range(start, periods=N, freq="1min"))
        r["c"] = r.c.ffill().bfill()
        for k in "ohl": r[k] = r[k].fillna(r.c)
        r["v"] = r.v.fillna(0)
        a = {k: r[k].values for k in "ohlcv"}
        tp = (a["h"] + a["l"] + a["c"]) / 3; m16 = np.arange(N) < 1320; v = a["v"][m16]
        vw = (tp[m16] * v).sum() / max(v.sum(), 1); sg = np.sqrt((v * (tp[m16] - vw) ** 2).sum() / max(v.sum(), 1))
        if len(closes) >= 3:
            S.append(dict(d=d, closes=closes[-3:][::-1], M=vw16[-1], S=1.10 * np.mean(sg16[-3:]),
                          o5=a["o"][::5], h5=a["h"].reshape(-1, 5).max(1), l5=a["l"].reshape(-1, 5).min(1),
                          c5=a["c"][4::5], h1=a["h"], l1=a["l"], c1=a["c"], rng=g.h.max() - g.l.min()))
        closes.append(g.c.iloc[-1]); vw16.append(vw); sg16.append(sg)
    return S


def zones(s, kind, H, shift=0.0):
    z = []
    if kind in ("blue", "past", "all"):
        for c in (s["closes"][:1] if kind == "blue" else s["closes"]): z.append((c + shift - H, c + shift + H))
    if kind in ("ladder", "all"):
        h = 0.1 * s["S"]
        for k in (-3, -2, -1, 1, 2, 3): c = s["M"] + shift + k * s["S"]; z.append((c - h, c + h))
    return z


def signals(s, lo, hi, a, b):
    """Raw counter-close signals of one zone inside 5m bars [a, b)."""
    o, h, l, c = s["o5"], s["h5"], s["l5"], s["c5"]; out = []
    side = -1 if c[a] < lo else (1 if c[a] > hi else 0); touch = None
    for i in range(a + 1, b - 1):
        if side == -1:
            if touch is None and h[i] >= lo: touch = i
            if touch is not None and touch < i and c[i] < lo and c[i] < o[i]: out.append((i, -1, c[i], hi + 2 * TICK)); touch = None
        elif side == 1:
            if touch is None and l[i] <= hi: touch = i
            if touch is not None and touch < i and c[i] > hi and c[i] > o[i]: out.append((i, 1, c[i], lo - 2 * TICK)); touch = None
        if c[i] < lo:
            if side != -1: touch = None
            side = -1
        elif c[i] > hi:
            if side != 1: touch = None
            side = 1
    return out


def day(s, kind, H, tgt, win, flip, shift=0.0):
    a, b = WIN[win][0] // 5, WIN[win][1] // 5; Z = zones(s, kind, H, shift)
    cands = sorted((i, d, e, st, zi) for zi, (lo, hi) in enumerate(Z) for (i, d, e, st) in signals(s, lo, hi, a, b))
    used = {}; free_from = 0; trades = []
    for i, d, e, st, zi in cands:
        if i < free_from: continue
        u = used.get(zi)
        if u is not None and not (flip and u[1] and d == -u[0] and u[2] == 1): continue
        R = abs(e - st)
        if R <= 0: continue
        if tgt == "next":
            edges = [lo for lo, hi in Z if lo > e + R] if d == 1 else [hi for lo, hi in Z if hi < e - R]
            T = (min(edges) - e) / R if (d == 1 and edges) else ((e - max(edges)) / R if edges else 2.0)
        else: T = float(tgt)
        tp = e + d * T * R; res = None; end = WIN[win][1]
        for j in range((i + 1) * 5, end):
            if (d == -1 and s["h1"][j] >= st) or (d == 1 and s["l1"][j] <= st): res = -1.0; break
            if (d == -1 and s["l1"][j] <= tp) or (d == 1 and s["h1"][j] >= tp): res = T; break
        if res is None: j = end - 1; res = d * (s["c1"][j] - e) / R
        trades.append((s["d"].year, res - COST / R))
        used[zi] = (d, res == -1.0, 1 if u is None else 2); free_from = j // 5 + 1
    return trades


def stats(tr, y0, y1):
    r = np.array([x for y, x in tr if y0 <= y <= y1])
    if len(r) < 30: return len(r), np.nan, np.nan
    return len(r), r.mean(), r.mean() / r.std(ddof=1) * np.sqrt(len(r))


if __name__ == "__main__":
    S = sessions(); print(f"{len(S)} sessions {S[0]['d'].date()} .. {S[-1]['d'].date()}", flush=True)
    grid = list(itertools.product(("blue", "past", "ladder", "all"), (35, 45), ("2", "3", "next"), tuple(WIN), (0, 1)))
    res = []
    for g in grid:
        kind, H, tgt, win, flip = g; tr = []
        for s in S: tr += day(s, kind, H, tgt, win, flip)
        res.append((g, stats(tr, 2011, 2019), stats(tr, 2020, 2026)))
        print(".", end="", flush=True)
    print()
    ok = [r for r in res if r[1][0] >= 200 and not np.isnan(r[1][1])]
    ok.sort(key=lambda r: -r[1][1])
    pos_oos = sum(1 for r in res if not np.isnan(r[2][1]) and r[2][1] > 0 and r[2][2] >= 2)
    print(f"\n{len(res)} settings. Out-of-sample positive with t>=2: {pos_oos} (chance alone gives ~{len(res) * 0.025:.0f})")
    print("\nTOP 10 by 2011-19 (chosen in-sample) -> 2020-26 judged once")
    print(" zones  H  target window flip |  IS n  avgR    t  |  OOS n  avgR    t")
    for (kind, H, tgt, win, flip), a, b in ok[:10]:
        print(f" {kind:6} {H} {tgt:>5} {win:6} {flip}   | {a[0]:5d} {a[1]:+.3f} {a[2]:5.2f} | {b[0]:5d} {b[1]:+.3f} {b[2]:5.2f}")
    print("\nBEST OUT-OF-SAMPLE (for information only: picking on these numbers is cheating)")
    oo = sorted([r for r in res if not np.isnan(r[2][1]) and r[2][0] >= 200], key=lambda r: -r[2][1])
    for (kind, H, tgt, win, flip), a, b in oo[:5]:
        print(f" {kind:6} {H} {tgt:>5} {win:6} {flip}   | {a[0]:5d} {a[1]:+.3f} {a[2]:5.2f} | {b[0]:5d} {b[1]:+.3f} {b[2]:5.2f}")
    (kind, H, tgt, win, flip), a, b = ok[0]
    rng = np.random.default_rng(7); pl = []; oos = [s for s in S if s["d"].year >= 2020]
    for k in range(30):
        tr = []
        for s in oos:
            off = 0
            while abs(off) < 4 * H: off = rng.uniform(-1, 1) * max(s["rng"], 8 * H)
            tr += day(s, kind, H, tgt, win, flip, shift=off)
        pl.append(stats(tr, 2020, 2026)[1])
    pl = np.array(pl); p = (np.sum(pl >= b[1]) + 1) / (len(pl) + 1)
    print(f"\nPLACEBO for the in-sample pick ({kind},{H},{tgt},{win},{flip}), 2020-26, 30 runs of random zones:"
          f" mean {np.nanmean(pl):+.3f}R, 95th pct {np.nanpercentile(pl, 95):+.3f}R, real {b[1]:+.3f}R, p = {p:.2f}")
