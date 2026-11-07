"""Overnight-range quarters claim: at the 09:30 open, locate the open inside the overnight (18:00-09:29 ET) high-low range.
Claim: open in the half near the low -> RTH takes the ON low 75.6%; near the high -> takes the ON high 81%.
Tests: (1) replicate hit rates by zone; (2) EDGE check: hit rate of ON level vs a mirror level at the same distance on the
other side of the open (if equal, the 'edge' is just distance); (3) tradeable versions, net of cost, select 2012-19, OOS 2020-26."""
import sys, os, math, pickle
sys.path.insert(0, "../multi"); import numpy as np, pandas as pd, mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/onrange/"; os.makedirs(SP, exist_ok=True)

def build(sym):
    f = SP + sym + ".pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    if sym in ("NSXUSD", "SPXUSD"): df = mdata.histdata(sym); tz, st = "America/New_York", "09:30"
    else:
        tz, st, _, _ = mdata.MK[sym]; z = np.load(mdata.DK + sym + ".npz")
        t = pd.to_datetime(z["t"] * 60, unit="s", utc=True).tz_convert(tz).tz_localize(None)
        df = pd.DataFrame({k: z[k] for k in "ohlc"}, index=t)
    df = df.sort_index(); df = df[~df.index.duplicated()]
    s0 = int(st[:2]) * 60 + int(st[3:]); m = df.index.hour * 60 + df.index.minute
    # overnight = from previous session close (s0+390) to s0; label by the next trading date
    d = df.index.normalize(); after = m >= s0 + 390
    lab = d.where(~after, d + pd.Timedelta(days=1))
    lab = pd.DatetimeIndex([x + pd.Timedelta(days=(7 - x.weekday()) % 7 if x.weekday() >= 5 else 0) for x in lab]) if False else lab
    df["lab"] = lab; df["m"] = m
    D = mdata.load(sym); out = []
    on = df[(df.m < s0) | (df.m >= s0 + 390)].copy()
    # weekend: Friday evening / Sunday evening bars roll forward to Monday
    wd = on.lab.dt.weekday; on.loc[wd == 5, "lab"] += pd.Timedelta(days=2); on.loc[wd == 6, "lab"] += pd.Timedelta(days=1)
    g = on.groupby("lab").agg(onh=("h", "max"), onl=("l", "min"), n=("c", "size"))
    for i, day in enumerate(D["days"]):
        if day not in g.index or g.loc[day, "n"] < 120: continue
        out.append((day, g.loc[day, "onh"], g.loc[day, "onl"], i))
    R = pd.DataFrame(out, columns=["day", "onh", "onl", "i"]).set_index("day")
    res = dict(R=R, o=D["o"], h=D["h"], l=D["l"], c=D["c"], bp=D["bp"], days=D["days"])
    pd.to_pickle(res, f); return res

def first_touch(h, l, up, dn, t0=0, t1=390):
    """minute index of first touch of level up (high>=up) and dn (low<=dn) from t0; 999 if none"""
    hu = np.nonzero(h[t0:t1] >= up)[0]; ld = np.nonzero(l[t0:t1] <= dn)[0]
    return (hu[0] + t0 if len(hu) else 999), (ld[0] + t0 if len(ld) else 999)

def analyse(sym):
    Z = build(sym); R = Z["R"]; rows = []
    for day, r in R.iterrows():
        i = int(r.i); o = Z["o"][i, 0]; h, l, c = Z["h"][i], Z["l"][i], Z["c"][i]; rng = r.onh - r.onl
        if rng <= 0: continue
        pos = (o - r.onl) / rng
        tH, tL = first_touch(h, l, r.onh, r.onl)
        # mirror levels: same distance as the near ON level, other side of the open
        dL, dH = o - r.onl, r.onh - o
        tmU, _ = first_touch(h, l, o + max(dL, 1e-9), -1e18)        # mirror of ON low (above open)
        _, tmD = first_touch(h, l, 1e18, o - max(dH, 1e-9))          # mirror of ON high (below open)
        rows.append(dict(day=day, pos=pos, rng=rng, o=o, onh=r.onh, onl=r.onl, tH=tH, tL=tL, tmU=tmU, tmD=tmD, c=c[-1], i=i))
    return pd.DataFrame(rows).set_index("day"), Z

if __name__ == "__main__":
    for sym in sys.argv[1:] or ["NSXUSD"]:
        A, Z = analyse(sym); A["yr"] = A.index.year
        ins = A[(A.pos >= 0) & (A.pos <= 1)]
        print(f"\n=== {sym}: {len(A)} days, open inside ON range {100*len(ins)/len(A):.0f}%")
        z = pd.cut(A.pos, [-9, 0, .25, .5, .75, 1, 9], labels=["below", "Q1 low", "Q2", "Q3", "Q4 high", "above"])
        t = A.groupby(z).apply(lambda g: pd.Series(dict(n=len(g), takeLow=100*(g.tL < 999).mean(), takeHigh=100*(g.tH < 999).mean(),
              mirrorOfLow=100*(g.tmU < 999).mean(), mirrorOfHigh=100*(g.tmD < 999).mean())))
        print(t.round(1).to_string())
        lo = ins[ins.pos < .5]; hi = ins[ins.pos >= .5]
        print(f"lower half: takes ON low {100*(lo.tL<999).mean():.1f}%  | same distance UP from open {100*(lo.tmU<999).mean():.1f}%")
        print(f"upper half: takes ON high {100*(hi.tH<999).mean():.1f}% | same distance DOWN from open {100*(hi.tmD<999).mean():.1f}%")
        A.to_pickle(SP + sym + "_A.pkl")
