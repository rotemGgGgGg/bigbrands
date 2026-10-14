"""STS (price at 09:30 below/above weekly+daily+session true opens) as a trade, 7 years, costs, IS/OOS, variants."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S, COST_PTS, IS_END
f = pd.read_pickle(S + "full1m.pkl"); T = f.index; m = (T.hour * 60 + T.minute).values
o, h, l, c = (f[k].values for k in ("open", "high", "low", "close"))
gwk = pd.Index((T + pd.Timedelta(hours=6)).date).map(lambda d: pd.Timestamp(d).to_period("W-SUN"))
wto = f[(T.weekday == 0) & (T.hour == 18) & (T.minute == 0)].open; wto.index = wto.index.map(lambda t: (t + pd.Timedelta(hours=6)).to_period("W-SUN"))
cal = pd.Series(np.arange(len(f))).groupby(T.date)
rows = []
for d, ix in cal:
    ix = ix.values
    if pd.Timestamp(d).weekday() >= 5: continue
    def at(mm):
        k = ix[m[ix] == mm]; return k[0] if len(k) else None
    i0, i930, i1200, i1600, i1030 = at(0), at(570), at(719), at(959), at(629)
    i730 = at(450)
    if None in (i0, i930, i1200, i730, i1030): continue
    w = wto.get(pd.Timestamp(d).to_period("W-SUN"), np.nan) if pd.Timestamp(d).weekday() != 0 else np.nan   # Monday 09:30 is before Monday 18:00 — no look-ahead
    p = o[i930]
    rows.append(dict(date=d, p=p, tdo=o[i0], tso=o[i730], two=w, c1030=c[i1030], c1200=c[i1200], c1600=c[i1600] if i1600 else np.nan,
                     lo=l[i930:i1200 + 1].min(), hi=h[i930:i1200 + 1].max()))
x = pd.DataFrame(rows); y = pd.to_datetime(x.date)
def rep(name, side, exitcol, mask):
    pts = (x[exitcol] - x.p) * side - COST_PTS
    p = pts[mask]; yy = y[mask]
    print(f"{name:44} n {mask.sum():4} win {100*(p>0).mean():5.1f}% avg ${2*p.mean():+6.1f}/MNQ  IS ${2*p[yy<IS_END].mean():+6.1f} OOS ${2*p[yy>=IS_END].mean():+6.1f}  yrs+ {(p.groupby(yy.dt.year).sum()>0).sum()}/7")
below3 = (x.p < x.tdo) & (x.p < x.tso) & (x.p < x.two); above3 = (x.p > x.tdo) & (x.p > x.tso) & (x.p > x.two)
for ex in ("c1030", "c1200", "c1600"):
    rep(f"STS long → exit {ex[1:]}", 1, ex, below3)
    rep(f"STS short → exit {ex[1:]}", -1, ex, above3)
rep("baseline: always long 09:30→12:00", 1, "c1200", pd.Series(True, index=x.index))
below2 = (x.p < x.tdo) & (x.p < x.tso); above2 = (x.p > x.tdo) & (x.p > x.tso)
rep("daily+session only, long → 12:00", 1, "c1200", below2)
rep("daily+session only, short → 12:00", -1, "c1200", above2)
# overnight move control: is STS just 'fade the overnight move'?
ov = x.p - x.tdo
rep("control: overnight down >0.3% → long 12:00", 1, "c1200", ov < -0.003 * x.p)
rep("control: overnight up >0.3% → short 12:00", -1, "c1200", ov > 0.003 * x.p)
print("--- robustness")
rep("weekly open only, long → 12:00", 1, "c1200", x.p < x.two)
rep("weekly open only, short → 12:00", -1, "c1200", x.p > x.two)
dist = (x.p - x.two) / x.p
for k in (0.0, 0.005, 0.01):
    rep(f"STS long & >{k*100:.1f}% below weekly open", 1, "c1200", below3 & (dist < -k))
    rep(f"STS short & >{k*100:.1f}% above weekly open", -1, "c1200", above3 & (dist > k))
x["wd"] = pd.to_datetime(x.date).dt.weekday
for wd, nm in enumerate("Mon Tue Wed Thu Fri".split()):
    pts = pd.concat([((x.c1200 - x.p) - COST_PTS)[below3 & (x.wd == wd)], ((x.p - x.c1200) - COST_PTS)[above3 & (x.wd == wd)]])
    print(f"STS both sides on {nm}: n {len(pts)} avg ${2*pts.mean():+.1f}")
