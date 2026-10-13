import os, lzma, struct, numpy as np, pandas as pd
rows = []
for f in sorted(os.listdir("raw")):
    b = open("raw/" + f, "rb").read()
    if not b: continue
    try:
        d = lzma.decompress(b)
    except Exception:
        continue
    day = pd.Timestamp(f[:10], tz="UTC")
    a = np.frombuffer(d, dtype=">i4").reshape(-1, 6)[:, :5].astype(float)
    t = day + pd.to_timedelta(a[:, 0], unit="s")
    rows.append(pd.DataFrame({"open": a[:, 1] / 1000, "close": a[:, 2] / 1000, "low": a[:, 3] / 1000, "high": a[:, 4] / 1000}, index=t))
g = pd.concat(rows).sort_index(); g.index = g.index.tz_convert("America/New_York")
g = g[(g.high > g.low) | (g.open != g.close)]                     # drop flat filler minutes
print("data", g.index[0].date(), "→", g.index[-1].date(), len(g), "minutes")
o, h, l, c = (g[k].values for k in ("open", "high", "low", "close")); T = g.index
m = (T.hour * 60 + T.minute).values; dates = T.date
def run(tp, sl):
    out = []
    for i in np.where((m >= 540) & (m < 600))[0]:
        if i == 0 or dates[i - 1] != dates[i] or c[i - 1] == o[i - 1]: continue
        side = 1 if c[i - 1] > o[i - 1] else -1
        e = o[i]; res = None
        for j in range(i, min(i + 600, len(o))):
            if dates[j] != dates[i] or m[j] >= 16 * 60 + 55: res = (c[j - 1] - e) * side; break
            if (l[j] <= e - sl) if side == 1 else (h[j] >= e + sl): res = -sl; break
            if (h[j] >= e + tp) if side == 1 else (l[j] <= e - tp): res = tp; break
        if res is None: continue
        out.append((dates[i], res))
    return pd.DataFrame(out, columns=["date", "pnl"])
for tp, sl, lab in ((1.0, 10.0, "10 pips / 100 pips ($1 / $10)"), (10.0, 100.0, "10 pts / 100 pts ($10 / $100)")):
    t = run(tp, sl)
    for spread in (0.0, 0.2, 0.35):
        net = t.pnl - spread
        print(f"{lab:32} cost ${spread:.2f}/oz: trades {len(t)} ({len(t)/t.date.nunique():.0f}/day) win {100*(net>0).mean():.1f}%  avg ${net.mean():+.3f}/oz  "
              f"total ${net.sum():+.0f}/oz = ${100*net.sum():+,.0f} per 1 lot  worst day ${100*net.groupby(t.date).sum().min():+,.0f}/lot")
