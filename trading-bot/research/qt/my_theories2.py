"""Round 2: 'liquidity sweep → reversal' at daily/weekly scale, with/without a trend filter (HTF bias).
RTH daily bars from NQ 1-min. Entry at the sweep day's 16:00 close, exits next close / 2 closes. Cost 1.25 pt."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S, COST_PTS, IS_END
f = pd.read_pickle(S + "full1m.pkl"); m = f.index.hour * 60 + f.index.minute
r = f[(m >= 570) & (m < 960)]
d = r.groupby(r.index.date).agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
d.index = pd.to_datetime(d.index); d = d[d.index.weekday < 5]
d["sma50"] = d.c.rolling(50).mean(); d["up"] = d.c > d.sma50
d["wk"] = d.index.to_period("W")
d["wk_lo_prior"] = d.groupby("wk").l.transform(lambda s: s.shift().cummin())
d["wk_hi_prior"] = d.groupby("wk").h.transform(lambda s: s.shift().cummax())
d["pdl"], d["pdh"] = d.l.shift(), d.h.shift()
d["c1"], d["c2"], d["c5"] = d.c.shift(-1), d.c.shift(-2), d.c.shift(-5)
rows = []
def ev(name, mask, side):
    for ex in ("c1", "c2", "c5"):
        p = ((d[ex] - d.c) * side - COST_PTS)[mask].dropna()
        y = p.index
        rows.append(dict(rule=name, exit=ex, n=len(p), win=round(100 * (p > 0).mean(), 1), avg_usd=round(2 * p.mean(), 1),
                         IS=round(2 * p[y < IS_END].mean(), 1), OOS=round(2 * p[y >= IS_END].mean(), 1),
                         yrs=f"{int((p.groupby(y.year).sum() > 0).sum())}/{y.year.nunique()}"))
bull_pdl = (d.l < d.pdl) & (d.c > d.pdl); bear_pdh = (d.h > d.pdh) & (d.c < d.pdh)
bull_wk = (d.l < d.wk_lo_prior) & (d.c > d.wk_lo_prior); bear_wk = (d.h > d.wk_hi_prior) & (d.c < d.wk_hi_prior)
for nm, bm, sm in (("PDL/PDH sweep & close back", bull_pdl, bear_pdh), ("week-so-far low/high sweep & close back", bull_wk, bear_wk)):
    ev(f"{nm} → long", bm, 1); ev(f"{nm} → short", sm, -1)
    ev(f"{nm} → long, uptrend only", bm & d.up, 1); ev(f"{nm} → short, downtrend only", sm & ~d.up, -1)
    ev(f"{nm} → long, downtrend only", bm & ~d.up, 1); ev(f"{nm} → short, uptrend only", sm & d.up, -1)
# controls: unconditional long, and real breaks (close beyond)
ev("control: every day long", pd.Series(True, index=d.index), 1)
ev("control: close below PDL (real break) → long", d.c < d.pdl, 1)
ev("control: close above PDH (real break) → short", d.c > d.pdh, -1)
out = pd.DataFrame(rows); out.to_csv("my_theories_round2.csv", index=False)
print(out[out.exit != "c5"].to_string(index=False))
