"""Placebo for the ON-zone filter: same IS zone-selection procedure, but zone labels shuffled across days (keeps zone sizes).
If shuffled labels also lift the portfolio, the 0.90 -> 1.25 is just 'skip some days' noise, not the ON range."""
import math, numpy as np, pandas as pd
from onrange import SP
MP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/mpool/"
sh = lambda x: x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0
el = pd.read_pickle(MP + "../mcombo.pkl")["el"]; SY = ["NSXUSD","SPXUSD","DEUIDXEUR","XAUUSD","USDJPY","JPNIDXJPY","EURUSD","LIGHTCMDUSD"]
data = []
for sym in SY:
    A = pd.read_pickle(SP + sym + "_A.pkl"); A = A[np.isfinite(A.pos)]; A = A[~A.index.duplicated()]
    z = pd.cut(A.pos, [-np.inf, .25, .5, .75, np.inf], labels=[0, 1, 2, 3]).astype(int)
    P = pd.read_pickle(MP + sym + ".pkl")["P"]; P = P[~P.index.duplicated()]
    zz = z.reindex(P.index).fillna(-1).astype(int).values
    ks = [k.split("|", 1)[1] for k in el if k.startswith(sym + "|")]
    X = P[ks].values; S = np.asarray(P.index.year <= 2019); sd = np.array([X[S, j][X[S, j] != 0].std() for j in range(len(ks))])
    data.append((sym, P.index, X / sd, zz, S))
idx = sorted(set().union(*[set(d[1]) for d in data])); idx = pd.DatetimeIndex(idx); O = idx.year >= 2020
def port(shuffle, rng, only=None):
    tot = pd.Series(0.0, index=idx)
    for sym, ix, X, zz, S in data:
        if only and sym not in only: continue
        z = rng.permutation(zz) if shuffle else zz; F = np.zeros_like(X)
        for q in range(4):
            m = z == q; keep = X[S & m].mean(0) > 0; F[m] = X[m] * keep
        tot = tot.add(pd.Series(F.sum(1), index=ix), fill_value=0)
    return tot
rng = np.random.default_rng(1)
for only in ():
    real = sh(port(False, rng, only)[O]); pl = [sh(port(True, rng, only)[O]) for _ in range(200)]
    print(f"{only or 'all 8'}: real filtered OOS {real:.2f} | shuffled-zone placebo median {np.median(pl):.2f}, 95th {np.percentile(pl,95):.2f} -> beats {100*np.mean(np.array(pl)<real):.0f}%")
print("per market:")
for s in SY:
    u = sh(port(False, rng, [s])[O]) ; pl = [sh(port(True, rng, [s])[O]) for _ in range(200)]
    raw = pd.Series(0.0, index=idx)
    for sym, ix, X, zz, S in data:
        if sym == s: raw = raw.add(pd.Series(X.sum(1), index=ix), fill_value=0)
    print(f"  {s:12s} unfiltered {sh(raw[O]):5.2f} | filtered {u:5.2f} | placebo median {np.median(pl):5.2f} 95th {np.percentile(pl,95):5.2f} -> beats {100*np.mean(np.array(pl)<u):.0f}%")
