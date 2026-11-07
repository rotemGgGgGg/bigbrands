"""ON-range zone as a FILTER on the existing eligible strategies (mcombo eligible list), per market.
For each strategy: on 2012-19 pick which zones to keep (zone kept if its 2012-19 mean P&L > 0), then compare OOS 2020-26
filtered vs unfiltered, single strategies and the whole all-eligible portfolio."""
import sys, math, numpy as np, pandas as pd
from onrange import analyse, SP
MP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/mpool/"
def sh(x): return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0
el = pd.read_pickle(MP + "../mcombo.pkl")["el"]
allU, allF, allZ = [], [], []
for sym in sys.argv[1:]:
    try: A = pd.read_pickle(SP + sym + "_A.pkl")
    except FileNotFoundError: A, _ = analyse(sym); A.to_pickle(SP + sym + "_A.pkl")
    A = A[np.isfinite(A.pos)]; z = pd.cut(A.pos, [-np.inf, .25, .5, .75, np.inf], labels=[0, 1, 2, 3]).astype(int)
    P = pd.read_pickle(MP + sym + ".pkl")["P"]; zz = z.reindex(P.index)
    ks = [k.split("|", 1)[1] for k in el if k.startswith(sym + "|")]; better = 0; rows = []
    for c in ks:
        x = P[c]; S = x.index.year <= 2019; O = ~S
        keep = [q for q in range(4) if x[S & (zz == q)].mean() > 0]
        f = x.where(zz.isin(keep), 0.0)
        sd = x[S][x[S] != 0].std(); u, fl = x / sd, f / sd
        allU.append(u.rename(f"{sym}|{c}")); allF.append(fl.rename(f"{sym}|{c}"))
        rows.append((c[:40], keep, sh(x[O]), sh(f[O]))); better += sh(f[O]) > sh(x[O])
    print(f"{sym}: {len(ks)} eligible strategies; zone filter improved OOS Sharpe in {better}/{len(ks)}")
from functools import reduce
add = lambda L: reduce(lambda a, b: a.add(b.groupby(level=0).sum(), fill_value=0), L[1:], L[0].groupby(level=0).sum())
U = add(allU); F = add(allF); O = U.index.year >= 2020
print(f"\nportfolio of these: unfiltered OOS Sharpe {sh(U[O]):.2f} | ON-zone filtered {sh(F[O]):.2f}")
