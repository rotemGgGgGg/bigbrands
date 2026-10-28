"""Funnel for the 9:23 Fib ladder grid: select on 2012-2019, validate 2020-2023, holdout 2024-2026 once."""
import math, numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/fib923/"
R = pd.read_pickle(SP + "grid.pkl")
for nm, ys in (("tr", range(2012, 2020)), ("va", range(2020, 2024)), ("ho", range(2024, 2027))):
    R[f"pts_{nm}"] = sum(R[f"y{y}"] for y in ys); R[f"n_{nm}"] = sum(R[f"n{y}"] for y in ys)
for nm in ("va", "ho"):
    mu = R[f"pts_{nm}"] / R[f"n_{nm}"].clip(lower=1); v = R[f"sq_{nm}"] / R[f"n_{nm}"].clip(lower=1) - mu ** 2
    R[f"t_{nm}"] = np.where(R[f"n_{nm}"] > 30, mu / np.sqrt(v.clip(lower=1e-12)) * np.sqrt(R[f"n_{nm}"]), 0)
R["win_tr"] = 100 * R.w_tr / R.n_tr.clip(lower=1); R["posyrs"] = sum((R[f"y{y}"] > 0).astype(int) for y in range(2012, 2020))
V = R[R.n_tr >= 150]; bar = math.sqrt(2 * math.log(len(V)))
print(f"variants {len(R):,}; >=150 train trading days {len(V):,}; luck bar {bar:.2f}; max train t {V.t_tr.max():.2f}; "
      f"train-profitable {(V.pts_tr > 0).sum():,}; t>=3 {(V.t_tr >= 3).sum():,} (noise ~{int(len(V) * 0.00135):,})")
spec = R[(R.anchor == 23) & (R.e1 == -2) & (R.e2 == -4) & (R.side == "both") & (R.exit == 419)]
c = ["anchor", "e1", "e2", "live", "side", "stop", "tgt", "t2", "exit", "n_tr", "win_tr", "t_tr", "pts_tr", "t_va", "pts_va", "t_ho", "pts_ho"]
pd.set_option("display.width", 250)
print("\nyour spec (09:23, -2/-4, both sides, hold to close) - best 8 of its stop/target/live variants by train t:")
print(spec.sort_values("t_tr", ascending=False)[c].head(8).round(2).to_string(index=False))
print("\nall 09:23 -2/-4 both-sides variants: train>0", (spec.pts_tr > 0).sum(), "/", len(spec), "| all three periods >0:", ((spec.pts_tr > 0) & (spec.pts_va > 0) & (spec.pts_ho > 0)).sum())
B = V[(V.t_tr >= 3) & (V.posyrs >= 6)]; VV = B[(B.pts_va > 0) & (B.t_va >= 2)]
print(f"\nsoft path: t>=3 & >=6/8 positive train years {len(B):,} -> validation (>0, t>=2) {len(VV):,} -> holdout >0 {(VV.pts_ho > 0).sum():,}")
print("strict path (t >= luck bar):", (V.t_tr >= bar).sum())
print("\ntop 12 by train t:"); print(V.sort_values("t_tr", ascending=False)[c].head(12).round(2).to_string(index=False))
if len(VV): print("\ntop 12 validation survivors by validation t:"); print(VV.sort_values("t_va", ascending=False)[c].head(12).round(2).to_string(index=False))
VV.to_csv(SP + "val.csv", index=False)
