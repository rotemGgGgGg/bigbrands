"""Find how AVP Zones sizes its ladder. Known: middle M = previous session's VWAP. Unknown: the step S.
Reads Databento NQ 1-minute bars ($EDGE_DATA/databento/NQ.npz) and prints, for each day whose ladder we read off
the screenshots, every candidate for S next to the observed one, so the matching rule stands out.

    python allo/avp_fit.py
"""
import os, numpy as np, pandas as pd

DATA = os.path.join(os.path.expanduser(os.environ.get("EDGE_DATA", "~/edge-data")), "")
# Observed ladders (zones_from_shot.py / legend readings): session date -> (middle M, step S)
OBS = {"2026-11-19": (27174, 210), "2026-11-23": (25805, 351), "2026-11-24": (26597, 405),
       "2026-11-25": (26331, 428), "2026-11-26": (25610, 262), "2026-11-27": (26250, 262)}


def load():
    z = np.load(DATA + "databento/NQ.npz")
    t = pd.to_datetime(z["t"] * 60, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
    df = pd.DataFrame({k: z[k] for k in "ohlcv"}, index=t)
    df["sess"] = (df.index + pd.Timedelta(hours=6)).normalize()        # Globex session 18:00 -> 17:00 belongs to the next date
    return df[df.index >= "2026-08-01"]


def vw(g):
    tp = (g.h + g.l + g.c) / 3; v = g.v.clip(lower=0)
    if v.sum() <= 0: return np.nan, np.nan
    m = (tp * v).sum() / v.sum(); return m, np.sqrt((v * (tp - m) ** 2).sum() / v.sum())


def stats(df):
    rows = {}
    for d, g in df.groupby("sess"):
        sh = g.index + pd.Timedelta(hours=6); m = sh.hour * 60 + sh.minute  # minutes since 18:00 (session start)
        full16 = g[m < 22 * 60]                                            # 18:00 .. 16:00 NY
        rth = g[(m >= 15 * 60 + 30) & (m < 22 * 60)]                       # 09:30 .. 16:00 NY
        vf, sf = vw(full16); vr, sr = vw(rth); va, sa = vw(g)
        rows[d] = dict(vwap16=vf, sig16=sf, vwapRTH=vr, sigRTH=sr, vwap17=va, sig17=sa,
                       hi=g.h.max(), lo=g.l.min(), rthHi=rth.h.max() if len(rth) else np.nan,
                       rthLo=rth.l.min() if len(rth) else np.nan, close=g.c.iloc[-1])
    s = pd.DataFrame(rows).T.sort_index()
    s["range"] = s.hi - s.lo; s["rthRange"] = s.rthHi - s.rthLo
    s["atr5"] = s.range.rolling(5).mean(); s["atr14"] = s.range.rolling(14).mean()
    for k in ("sig16", "sigRTH", "sig17"):
        s[k + "_avg3"] = s[k].rolling(3).mean(); s[k + "_avg5"] = s[k].rolling(5).mean()
    return s


if __name__ == "__main__":
    s = stats(load()); prev = s.shift(1)                                   # the ladder for day D uses day D-1
    cand = ["sig16", "sigRTH", "sig17", "sig16_avg3", "sig16_avg5", "sigRTH_avg3", "sigRTH_avg5", "sig17_avg3",
            "range", "rthRange", "atr5", "atr14"]
    pd.set_option("display.width", 220)
    print("day        M_obs  vwap16  vwapRTH vwap17 | S_obs  " + "  ".join(f"{c:>11}" for c in cand))
    ratios = {c: [] for c in cand}
    for d, (M, S) in OBS.items():
        p = prev.loc[pd.Timestamp(d)]
        print(f"{d} {M:6.0f} {p.vwap16:7.0f} {p.vwapRTH:7.0f} {p.vwap17:7.0f} | {S:5.0f}  " +
              "  ".join(f"{p[c]:6.0f}({S / p[c]:.2f})" for c in cand))
        for c in cand: ratios[c].append(S / p[c])
    print("\nratio S/candidate: mean and spread (the right candidate has a constant ratio, low spread)")
    for c in cand:
        r = np.array(ratios[c], float); print(f"  {c:12} mean {np.nanmean(r):.3f}  cv {np.nanstd(r) / np.nanmean(r):.3f}")
