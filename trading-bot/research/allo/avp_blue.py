"""Rebuild AVP's BLUE zones from real CME volume and score each recipe against the blue zones read off the screenshots.

What the seller says (video): blue = volume zones that historically were great reaction zones; recalculated daily by
"probability"; they persist for days. Table on his chart: anchor = high of the loaded history, ~2-pt profile rows.
Recipe space searched here (chosen by fit to the observed blue zones, Nov 19-26 2026):
  W     trailing sessions in the composite volume profile
  half  zone half-width (pt) around a high-volume peak
  K     how many zones are kept (best reaction rate first)
  rule  how a past touch counts as a reaction
Run:  python allo/avp_blue.py
"""
import os, itertools, numpy as np, pandas as pd

DATA = os.path.join(os.path.expanduser(os.environ.get("EDGE_DATA", "~/edge-data")), "")
ROW = 2.0
# Observed blue zone centres per session (NQZ6), from zones_from_shot.py and the seller's video.
OBS = {"2026-11-19": [27174], "2026-11-20": [26506], "2026-11-23": [25286], "2026-11-24": [26844],
       "2026-11-25": [26263, 26010], "2026-11-26": [25994, 26260]}


def load(since="2026-04-01"):
    z = np.load(DATA + "databento/NQ.npz")
    t = pd.to_datetime(z["t"] * 60, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
    df = pd.DataFrame({k: z[k] for k in "ohlcv"}, index=t)
    df = df[df.index >= since]
    df["sess"] = (df.index + pd.Timedelta(hours=6)).normalize()
    return df


def session_profiles(df):
    """Per session: volume by 2-pt row (typical price), plus 5m bars of the session for reaction counting."""
    out = {}
    for d, g in df.groupby("sess"):
        tp = ((g.h + g.l + g.c) / 3 / ROW).round().astype(int).values
        rows, inv = np.unique(tp, return_inverse=True)
        out[d] = (rows, np.bincount(inv, weights=g.v.values), g.resample("5min").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna())
    return out


def peaks(rows, vol, smooth=5, n=12):
    lo, hi = rows.min(), rows.max(); prof = np.zeros(hi - lo + 1); prof[rows - lo] = vol
    k = np.ones(smooth) / smooth; s = np.convolve(prof, k, mode="same")
    idx = [i for i in range(1, len(s) - 1) if s[i] >= s[i - 1] and s[i] >= s[i + 1] and s[i] > 0]
    idx = sorted(idx, key=lambda i: -s[i])
    keep = []
    for i in idx:                                                     # one peak per 40 pt
        if all(abs(i - j) * ROW > 40 for j in keep): keep.append(i)
        if len(keep) >= n: break
    return [(lo + i) * ROW for i in keep]


def reaction_rate(bars_list, c, half, rule):
    """Share of past touches of [c-half, c+half] that reversed: rule 'close' = a later bar within 6 closes back out on
    the side price came from; rule 'move' = price then moves >= 2*half away on that side within 12 bars."""
    touch = win = 0
    for b in bars_list:
        h, l, cl = b.h.values, b.l.values, b.c.values
        for i in range(1, len(b) - 1):
            above, below = cl[i - 1] > c + half, cl[i - 1] < c - half
            if not (above or below): continue
            if not (l[i] <= c + half and h[i] >= c - half): continue
            touch += 1; j = slice(i, min(i + (6 if rule == "close" else 12), len(b)))
            if rule == "close":
                ok = (cl[j] > c + half).any() if above else (cl[j] < c - half).any()
            else:
                ok = (h[j].max() >= c + 3 * half) if above else (l[j].min() <= c - 3 * half)
            win += ok
    return win / touch if touch >= 3 else 0.0


def blue(profs, days, d, W, half, K, rule):
    i = days.index(d); past = days[max(0, i - W):i]
    if not past: return []
    rows = np.concatenate([profs[p][0] for p in past]); vol = np.concatenate([profs[p][1] for p in past])
    u, inv = np.unique(rows, return_inverse=True); v = np.bincount(inv, weights=vol)
    bars = [profs[p][2] for p in past[-20:]]
    cands = peaks(u, v)
    scored = sorted(((reaction_rate(bars, c, half, rule), c) for c in cands), reverse=True)
    return [c for _, c in scored[:K]]


if __name__ == "__main__":
    df = load(); profs = session_profiles(df); days = sorted(profs)
    res = []
    for W, half, K, rule in itertools.product((10, 20, 40, 60, 120), (25, 35), (2, 3, 4), ("close", "move")):
        hit = tot = fp = 0
        for ds, obs in OBS.items():
            d = pd.Timestamp(ds)
            if d not in profs: continue
            pred = blue(profs, days, d, W, half, K, rule)
            for o in obs:
                tot += 1; hit += any(abs(o - p) <= 25 for p in pred)
            fp += sum(1 for p in pred if all(abs(o - p) > 25 for o in obs))
        res.append((hit / max(tot, 1), -fp, W, half, K, rule))
    res.sort(reverse=True)
    print("best recipes: share of observed blue zones matched (+/-25 pt), false zones, W, half, K, rule")
    for r in res[:12]: print(f"  {r[0]:.2f}  fp {-r[1]:2d}  W={r[2]:3d} half={r[3]} K={r[4]} rule={r[5]}")
    best = res[0]
    print("\nper day with the best recipe (observed vs predicted):")
    for ds, obs in OBS.items():
        d = pd.Timestamp(ds)
        if d in profs: print(" ", ds, "obs", obs, "pred", [round(p) for p in blue(profs, days, d, best[2], best[3], best[4], best[5])])
