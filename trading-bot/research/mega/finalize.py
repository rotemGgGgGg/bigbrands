"""Stage 3 (selection on 2012-2022) and stage 4 (final test 2023-2026-10, ONCE, finalists only).
Gates on selection data only:
  train 2012-2018 : t >= 4 and >= 5 of 7 years positive        (strict path also reported: t >= luck bar sqrt(2 ln N))
  valid 2019-2022 : net > 0, t >= 2.5, >= 3 of 4 years positive
  robustness      : 2x costs still > 0 on 2012-2022; >= 60% of parameter neighbours (level +-1 step, adjacent exit plans) > 0
  families        : best per (anchor, trigger, side), top 20 by validation t -> finalists
Final (2023-2026): net > 0 at 1x and 2x costs, and both coin flips (same trades on random days of the period / random direction at
the same fill, 1,000 draws each) p < 0.05."""
import os, glob, pickle, math, sys
import numpy as np, pandas as pd
import search as S, theories as TH
OUT = S.OUT; TOP = 20
HE = [(h, s, t) for h in TH.HOLD for s in TH.STOPS for t in TH.TGTS]


def load():
    rows, hist, nv = [], 0, 0
    for f in sorted(glob.glob(OUT + "chunk_*.pkl")):
        x = pickle.load(open(f, "rb")); rows += x["rows"]; hist = hist + x["hist"]; nv += x["nvalid"]
    R = pd.DataFrame([dict(ai=g[0], level=g[1], trig=g[2], win=g[3], side=g[4], plan=e, ctx=c, t_tr=t,
                           **{f"y{2012 + k}": s[k] for k in range(11)}, **{f"n{2012 + k}": n[k] for k in range(11)}, q_va=q)
                      for g, e, c, t, s, n, q in rows])
    return R, hist, nv


def detail(ai, x, trg, w, sd, plan, ctx, cx=1.0):
    """per-trade arrays on ALL years (final=True) for one variant."""
    h, s_, t_ = HE[plan]; P = S.run_group(ai, x, trg, w, sd, final=True)[:, plan]
    F = S.context(sd)[:, ctx].astype(bool); d = np.nonzero((P != 0) & F)[0]
    net = P[d] - (cx - 1) * S.COST[d]
    return d, net


def resim(d, sd, fm, fp, u, plan):
    """exit of a market entry at (day d, minute fm, price fp) with the variant's exit plan (for the coin flips)."""
    h, s_, t_ = HE[plan]; rr = np.arange(len(d)); Hh, Ll, Oo, Cc = S.H[d], S.L[d], S.O[d], S.C[d]
    MM = S.MM[None]; st = fp - sd * s_ * u; tg = fp + sd * t_ * u
    ms = S.first((MM >= fm[:, None]) & np.where(sd[:, None] > 0, Ll <= st[:, None], Hh >= st[:, None]))
    mt = S.first((MM > fm[:, None]) & np.where(sd[:, None] > 0, Hh >= tg[:, None] + S.TICK, Ll <= tg[:, None] - S.TICK))
    ex = np.minimum(fm + h, S.NB - 1) if h != 9999 else np.full(len(d), S.NB - 1)
    ox = Oo[rr, np.minimum(ms, S.NB - 1)]
    sx = np.where(ms > fm, np.where(sd > 0, np.minimum(st, ox), np.maximum(st, ox)), np.where(sd > 0, np.minimum(st, fp), np.maximum(st, fp)))
    xp = np.where((ms <= ex) & (ms <= mt), sx, np.where(mt <= ex, tg, Cc[rr, ex]))
    return sd * (xp - fp) - S.COST[d]


if __name__ == "__main__":
    R, hist, NV = load(); bar = math.sqrt(2 * math.log(NV))
    yt, yv = [f"y{y}" for y in range(2012, 2019)], [f"y{y}" for y in range(2019, 2023)]
    R["pts_tr"] = R[yt].sum(1); R["n_tr"] = R[[f"n{y}" for y in range(2012, 2019)]].sum(1); R["pos_tr"] = (R[yt] > 0).sum(1)
    R["pts_va"] = R[yv].sum(1); R["n_va"] = R[[f"n{y}" for y in range(2019, 2023)]].sum(1); R["pos_va"] = (R[yv] > 0).sum(1)
    mu = R.pts_va / R.n_va.clip(lower=1); R["t_va"] = np.where(R.n_va >= 30, mu / np.sqrt((R.q_va / R.n_va.clip(lower=1) - mu ** 2).clip(lower=1e-12)) * np.sqrt(R.n_va), 0)
    print(f"variants tested {NV:,} | luck bar t {bar:.2f} | max train t {R.t_tr.max():.2f} | train t>=2.5 kept {len(R):,} "
          f"(normal noise would give ~{int(NV * 0.0062):,}) | t>=4: {(R.t_tr >= 4).sum():,} (noise ~{int(NV * 3.2e-5):,})")
    print("strict path: train t >= bar:", (R.t_tr >= bar).sum(), "-> validation ok:", ((R.t_tr >= bar) & (R.pts_va > 0) & (R.t_va >= 2.5)).sum())
    A1 = R[(R.t_tr >= 4) & (R.pos_tr >= 5)]; A2 = A1[(A1.pts_va > 0) & (A1.t_va >= 2.5) & (A1.pos_va >= 3)]
    print(f"soft path: train {len(A1):,} -> validation {len(A2):,}")
    A2.to_pickle(OUT + "validated.pkl")
    if "--final" not in sys.argv: sys.exit()
    # robustness on selection years, then families
    keep = []
    for i, r in A2.sort_values("t_va", ascending=False).iterrows():
        d, net = detail(r.ai, r.level, r.trig, r.win, r.side, r.plan, r.ctx, cx=2.0); sel = S.YR[d] <= 2022
        if net[sel].sum() <= 0: continue
        li = TH.LEVELS.index(r.level); nb = []
        for lv in TH.LEVELS[max(li - 1, 0):li + 2]:
            for pl in {max(r.plan - 1, 0), r.plan, min(r.plan + 1, 59)}:
                if lv == r.level and pl == r.plan: continue
                dd, nn = detail(r.ai, lv, r.trig, r.win, r.side, pl, r.ctx); nb.append(nn[S.YR[dd] <= 2022].sum() > 0)
        if np.mean(nb) < 0.6: continue
        fam = (r.ai, r.trig, r.side)
        if fam in {k[0] for k in keep}: continue
        keep.append((fam, r))
        if len(keep) >= TOP: break
    print(f"finalists after 2x-cost + neighbour gates and family de-dup: {len(keep)}")
    rng = np.random.default_rng(2026); out = []
    for fam, r in keep:
        d, net = detail(r.ai, r.level, r.trig, r.win, r.side, r.plan, r.ctx); fin = S.YR[d] >= 2023
        d2, net2 = detail(r.ai, r.level, r.trig, r.win, r.side, r.plan, r.ctx, cx=2.0)
        P, fm, fp, u = S.run_group(r.ai, r.level, r.trig, r.win, r.side, final=True, fills=True)
        df = d[fin]; real = net[fin].sum(); pool = np.nonzero(S.YR >= 2023)[0]; sdv = np.full(len(df), r.side)
        n_rd = n_fl = 0; DR = 1000
        for _ in range(DR):
            dd = rng.choice(pool, len(df), replace=len(df) > len(pool)); fmr = fm[df]
            n_rd += resim(dd, sdv, fmr, S.O[dd, np.minimum(fmr, S.NB - 1)], u[df], r.plan).sum() >= real
            sg = rng.choice([-1, 1], len(df)); n_fl += resim(df, sdv * sg, fmr, fp[df], u[df], r.plan).sum() >= real
        p_days, p_dir = (1 + n_rd) / (DR + 1), (1 + n_fl) / (DR + 1)
        out.append(dict(p_days=p_days, p_dir=p_dir, rule=TH.describe(r.ai, r.level, r.trig, r.win, r.side, TH.CONTEXT[r.ctx]), exit=HE[r.plan], t_tr=r.t_tr, t_va=r.t_va,
                        n_final=int(fin.sum()), final_pts=net[fin].sum(), final_pts_2x=net2[S.YR[d2] >= 2023].sum(),
                        final_win=100 * (net[fin] > 0).mean() if fin.any() else np.nan,
                        **{f"usd{y}": 2 * net[S.YR[d] == y].sum() for y in range(2012, 2027)}))
    F = pd.DataFrame(out); F.to_csv(OUT + "final.csv", index=False); pd.set_option("display.width", 300); pd.set_option("display.max_colwidth", 200)
    print(F.round(2).to_string())
