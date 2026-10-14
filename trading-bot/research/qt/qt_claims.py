"""Quarterly Theory claims that can be tested on NQ alone (no ES/YM). MNQ 1-min 2020–2026.
Times in New York. Daily cycle: Asia 18:00–00:00, London 00:00–06:00, NY AM 06:00–12:00, NY PM 12:00–18:00.
True opens (playbook): daily = 00:00 (London open), session = Q2 of the 6h session, weekly = Monday 18:00 (Tue 01:00 IL)."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S
f = pd.read_pickle(S + "full1m.pkl")
T = f.index; m = (T.hour * 60 + T.minute).values
o, h, l, c = (f[k].values for k in ("open", "high", "low", "close"))
gday = pd.Index((T + pd.Timedelta(hours=6)).date)       # Globex day (18:00 → 17:00)
res = {}

def seg(day_idx, a, b):
    """minutes [a,b) NY clock of the calendar date (a<b, same date)."""
    return day_idx[(m[day_idx] >= a) & (m[day_idx] < b)]

cal = pd.Series(np.arange(len(f))).groupby(T.date)
rows = []
for d, ix in cal:
    ix = ix.values
    if pd.Timestamp(d).weekday() >= 5: continue
    q = {k: seg(ix, a, b) for k, (a, b) in {"q1": (360, 450), "q2": (450, 540), "q3": (540, 630), "q4": (630, 720)}.items()}
    if any(len(v) < 80 for v in q.values()): continue
    lon = seg(ix, 0, 360)
    r = dict(date=d)
    for k, v in q.items():
        r[k + "_o"], r[k + "_c"], r[k + "_h"], r[k + "_l"] = o[v[0]], c[v[-1]], h[v].max(), l[v].min()
    r["tdo"] = o[lon[0]] if len(lon) else np.nan                 # true daily open 00:00
    r["tso"] = o[q["q2"][0]]                                    # true session open 07:30
    rows.append(r)
x = pd.DataFrame(rows)
# --- 1. AMDX: Q2 (07:30–09:00) takes one side of Q1 (06:00–07:30); does Q3 (09:00–10:30) move the other way?
up_sweep = (x.q2_h > x.q1_h) & (x.q2_l >= x.q1_l); dn_sweep = (x.q2_l < x.q1_l) & (x.q2_h <= x.q1_h)
q3ret = x.q3_c - x.q3_o
res["AMDX: Q2 swept only Q1 high → Q3 closes down"] = f"{100*(q3ret[up_sweep] < 0).mean():.1f}% of {up_sweep.sum()} days"
res["AMDX: Q2 swept only Q1 low → Q3 closes up"] = f"{100*(q3ret[dn_sweep] > 0).mean():.1f}% of {dn_sweep.sum()} days"
res["  baseline: Q3 closes up (all days)"] = f"{100*(q3ret > 0).mean():.1f}%"
# --- 2. True open premium/discount: price at 09:30 vs TDO / TSO → direction of 09:30–12:00
p930 = np.array([o[seg(cal.get_group(d).values, 570, 571)[0]] for d in x.date])
fwd = x.q4_c - p930                                            # 09:30 → 12:00
for name, ref in (("true daily open 00:00", x.tdo), ("true session open 07:30", x.tso)):
    below = p930 < ref
    res[f"TrueOpen {name}: below (discount) → up by 12:00"] = f"{100*(fwd[below] > 0).mean():.1f}% (n {below.sum()}), avg {fwd[below].mean():+.1f} pt"
    res[f"TrueOpen {name}: above (premium) → down by 12:00"] = f"{100*(fwd[~below] < 0).mean():.1f}% (n {(~below).sum()}), avg {fwd[~below].mean():+.1f} pt"
# --- 3. Weekly cycle: which weekday prints the week's high / low
wk = f[["high", "low"]].copy(); wk["wd"] = pd.Index(gday).map(lambda d: pd.Timestamp(d).weekday()); wk["w"] = pd.Index(gday).map(lambda d: pd.Timestamp(d).to_period("W-SUN"))
hi_day = wk.groupby("w").apply(lambda g: g.wd.iloc[g.high.values.argmax()]); lo_day = wk.groupby("w").apply(lambda g: g.wd.iloc[g.low.values.argmin()])
names = "Mon Tue Wed Thu Fri".split()
res["Weekly high made on (%)"] = " ".join(f"{names[k]} {100*(hi_day==k).mean():.0f}" for k in range(5))
res["Weekly low made on (%)"] = " ".join(f"{names[k]} {100*(lo_day==k).mean():.0f}" for k in range(5))
# --- 4. Monthly cycle: is week 3 the biggest-range / trending week?
dd = f.resample("D").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
dd["wom"] = np.minimum((dd.index.day - 1) // 7 + 1, 4)
wr = dd.groupby([dd.index.to_period("M"), "wom"]).agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
wr["trend"] = (wr.c - wr.o).abs() / (wr.h - wr.l)
res["Monthly: avg |open→close| / range by week 1-4"] = " ".join(f"W{k} {wr.xs(k, level=1).trend.mean():.2f}" for k in (1, 2, 3, 4))
res["Monthly: avg range (pt) by week 1-4"] = " ".join(f"W{k} {(wr.xs(k, level=1).h - wr.xs(k, level=1).l).mean():.0f}" for k in (1, 2, 3, 4))
# --- 5. STS: 09:30 below weekly, daily and session true opens at once → long to 12:00
wto = {}
for wkey, g in f.groupby(pd.Index(gday).map(lambda d: pd.Timestamp(d).to_period("W-SUN"))):
    mon = g[(g.index.weekday == 0) & (g.index.hour == 18) & (g.index.minute == 0)]
    if len(mon): wto[wkey] = mon.open.iloc[0]
wtoa = np.array([wto.get(pd.Timestamp(d).to_period("W-SUN"), np.nan) for d in x.date])
sts_l = (p930 < x.tdo) & (p930 < x.tso) & (p930 < wtoa); sts_s = (p930 > x.tdo) & (p930 > x.tso) & (p930 > wtoa)
res["STS long (below all 3 opens) → up by 12:00"] = f"{100*(fwd[sts_l] > 0).mean():.1f}% (n {sts_l.sum()}), avg {fwd[sts_l].mean():+.1f} pt"
res["STS short (above all 3 opens) → down by 12:00"] = f"{100*(fwd[sts_s] < 0).mean():.1f}% (n {sts_s.sum()}), avg {fwd[sts_s].mean():+.1f} pt"
res["  baseline 09:30→12:00 up"] = f"{100*(fwd > 0).mean():.1f}%, avg {fwd.mean():+.1f} pt"
for k, v in res.items(): print(f"{k:52} {v}")
pd.Series(res).to_csv("qt_claims_results.csv")
