"""04:00-15:59 NY 1-minute grid (720 bars; 09:30 = index 330) per trading day, HistData NSXUSD (Nasdaq-100 CFD, same index as NQ).
Forward-filled inside the day; days need >= 300 RTH bars."""
import os, glob, zipfile, io, pickle, numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
T0 = 240; NB = 720; RTH = 330


def load(sym="NSXUSD"):
    cache = SP + f"mega_{sym}.pkl"
    if os.path.exists(cache): return pickle.load(open(cache, "rb"))
    parts = []
    for z in sorted(glob.glob(SP + f"histdata/{sym}_*.zip")):
        with zipfile.ZipFile(z) as f:
            nm = [n for n in f.namelist() if n.endswith(".csv")][0]
            df = pd.read_csv(io.BytesIO(f.read(nm)), sep=";", header=None, names=["t", "o", "h", "l", "c", "v"])
        df.index = pd.to_datetime(df.t, format="%Y%m%d %H%M%S"); parts.append(df[["o", "h", "l", "c"]])
    f = pd.concat(parts).sort_index(); f = f[~f.index.duplicated()]
    m = (f.index.hour * 60 + f.index.minute).values - T0; f = f[(m >= 0) & (m < NB)]; m = m[(m >= 0) & (m < NB)]
    day = f.index.normalize(); days = day.unique(); days = days[days.weekday < 5]
    pos = pd.Series(np.arange(len(days)), index=days); di = pos.reindex(day).values
    ok = ~np.isnan(di); di = di[ok].astype(int); m = m[ok]
    A = {k: np.full((len(days), NB), np.nan) for k in "ohlc"}
    for k in "ohlc": A[k][di, m] = f[k].values[ok]
    keep = (~np.isnan(A["c"][:, RTH:])).sum(1) >= 300
    for k in "ohlc": A[k] = A[k][keep]
    c = pd.DataFrame(A["c"]).ffill(axis=1).bfill(axis=1).values
    for k in "ohl": A[k] = np.where(np.isnan(A[k]), c, A[k])
    A["c"] = c; A["days"] = days[keep]; pickle.dump(A, open(cache, "wb"), protocol=4); return A


if __name__ == "__main__":
    import sys
    A = load(sys.argv[1]); print(sys.argv[1], A["o"].shape, A["days"][0].date(), A["days"][-1].date())
