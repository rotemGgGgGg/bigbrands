"""Multiple-testing control: rerun the exact mining with the event attributes (correlation, quarter, session, bias, size,
displacement, direction-independent) SHUFFLED across events, outcomes untouched. If the shuffled data produce as many
'test-pass' candidates as the real data, the real candidates are selection noise. Also prints unfiltered base rates."""
import numpy as np, pandas as pd, pickle, subprocess, sys, os
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
for tf in ("15m", "1h", "4h", "5m"):
    EV, sims, t0, t1 = pickle.load(open(S + f"cfvg_{tf}.pkl", "rb"))
    cut = t0 + (t1 - t0) * 0.6; TR = (EV.ts < cut).values
    base = []
    for k in (("far", "atr1", 1.0, False, False), ("near", "edge", 2.0, False, False), ("market", "edge", 1.0, False, False), ("far", "atr05", 2.0, False, False)):
        x = sims[k]; ok = ~np.isnan(x)
        base.append(f"{k[:3]}: n {ok.sum()} win {100*(x[ok]>0).mean():.1f}% R {np.nanmean(x):+.3f}")
    print(tf, "unfiltered:", " | ".join(base))
    for seed in (1, 2):
        rng = np.random.default_rng(seed); E2 = EV.copy()
        perm = rng.permutation(len(EV))
        for col in ("es", "ym", "q", "sess", "bias_ema", "bias_dopen", "gap_atr", "disp_atr"):
            E2[col] = EV[col].values[perm]
        pickle.dump((E2, sims, t0, t1), open(S + f"cfvg_null{seed}_{tf}.pkl", "wb"))
        out = subprocess.run([sys.executable, "mine.py", f"null{seed}_{tf}"], capture_output=True, text=True).stdout
        print("   NULL seed", seed, out.strip().replace("\n", " "))
