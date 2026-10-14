"""Stage 1: every alternative-chart generator × parameters × stop model × reward:risk × time window × direction.
Selection on TRAIN only. A config is promoted to VAL only if TRAIN: n ≥ 40, win ≥ 50 %, expectancy > 0.
TEST is never touched here. Resumable: finished generator configs are listed in stage1_done.txt."""
import sys, os, json, itertools, time
import numpy as np, pandas as pd
from core import first_passage, metrics, Logger, SPLIT, SIG, o, HERE
import charts as C

GENS = []
for k, run, mode in itertools.product((0.05, 0.08, 0.12, 0.18), (2, 3, 4, 6), ("rev_follow", "rev_fade", "pullback")): GENS.append(("renko", C.gen_renko, dict(k=k, run=run, mode=mode)))
for n, run, mode in itertools.product((1, 3, 5, 15), (3, 5, 8), ("flip_follow", "strong_cont")): GENS.append(("heikin", C.gen_ha, dict(n=n, run=run, mode=mode)))
for k, run in itertools.product((0.05, 0.1, 0.15, 0.25), (2, 3, 5)): GENS.append(("rangebar", C.gen_range, dict(k=k, run=run, mode="exhaust_fade")))
for k in (0.05, 0.1, 0.15, 0.25): GENS.append(("rangebar", C.gen_range, dict(k=k, run=3, mode="three_push")))
for q, z in itertools.product((40, 80, 160), (0.3, 0.5)): GENS.append(("volbar", C.gen_volbars, dict(q=q, z=z, mode="absorb_fade")))
for q, z in itertools.product((40, 80, 160), (2.0, 3.0)): GENS.append(("volbar", C.gen_volbars, dict(q=q, z=z, mode="ignite_follow")))
for a in (15, 30, 60): GENS.append(("profile", C.gen_profile, dict(mode="eighty", accept_min=a)))
for a in (5, 15, 30): GENS.append(("profile", C.gen_profile, dict(mode="reject", accept_min=a)))
for k, mode in itertools.product((0.04, 0.06, 0.1, 0.15), ("double_break", "triple_break")): GENS.append(("pnf", C.gen_pnf, dict(k=k, mode=mode)))
for n, run in itertools.product((1, 3, 5, 15), (3, 5, 7)): GENS.append(("3linebreak", C.gen_tlb, dict(n=n, run=run)))
for n, look in itertools.product((1, 3, 5, 15), (6, 12, 24)): GENS.append(("delta_approx", C.gen_delta, dict(n=n, look=look)))
for win, thr, mode in itertools.product((20, 40), (0.7, 0.8), ("follow", "fade")): GENS.append(("entropy", C.gen_entropy, dict(win=win, thr=thr, mode=mode)))

STOPS = [("struct", 1.0), ("struct", 1.5), ("sigma", 0.1), ("sigma", 0.2), ("sigma", 0.3)]
RRS = (2.0, 2.5, 3.0)
WINDOWS = {"all": (0, 390), "am": (0, 120), "mid": (120, 270), "pm": (270, 390)}
DIRS = {"both": (1, -1), "long": (1,), "short": (-1,)}
MAX_STOP_SIG = 0.6          # reject stops wider than 0.6 × typical daily move (no hidden giant stops)

def run_gen(family, fn, params, L):
    ev = fn(**params)
    if ev.empty: return 0, []
    out = {}; promoted = []
    for (sk, sm), rr in itertools.product(STOPS, RRS):
        R = []; keep = []
        for r in ev.itertuples(index=False):
            i, m, side, ss = int(r.i), int(r.m), int(r.side), r.sstop
            px = o[i, 0]; sig_pts = SIG[i] * px
            sp = ss * sm if sk == "struct" else sm * sig_pts
            if not np.isfinite(sp) or sp < 2.0 or sp > MAX_STOP_SIG * sig_pts or m + 1 > 384: R.append(np.nan); continue
            R.append(first_passage(i, m + 1, side, o[i, m + 1], sp, rr)[0])
        R = np.array(R); ok = ~np.isnan(R)
        for (wn, (a, b)), (dn, dset) in itertools.product(WINDOWS.items(), DIRS.items()):
            sel = ok & (ev.m.values >= a) & (ev.m.values < b) & np.isin(ev.side.values, dset)
            cfg = dict(params, gen=family, stop=f"{sk}x{sm}", rr=rr, window=wn, dir=dn)
            tr = sel & (SPLIT[ev.i.values] == 0)
            m_tr = metrics(R[tr])
            status = "rejected"; reason = ""
            if m_tr.get("n", 0) < 40: reason = "n_train<40"
            elif m_tr["win"] < 50: reason = "train_win<50"
            elif m_tr["exp_R"] <= 0: reason = "train_exp<=0"
            else: status = "to_val"
            L.log(family, cfg, "train", m_tr, status, reason)
            if status == "to_val":
                va = sel & (SPLIT[ev.i.values] == 1)
                m_va = metrics(R[va])
                vst = "val_pass" if m_va.get("n", 0) >= 20 and m_va["win"] >= 70 and m_va["exp_R"] > 0 else "val_fail"
                L.log(family, cfg, "val", m_va, vst, "" if vst == "val_pass" else "val win<70 or exp<=0 or n<20")
                promoted.append((cfg, m_tr, m_va, vst))
    return len(ev), promoted

if __name__ == "__main__":
    part, nparts = int(sys.argv[1]), int(sys.argv[2])
    done_f = os.path.join(HERE, f"stage1_done_{part}.txt")
    done = set(open(done_f).read().split("\n")) if os.path.exists(done_f) else set()
    L = Logger(f"stage1_{part}")
    for g, (fam, fn, p) in enumerate(GENS):
        if g % nparts != part: continue
        key = fam + json.dumps(p, sort_keys=True)
        if key in done: continue
        t = time.time(); nev, prom = run_gen(fam, fn, p, L); L.f.flush()
        best = sorted(prom, key=lambda x: -x[2].get("win", 0))[:1]
        print(f"{fam} {p} events={nev} promoted={len(prom)} best_val={best[0][2] if best else None} {time.time()-t:.0f}s", flush=True)
        open(done_f, "a").write(key + "\n")
    L.close()
