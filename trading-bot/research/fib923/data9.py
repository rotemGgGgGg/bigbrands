"""1-minute grid 09:00-15:59 NY (420 bars, minute 0 = 09:00, 09:30 = index 30) from the HistData NSXUSD cache, for the
pre-market-candle Fib model. Days = the same trading days as papers/pdata."""
import os, sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "papers")); import pdata
CACHE = pdata.SP + "grid0900.pkl"


def load():
    if os.path.exists(CACHE): return pickle.load(open(CACHE, "rb"))
    P = pdata.load(); f = pdata.minute_frame(); m = f.index.hour * 60 + f.index.minute
    f = f[(m >= 540) & (m < 960)]; dd = f.index.normalize(); mi = (f.index.hour * 60 + f.index.minute - 540).values
    keep = set(P["days"]); A = {k: np.full((len(P["days"]), 420), np.nan) for k in "ohlc"}; pos = {d: i for i, d in enumerate(P["days"])}
    di = np.array([pos.get(d, -1) for d in dd]); ok = di >= 0
    for k in "ohlc": A[k][di[ok], mi[ok]] = f[k].values[ok]
    c = pd.DataFrame(A["c"]).ffill(axis=1).bfill(axis=1).values
    for k in "ohl": A[k] = np.where(np.isnan(A[k]), c, A[k])
    A["c"] = c
    # flag days that really have a 09:23 bar (no forward-fill)
    raw = np.zeros(len(P["days"]), bool); raw[di[ok & (mi == 23)]] = True; A["real923"] = raw
    A["days"] = P["days"]; pickle.dump(A, open(CACHE, "wb"), protocol=4); return A


if __name__ == "__main__":
    A = load(); print(A["o"].shape, A["real923"].mean())
