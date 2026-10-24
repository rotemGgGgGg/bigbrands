"""Phase 2b — portfolio search over daily R series: Phase-1 survivors (top 5 per strategy) + the four earlier components
(top train variants of No-Wick / GapFB / Pre-Fade / Opex from research/god). Beam search (width 20, up to 6 members),
weights {0.5, 1, 2}, objective = TRAIN (2010-19) daily Sharpe. Validate / test Sharpe reported for the final beam."""
import pickle, time
import numpy as np, pandas as pd
from phase1 import SP

GOD = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/god/daily.pkl"
W = (0.5, 1.0, 2.0)


def sharpe(x): return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0


if __name__ == "__main__":
    t0 = time.time(); D = pickle.load(open(SP + "phase2_daily.pkl", "rb"))
    for comp, df in pickle.load(open(GOD, "rb")).items():
        for c in df.columns[:5]: D[c] = df[c]
    idx = pd.DatetimeIndex(sorted(set().union(*[set(s.index) for s in D.values()]))); idx = idx[(idx.weekday < 5) & (idx <= "2026-07-22")]
    M = pd.DataFrame({k: v.reindex(idx).fillna(0.0) for k, v in D.items()}); names = list(M.columns); X = M.values
    tr = idx.year <= 2019; va = (idx.year >= 2020) & (idx.year <= 2023); te = idx.year >= 2024
    print(len(names), "series", f"{time.time() - t0:.0f}s")
    beam = [((), np.zeros(len(idx)))]; seen = set(); evaluated = 0; hist = []
    for depth in range(6):
        cand = []
        for members, x in beam:
            used = {m for m, _ in members}
            for j, nm in enumerate(names):
                if nm in used: continue
                for w in W:
                    key = tuple(sorted(members + ((nm, w),)))
                    if key in seen: continue
                    seen.add(key); y = x + w * X[:, j]; evaluated += 1
                    cand.append((sharpe(y[tr]), key, y))
        cand.sort(key=lambda z: -z[0]); beam = [(k, y) for _, k, y in cand[:20]]
        hist.append(cand[0][0]); print("depth", depth + 1, "best train Sharpe", round(cand[0][0], 3), "evaluated", evaluated, flush=True)
    rows = []
    for k, y in beam:
        eq = np.cumsum(y[tr]); dd = (np.maximum.accumulate(eq) - eq).max()
        rows.append(dict(members=" + ".join(f"{w}×{n}" for n, w in k), sh_tr=sharpe(y[tr]), sh_va=sharpe(y[va]), sh_te=sharpe(y[te]),
                         Ryr_tr=y[tr].mean() * 252, Ryr_va=y[va].mean() * 252, Ryr_te=y[te].mean() * 252, dd_tr=dd))
    R = pd.DataFrame(rows); R.to_csv(SP + "phase2_portfolio.csv", index=False)
    pd.set_option("display.width", 300); pd.set_option("display.max_colwidth", 200); print(R.round(3).to_string(index=False))
    print("portfolios evaluated:", evaluated)
