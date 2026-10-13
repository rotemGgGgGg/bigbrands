"""Noise-Area variants. Selection on IS (2020–23) only; OOS (2024–26) reported, never used to choose."""
import pickle, json
import numpy as np, pandas as pd
from engine import S, summarize, walk, COST_PTS, PT_USD, IS_END
D = pickle.load(open(S + "D.pkl", "rb"))

def na(look=14, every=30, first=29, last_entry=359, vwap_trail=False, vwap_entry=False, long_only=False,
       stop_sig=None, tgt_sig=None, size=None):
    move = np.abs(D.c / D.o[:, :1] - 1)
    rows = []
    marks = [k for k in range(first, 389) if (k + 1) % every == 0]
    dret = D.c[:, 389] / np.r_[np.nan, D.c[:-1, 389]] - 1
    for i in range(max(look, 15), len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4: continue
        sig = move[i - look:i].mean(0)
        o0, pc = D.o[i, 0], D.c[i - 1, 389]
        ub, lb = max(o0, pc) * (1 + sig), min(o0, pc) * (1 - sig)
        vw = D.vwap(i); c, o, h, l = D.c[i], D.o[i], D.h[i], D.l[i]
        mult = 1.0
        if size == "vol":
            sd = np.nanstd(dret[i - 14:i])
            mult = min(4, 0.02 / sd) / 2 if sd > 0 else 1   # /2: average ≈ 1
        pos, ent, k0 = 0, 0.0, 0
        mi = 0
        while mi < len(marks):
            k = marks[mi]
            if pos:   # intrabar protective stop / target between marks (1-minute walk)
                if stop_sig or tgt_sig:
                    st = ent - pos * stop_sig * sig[k0] * ent if stop_sig else None
                    tg = ent + pos * tgt_sig * sig[k0] * ent if tgt_sig else None
                    px, j, why = walk(o, h, l, c, k0, pos, ent, st, tg, k)
                    if why != "time":
                        rows.append((D.days[i], pos, (px - ent) * pos * mult, np.nan)); pos = 0
                        # resume at the next mark after j
                        while mi < len(marks) and marks[mi] < j: mi += 1
                        if mi >= len(marks): break
                        k = marks[mi]
            want = pos
            if pos == 1 and c[k] < (max(ub[k], vw[k]) if vwap_trail else lb[k]): want = 0
            if pos == -1 and c[k] > (min(lb[k], vw[k]) if vwap_trail else ub[k]): want = 0
            if k <= last_entry:
                if c[k] > ub[k] and (not vwap_entry or c[k] > vw[k]): want = 1
                elif c[k] < lb[k] and (not vwap_entry or c[k] < vw[k]) and not long_only: want = -1
            if want != pos:
                px = o[k + 1]
                if pos: rows.append((D.days[i], pos, (px - ent) * pos * mult, np.nan))
                pos, ent, k0 = want, px, k + 1
            mi += 1
        if pos: rows.append((D.days[i], pos, (c[389] - ent) * pos * mult, np.nan))
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])

V = {
 "base": dict(),
 "every60": dict(every=60),
 "vwap_trail": dict(vwap_trail=True),
 "vwap_both": dict(vwap_trail=True, vwap_entry=True),
 "long_only": dict(long_only=True),
 "first10:30": dict(first=59),
 "no_entry_after_15:00": dict(last_entry=329),
 "stop 1σ": dict(stop_sig=1.0), "stop 2σ": dict(stop_sig=2.0),
 "tgt 2σ": dict(tgt_sig=2.0), "tgt 3σ": dict(tgt_sig=3.0),
 "stop1σ tgt2σ": dict(stop_sig=1.0, tgt_sig=2.0),
 "vol sizing": dict(size="vol"),
 "every60 stop 2σ": dict(every=60, stop_sig=2.0),
 "every60 vwap_trail": dict(every=60, vwap_trail=True),
}
out = []
for name, kw in V.items():
    tr = na(**kw); r = summarize(name, tr); out.append(r)
    print(f"{name:22} n{r['n']:5} win{r['win']:5} rr{r['rr']:5} pf{r['pf']:5} \$/tr{r['avg_usd']:6} dd{r['maxdd_usd']:6} IS_sh{r['IS_sh']:5} | OOS_sh{r['OOS_sh']:5} yrs{r['yrs_pos']}", flush=True)
pd.DataFrame(out).to_csv("na_explore.csv", index=False)
