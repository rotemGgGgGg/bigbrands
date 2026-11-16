"""Grid over every CRT / sweep variant built by sweep.py. A variant = market x timeframe x kind x stop x target x hold x
depth filter x real-range filter x session filter. Stats in R per trade (net of cost). Selection on 2012-19 only."""
import sys, os, math, itertools, numpy as np, pandas as pd
from sweep import SP, MKT, TFS, HOLDS, STOPS, TGTS
def tst(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0
rows = []
for nm, tf in itertools.product(MKT, TFS):
    f = SP + f"sig_{nm}_{tf}.pkl"
    if not os.path.exists(f): continue
    S = pd.read_pickle(f); Y = S.time.dt.year.values; I, O = Y <= 2019, Y >= 2020
    sess_ok = ((S.hour >= 2) & (S.hour < 12)).values
    for kind, dep, real, sess in itertools.product(("inside", "engulf", "both"), (0.0, 0.1), (False, True), (False, True)):
        if sess and tf >= 240: continue
        m = np.ones(len(S), bool)
        if kind != "both": m &= (S.kind == kind).values
        m &= (S.depth >= dep).values
        if real: m &= S.real.values
        if sess: m &= sess_ok
        if m.sum() < 100: continue
        for sn, tn, hd in itertools.product(STOPS, TGTS, HOLDS):
            col = f"{sn}|{tn}|{hd}"
            if col not in S: continue
            r = S[col].values; ok = m & np.isfinite(r)
            ri, ro = r[ok & I], r[ok & O]
            if len(ri) < 50 or len(ro) < 30: continue
            yy = pd.Series(ri).groupby(Y[ok & I]).sum()
            rows.append(dict(mk=nm, tf=tf, kind=kind, depth=dep, real=real, sess=sess, stop=sn, tgt=tn, hold=hd,
                             n_yr=ok.sum() / 14.8, win=100 * (r[ok] > 0).mean(), rr=r[ok][r[ok] > 0].mean() / -r[ok][r[ok] < 0].mean(),
                             IS=ri.mean(), IS_t=tst(ri), IS_pos=int((yy > 0).sum()), OOS=ro.mean(), OOS_t=tst(ro), OOS_win=100 * (ro > 0).mean()))
T = pd.DataFrame(rows); T.to_csv(SP + "grid.csv", index=False); pd.set_option("display.width", 250)
print(f"variants: {len(T)}")
print(f"positive IS: {(T.IS>0).mean()*100:.1f}% | positive OOS: {(T.OOS>0).mean()*100:.1f}% | IS t>=2: {(T.IS_t>=2).sum()} | OOS t>=2: {(T.OOS_t>=2).sum()}")
el = T[(T.IS_t >= 2.5) & (T.IS_pos >= 6)]
print(f"IS-eligible (t>=2.5, >=6/8 yrs): {len(el)}; OOS positive {(el.OOS > 0).sum()}; OOS t>=2 {(el.OOS_t >= 2).sum()}")
print(el.sort_values("IS_t", ascending=False).head(25).round(2).to_string(index=False))
print("\nfamily averages (mean R per trade):")
for g in ("tf", "kind", "tgt", "stop", "mk", "hold"):
    print(T.groupby(g)[["IS", "OOS"]].mean().round(3).T.to_string(), "\n")
print("classic CRT (inside, wick stop, range target, hold 1-3), by market x tf, OOS mean R / win%:")
c = T[(T.kind == "inside") & (T.stop == "wick") & (T.tgt == "range") & (T.depth == 0) & (~T.real) & (~T.sess)]
print(c.pivot_table(index="mk", columns=["tf", "hold"], values="OOS").round(3).to_string())
print(c.pivot_table(index="mk", columns=["tf", "hold"], values="win").round(0).to_string())
print("\nbest OOS among ALL (beware: chosen with hindsight):"); print(T.sort_values("OOS_t", ascending=False).head(8).round(2).to_string(index=False))
