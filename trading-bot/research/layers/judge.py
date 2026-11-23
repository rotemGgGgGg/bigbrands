"""Gate all 13,271,040 strategies (real) and their placebo twins from the chunk sums written by layers.py."""
import itertools, numpy as np, pandas as pd, glob
from layers import TFS, TOUCH, MODE, CONF, ENTRY, STOP, TGT, OUT, NCELL
SESS = ["all", "Asia", "London", "NY AM", "NY PM"]; TREND = ["all", "with", "against"]; DS = ["all", "with day", "against day", "expanded"]
cells = np.array(list(itertools.product(range(4), range(4), range(4), range(2), range(2), range(2))))   # size, age, sess, trend, with, exp
FIL = list(itertools.product(range(4), range(4), range(5), range(3), range(4)))
M = np.zeros((NCELL, len(FIL)))
for f, (sm, am, ss, tr, ds) in enumerate(FIL):
    m = (cells[:, 0] >= sm) & (cells[:, 1] <= am) & ((ss == 0) | (cells[:, 2] == ss - 1)) & ((tr == 0) | (cells[:, 3] == (1 if tr == 1 else 0)))
    m &= (ds == 0) | ((ds == 1) & (cells[:, 4] == 1)) | ((ds == 2) & (cells[:, 4] == 0)) | ((ds == 3) & (cells[:, 5] == 1))
    M[:, f] = m


def judge(kind):
    rows = []; total = 0
    for tf in TFS:
        for touch in TOUCH:
            z = np.load(OUT + f"{kind}_{tf}_{touch}.npz"); sh = z["n"].shape          # (2 modes, 768, 512, 3)
            n, s, q = (np.einsum("bcp,cf->bfp", z[k].reshape(-1, NCELL, 3).astype(float), M) for k in "nsq")
            total += n.shape[0] * n.shape[1]
            with np.errstate(all="ignore"):
                mu = s / n; sd = np.sqrt(np.maximum(q / n - mu**2, 1e-12) * n / np.maximum(n - 1, 1)); t = mu / sd * np.sqrt(n)
            g = (n[..., 0] >= 40) & (t[..., 0] >= 3) & (n[..., 1] >= 20) & (t[..., 1] >= 2)
            for b, f in zip(*np.nonzero(g)):
                mi, rest = divmod(b, 768); ci, rest = divmod(rest, 96); ei, rest = divmod(rest, 24); si, ti = divmod(rest, 6)
                sm, am, ss, tr, ds = FIL[f]
                rows.append(dict(tf=tf, touch=touch, mode=MODE[mi], conf=CONF[ci], entry=ENTRY[ei], stop=STOP[si], tgt=TGT[ti],
                                 min_size=[0, .25, .5, 1][sm], max_age=[1, 3, 10, 30][am], sess=SESS[ss], trend=TREND[tr], day=DS[ds],
                                 n1=int(n[b, f, 0]), R1=mu[b, f, 0], t1=t[b, f, 0], n2=int(n[b, f, 1]), R2=mu[b, f, 1], t2=t[b, f, 1],
                                 n3=int(n[b, f, 2]), R3=mu[b, f, 2], t3=t[b, f, 2]))
    return pd.DataFrame(rows), total


if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    R, tot = judge("R"); P, totp = judge("P")
    print(f"strategies tested: real {tot:,}  placebo {totp:,}")
    for lab, X in (("REAL", R), ("PLACEBO", P)):
        if not len(X): print(lab, "survivors 0"); continue
        print(f"{lab}: survivors of gates 1+2: {len(X):,} | 2022-26: positive {100*(X.R3>0).mean():.1f}%, avg {X.R3.mean():+.3f}R, t>=2 {100*(X.t3>=2).mean():.1f}%")
    R.to_pickle(OUT + "surv_real.pkl"); P.to_pickle(OUT + "surv_placebo.pkl")
    for col in ("tf", "touch", "mode", "conf", "entry", "stop", "tgt", "sess"):
        a = R[col].value_counts(); b = P[col].value_counts() if len(P) else a * 0
        print(col, " | ".join(f"{k}: {a.get(k,0)} vs {b.get(k,0)}" for k in a.index))
    if len(R):
        print("\nTOP 25 real by 2012-21 combined t (2022-26 shown, never used to choose):")
        R["t12"] = (R.t1 + R.t2) / np.sqrt(2)
        print(R.sort_values("t12", ascending=False).head(25).round(3).to_string(index=False))
