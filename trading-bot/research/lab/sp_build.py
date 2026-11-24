"""SP Model v8 deep-dive data for the Edge Lab page: both London windows, by scenario, side, hour, year, Monte Carlo."""
import json, math, numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
rng = np.random.default_rng(2026); out = {}
t = lambda x: float(x.mean() / x.std() * math.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else 0.0
for k, lab in (("A", "London 00:00–06:00"), ("B", "London 02:00–09:30")):
    d = pd.read_csv(SP + f"sp_trades_{k}.csv"); d.index = pd.to_datetime(d.entry_time, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    r = d.r; w, l = r[r > 0], r[r < 0]; yrs = r.groupby(r.index.year).sum(); eq = r.cumsum()
    n = int(round(len(r) / 14.9)); idx = rng.integers(0, len(r), (5000, n)); P = np.cumsum(r.values[idx], 1)
    dd = (np.maximum.accumulate(np.maximum(P, 0), 1) - P).max(1)
    grp = lambda g: [dict(k=str(a), n=int(len(x)), win=round(100 * (x > 0).mean(), 1), R=round(float(x.mean()), 3), t=round(t(x), 2)) for a, x in r.groupby(g)]
    out[k] = dict(label=lab, n=len(r), per_yr=round(len(r) / 14.9, 1), win=round(100 * (r > 0).mean(), 1), rr=round(float(w.mean() / -l.mean()), 2),
                  avg=round(float(r.mean()), 3), t=round(t(r), 2), total=round(float(r.sum()), 1), is_avg=round(float(r[r.index.year <= 2019].mean()), 3),
                  oos_avg=round(float(r[r.index.year >= 2020].mean()), 3), maxdd=round(float((eq.cummax() - eq).max()), 1),
                  pos_years=int((yrs > 0).sum()), n_years=int(len(yrs)), years={int(a): round(float(b), 1) for a, b in yrs.items()},
                  curve=[[a.strftime("%Y-%m-%d"), round(float(b), 2)] for a, b in eq.iloc[::max(1, len(eq) // 300)].items()],
                  scen=grp(d.scenario.values), side=grp(d.side.values), hour=grp(d.index.hour.values),
                  exits=grp(d.exit.values),
                  mc=dict(p_year_pos=round(100 * float((P[:, -1] > 0).mean()), 1), median_year=round(float(np.median(P[:, -1])), 1),
                          p5_year=round(float(np.percentile(P[:, -1], 5)), 1), p95_dd=round(float(np.percentile(dd, 95)), 1),
                          fan=[[round(float(np.percentile(P[:, j], q)), 2) for q in (5, 25, 50, 75, 95)] for j in np.linspace(0, n - 1, 40).astype(int)]))
out["variants"] = [
    dict(name="As specified (A)", per_yr=172, win=46.1, rr=1.10, is_R=-0.04, oos_R=-0.02, note="Baseline, no costs"),
    dict(name="S2 only + daily trend", per_yr=32, win=52.0, rr=1.07, is_R=0.07, oos_R=0.08, note="Best variant, t 1.1 both periods"),
    dict(name="Target −0.27 ext. + stop fib 1.0", per_yr=172, win=42.0, rr=1.44, is_R=0.03, oos_R=0.03, note="11/15 years, t 0.9"),
    dict(name="London Break & Retest", per_yr=220, win=29.0, rr=2.6, is_R=0.065, oos_R=0.04, note="Rebuilt from the autopsy, t 1.2 / 0.8"),
]
out["prop"] = dict(A=dict(pay=5, fail=82), B=dict(pay=20, fail=76))
json.dump(out, open("sp.json", "w"))
for k in "AB": o = out[k]; print(k, o["n"], o["win"], o["rr"], o["avg"], o["t"], o["total"], o["maxdd"], o["pos_years"], o["mc"]["p_year_pos"], o["mc"]["p95_dd"]); print(o["scen"]); print(o["side"])
