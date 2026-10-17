"""(1) Print DFR levels for the last sessions so they can be checked against TradingView.
(2) Confirmation variant: price trades beyond a level, then a 5-minute candle CLOSES back inside → enter next minute against
the move; stop = extreme of the excursion (+tick); targets: previous level, range edge, 1R, 2R. Windows as before."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd, itertools
src = open("dfr.py").read(); exec(src.split("WINDOWS =")[0]); exec("def simulate" + src.split("def simulate")[1].split("rows = []")[0])
print("\n(1) levels for checking (MNQ continuous, Databento) — date | Asia H | Asia L | −1 / −2 / −2.5 / −4 up | down")
for d, hh, ll, day in DAYS[-5:]:
    R = hh - ll
    print(d.date(), round(hh, 2), round(ll, 2), [round(hh + k * R, 2) for k in (1, 2, 2.5, 4)], [round(ll - k * R, 2) for k in (1, 2, 2.5, 4)])
WINDOWS = {"london 00-05": (0, 300), "pre 05-0930": (300, 570), "nyam 0930-12": (570, 720), "nypm 12-1555": (720, 955), "all": (0, 955)}
rows = []
for d, hh, ll, day in DAYS:
    R = hh - ll
    if R < 4: continue
    for (wn, (w0, w1)), lv, upper in itertools.product(WINDOWS.items(), (1.0, 2.0, 2.5, 4.0), (True, False)):
        lvl = hh + lv * R if upper else ll - lv * R
        wi = day[(mm[day] >= w0) & (mm[day] < w1)]
        if len(wi) < 10: continue
        t = np.nonzero(H[wi] > lvl)[0] if upper else np.nonzero(L[wi] < lvl)[0]
        if not len(t): continue
        k0 = wi[t[0]]
        # 5-minute closes after the first breach: minute index where (minute+1) % 5 == 0
        after = day[(day >= k0) & (mm[day] < w1)]
        conf = next((k for k in after if (mm[k] + 1) % 5 == 0 and ((C[k] < lvl) if upper else (C[k] > lvl))), None)
        if conf is None: continue
        ext = H[k0:conf + 1].max() if upper else L[k0:conf + 1].min()
        side = -1 if upper else 1; ent = conf + 1
        if ent >= len(O) or mm[ent] >= 955: continue
        e = O[ent]; sl = ext + (0.25 if upper else -0.25)
        if (sl - e) * side >= 0: continue
        risk = abs(e - sl)
        if risk <= 1: continue
        prev = hh + ([0, 1, 2, 2.5][[1, 2, 2.5, 4].index(lv)]) * R if upper else ll - ([0, 1, 2, 2.5][[1, 2, 2.5, 4].index(lv)]) * R
        for tg, tp in (("prev_level", prev), ("range_edge", hh if upper else ll), ("1R", e + side * risk), ("2R", e + side * 2 * risk)):
            if (tp - e) * side <= 0: continue
            rest = day[day >= ent]
            pts = simulate(rest, side, e, sl, tp)
            rows.append((d, wn, lv, "upper" if upper else "lower", tg, pts, risk, abs(tp - e) / risk))
T = pd.DataFrame(rows, columns=["date", "window", "level", "edge", "target", "pts", "risk", "rr"]); T["R"] = T.pts / T.risk
T["tr"] = pd.to_datetime(T.date).dt.year < 2024; T["Rg"] = (T.pts + COST) / T.risk
out = []
for k, g in T.groupby(["window", "level", "edge", "target"]):
    a, b = g[g.tr], g[~g.tr]
    if len(a) < 30 or len(b) < 15: continue
    out.append(dict(zip(["window", "level", "edge", "target"], k), n=len(g), win=round(100 * (g.pts > 0).mean(), 1), rr=round(g.rr.median(), 2),
                    R_tr=round(a.R.mean(), 3), R_te=round(b.R.mean(), 3), R_gross=round(g.Rg.mean(), 3),
                    t_tr=round(a.R.mean() / a.R.std() * np.sqrt(len(a)), 2), t_te=round(b.R.mean() / b.R.std() * np.sqrt(len(b)), 2)))
O2 = pd.DataFrame(out); O2.to_csv("dfr_confirm.csv", index=False); pd.set_option("display.width", 220)
print(f"\n(2) confirmation variant: {len(O2)} configs; positive in TRAIN {int((O2.R_tr>0).sum())}, in both {int(((O2.R_tr>0)&(O2.R_te>0)).sum())}, "
      f"TRAIN t>2 & TEST t>2: {int(((O2.t_tr>2)&(O2.t_te>2)).sum())}; mean R {O2.R_tr.mean():+.3f} / {O2.R_te.mean():+.3f}; mean GROSS R {O2.R_gross.mean():+.3f}")
print(O2.sort_values("R_tr", ascending=False).head(12).to_string(index=False))
