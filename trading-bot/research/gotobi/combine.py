"""Gotobi sleeve added to the existing portfolio (OLD = all-eligible multi-market, LB = USDJPY London breakout). Equal risk on 2012-19."""
import os as _os; DATA = _os.path.join(_os.path.expanduser(_os.environ.get("EDGE_DATA", "~/edge-data")), "")  # raw data + caches (set EDGE_DATA to move it)
import sys, math, pickle, numpy as np, pandas as pd
sys.path.insert(0, "../vidstrats"); sys.path.insert(0, "../combo15")
from vs import summarize, SP as VSP
import combo3 as K
SP = DATA
sh = lambda x: x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0
res = pickle.load(open(VSP + "LB_res.pkl", "rb")); T = summarize("LB", res, ""); el = T[(T.IS_t >= 1) & (T.IS_pos_yrs >= 5)].params.tolist()
D = pd.DataFrame({"OLD": pd.read_pickle(SP + "mcombo.pkl")["port"], "LB": pd.DataFrame({k: res[eval(k)] for k in el}).fillna(0).mean(1),
                  "GOTOBI": pd.read_pickle(SP + "gotobi_series.pkl")}).sort_index().fillna(0)
D = D[D.index.year >= 2012]; Y = D.index.year; S, O = Y <= 2019, Y >= 2020; D = D / D[S].std()
print("OOS corr:\n", D[O].corr().round(2))
for c in (["OLD"], ["GOTOBI"], ["OLD", "LB"], ["OLD", "GOTOBI"], ["OLD", "LB", "GOTOBI"]):
    p = D[c].sum(1); p = p / (p[S].std() * math.sqrt(252)) * .10; o = p[O]; cs = o.cumsum()
    print(f"{'+'.join(c):18s} IS {sh(p[S]):.2f} | OOS {sh(o):.2f} t {o.mean()/o.std()*math.sqrt(len(o)):.2f} | 2023-26 {sh(p[Y>=2023]):.2f} | "
          f"{100*o.mean()*252:.1f}%/yr | maxDD {100*(cs-cs.cummax()).min():.1f}% | pos yrs {(o.groupby(o.index.year).sum()>0).sum()}/7")
    if len(c) == 3:
        for vol in (.05, .08):
            r = K.prop((p * vol / .10 * 50000).values, np.nonzero(O)[0][:-60:5]); pv = r[r.r == "payout"]
            print(f"   prop 50K @{int(vol*100)}% vol: payout {100*len(pv)/len(r):.0f}% fail {100*(r.r=='fail').mean():.0f}% days to payout {pv.d_payout.median()}")
