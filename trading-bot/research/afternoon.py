"""Afternoon momentum (found by search.py, IS-selected / OOS-confirmed): at time E, if the move since the prior
close is larger than k × its 20-day std, trade in that direction for H minutes. Then Lucid lifecycle sims."""
import pickle, numpy as np, pandas as pd
from engine import S, COST_PTS, PT_USD, IS_END
from prop_sim import na_days
from prop_sim2 import lifecycle
D = pickle.load(open(S + "D.pkl", "rb"))
N = len(D.days); pc = np.r_[np.nan, D.c[:-1, 389]]
valid = ~(D.roll | (D.prev_gap_days > 4))

def am_days(E=330, H=30, k=1.0):           # E = minutes after 09:30 (330 = 15:00)
    r = D.c[:, E - 1] / pc - 1
    sd = pd.Series(r).rolling(20).std().shift().values
    pnl = np.zeros(N); low = np.zeros(N)
    for i in range(N):
        if not valid[i] or np.isnan(sd[i]) or abs(r[i]) <= k * sd[i]: continue
        s = 1 if r[i] > 0 else -1; e = D.o[i, E]; x = E + H - 1
        worst = ((D.l[i, E:x + 1].min() - e) if s == 1 else (e - D.h[i, E:x + 1].max()))
        pnl[i] = ((D.c[i, x] - e) * s - COST_PTS) * PT_USD
        low[i] = min(0, worst * PT_USD - COST_PTS * PT_USD)
    return pd.DataFrame({"date": D.days, "pnl": pnl, "low": low})

def show(name, b):
    dts = pd.to_datetime(b.date)
    t = b[b.pnl != 0]; y = pd.to_datetime(t.date)
    print(f"\n{name}: trades {len(t)} ({len(t)/6.8/12:.1f}/month) win {100*(t.pnl>0).mean():.1f}% avg ${t.pnl.mean():+.1f} "
          f"yrs+ {int((t.pnl.groupby(y.dt.year).sum()>0).sum())}/7 worst day ${t.pnl.min():.0f}")
    for keep in (1500, 2500):
        for lab, sel in (("IS", dts < IS_END), ("OOS", dts >= IS_END)):
            st = [k for k in range(len(b)) if sel.iloc[k]]
            res = pd.DataFrame([lifecycle(b.pnl.values, b.low.values, s, keep) for s in st], columns=["status", "paid", "npay"])
            c = res[res.status != "open"]
            print(f"   keep ${keep} {lab:3}: pass {100*(c.status!='eval_fail').mean():5.1f}%  ≥1 payout {100*(c.paid>0).mean():5.1f}%  "
                  f"avg payouts {c.npay.mean():.2f}  EV/attempt ${c.paid.mean()-146:+.0f}  (unfinished {100*(res.status=='open').mean():.0f}%)")

na = na_days(None); na["date"] = na.date
am = am_days(); am14 = am_days(300, 60, 1.0)
nad = na.set_index("date"); amd = am.set_index("date").reindex(nad.index).fillna(0)
show("Afternoon momentum 15:00–15:30, 1 MNQ", am)
for n in (2, 3):
    show(f"Afternoon momentum 15:00–15:30, {n} MNQ", am.assign(pnl=am.pnl * n, low=am.low * n))
show("Afternoon momentum 14:30–15:30, 1 MNQ", am14)
show("Noise-Area 1 MNQ", na)
comb = pd.DataFrame({"date": nad.index, "pnl": (nad.pnl + amd.pnl).values, "low": (nad.low + amd.low).values})
show("Noise-Area 1 + Afternoon 1", comb)
