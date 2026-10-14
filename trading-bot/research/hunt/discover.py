"""Stage 1 — directional edge discovery. Each test: at decision minute T (bar open), condition on one or two
features (IS-quintile buckets), trade the side that IS says, hold to a fixed exit. Net of 1.25 pt costs.
Selection uses 2020–2023 only; 2024–2026 is reported, never used to pick."""
import numpy as np, pandas as pd, itertools, sys
from feat import load
F, D = load()
N = len(D.days)
yr = F.index.year.values
IS = yr < 2024
COST = 1.25
o, h, l, c, v = D.o, D.h, D.l, D.c, D.v
valid = F.valid.values & ~np.isnan(F.sig.values)

def intraday_state(T):
    """Features known at the open of minute T (uses bars < T)."""
    s = {}
    sig = F.sig.values
    o0 = o[:, 0]
    if T > 0:
        lastc = c[:, T - 1]
        hi, lo = h[:, :T].max(1), l[:, :T].min(1)
        s["mv"] = (lastc / o0 - 1) / sig                         # move since open in sigma units
        s["mv_pc"] = (lastc / F.pc.values - 1) / sig             # move since prior close
        s["pos"] = (lastc - lo) / np.maximum(hi - lo, 1e-9)      # location in today's range
        s["rng"] = (hi - lo) / o0 / F.rsig.values                # range so far vs typical full-day range
        tp = (h[:, :T] + l[:, :T] + c[:, :T]) / 3
        vw = (tp * v[:, :T]).sum(1) / np.maximum(v[:, :T].sum(1), 1)
        s["vwd"] = (lastc / vw - 1) / sig
        k = min(30, T)
        s["mv30"] = (lastc / o[:, T - k] - 1) / sig              # last 30-min move
        vv = v[:, :T].sum(1)
        s["vol"] = vv / pd.Series(vv).rolling(20).mean().shift().values
        s["above_onh"] = (lastc > F.onh.values).astype(float) - (lastc < F.onl.values).astype(float)
    return s

PRE = ["gap", "pret", "pret2", "prange", "pclv", "o_vs_ph", "o_vs_pl", "vol_ratio", "ret5", "ret10", "ret20", "ret50",
       "on_range", "on_pos", "on_vol_ratio", "lon_ret", "dow", "tdm", "tdm_rev"]

def buckets(x, q=5):
    """IS quantile edges → bucket ids (−1 for nan)."""
    xi = x[IS & ~np.isnan(x)]
    if len(np.unique(xi)) <= 6:                                  # categorical-ish
        vals = np.unique(xi)
        b = np.full(len(x), -1)
        for k, val in enumerate(vals): b[x == val] = k
        return b, [f"={v_:g}" for v_ in vals]
    e = np.quantile(xi, np.linspace(0, 1, q + 1))
    e[0], e[-1] = -np.inf, np.inf
    b = np.digitize(x, e[1:-1]); b[np.isnan(x)] = -1
    lab = [f"[{e[k]:.3g},{e[k+1]:.3g})" for k in range(q)]
    return b, lab

def tstat(x):
    x = x[~np.isnan(x)]
    return x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0

def run(T_list=(0, 5, 15, 30, 60, 90, 120, 180, 240, 300, 330), exits=("close", 30, 60, 120), min_n=60):
    rows = []
    for T in T_list:
        st = intraday_state(T)
        feats = {k: F[k].values for k in PRE} | st
        B = {k: buckets(x) for k, x in feats.items()}
        ent = o[:, T]
        rets = {}
        for ex in exits:
            jx = 389 if ex == "close" else min(T + ex, 389)
            if jx <= T: continue
            rets[ex] = c[:, jx] - ent
        names = list(B)
        combos = [(a,) for a in names] + list(itertools.combinations(names, 2))
        for combo in combos:
            if len(combo) == 1:
                b, lab = B[combo[0]]
                keys = [(k,) for k in range(len(lab))]
                masks = [(b == k) for k in range(len(lab))]
                labels = [f"{combo[0]}{lab[k]}" for k in range(len(lab))]
            else:
                (b1, l1), (b2, l2) = B[combo[0]], B[combo[1]]
                # 2-feature: extreme buckets only (first/last) to keep the count sane
                ks1 = [0, len(l1) - 1]; ks2 = [0, len(l2) - 1]
                masks, labels = [], []
                for k1 in ks1:
                    for k2 in ks2:
                        masks.append((b1 == k1) & (b2 == k2)); labels.append(f"{combo[0]}{l1[k1]} & {combo[1]}{l2[k2]}")
            for m, lab_ in zip(masks, labels):
                m = m & valid
                if (m & IS).sum() < min_n or (m & ~IS).sum() < min_n // 3: continue
                for ex, r in rets.items():
                    ri, ro = r[m & IS], r[m & ~IS]
                    side = 1 if ri.mean() > 0 else -1
                    ni, no = side * ri - COST, side * ro - COST
                    rows.append(dict(T=T, exit=ex, rule=lab_, side=side, nIS=len(ni), nOOS=len(no),
                                     IS=ni.mean(), tIS=tstat(ni), OOS=no.mean(), tOOS=tstat(no),
                                     winIS=(ni > 0).mean(), winOOS=(no > 0).mean(), nf=len(combo)))
        print("T", T, "tests so far", len(rows), file=sys.stderr, flush=True)
    return pd.DataFrame(rows)

if __name__ == "__main__":
    R = run()
    R.to_pickle("/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/hunt_R1.pkl")
    print("tests:", len(R))
    good = R[(R.tIS > 3.5) & (R.tOOS > 2)].sort_values("tOOS", ascending=False)
    print("IS t>3.5 & OOS t>2:", len(good))
    print(good.head(60).round(3).to_string())
    # null check: how many would pass if OOS were random? share of IS t>3.5 that keep OOS t>2
    s = R[R.tIS > 3.5]; print("IS-pass", len(s), "OOS-confirm rate", round((s.tOOS > 2).mean(), 3), "OOS mean of IS-pass", round(s.OOS.mean(), 2))
