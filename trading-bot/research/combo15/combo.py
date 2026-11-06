"""Stage 2-4 - build a portfolio of up to 15 strategies the honest way.
SELECT (2012-2019 only): a strategy is eligible if it has >= 80 trading days, t >= 1.0 and >= 5 of 8 years positive.
  Each eligible strategy is risk-normalised (equal daily stdev on its trading days); then greedy forward selection adds the one that
  most raises the portfolio's daily Sharpe, up to 15 (stops early if nothing improves it).
VALIDATE (2020-2022) and FINAL (2023-2026-10, looked at once): Sharpe, $ per year, max drawdown, years positive.
Selection-luck check: the same numbers for 2,000 random 15-strategy portfolios drawn from the eligible pool and for
'all eligible, equal risk'. The greedy portfolio is only worth anything if it beats the random ones out of sample."""
import sys, os, math
import numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/combo15/"
P = pd.read_pickle(SP + "pool.pkl"); Y = P.index.year
S, V, F = (Y <= 2019), (Y >= 2020) & (Y <= 2022), (Y >= 2023)
RNG = np.random.default_rng(15)


def sharpe(x): return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0.0


def stats(x, m):
    z = x[m]; cs = z.cumsum(); yrs = z.groupby(z.index.year).sum(); td = z[z != 0]
    return dict(sharpe=sharpe(z), usd_yr=2 * z.sum() / len(yrs), maxdd_usd=2 * (cs - cs.cummax()).min(), yrs_pos=f"{(yrs > 0).sum()}/{len(yrs)}",
                win_days=100 * (td > 0).mean(), rr=(td[td > 0].mean() / -td[td < 0].mean()), days_yr=len(td) / len(yrs))


if __name__ == "__main__":
    el = []
    for c in P.columns:
        x = P[c][S]; td = x[x != 0]
        if len(td) < 80: continue
        t = td.mean() / td.std() * math.sqrt(len(td)); pos = (x.groupby(x.index.year).sum() > 0).sum()
        if t >= 1.0 and pos >= 5: el.append(c)
    print(f"pool {P.shape[1]} strategies -> eligible on 2012-19: {len(el)}")
    sd = {c: P[c][S][P[c][S] != 0].std() for c in el}; ref = np.median(list(sd.values()))
    W = pd.DataFrame({c: P[c] * ref / sd[c] for c in el})               # equal risk per trading day, in 'reference contract' points
    chosen = []; best = -9
    while len(chosen) < 15:
        cand = [(sharpe(W[chosen + [c]][S].sum(1)), c) for c in el if c not in chosen]
        if not cand: break
        s, c = max(cand)
        if s <= best + 1e-6: break
        best = s; chosen.append(c)
    port = W[chosen].sum(1); allw = W[el].sum(1) * 15 / len(el)
    rho = W[chosen][S].replace(0, np.nan).corr().values; avg_rho = np.nanmean(rho[np.triu_indices(len(chosen), 1)])
    print(f"\ngreedy portfolio ({len(chosen)} strategies, avg pairwise corr on shared days {avg_rho:.2f}):")
    for c in chosen: print("  ", c[:110])
    R = []
    for nm, x in (("greedy", port), ("all-eligible", allw)):
        for pn, m in (("select 2012-19", S), ("validate 2020-22", V), ("FINAL 2023-26", F)): R.append(dict(portfolio=nm, period=pn, **stats(x, m)))
    rv, rf = [], []
    for _ in range(2000):
        k = list(RNG.choice(el, size=min(15, len(el)), replace=False)); x = W[k].sum(1); rv.append(sharpe(x[V])); rf.append(sharpe(x[F]))
    print(pd.DataFrame(R).round(2).to_string(index=False))
    print(f"\nrandom 15-of-eligible portfolios: validate Sharpe median {np.median(rv):.2f}, greedy beats {100*np.mean(np.array(rv) < sharpe(port[V])):.0f}% | "
          f"final Sharpe median {np.median(rf):.2f}, greedy beats {100*np.mean(np.array(rf) < sharpe(port[F])):.0f}%")
    pd.Series(chosen).to_csv(SP + "chosen.csv", index=False); port.to_pickle(SP + "port.pkl")
    yy = port.groupby(Y).sum() * 2; print("\n$ per year (reference units, 1 unit ~ 1 MNQ per strategy):", yy.round(0).to_dict())
