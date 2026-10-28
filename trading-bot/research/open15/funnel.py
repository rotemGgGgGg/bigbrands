"""Funnel over the 12.4M-variant search. Train 2012-2019 only for selection; validation 2020-2023; holdout 2024-2026 once."""
import pickle, math, numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/open15/"
S = pickle.load(open(SP + "search.pkl", "rb")); R = pd.DataFrame(S["rows"]); NV = S["nvalid"]
yrs = range(2012, 2027); tr, va, ho = range(2012, 2020), range(2020, 2024), range(2024, 2027)
for nm, ys in (("tr", tr), ("va", va), ("ho", ho)):
    R[f"pts_{nm}"] = sum(R[f"y{y}"] for y in ys); R[f"n_{nm}"] = sum(R[f"n{y}"] for y in ys)
for nm in ("va", "ho"):
    mu = R[f"pts_{nm}"] / R[f"n_{nm}"].clip(lower=1); var = R[f"sq_{nm}"] / R[f"n_{nm}"].clip(lower=1) - mu ** 2
    R[f"t_{nm}"] = np.where(R[f"n_{nm}"] > 30, mu / np.sqrt(var.clip(lower=1e-12)) * np.sqrt(R[f"n_{nm}"]), 0)
R["posyrs_tr"] = sum((R[f"y{y}"] > 0).astype(int) for y in tr)
bar = math.sqrt(2 * math.log(NV))
print(f"variants {S['ntot']:,}; with >=150 train trades {NV:,}; luck bar t = {bar:.2f}; max train t = {R.t_tr.max():.2f}")
print("train t >= 3:", len(R), "| >= 4:", (R.t_tr >= 4).sum(), "| >= luck bar:", (R.t_tr >= bar).sum())
# expected count of t>=3 under pure noise (normal tail) for comparison
print("noise would give about", int(NV * 0.5 * math.erfc(3 / math.sqrt(2))), "with t>=3")
A = R[R.t_tr >= bar]; B = R[(R.t_tr >= 3) & (R.posyrs_tr >= 6)]
V = B[(B.pts_va > 0) & (B.t_va >= 2)]
print("strict path (t>=bar):", len(A), "-> validation pass:", ((A.pts_va > 0) & (A.t_va >= 2)).sum())
print("soft path (t>=3, >=6/8 positive train years):", len(B), "-> validation (>0, t>=2):", len(V))
cols = ["K", "anchor", "level", "side", "order", "exit", "stop", "tgt", "filt", "n_tr", "t_tr", "pts_tr", "n_va", "t_va", "pts_va", "n_ho", "t_ho", "pts_ho"]
pd.set_option("display.width", 250)
print(R.sort_values("t_tr", ascending=False)[cols].head(15).round(2).to_string(index=False))
print("\nvalidation survivors (top 25 by validation t):")
print(V.sort_values("t_va", ascending=False)[cols].head(25).round(2).to_string(index=False))
print("validation survivors positive in holdout:", (V.pts_ho > 0).sum(), "/", len(V))
V.to_csv(SP + "val_survivors.csv", index=False); R.sort_values("t_tr", ascending=False).head(500).to_csv(SP + "top_train.csv", index=False)
