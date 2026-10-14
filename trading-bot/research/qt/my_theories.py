"""My own theories built from the QT material, stated as testable rules. NQ 1-min 2020–2026, NY time.
Each trade: 1 contract, cost 1.25 pt. IS 2020–23, OOS 2024–26."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S, COST_PTS, IS_END
f = pd.read_pickle(S + "full1m.pkl"); T = f.index; m = (T.hour * 60 + T.minute).values
o, h, l, c = (f[k].values for k in ("open", "high", "low", "close"))
cal = {d: ix.values for d, ix in pd.Series(np.arange(len(f))).groupby(T.date)}
dates = sorted(d for d in cal if pd.Timestamp(d).weekday() < 5)
def w(d, a, b):
    ix = cal[d]; return ix[(m[ix] >= a) & (m[ix] < b)]
def px_at(d, mm, kind="o"):
    k = w(d, mm, mm + 1)
    return (o if kind == "o" else c)[k[0]] if len(k) else np.nan
R = []
def add(theory, d, side, entry, exitp):
    if side and not np.isnan(entry) and not np.isnan(exitp):
        R.append(dict(theory=theory, date=d, pts=(exitp - entry) * side - COST_PTS))
prev = None
for d in dates:
    ny = w(d, 360, 720); lon = w(d, 0, 360)
    if len(ny) < 300 or len(lon) < 300: prev = d; continue
    q = {k: w(d, a, a + 90) for k, a in (("Q1", 360), ("Q2", 450), ("Q3", 540), ("Q4", 630))}
    p1030, p1200, p0900, p1600 = px_at(d, 630), px_at(d, 719, "c"), px_at(d, 540), px_at(d, 959, "c")
    # T1: Q3 breaks the Q1+Q2 (06:00–09:00) range on a 5-min close → follow to 12:00 / fade to 12:00
    hi12, lo12 = h[np.r_[q["Q1"], q["Q2"]]].max(), l[np.r_[q["Q1"], q["Q2"]]].min()
    q3 = q["Q3"]
    for k in range(4, len(q3), 5):
        cc = c[q3[k]]
        if cc > hi12 or cc < lo12:
            s = 1 if cc > hi12 else -1
            add("T1 Q3 breaks Q1–Q2 range → follow to 12:00", d, s, cc, p1200)
            add("T1b … → fade to 12:00", d, -s, cc, p1200); break
    # T2: Q2 sweeps a Q1 extreme and closes back inside (manipulation) → Q3/Q4 the other way
    q1h, q1l = h[q["Q1"]].max(), l[q["Q1"]].min(); q2c = c[q["Q2"][-1]]
    if h[q["Q2"]].max() > q1h and l[q["Q2"]].min() >= q1l and q2c < q1h:
        add("T2 Q2 fake-out of Q1 high → short 09:00→12:00", d, -1, p0900, p1200)
    if l[q["Q2"]].min() < q1l and h[q["Q2"]].max() <= q1h and q2c > q1l:
        add("T2 Q2 fake-out of Q1 low → long 09:00→12:00", d, 1, p0900, p1200)
    # T7: London vs Asia (prev 18:00–00:00) → NY AM 09:30→12:00
    if prev is not None:
        ix = cal[prev]; asia = ix[m[ix] >= 1080]
        if len(asia) > 200:
            ah, al = h[asia].max(), l[asia].min(); lc = c[lon[-1]]; lh, ll = h[lon].max(), l[lon].min()
            p930 = px_at(d, 570)
            if lh > ah and ll >= al:
                add("T7 London took Asia high, closed back in → short NY AM", d, -1, p930, p1200) if lc < ah else add("T7 London took Asia high & held → long NY AM", d, 1, p930, p1200)
            if ll < al and lh <= ah:
                add("T7 London took Asia low, closed back in → long NY AM", d, 1, p930, p1200) if lc > al else add("T7 London took Asia low & held → short NY AM", d, -1, p930, p1200)
    # T3: alignment at 10:30 (end of Q3): price vs true daily open (00:00), true session open (07:30), Q3 open (09:00)
    tdo, tso = o[lon[0]], o[q["Q2"][0]]
    sgn = [np.sign(p1030 - tdo), np.sign(p1030 - tso), np.sign(p1030 - p0900)]
    if abs(sum(sgn)) == 3:
        add("T3 all-aligned at 10:30 → continue to 12:00", d, int(sgn[0]), p1030, p1200)
        add("T3 all-aligned at 10:30 → continue to 16:00", d, int(sgn[0]), p1030, p1600)
    # T4: draw on liquidity — prev-day high/low reached by 10:30 → Q4 reversal, else continuation
    if prev is not None:
        pix = cal[prev]; prth = pix[(m[pix] >= 570) & (m[pix] < 960)]
        if len(prth) > 300:
            pdh, pdl = h[prth].max(), l[prth].min(); upto = np.r_[w(d, 0, 630)]
            took_h, took_l = h[upto].max() > pdh, l[upto].min() < pdl
            if took_h and not took_l: add("T4 PDH taken by 10:30 → short Q4 (reversal)", d, -1, p1030, p1200)
            if took_l and not took_h: add("T4 PDL taken by 10:30 → long Q4 (reversal)", d, 1, p1030, p1200)
            if not took_h and not took_l and sgn[0] != 0: add("T4 no draw yet → continue vs TDO to 12:00", d, int(sgn[0]), p1030, p1200)
    prev = d
# T5 weekly: Wednesday breaks the Mon–Tue range (by Wed 16:00 close) → hold to Thu 16:00
day = pd.DataFrame([dict(date=d, h=h[w(d, 570, 960)].max() if len(w(d, 570, 960)) else np.nan, l=l[w(d, 570, 960)].min() if len(w(d, 570, 960)) else np.nan,
                         c=px_at(d, 959, "c")) for d in dates]).dropna()
day["wd"] = pd.to_datetime(day.date).dt.weekday; day["wk"] = pd.to_datetime(day.date).dt.to_period("W")
for wk, g in day.groupby("wk"):
    g = g.set_index("wd")
    if not {0, 1, 2, 3}.issubset(g.index): continue
    mh, ml = max(g.loc[0, "h"], g.loc[1, "h"]), min(g.loc[0, "l"], g.loc[1, "l"])
    wc = g.loc[2, "c"]
    if wc > mh: add("T5 Wed closes above Mon–Tue high → long to Thu close", g.loc[2, "date"], 1, wc, g.loc[3, "c"])
    if wc < ml: add("T5 Wed closes below Mon–Tue low → short to Thu close", g.loc[2, "date"], -1, wc, g.loc[3, "c"])
    if g.loc[2, "h"] > mh and wc < mh: add("T5 Wed fake-out above Mon–Tue → short to Thu", g.loc[2, "date"], -1, wc, g.loc[3, "c"])
    if g.loc[2, "l"] < ml and wc > ml: add("T5 Wed fake-out below Mon–Tue → long to Thu", g.loc[2, "date"], 1, wc, g.loc[3, "c"])
r = pd.DataFrame(R); r["y"] = pd.to_datetime(r.date)
out = []
for t, g in r.groupby("theory"):
    p = g.pts; isd = g.y < IS_END
    out.append(dict(theory=t, n=len(g), win=round(100 * (p > 0).mean(), 1), avg_usd=round(2 * p.mean(), 1),
                    IS=round(2 * p[isd].mean(), 1), OOS=round(2 * p[~isd].mean(), 1), yrs=f"{int((p.groupby(g.y.dt.year).sum() > 0).sum())}/7"))
out = pd.DataFrame(out).sort_values("avg_usd", ascending=False); out.to_csv("my_theories_round1.csv", index=False)
print(out.to_string(index=False))
