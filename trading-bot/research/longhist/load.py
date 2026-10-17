"""HistData.com free 1-minute CFD bars (NSXUSD = Nasdaq-100, SPXUSD = S&P 500, UDXUSD = dollar index), 2012–2025.
Timestamps verified to be New York wall-clock time (daily halt resumes 18:00 NY in both seasons; aligned with Databento MNQ, see check below). No volume (CFD).
Builds (a) the 24h frame and (b) an RTH grid (09:30–15:59, 390 minutes) compatible with the MNQ research code."""
import os, glob, zipfile, io, pickle, sys
import numpy as np, pandas as pd
HD = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/histdata/"
def frame(pair):
    out = os.path.join(HD, f"{pair}_full.pkl")
    if os.path.exists(out): return pd.read_pickle(out)
    parts = []
    for z in sorted(glob.glob(os.path.join(HD, f"{pair}_*.zip"))):
        with zipfile.ZipFile(z) as f:
            name = [n for n in f.namelist() if n.endswith(".csv")][0]
            df = pd.read_csv(io.BytesIO(f.read(name)), sep=";", header=None, names=["t", "open", "high", "low", "close", "v"])
        df.index = pd.to_datetime(df.t, format="%Y%m%d %H%M%S").dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT")
        parts.append(df[["open", "high", "low", "close"]])
    f = pd.concat(parts).sort_index(); f = f[~f.index.duplicated()]; f.to_pickle(out); return f
class RTH:
    def __init__(self, f):
        m = f.index.hour * 60 + f.index.minute; r = f[(m >= 570) & (m < 960)]
        days, arr = [], {k: [] for k in "ohlc"}
        for d, g in r.groupby(r.index.date):
            if pd.Timestamp(d).weekday() >= 5 or len(g) < 360: continue
            mins = g.index.hour * 60 + g.index.minute - 570
            if mins.max() < 385: continue
            gg = g.set_index(mins).reindex(range(390)); gg["close"] = gg.close.ffill().bfill()
            for k in ("open", "high", "low"): gg[k] = gg[k].fillna(gg.close)
            days.append(d); arr["o"].append(gg.open.values); arr["h"].append(gg.high.values); arr["l"].append(gg.low.values); arr["c"].append(gg.close.values)
        self.days = days
        for k, v in arr.items(): setattr(self, k, np.array(v))
if __name__ == "__main__":
    for p in ("NSXUSD", "SPXUSD", "UDXUSD"):
        f = frame(p); print(p, len(f), f.index[0], f.index[-1])
        jul = f[(f.index.month == 7) & (f.index.year == 2019)]
        gaps = jul.index.to_series().diff().dt.total_seconds()
        print("  July-2019 daily gap starts (NY time):", sorted(set((jul.index[gaps.values > 3000] - pd.Timedelta(seconds=1)).strftime("%H:%M")))[:3],
              "| Jan:", sorted(set(f[(f.index.month == 1) & (f.index.year == 2019)].index[f[(f.index.month == 1) & (f.index.year == 2019)].index.to_series().diff().dt.total_seconds().values > 3000].strftime("%H:%M")))[:3])
