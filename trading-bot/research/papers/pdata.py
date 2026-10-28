"""Data for the classic-papers study: HistData free 1-minute NSXUSD (Nasdaq-100 CFD, New York wall-clock time), 2012-01 → 2026-10.
(The user's Databento NQ file was lost with the container reset; the CFD is the cash Nasdaq-100 — no contract rolls, no volume.)
Builds per trading day: RTH 1-minute grid 09:30-15:59 (390 bars, forward-filled), pre-market 1-minute bars (04:00-09:29) and
daily RTH OHLC. Run with /usr/bin/python3 (numpy + pandas)."""
import os, glob, zipfile, io, pickle
import numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
HD = SP + "histdata/"; CACHE = SP + "papers_data.pkl"


def minute_frame():
    parts = []
    for z in sorted(glob.glob(HD + "NSXUSD_*.zip")):
        with zipfile.ZipFile(z) as f:
            name = [n for n in f.namelist() if n.endswith(".csv")][0]
            df = pd.read_csv(io.BytesIO(f.read(name)), sep=";", header=None, names=["t", "o", "h", "l", "c", "v"])
        df.index = pd.to_datetime(df.t, format="%Y%m%d %H%M%S"); parts.append(df[["o", "h", "l", "c"]])
    f = pd.concat(parts).sort_index(); return f[~f.index.duplicated()]


def load():
    if os.path.exists(CACHE): return pickle.load(open(CACHE, "rb"))
    f = minute_frame(); m = f.index.hour * 60 + f.index.minute; day = f.index.normalize()
    rth = f[(m >= 570) & (m < 960)]; rd = rth.index.normalize(); rm = rth.index.hour * 60 + rth.index.minute - 570
    days = []; O, H, L, C = [], [], [], []; PMH, PML, PMO, PMC = [], [], [], []
    pm = f[(m >= 240) & (m < 570)]; pmg = {k: g for k, g in pm.groupby(pm.index.normalize())}
    for d, g in rth.groupby(rd):
        if d.weekday() >= 5 or len(g) < 300: continue
        x = g.set_index(rm[rd == d]).reindex(range(390)); x["c"] = x.c.ffill().bfill()
        for k in ("o", "h", "l"): x[k] = x[k].fillna(x.c)
        days.append(d); O.append(x.o.values); H.append(x.h.values); L.append(x.l.values); C.append(x.c.values)
        p = pmg.get(d)
        if p is not None and len(p) > 30: PMO.append(p.o.iloc[0]); PMC.append(p.c.iloc[-1]); PMH.append(p.h.max()); PML.append(p.l.min())
        else: PMO.append(np.nan); PMC.append(np.nan); PMH.append(np.nan); PML.append(np.nan)
    O, H, L, C = (np.array(a, dtype=np.float64) for a in (O, H, L, C)); days = pd.DatetimeIndex(days)
    D = dict(days=days, o=O, h=H, l=L, c=C, pmo=np.array(PMO), pmc=np.array(PMC), pmh=np.array(PMH), pml=np.array(PML),
             do=O[:, 0], dh=H.max(1), dl=L.min(1), dc=C[:, -1])
    pickle.dump(D, open(CACHE, "wb"), protocol=4); return D


if __name__ == "__main__":
    D = load(); print(len(D["days"]), D["days"][0].date(), D["days"][-1].date(), D["dc"][[0, -1]])
