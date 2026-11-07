"""Combine the video strategies with our existing portfolio. No picking: each strategy = average of ALL its IS-eligible variants
(IS t>=1, >=5/8 positive years on 2012-19). Every sleeve scaled to the same daily vol on 2012-19. OOS = 2020-26.
Sleeves: LB (USDJPY London breakout), GF (gold), NM (NQ opening momentum), OLD (our 145-series all-eligible multi-market portfolio).
All 15 combinations reported; prop sim for the best few."""
import sys, os, math, pickle, itertools, numpy as np, pandas as pd
sys.path.insert(0, "../combo15"); from vs import summarize, SP
sh = lambda x: x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0
sl = {}
for w in ("LB", "GF", "NM"):
    res = pickle.load(open(SP + w + "_res.pkl", "rb")); T = summarize(w, res, "")
    el = T[(T.IS_t >= 1.0) & (T.IS_pos_yrs >= 5)].params.tolist(); print(w, "eligible variants:", len(el))
    sl[w] = pd.DataFrame({k: res[eval(k)] for k in el}).fillna(0).mean(1)
sl["OLD"] = pd.read_pickle(SP + "../mcombo.pkl")["port"]
D = pd.DataFrame(sl).sort_index().fillna(0); D = D[D.index.year >= 2012]; Y = D.index.year; S, O = Y <= 2019, Y >= 2020
D = D / D[S].std()                                                                     # equal daily risk on 2012-19
print("\nOOS correlations:\n", D[O].corr().round(2).to_string())
rows = []
for r in range(1, 5):
    for c in itertools.combinations(D.columns, r):
        p = D[list(c)].sum(1); p = p / (p[S].std() * math.sqrt(252)) * .10
        o = p[O]; t = o.mean() / o.std() * math.sqrt(len(o)); cs = o.cumsum()
        rows.append(dict(combo="+".join(c), IS=sh(p[S]), OOS=sh(o), t=t, y2023_26=sh(p[Y >= 2023]), pct_yr=100 * o.mean() * 252,
                         maxDD=100 * (cs - cs.cummax()).min(), win_days=100 * (o[o != 0] > 0).mean(), pos_years=int((o.groupby(o.index.year).sum() > 0).sum())))
R = pd.DataFrame(rows).sort_values("OOS", ascending=False); pd.set_option("display.width", 200)
print("\n(at 10% annual vol)\n", R.round(2).to_string(index=False)); R.to_csv(SP + "combos.csv", index=False)
import combo3 as K
for name in R.combo.head(3):
    p = D[name.split("+")].sum(1); p = p / (p[S].std() * math.sqrt(252)) * .10; days = np.nonzero(O)[0]; st = days[:-60:5]
    for vol in (.05, .10):
        T = K.prop((p * vol / .10 * 50000).values, st); pv = T[T.r == "payout"]
        print(f"prop 50K {name} @ {int(vol*100)}% vol: payout {100*len(pv)/len(T):.0f}% fail {100*(T.r=='fail').mean():.0f}% "
              f"days to pass {pv.d_pass.median()} to payout {pv.d_payout.median()}")
