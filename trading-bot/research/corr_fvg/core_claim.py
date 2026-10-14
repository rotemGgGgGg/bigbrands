"""The indicator's core claim, with NO other filters: does a gap whose ES/YM twin is still ALIVE at entry beat a plain NQ gap?
Compares alive-correlated vs all, per timeframe × entry × stop × R:R, TRAIN (first 60 %) and TEST (last 40 %)."""
import numpy as np, pandas as pd, pickle, itertools
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
rows = []
for tf in ("5m", "15m", "1h", "4h"):
    EV, sims, t0, t1 = pickle.load(open(S + f"cfvg_{tf}.pkl", "rb")); cut = t0 + (t1 - t0) * 0.6; TR = (EV.ts < cut).values; nd = ~EV.ndog.values
    for entry, stop, rr in itertools.product(("near", "ce", "market"), ("edge", "atr05", "atr1"), (1.0, 2.0)):
        for alive in (False, True):
            x = sims[(entry, stop, rr, False, alive)]; ok = ~np.isnan(x) & nd
            r = dict(tf=tf, entry=entry, stop=stop, rr=rr, alive=alive)
            for nm, p in (("tr", TR), ("te", ~TR)):
                y = x[ok & p]; r[f"n_{nm}"] = len(y); r[f"win_{nm}"] = round(100 * (y > 0).mean(), 1); r[f"R_{nm}"] = round(y.mean(), 3)
            rows.append(r)
R = pd.DataFrame(rows); pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
w = R.pivot_table(index=["tf", "entry", "stop", "rr"], columns="alive", values=["R_tr", "R_te", "win_te"])
w["dR_tr"] = w[("R_tr", True)] - w[("R_tr", False)]; w["dR_te"] = w[("R_te", True)] - w[("R_te", False)]
print(w.round(3).to_string())
print("\nalive improves expectancy in TRAIN:", int((w.dR_tr > 0).sum()), "/", len(w), "| in TEST:", int((w.dR_te > 0).sum()), "/", len(w))
print("alive configs with TEST R > 0:", int((w[("R_te", True)] > 0).sum()), " | of those TRAIN R > 0 too:", int(((w[("R_te", True)] > 0) & (w[("R_tr", True)] > 0)).sum()))
