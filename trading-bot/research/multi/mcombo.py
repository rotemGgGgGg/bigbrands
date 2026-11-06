"""Multi-market portfolio, same honest rule as combo15/combo3 (no picking):
eligible = strategy x market with >= 80 trading days and alpha t >= 1.0 (alpha = P&L minus beta x that market's buy & hold, beta
on 2012-19) and >= 5 of its 2012-19 years with positive alpha (market must have data from 2014 or earlier);
portfolio = ALL eligible, equal risk (same daily stdev on trading days), beta-hedged per market. Out-of-sample = 2020-2026-10.
Placebo: the same number of strategy x market series drawn at random from the whole pool (300 draws).
Reported in % of account at 10% annual volatility; prop simulation on a $50K account."""
import sys, os, glob, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../combo15"))
import numpy as np, pandas as pd
MP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/mpool/"
RNG = np.random.default_rng(20)
def sh(x): return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0.0

if __name__ == "__main__":
    cols, hedged_cols, meta = {}, {}, []
    for f in sorted(glob.glob(MP + "*.pkl")):
        sym = os.path.basename(f)[:-4]; z = pd.read_pickle(f); P, bh = z["P"], z["bh"]; Y = P.index.year; S = Y <= 2019
        if P.index[0].year > 2014: print("skip (starts", P.index[0].date(), ")", sym); continue
        for c in P.columns:
            x = P[c]; on = x[S] != 0
            if on.sum() < 80: continue
            b = np.cov(x[S], bh[S])[0, 1] / bh[S].var(); a = x - b * bh; sd = x[S][on].std()
            if not sd > 0: continue
            k = f"{sym}|{c}"; cols[k] = x / sd; hedged_cols[k] = a / sd
            yy = a[S].groupby(Y[S]).sum(); t = a[S].mean() / a[S].std() * math.sqrt(S.sum()); pos = (yy > 0).mean() * 8
            meta.append((k, sym, t, pos >= 5 and t >= 1.0))
    A = pd.DataFrame(hedged_cols).sort_index().fillna(0); M = pd.DataFrame(meta, columns=["k", "sym", "t", "ok"]).set_index("k")
    el = list(M.index[M.ok]); Yi = A.index.year; S, O = Yi <= 2019, Yi >= 2020
    print(f"series: {len(M)} strategy x market over {M.sym.nunique()} markets; eligible {len(el)}")
    print(M[M.ok].groupby("sym").size().to_string())
    port = A[el].sum(1); scale = .10 / (port[S].std() * math.sqrt(252)); port = port * scale       # 10 % annual vol on 2012-19
    o = port[O]; t = o.mean() / o.std() * math.sqrt(len(o))
    print(f"\nALL-ELIGIBLE hedged: 2012-19 Sharpe {sh(port[S]):.2f} | 2020-22 {sh(port[(Yi>=2020)&(Yi<=2022)]):.2f} | 2023-26 {sh(port[Yi>=2023]):.2f} | OOS t {t:.2f}")
    print("per-year % (10% vol target):", (100 * port.groupby(Yi).sum()).round(1).to_dict())
    cs = port[O].cumsum(); print(f"OOS max drawdown {100*(cs-cs.cummax()).min():.1f}%, winning days {100*(o[o!=0]>0).mean():.0f}%, "
                                 f"avg win/loss {o[o>0].mean()/-o[o<0].mean():.2f}")
    pl = []
    for _ in range(300):
        k = list(RNG.choice(A.columns, size=len(el), replace=False)); x = A[k].sum(1); pl.append(sh(x[O]))
    print(f"placebo: OOS Sharpe median {np.median(pl):.2f}, 95th {np.percentile(pl,95):.2f} -> ours beats {100*np.mean(np.array(pl)<sh(o)):.0f}%")
    nq = [k for k in el if k.startswith("USATECH")]
    if nq: x = A[nq].sum(1); print(f"NQ-only part ({len(nq)}): OOS Sharpe {sh(x[O]):.2f}; non-NQ part ({len(el)-len(nq)}): OOS Sharpe {sh(A[[k for k in el if k not in nq]].sum(1)[O]):.2f}")
    import combo3 as K
    days = np.nonzero(O)[0]; starts = days[:-60:5]
    for vol in (.05, .10, .20):
        pnl = (port * vol / .10 * 50000).values; T = K.prop(pnl, starts); pv = T[T.r == "payout"]
        print(f"prop 50K at {int(vol*100)}% annual vol: payout {100*len(pv)/len(T):.0f}%, fail {100*(T.r=='fail').mean():.0f}%, "
              f"median days to pass {pv.d_pass.median()}, to payout {pv.d_payout.median()}")
    pd.to_pickle(dict(el=el, port=port, M=M), MP + "../mcombo.pkl")
