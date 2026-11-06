"""Turn a Dukascopy UTC 1-minute file into the same day dict the NQ engine uses (papers/pdata.py): a 390-minute main-session grid
in the market's own local time, the 4 hours before it as 'pre-market', and daily session OHLC. Costs and tick per market."""
import os, pickle
import numpy as np, pandas as pd
DK = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/duka/"
CACHE = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/mdata/"
# name: (timezone, session start, round-trip cost in basis points of price, tick)
MK = {
    "USATECHIDXUSD": ("America/New_York", "09:30", 1.3, 0.25), "USA500IDXUSD": ("America/New_York", "09:30", 1.3, 0.25),
    "USA30IDXUSD": ("America/New_York", "09:30", 1.3, 1.0), "DEUIDXEUR": ("Europe/Berlin", "09:00", 1.3, 0.5),
    "EUSIDXEUR": ("Europe/Berlin", "09:00", 1.5, 1.0), "FRAIDXEUR": ("Europe/Paris", "09:00", 1.5, 0.5),
    "GBRIDXGBP": ("Europe/London", "08:00", 1.5, 0.5), "JPNIDXJPY": ("Asia/Tokyo", "09:00", 1.5, 5.0),
    "AUSIDXAUD": ("Australia/Sydney", "10:00", 2.0, 1.0), "HKGIDXHKD": ("Asia/Hong_Kong", "09:30", 2.0, 1.0),
    "XAUUSD": ("America/New_York", "08:30", 1.6, 0.1), "XAGUSD": ("America/New_York", "08:30", 3.0, 0.005),
    "LIGHTCMDUSD": ("America/New_York", "09:00", 4.0, 0.01), "BRENTCMDUSD": ("America/New_York", "09:00", 4.0, 0.01),
    "EURUSD": ("America/New_York", "08:00", 0.8, 0.00001), "GBPUSD": ("America/New_York", "08:00", 1.0, 0.00001),
    "AUDUSD": ("America/New_York", "08:00", 1.2, 0.00001), "USDCAD": ("America/New_York", "08:00", 1.2, 0.00001),
    "USDJPY": ("America/New_York", "08:00", 1.0, 0.001), "EURJPY": ("America/New_York", "08:00", 1.5, 0.001)}


MK["SPXUSD"] = ("America/New_York", "09:30", 1.3, 0.25); MK["NSXUSD"] = ("America/New_York", "09:30", 1.3, 0.25)
HD = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/histdata/"


def histdata(sym):
    import glob, zipfile, io
    parts = []
    for zf in sorted(glob.glob(HD + sym + "_*.zip")):
        with zipfile.ZipFile(zf) as f:
            n = [x for x in f.namelist() if x.endswith(".csv")][0]
            d = pd.read_csv(io.BytesIO(f.read(n)), sep=";", header=None, names=["t", "o", "h", "l", "c", "v"])
        d.index = pd.to_datetime(d.t, format="%Y%m%d %H%M%S"); parts.append(d[["o", "h", "l", "c"]])
    return pd.concat(parts).sort_index()


def load(sym):
    f = CACHE + sym + ".pkl"
    if os.path.exists(f): return pickle.load(open(f, "rb"))
    tz, st, bp, tick = MK[sym]
    if sym in ("SPXUSD", "NSXUSD"): df = histdata(sym)                       # HistData: already New York wall-clock time
    else:
        z = np.load(DK + sym + ".npz"); t = pd.to_datetime(z["t"] * 60, unit="s", utc=True).tz_convert(tz).tz_localize(None)
        df = pd.DataFrame({k: z[k] for k in "ohlc"}, index=t)
    df = df.sort_index(); df = df[~df.index.duplicated()]
    s0 = int(st[:2]) * 60 + int(st[3:]); m = df.index.hour * 60 + df.index.minute; dd = df.index.normalize()
    rth = df[(m >= s0) & (m < s0 + 390)]; rm = (rth.index.hour * 60 + rth.index.minute - s0).values; rd = rth.index.normalize()
    pm = df[(m >= s0 - 240) & (m < s0)]; pmg = {k: g for k, g in pm.groupby(pm.index.normalize())}
    days, O, H, L, C, PM = [], [], [], [], [], []
    for d, idx in pd.Series(np.arange(len(rth)), index=rd).groupby(level=0):
        if d.weekday() >= 5 or len(idx) < 300: continue
        x = rth.iloc[idx.values].set_index(rm[idx.values]).reindex(range(390)); x["c"] = x.c.ffill().bfill()
        for k in "ohl": x[k] = x[k].fillna(x.c)
        days.append(d); O.append(x.o.values); H.append(x.h.values); L.append(x.l.values); C.append(x.c.values)
        p = pmg.get(d); PM.append((p.o.iloc[0], p.c.iloc[-1], p.h.max(), p.l.min()) if p is not None and len(p) > 30 else (np.nan,) * 4)
    O, H, L, C = (np.array(a, float) for a in (O, H, L, C)); PM = np.array(PM)
    D = dict(days=pd.DatetimeIndex(days), o=O, h=H, l=L, c=C, pmo=PM[:, 0], pmc=PM[:, 1], pmh=PM[:, 2], pml=PM[:, 3],
             do=O[:, 0], dh=H.max(1), dl=L.min(1), dc=C[:, -1], sym=sym, bp=bp, tick=tick)
    os.makedirs(CACHE, exist_ok=True); pickle.dump(D, open(f, "wb"), protocol=4); return D
