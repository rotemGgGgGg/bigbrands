"""Round 2 - select on ALPHA, not on profit (round 1 showed the portfolio was ~1 contract long NQ and greedy picking was luck).
Each strategy's daily P&L is split into beta x (NQ 1-contract daily P&L) + alpha, beta estimated on 2012-2019 only.
Eligible: alpha t >= 1.0 and >= 5/8 years of positive alpha on 2012-19, >= 80 trading days.
Portfolio (one pre-set rule, no search): rank eligible by alpha t, walk down the list and keep a strategy if its daily P&L correlation
with every one already kept is < 0.3, stop at 15. Equal risk per strategy. Reported raw and beta-hedged (short NQ for the beta).
Compared with 2,000 random 15-strategy portfolios from the same eligible list (selection-luck check)."""
import sys, os, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../papers"))
import numpy as np, pandas as pd
import pdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/combo15/"
P = pd.read_pickle(SP + "pool.pkl"); Y = P.index.year; D = pdata.load()
BH = pd.Series(D["dc"], index=P.index).diff().fillna(0)
S, V, F = (Y <= 2019), (Y >= 2020) & (Y <= 2022), (Y >= 2023); RNG = np.random.default_rng(152)
def sh(x): return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0.0


def stats(x, m):
    z = x[m]; cs = z.cumsum(); yrs = z.groupby(z.index.year).sum(); td = z[z != 0]
    return dict(sharpe=round(sh(z), 2), usd_yr=round(2 * z.sum() / len(yrs)), maxdd_usd=round(2 * (cs - cs.cummax()).min()),
                yrs_pos=f"{(yrs > 0).sum()}/{len(yrs)}", win_days=round(100 * (td > 0).mean(), 1), rr=round(td[td > 0].mean() / -td[td < 0].mean(), 2))


if __name__ == "__main__":
    beta = {c: np.cov(P[c][S], BH[S])[0, 1] / BH[S].var() for c in P.columns}
    A = pd.DataFrame({c: P[c] - beta[c] * BH for c in P.columns}); rows = []
    for c in P.columns:
        x = P[c][S]; on = x != 0
        if on.sum() < 80: continue
        a = A[c][S]; t = a.mean() / a.std() * math.sqrt(len(a)); pos = (a.groupby(a.index.year).sum() > 0).sum()
        if t >= 1.0 and pos >= 5: rows.append((t, c))
    rows.sort(reverse=True); el = [c for _, c in rows]; print(f"eligible on alpha (2012-19): {len(el)} of {P.shape[1]}")
    sd = {c: P[c][S][P[c][S] != 0].std() for c in el}; ref = np.median(list(sd.values()))
    W = pd.DataFrame({c: P[c] * ref / sd[c] for c in el}); kept = []
    for c in el:
        if all(abs(W[c][S].corr(W[k][S])) < .3 for k in kept): kept.append(c)
        if len(kept) == 15: break
    port = W[kept].sum(1); b = np.cov(port[S], BH[S])[0, 1] / BH[S].var(); hedged = port - b * BH
    print(f"portfolio: {len(kept)} strategies, beta {b:.2f}")
    for t, c in rows:
        if c in kept: print(f"   alpha t {t:4.2f}  {c[:105]}")
    R = []
    for nm, x in (("raw", port), ("beta-hedged", hedged), ("NQ buy&hold x beta", b * BH)):
        for pn, m in (("select 2012-19", S), ("validate 2020-22", V), ("FINAL 2023-26", F)): R.append(dict(series=nm, period=pn, **stats(x, m)))
    print(pd.DataFrame(R).to_string(index=False))
    rv, rf = [], []
    for _ in range(2000):
        k = list(RNG.choice(el, size=min(15, len(el)), replace=False)); x = W[k].sum(1); bb = np.cov(x[S], BH[S])[0, 1] / BH[S].var(); x = x - bb * BH
        rv.append(sh(x[V])); rf.append(sh(x[F]))
    print(f"random hedged 15-portfolios: validate median {np.median(rv):.2f} (ours beats {100*np.mean(np.array(rv) < sh(hedged[V])):.0f}%), "
          f"final median {np.median(rf):.2f} (ours beats {100*np.mean(np.array(rf) < sh(hedged[F])):.0f}%)")
    print("hedged $ per year:", (2 * hedged.groupby(Y).sum()).round(0).astype(int).to_dict())
    pd.to_pickle(dict(kept=kept, W=W[kept], beta=b), SP + "combo2.pkl")
