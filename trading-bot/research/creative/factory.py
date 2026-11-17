"""THEORY FACTORY - millions of ICT-style time x price theories, generated from a grammar, tested with three gates.
Theory = 1-3 signed conditions (+1 = 'bullish / discount' reading, -1 = mirror) x entry time x exit time x orientation.
  long when every chosen condition reads +1, short when every one reads -1 (perfect mirror); orientation 'against' flips it.
Conditions (all known at their time stamp, used only when that time <= entry):
  POS  price at T below / above reference R (true opens 00:00, 06:00, 07:30, 09:00, 09:30, prev close, prev-day mid,
       London mid, overnight mid) for T in 07:30, 09:00, 09:30, 09:45, 10:00, 10:30, 11:00
  BAND price at T in the bottom / top quarter of yesterday's range and of the London range
  SWEEP London low swept (high not) by T -> +1 ; high swept (low not) -> -1 ; session Q2 swept Q1 low/high (by 09:00)
  FLOW yesterday up/down, 50-day trend, gap sign, first 15 / 30 minutes direction
Entries 09:30 / 09:45 / 10:00 / 10:30 / 11:00 / 13:30; exits +30 min, +60 min, 12:00, 14:00, 15:55. Cost 1.3 bp.
Gates: discovery 2012-17 (n>=60, |t|>=3) -> validation 2018-21 (same sign, t>=2) -> final 2022-26 reported once.
Placebo: identical pipeline with every condition's day labels shuffled (what luck alone produces)."""
import sys, os, math, itertools, time, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../spmodel")); sys.path.insert(0, os.path.join(H, "../multi"))
from lbr import days
import mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"; BP = 1.3
G = days("NSXUSD"); D = sorted(G)[1:]; PREVD = dict(zip(sorted(G)[1:], sorted(G)[:-1])); ND = len(D)
Y = np.array([d.year for d in D])
EN = [570, 585, 600, 630, 660, 810]; EX = lambda e: [e + 30, e + 60, 720, 840, 955]


def features():
    dcs = mdata.load("NSXUSD"); dc = pd.Series(dcs["dc"], index=dcs["days"]); tr = (dc > dc.rolling(50).mean()).shift(1)
    F, names, times = [], [], []
    def add(name, t, vals): F.append(np.array(vals, np.int8)); names.append(name); times.append(t)
    rows = []
    for d in D:
        o, h, l, c = G[d]; po, ph, pl, pc_ = G[PREVD[d]]
        LH, LL = h[:360].max(), l[:360].min()
        rows.append(dict(o=o, h=h, l=l, c=c, pc=pc_[959], pmid=(ph.max() + pl.min()) / 2, pH=ph.max(), pL=pl.min(), LH=LH, LL=LL,
                         lmid=(LH + LL) / 2, onmid=(h[:570].max() + l[:570].min()) / 2))
    refs = {"TO00": (0, lambda r: r["o"][0]), "TO06": (360, lambda r: r["o"][360]), "TO0730": (450, lambda r: r["o"][450]),
            "TO09": (540, lambda r: r["o"][540]), "TO0930": (570, lambda r: r["o"][570]), "prevclose": (0, lambda r: r["pc"]),
            "prevmid": (0, lambda r: r["pmid"]), "Lmid": (360, lambda r: r["lmid"]), "ONmid": (570, lambda r: r["onmid"])}
    for T in (450, 540, 570, 585, 600, 630, 660):
        for rn, (rt, fn) in refs.items():
            if rt >= T: continue
            add(f"price@{T//60}:{T%60:02d} vs {rn}", T, [1 if r["o"][T] < fn(r) else (-1 if r["o"][T] > fn(r) else 0) for r in rows])
        for lab, lo, hi in (("prevday", "pL", "pH"), ("London", "LL", "LH")):
            vals = []
            for r in rows:
                rg = r[hi] - r[lo]; q = (r["o"][T] - r[lo]) / rg if rg > 0 else .5
                vals.append(1 if q < .25 else (-1 if q > .75 else 0))
            add(f"band@{T//60}:{T%60:02d} in {lab} quarters", T, vals)
    for T in (570, 600, 630, 660):
        vals = []
        for r in rows:
            lo = r["l"][360:T].min() < r["LL"]; hi = r["h"][360:T].max() > r["LH"]
            vals.append(1 if lo and not hi else (-1 if hi and not lo else 0))
        add(f"London sweep by {T//60}:{T%60:02d}", T, vals)
    vals = []
    for r in rows:
        q1h, q1l = r["h"][360:450].max(), r["l"][360:450].min(); q2h, q2l = r["h"][450:540].max(), r["l"][450:540].min()
        lo, hi = q2l < q1l, q2h > q1h; vals.append(1 if lo and not hi else (-1 if hi and not lo else 0))
    add("Q2 swept Q1 (session 06-12)", 540, vals)
    add("yesterday direction", 0, [1 if r["pc"] > PREV_OPEN.get(i, r["pc"]) else -1 for i, r in enumerate(rows)])
    add("50-day trend", 0, [0 if pd.isna(tr.get(d)) else (1 if tr.get(d) else -1) for d in D])
    add("gap", 570, [1 if r["o"][570] > r["pc"] else -1 for r in rows])
    add("first 15 min", 585, [1 if r["c"][584] > r["o"][570] else -1 for r in rows])
    add("first 30 min", 600, [1 if r["c"][599] > r["o"][570] else -1 for r in rows])
    return np.stack(F), names, np.array(times)


PREV_OPEN = {}
def rets():
    R, lab, et = [], [], []
    for e in EN:
        for x in EX(e):
            R.append([(G[d][3][x - 1] / G[d][0][e] - 1) * 1e4 for d in D]); lab.append(f"{e//60}:{e%60:02d}->{x//60}:{x%60:02d}"); et.append(e)
    return np.array(R), lab, np.array(et)


def scan(F, names, ftime, R, rlab, et, tag):
    nF = len(F); P = [(Y <= 2017), (Y >= 2018) & (Y <= 2021), (Y >= 2022)]
    RP = [(R * m).T for m in P]; R2P = [((R ** 2) * m).T for m in P]; ONE = [m.astype(float) for m in P]
    keep, total = [], 0
    def evaluate(S, combos, tmax):
        nonlocal total
        A = np.abs(S).astype(float); Sf = S.astype(float)
        cnt = [A @ o for o in ONE]; sm = [Sf @ rp for rp in RP]; sq = [A @ r2 for r2 in R2P]
        valid = tmax[:, None] <= et[None, :]; total += int(valid.sum()) * 2
        for orient in (1, -1):
            out = []
            for k in range(3):
                n = cnt[k][:, None]; s = orient * sm[k] - BP * n; q = sq[k] - 2 * BP * orient * sm[k] + BP ** 2 * n
                mu = np.where(n > 0, s / np.maximum(n, 1), 0); var = np.where(n > 1, q / np.maximum(n, 1) - mu ** 2, 0)
                t = np.where(var > 0, mu / np.sqrt(np.maximum(var, 1e-12)) * np.sqrt(np.maximum(n, 1)), 0)
                out.append((n, mu, t))
            (n0, m0, t0), (n1, m1, t1), (n2, m2, t2) = out
            ok = valid & (n0 >= 60) & (t0 >= 3) & (t1 >= 2) & (m1 > 0)
            for a, b in zip(*np.nonzero(ok)):
                keep.append(dict(theory=" & ".join(names[x] for x in combos[a]), trade=rlab[b], orient="with" if orient == 1 else "against",
                                 n_yr=(n0[a, 0] + n1[a, 0] + n2[a, 0]) / 14.8, disc_bp=m0[a, b], disc_t=t0[a, b], val_bp=m1[a, b], val_t=t1[a, b],
                                 final_bp=m2[a, b], final_t=t2[a, b], final_n=int(n2[a, 0])))
    t0_ = time.time()
    evaluate(F, [(i,) for i in range(nF)], ftime)
    for i in range(nF):
        S = F[i][None, :] * (F[i][None, :] == F[i + 1:]); evaluate(S, [(i, j) for j in range(i + 1, nF)], np.maximum(ftime[i], ftime[i + 1:]))
    for i, j in itertools.combinations(range(nF), 2):
        if j + 1 >= nF: continue
        base = F[i] * (F[i] == F[j]); S = base[None, :] * (base[None, :] == F[j + 1:])
        evaluate(S, [(i, j, k) for k in range(j + 1, nF)], np.maximum(max(ftime[i], ftime[j]), ftime[j + 1:]))
    K = pd.DataFrame(keep); print(f"[{tag}] theories tested: {total:,} | passed discovery+validation: {len(K)} | {time.time()-t0_:.0f}s", flush=True)
    return K, total


if __name__ == "__main__":
    for i, d in enumerate(D): PREV_OPEN[i] = G[PREVD[d]][0][570]
    F, names, ftime = features(); R, rlab, et = rets(); print(f"{len(F)} conditions, {len(rlab)} entry/exit pairs, {ND} days", flush=True)
    K, tot = scan(F, names, ftime, R, rlab, et, "REAL")
    rng = np.random.default_rng(7); Fs = np.stack([f[rng.permutation(ND)] for f in F])
    Kp, _ = scan(Fs, names, ftime, R, rlab, et, "PLACEBO (shuffled days)")
    pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 90)
    K.to_csv(SP + "factory_real.csv", index=False); Kp.to_csv(SP + "factory_placebo.csv", index=False)
    for lab, X in (("REAL", K), ("PLACEBO", Kp)):
        if len(X):
            print(f"\n{lab}: final 2022-26 positive {int((X.final_bp > 0).sum())}/{len(X)}, final t>=2: {int((X.final_t >= 2).sum())}, median final bp {X.final_bp.median():.2f}")
    if len(K): print("\nREAL survivors (sorted by final t):\n", K.sort_values("final_t", ascending=False).head(30).round(2).to_string(index=False))
