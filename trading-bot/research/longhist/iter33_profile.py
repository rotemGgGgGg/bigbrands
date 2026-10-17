"""Iter 33 — old market-profile / pit-era ideas that are rarely backtested, all at planned 1:2, three periods
(NSXUSD 24 h CFD 2012–19; Databento MNQ 24 h 2020–23 / 2024–26). Profiles are TPO-based (1-minute closes rounded to a bin of
0.02σ) so the CFD (no volume) and the futures are treated the same.
A Dalton overnight-inventory correction: open in the top/bottom q of the overnight (18:00–09:29) range AND beyond the prior close
  → fade at 09:30 toward the overnight midpoint (target), stop = half the distance.
B Prior-day POC magnet: |open − prior RTH POC| ≥ x·σ → trade toward the POC at 09:30, stop half the distance.
  B2 'virgin' POC: nearest POC of the last 10 sessions not traded since → same trade.
C Poor high / poor low repair: prior RTH high (low) printed in ≥ 2 separate 30-minute periods within 0.03σ → if today opens below
  (above) it, trade toward it at 09:30, stop half the distance.
D Taylor 3-day cycle: day 0 = most recent day that closed at a 10-day low (buy day), cycle = days since mod 3.
  On buy days: first undercut of the prior day low then a close back above it (before 12:00) → long, stop under the session low
  (≥ 0.1σ), target 2×. On short-sell days (mod 3 == 2): the mirror at the prior day high.
Exits at the 15:59 close. Cost 2.25 pt scaled to price. One trade per day per rule."""
import sys; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd, itertools
from load import frame
from engine import walk
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/full1m.pkl"
def days_from(f):
    f = f[f.index.notna()]; m = f.index.hour * 60 + f.index.minute
    # session key: bars from 18:00 belong to the next day's session
    key = (f.index + pd.Timedelta(hours=6)).normalize().tz_localize(None)
    out = []
    for k, g in f.groupby(key):
        if k.weekday() >= 5: continue
        mm = g.index.hour * 60 + g.index.minute; r = g[(mm >= 570) & (mm < 960)]
        if len(r) < 360: continue
        on = g[(mm >= 1080) | (mm < 570)]
        if len(on) < 300: continue
        rm = r.index.hour * 60 + r.index.minute - 570
        rr = r.set_index(rm).reindex(range(390)); rr["close"] = rr.close.ffill().bfill()
        for c_ in ("open", "high", "low"): rr[c_] = rr[c_].fillna(rr.close)
        out.append((k, rr.open.values, rr.high.values, rr.low.values, rr.close.values, on.high.max(), on.low.min()))
    k, o, h, l, c, onh, onl = zip(*out)
    return pd.DatetimeIndex(k), *map(np.array, (o, h, l, c, onh, onl))
def periods():
    f = frame("NSXUSD"); yield "2012-19", days_from(f[:"2019-12-31"])
    g = pd.read_pickle(SP); dd = days_from(g)
    for nm, m in (("2020-23", dd[0].year < 2024), ("2024-26", dd[0].year >= 2024)):
        yield nm, tuple(x[m] for x in dd)
res = []
def add(per, rule, R):
    R = np.array([r for r in R if np.isfinite(r)])
    if len(R) < 15: return
    res.append(dict(per=per, rule=rule, n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
for per, (days, o, h, l, c, onh, onl) in periods():
    N = len(o); O = o[:, 0]; C = c[:, 389]; H = h.max(1); L = l.min(1)
    sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    cost = lambda e: 2.25 * e / 17000
    def go(i, m, s, e, stop, tgt):
        px, _, _ = walk(o[i], h[i], l[i], c[i], m, s, e, stop, tgt, 389); return (s * (px - e) - cost(e)) / abs(e - stop)
    def toward(i, tgt, minfrac=0.1):
        e = O[i]; d = tgt - e
        if abs(d) < minfrac * sig[i] * e: return np.nan
        s = int(np.sign(d)); return go(i, 0, s, e, e - s * abs(d) / 2, tgt)
    # TPO POC per day
    poc = np.full(N, np.nan); poorH = np.zeros(N, bool); poorL = np.zeros(N, bool)
    for i in range(N):
        if not np.isfinite(sig[i]): continue
        b = 0.02 * sig[i] * O[i]; q = np.round(c[i] / b); v, cnt = np.unique(q, return_counts=True)
        top = v[cnt == cnt.max()]; poc[i] = np.median(top) * b
        tol = 0.03 * sig[i] * O[i]; h30 = h[i].reshape(13, 30).max(1); l30 = l[i].reshape(13, 30).min(1)
        poorH[i] = (h30 >= H[i] - tol).sum() >= 2; poorL[i] = (l30 <= L[i] + tol).sum() >= 2
    # A overnight inventory
    for q, tgt_mode in itertools.product((0.8, 0.9, 1.0), ("on_mid", "prev_close")):
        R = []
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            rng = onh[i] - onl[i]
            if rng <= 0: continue
            pos = (O[i] - onl[i]) / rng; s = 0
            if pos >= q - 1e-9 and O[i] > C[i - 1]: s = -1
            if pos <= 1 - q + 1e-9 and O[i] < C[i - 1]: s = 1
            if s == 0: continue
            tgt = (onh[i] + onl[i]) / 2 if tgt_mode == "on_mid" else C[i - 1]
            if s * (tgt - O[i]) <= 0: continue
            R.append(toward(i, tgt))
        add(per, f"A ON inventory q{q} → {tgt_mode}", R)
    # B prior-day POC and virgin POC
    for x in (0.1, 0.25, 0.5, 0.75):
        R = [toward(i, poc[i - 1], x) for i in range(15, N) if np.isfinite(sig[i]) and np.isfinite(poc[i - 1])]
        add(per, f"B prior POC dist≥{x}σ", R)
        R = []
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            cands = []
            for j in range(i - 10, i):
                p = poc[j]
                if not np.isfinite(p): continue
                if j + 1 < i and ((L[j + 1:i] <= p) & (H[j + 1:i] >= p)).any(): continue
                cands.append(p)
            if not cands: continue
            p = min(cands, key=lambda z: abs(z - O[i])); R.append(toward(i, p, x))
        add(per, f"B2 virgin POC (10d) dist≥{x}σ", R)
    # C poor high / low
    for x in (0.1, 0.25, 0.5):
        R = []
        for i in range(15, N):
            if not np.isfinite(sig[i]): continue
            if poorH[i - 1] and O[i] < H[i - 1]: R.append(toward(i, H[i - 1], x))
            elif poorL[i - 1] and O[i] > L[i - 1]: R.append(toward(i, L[i - 1], x))
        add(per, f"C poor high/low repair dist≥{x}σ", R)
    # D Taylor
    lo10 = pd.Series(C).rolling(10).min().values; anchor = -1; cyc = np.full(N, -1)
    for i in range(N):
        if anchor >= 0: cyc[i] = (i - anchor) % 3
        if C[i] == lo10[i]: anchor = i
    for day, s in (("buy", 1), ("short", -1)):
        R = []
        for i in range(15, N):
            if not np.isfinite(sig[i]) or cyc[i] != (1 if day == "buy" else 0): continue   # day after anchor = buy day
            lvl = L[i - 1] if s == 1 else H[i - 1]
            pen = np.nonzero(s * (l[i, :150] if s == 1 else h[i, :150]) < s * lvl)[0]
            if not len(pen): continue
            back = np.nonzero(s * (c[i, pen[0]:150] - lvl) > 0)[0]
            if not len(back): continue
            m = pen[0] + back[0] + 1; e = o[i, m]; ext = l[i, :m].min() if s == 1 else h[i, :m].max()
            st = max(s * (e - ext), 0.1 * sig[i] * e); R.append(go(i, m, s, e, e - s * st, e + s * 2 * st))
        add(per, f"D Taylor {day}-day violation reclaim", R)
    print(per, N, "days done", flush=True)
T = pd.DataFrame(res); T.to_csv("iter33_profile.csv", index=False)
W = T.pivot_table(index="rule", columns="per", values=["win", "R", "n"]); W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
pd.set_option("display.width", 250); print(W.sort_values("minR", ascending=False).round(3).to_string())
