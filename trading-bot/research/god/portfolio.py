"""'God strategy' stage 2 — combine the train-selected component variants into one portfolio.
Each component is either off or one of its top-K train variants (NW 25, GFB 10, PF 6, OPX 4) at risk weight {0.5, 1, 2} R:
(25·3+1)(10·3+1)(6·3+1)(4·3+1) − 1 = 581,931 portfolios. Components trade independently (separate positions).
Selection rule fixed in advance: highest TRAIN (2010-19) daily Sharpe whose VALIDATE (2020-23) Sharpe is > 0. TEST (2024-26) once."""
import os, pickle, itertools, time
import numpy as np, pandas as pd
from numba import njit, prange
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/god" + ("_stress/" if os.environ.get("STRESS", "0") == "1" else "/")
W = (0.5, 1.0, 2.0)
COMP = ("NW", "GFB", "PF", "OPX")


def load():
    D = pickle.load(open(SP + "daily.pkl", "rb"))
    idx = pd.DatetimeIndex(sorted(set().union(*[set(v.index) for v in D.values()])))
    idx = idx[idx.weekday < 5]
    M = {c: D[c].reindex(idx).fillna(0.0) for c in COMP}
    return idx, M


@njit(parallel=True, cache=True)
def evaluate(Ms, choice, weight, per):
    n = choice.shape[0]; out = np.zeros((n, 9))
    for q in prange(n):
        sums = np.zeros(3); sq = np.zeros(3); cnt = np.zeros(3); eq = 0.0; pk = 0.0; dd = 0.0
        for t in range(Ms.shape[1]):
            x = 0.0
            for c in range(4):
                j = choice[q, c]
                if j >= 0: x += weight[q, c] * Ms[c, t, j]
            p = per[t]; sums[p] += x; sq[p] += x * x; cnt[p] += 1
            if p == 0:
                eq += x; pk = max(pk, eq); dd = max(dd, pk - eq)
        for p in range(3):
            m = sums[p] / cnt[p]; v = sq[p] / cnt[p] - m * m
            out[q, p] = m / np.sqrt(v) * np.sqrt(252.0) if v > 0 else 0.0
            out[q, 3 + p] = sums[p] / cnt[p] * 252.0
        out[q, 6] = dd
    return out


if __name__ == "__main__":
    t0 = time.time(); idx, M = load(); K = max(M[c].shape[1] for c in COMP)
    Ms = np.zeros((4, len(idx), K))
    for k, c in enumerate(COMP): Ms[k, :, :M[c].shape[1]] = M[c].values
    per = np.where(idx.year <= 2019, 0, np.where(idx.year <= 2023, 1, 2)).astype(np.int64)
    opts = [[(-1, 0.0)] + [(j, w) for j in range(M[c].shape[1]) for w in W] for c in COMP]
    combos = [p for p in itertools.product(*opts) if any(j >= 0 for j, _ in p)]
    choice = np.array([[j for j, _ in p] for p in combos], np.int64); weight = np.array([[w for _, w in p] for p in combos])
    print(len(combos), "portfolios", f"{time.time() - t0:.0f}s", flush=True)
    out = evaluate(Ms, choice, weight, per)
    names = {c: list(M[c].columns) for c in COMP}
    T = pd.DataFrame(out[:, :7], columns=["sh_tr", "sh_va", "sh_te", "Ryr_tr", "Ryr_va", "Ryr_te", "dd_tr"])
    for k, c in enumerate(COMP):
        T[c] = [names[c][j] if j >= 0 else "-" for j in choice[:, k]]; T["w_" + c] = weight[:, k]
    T.to_csv(SP + "portfolios.csv.gz", index=False)
    T = T.sort_values("sh_tr", ascending=False)
    final = T[T.sh_va > 0].iloc[0]
    pd.set_option("display.width", 250); print(T.head(15).round(3).to_string(index=False))
    print("\nFINAL (rule: best train Sharpe with validate Sharpe > 0):"); print(final.to_string())
    final.to_frame().T.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_pick" + ("_stress" if os.environ.get("STRESS", "0") == "1" else "") + ".csv"), index=False)
    print(f"{time.time() - t0:.0f}s")
