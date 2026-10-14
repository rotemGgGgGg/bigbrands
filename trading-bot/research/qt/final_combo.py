"""Round 4: 'Intraday momentum + inter-day reversal' book. Legs (1 MNQ each): Noise-Area, afternoon momentum,
Rebound (prev RTH day fell >1% → long 09:30→12:00). Daily P&L with intraday low → Lucid 50K lifecycle sim."""
import sys; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from engine import S, COST_PTS, PT_USD, IS_END
from prop_sim import na_days
from prop_sim2 import lifecycle
from afternoon import am_days, D
N = len(D.days)
pc = np.r_[np.nan, D.c[:-1, 389]]; ppc = np.r_[np.nan, np.nan, D.c[:-2, 389]]
ret_prev = pc / ppc - 1
valid = ~(D.roll | (D.prev_gap_days > 4)) & ~np.r_[True, D.roll[:-1]]
pnl = np.zeros(N); low = np.zeros(N)
for i in range(N):
    if valid[i] and ret_prev[i] < -0.01:
        e = D.o[i, 0]
        pnl[i] = ((D.c[i, 149] - e) - COST_PTS) * PT_USD
        low[i] = min(0, (D.l[i, :150].min() - e) * PT_USD - COST_PTS * PT_USD)
reb = pd.DataFrame({"date": D.days, "pnl": pnl, "low": low})
na = na_days(None); am = am_days()
legs = {"NA": na.set_index("date"), "AM": am.set_index("date"), "REB": reb.set_index("date")}
ix = legs["NA"].index
L = {k: v.reindex(ix).fillna(0) for k, v in legs.items()}
print("daily P&L correlation:\n", pd.DataFrame({k: v.pnl for k, v in L.items()}).corr().round(2))
def show(name, keys):
    p = sum(L[k].pnl for k in keys); lo = sum(L[k].low for k in keys)
    dts = pd.to_datetime(ix); act = p[p != 0]
    eq = p.cumsum(); dd = (eq - eq.cummax()).min()
    sh = p.mean() / p.std() * np.sqrt(252)
    yrs = p.groupby(dts.year).sum()
    line = f"{name:22} net ${p.sum():>8,.0f} maxDD ${dd:>7,.0f} Sharpe {sh:4.2f} yrs+ {(yrs>0).sum()}/7"
    for lab, sel in (("IS", dts < IS_END), ("OOS", dts >= IS_END)):
        st = [k for k in range(len(ix)) if sel[k]]
        res = pd.DataFrame([lifecycle(p.values, lo.values, s, 1500) for s in st], columns=["status", "paid", "npay"])
        c = res[res.status != "open"]
        line += f" | {lab} pass {100*(c.status!='eval_fail').mean():4.1f}% payout {100*(c.paid>0).mean():4.1f}% EV ${c.paid.mean()-146:+,.0f}"
    print(line)
show("Rebound only", ["REB"])
show("NA + AM", ["NA", "AM"])
show("NA + AM + Rebound", ["NA", "AM", "REB"])
show("NA + Rebound", ["NA", "REB"])
