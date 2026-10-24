"""Final stage: funnel over every tested configuration → finalists → validation pack → ONE holdout run (2024-01 → 2026-10)
→ Lucid 50K prop simulation → per-year results → deliverables (xlsx workbook, sqlite DB, trade logs, SVG equity curves, report data).
Pre-registered funnel (fixed before looking at results):
  F1 train 2010-17: ≥ 200 trades, R > 0, t ≥ 3
  F2 validate 2018-20: ≥ 60 trades, R > 0, t ≥ 2
  F3 test 2021-23: R > 0 (confirmation only)
  ranking: min(train t, validate t). Finalists = best 5 distinct families (window, confirmation, entry, side)."""
import os, json, glob, sqlite3
import numpy as np, pandas as pd
from scipy.stats import skew, kurtosis
import ict_data as data, ict_search as S, ict_validate as V, xlsx
from ict_space import WINDOWS

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"); os.makedirs(RES, exist_ok=True)
D = data.load(); DAYS = D["days"]; H = int(np.searchsorted(DAYS.values, np.datetime64("2024-01-01")))
XL = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"


def load_all():
    A = pd.concat([pd.read_csv(f) for f in glob.glob(S.OUT + "c*.csv.gz")]); A["src"] = "random"
    f = data.SP + "evo/evo.csv.gz"
    if os.path.exists(f): B = pd.read_csv(f); B["src"] = "evolution"; A = pd.concat([A, B])
    return A.drop_duplicates("cfg").reset_index(drop=True)


def family(cfg):
    c = json.loads(cfg); return (c["w"], c["conf"], c["entry"], c["side"])


def ystats(T, a=2010, b=2026):
    y = T.date.dt.year; rows = []
    for Y in range(a, b + 1):
        r = T[y == Y]
        if not len(r): continue
        w = r.R[r.R > 0]; ls = r.R[r.R <= 0]
        rows.append(dict(year=Y, trades=len(r), win_pct=100 * (r.R > 0).mean(), avg_win_R=w.mean(), avg_loss_R=ls.mean(),
                         rr=w.mean() / -ls.mean() if len(ls) and len(w) else np.nan, R=r.R.sum(), usd_1micro=2 * r.pts.sum(),
                         pct_of_50k=100 * 2 * r.pts.sum() / 50000))
    return pd.DataFrame(rows)


def prop_sim(T, start="2020-01-01", target=3000, dd=2000, mind=150, req=3000.0, cap=2000):
    """LucidFlex 50K, 1 MNQ per trade. Every trading day from `start` is a possible start; days = ALL trading days."""
    idx = DAYS[DAYS >= start]; T = T[T.date >= start].sort_values(["date", "minute"])
    pnl = (2 * T.groupby("date").pts.sum()).reindex(idx).fillna(0.0).values
    low = (2 * T.groupby("date").pts.apply(lambda s: min(0.0, s.cumsum().min()))).reindex(idx).fillna(0.0).values
    out = []
    for s in range(len(idx)):
        bal = peak = best = 0.0; d = s; ok = False
        while d < len(idx):
            if bal + low[d] <= peak - dd: break
            bal += pnl[d]; best = max(best, pnl[d])
            if bal <= peak - dd: break
            peak = max(peak, bal); d += 1
            if bal >= target and best <= 0.5 * bal and d - s >= 2: ok = True; break
        if not ok: out.append(dict(passed=False, complete=d < len(idx))); continue
        ed = d - s; bal = peak = 0.0; floor = -dd; locked = False; good = 0; cyc = 0.0; f0 = d; pay = None; dead = False
        while d < len(idx):
            if bal + low[d] <= floor: dead = True; break
            bal += pnl[d]; cyc += pnl[d]; good += pnl[d] >= mind
            if bal <= floor: dead = True; break
            if not locked: peak = max(peak, bal); floor = max(floor, min(peak - dd, 100.0))
            d += 1
            if good >= 5 and cyc > 0 and bal >= req: pay = (d - f0, min(0.5 * bal, cap)); break
        out.append(dict(passed=True, complete=True, eval_days=ed, payout_days=pay[0] if pay else np.nan,
                        payout=pay[1] if pay else np.nan, bust_before_payout=dead))
    R = pd.DataFrame(out); C_ = R[R.complete]
    return dict(starts=len(C_), pass_pct=100 * C_.passed.mean(), eval_days_median=C_[C_.passed].eval_days.median(),
                eval_days_p75=C_[C_.passed].eval_days.quantile(0.75),
                payout_days_median=C_[C_.passed].payout_days.median(), first_payout_median=C_[C_.passed].payout.median(),
                bust_before_payout_pct=100 * C_[C_.passed].bust_before_payout.mean())


def svg_equity(T, path, title):
    eq = (2 * T.sort_values(["date", "minute"]).pts).cumsum().values
    if len(eq) < 2: return
    W, Hh = 900, 300; mn, mx = min(0, eq.min()), max(eq.max(), 1); xs = np.linspace(40, W - 10, len(eq)); ys = Hh - 30 - (eq - mn) / (mx - mn) * (Hh - 60)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys)); z = Hh - 30 - (0 - mn) / (mx - mn) * (Hh - 60)
    open(path, "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{Hh}"><rect width="100%" height="100%" fill="white"/>'
                          f'<text x="40" y="18" font-family="sans-serif" font-size="13">{title} — cumulative $ per 1 MNQ</text>'
                          f'<line x1="40" y1="{z:.1f}" x2="{W - 10}" y2="{z:.1f}" stroke="#bbb"/><polyline fill="none" stroke="#2563eb" stroke-width="1.4" points="{pts}"/>'
                          f'<text x="{W - 160}" y="{Hh - 8}" font-family="sans-serif" font-size="11">end ${eq[-1]:,.0f}</text></svg>')


def main():
    A = load_all(); n_total = len(A); out = {"n_configs": int(n_total)}
    F1 = A[(A.tr_n >= 200) & (A.tr_R > 0) & (A.tr_t >= 3)]
    F2 = F1[(F1.va_n >= 60) & (F1.va_R > 0) & (F1.va_t >= 2)]
    F3 = F2[F2.te_R > 0].copy()
    out["funnel"] = dict(F1=len(F1), F2=len(F2), F3=len(F3))
    F3["rank"] = np.minimum(F3.tr_t, F3.va_t); F3["fam"] = F3.cfg.map(family)
    fin = F3.sort_values("rank", ascending=False).groupby("fam").head(1).head(5)
    # multiple-testing references
    ok = A[(A.tr_n >= 200) & np.isfinite(A.tr_t)]; srs = ok.tr_t / np.sqrt(ok.tr_n); out["luck_t_bar"] = float(np.sqrt(2 * np.log(n_total)))
    # PBO on the 100 best train configs (daily R, 2010-2023)
    pool = ok.sort_values("tr_t", ascending=False).head(100)
    M = np.array([V.daily_series(json.loads(c)) for c in pool.cfg]); pbo, _ = V.pbo(M); out["pbo_top100"] = pbo
    # walk-forward over the top-200 train pool: each year pick best trailing-4-year t, trade next year
    wpool = ok.sort_values("tr_t", ascending=False).head(200); Ys = np.arange(2010, 2024); S_ = []; N_ = []; Q_ = []
    for c in wpool.cfg:
        T = V.trades(json.loads(c)); y = T.date.dt.year.values
        S_.append([T.R[y == Y].sum() for Y in Ys]); N_.append([(y == Y).sum() for Y in Ys]); Q_.append([(T.R[y == Y] ** 2).sum() for Y in Ys])
    S_, N_, Q_ = map(np.array, (S_, N_, Q_)); wf = []
    for k, Y in enumerate(Ys):
        if k < 4: continue
        s, n, q = S_[:, k - 4:k].sum(1), N_[:, k - 4:k].sum(1), Q_[:, k - 4:k].sum(1); mu = s / np.maximum(n, 1)
        t = np.where(n >= 60, mu / np.sqrt(np.maximum(q / np.maximum(n, 1) - mu ** 2, 1e-12)) * np.sqrt(n), -9); j = int(np.argmax(t))
        wf.append(dict(year=int(Y), R=float(S_[j, k]), n=int(N_[j, k])))
    out["walk_forward"] = wf
    rows = []; best_T = None
    for i, (cfgs, r) in enumerate(zip(fin.cfg, fin.itertuples())):
        cfg = json.loads(cfgs); T = V.trades(cfg); T2 = V.trades(cfg, cx=2.0)
        re_ = V.random_entry(T, cfg, 500); fl = V.flip_direction(T, cfg, 500); bd = V.bootstrap_dd(T.R.values, 2000)
        nb = V.neighbours(cfg); nbres = []
        for name, c in nb:
            t = V.trades(c); y = t.date.dt.year
            nbres.append((t.R[y <= 2017].mean() > 0) and (t.R[(y >= 2018) & (y <= 2020)].mean() > 0))
        sr = T.R.mean() / T.R.std(); dsr, emax = V.dsr(sr, n_total, float(srs.var()), len(T), float(skew(T.R)), float(kurtosis(T.R, fisher=False)))
        HO = V.trades(cfg, H, len(DAYS)); hy = HO.date.dt.year
        w = T.R[T.R > 0]; ls = T.R[T.R <= 0]
        row = dict(rank=i + 1, cfg=cfgs, window=WINDOWS[cfg["w"]], trades_2010_23=len(T), win_pct=100 * (T.R > 0).mean(),
                   rr=w.mean() / -ls.mean(), R_trade=T.R.mean(), R_trade_cost2x=T2.R.mean(), tr_R=r.tr_R, va_R=r.va_R, te_R=r.te_R,
                   yrs_pos=f"{(T.groupby(T.date.dt.year).R.sum() > 0).sum()}/{T.date.dt.year.nunique()}",
                   p_random_entry=float((re_ >= T.R.mean()).mean()), p_flip=float((fl >= T.R.mean()).mean()),
                   neighbours_ok_pct=100 * np.mean(nbres), dsr=dsr, dsr_emax=emax, dd_R=float((T.R.cumsum().cummax() - T.R.cumsum()).max()),
                   dd_boot95_R=float(np.percentile(bd, 95)),
                   holdout_trades=len(HO), holdout_win=100 * (HO.R > 0).mean() if len(HO) else np.nan,
                   holdout_R=HO.R.mean() if len(HO) else np.nan, holdout_usd=2 * HO.pts.sum(),
                   holdout_yrs_pos=f"{(HO.groupby(hy).R.sum() > 0).sum()}/{hy.nunique()}" if len(HO) else "0/0")
        rows.append(row)
        TT = pd.concat([T, HO]); TT.to_csv(f"{RES}/trades_finalist{i + 1}.csv", index=False)
        svg_equity(TT, f"{RES}/equity_finalist{i + 1}.svg", f"Finalist {i + 1}")
        if i == 0: best_T = TT
    FIN = pd.DataFrame(rows); FIN.to_csv(f"{RES}/finalists.csv", index=False)
    if best_T is not None:
        Y = ystats(best_T); Y.to_csv(f"{RES}/yearly_finalist1.csv", index=False)
        out["prop"] = {f"req{int(q)}": prop_sim(best_T, req=q) for q in (1000.0, 2000.0, 3000.0)}
    json.dump(out, open(f"{RES}/summary.json", "w"), indent=1, default=float)
    # deliverables: sqlite with every tested config, workbook
    con = sqlite3.connect(XL + "ict_configs.sqlite"); A.to_sql("configs", con, if_exists="replace", index=False); con.close()
    lead = lambda p: pd.read_csv(XL + p)
    cr = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "creators_summary.csv"))
    top = A.sort_values("tr_t", ascending=False).head(3000)
    sheets = {"Leads_70pct": lead("xl_87c6c967-NQ_MNQ_70pct_Expanded_Research/Expanded_Leads.csv"),
              "Rejected_Controls": lead("xl_87c6c967-NQ_MNQ_70pct_Expanded_Research/Rejected_Controls.csv"),
              "Leads_Creators60": lead("xl_696c69d5-Creator_Strategy_Research_60plus/60_Research_Leads.csv"),
              "Creator_Replications": cr, "Funnel": pd.DataFrame([dict(stage=k, configs=v) for k, v in [("tested", n_total)] + list(out["funnel"].items())]),
              "Top3000_by_train_t": top, "Finalists_Validation": FIN,
              "WalkForward": pd.DataFrame(wf)}
    if best_T is not None:
        sheets["Yearly_Finalist1"] = Y
        sheets["Prop_LucidFlex50K"] = pd.DataFrame([dict(policy=k, **v) for k, v in out["prop"].items()])
    xlsx.write(sheets, f"{RES}/ICT_NQ_research_master.xlsx")
    print(json.dumps({k: v for k, v in out.items() if k != "walk_forward"}, indent=1, default=float)); pd.set_option("display.width", 250)
    if len(FIN): print(FIN.drop(columns=["cfg"]).round(3).to_string(index=False))
    if best_T is not None: print(Y.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
