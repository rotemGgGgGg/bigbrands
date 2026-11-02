"""Stage 5 - test every corpus rule on NQ (NSXUSD 1-min, 2012 - 2026-10). The rules were written before 2002 and are coded with
the poster's own numbers, so the whole period is out-of-sample; nothing is tuned. A rule PASSES only if all hold:
  net > 0 at 1x and at 2x costs (2.25 pt x price/17000 per round trip),
  one-sided t-test p < 0.05 / N  (Bonferroni over every rule tested),
  both coin flips p < 0.05 (1,000 draws: random timing/days, random direction),
  net > 0 in at least 2 of the 3 sub-periods 2012-16 / 2017-21 / 2022-26."""
import sys, os, math, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "papers"))
import pdata, engine as E, rules as R
OUT = os.path.dirname(os.path.abspath(__file__)) + "/"
D = pdata.load(); YR = D["days"].year.values; RET = E.day_returns(D); RNG = np.random.default_rng(2002); DRAWS = 1000


def trades(r, cx=1.0):
    o = r["fn"](D)
    if o[0] == "d":
        _, hold, mode = o; net, g, _, st = E.daily_eval(hold, RET[mode], mode, D["do"], cx); return net, g, st, o
    if o[0] == "i":
        T = E.intraday_trades(D, o[1], cx)
        return (T["net"], T["gross"], T["d"], o) if T else (np.zeros(0), np.zeros(0), np.zeros(0, int), o)
    tr = o[1]
    if not tr: return np.zeros(0), np.zeros(0), np.zeros(0, int), o
    d = np.array([x[0] for x in tr]); sd = np.array([x[1] for x in tr]); fp = np.array([x[2] for x in tr], float); xp = np.array([x[3] for x in tr], float)
    g = sd * (xp - fp); return g - E.rt_cost(fp, cx), g, d, o


def nulls(r, o, net, g, d):
    real = net.sum(); cost = (g - net).sum()
    S_ = RNG.choice([-1.0, 1.0], size=(DRAWS, len(g))); p_dir = (1 + ((S_ @ g - cost) >= real).sum()) / (DRAWS + 1)
    if o[0] == "d":
        _, hold, mode = o; _, p_t, _ = E.daily_null(hold, RET[mode], mode, D["do"], DRAWS, RNG); return p_t, p_dir
    if o[0] == "i":
        T = E.intraday_trades(D, o[1]); _, p_days, p_d2 = E.intraday_null(D, T, np.arange(len(YR)), DRAWS, RNG); return p_days, max(p_dir, p_d2)
    # custom per-day rules: the same number of trades, same direction, placed on random days and held open -> close
    oc = np.nan_to_num(D["dc"] - D["do"]); sd = np.array([x[1] for x in o[1]]); rd = np.empty(DRAWS)
    for i in range(DRAWS):
        k = RNG.integers(0, len(YR), len(sd)); rd[i] = (sd * oc[k]).sum() - cost
    return (1 + (rd >= real).sum()) / (DRAWS + 1), p_dir


if __name__ == "__main__":
    N = len(R.REG); rows = []; t0 = time.time()
    for r in R.REG:
        net, g, d, o = trades(r); n = len(net)
        row = dict(rid=r["rid"], name=r["name"], kind=o[0], n=n, src=r["src"])
        if n < 30: row.update(verdict="too few trades"); rows.append(row); continue
        yrs = YR[d]; sd = net.std(ddof=1); t = net.mean() / sd * math.sqrt(n) if sd > 0 else 0; p = 0.5 * math.erfc(t / math.sqrt(2))
        net2 = trades(r, 2.0)[0]; w, lo = net[net > 0], net[net <= 0]
        per = [net[(yrs >= a) & (yrs <= b)].sum() for a, b in ((2012, 2016), (2017, 2021), (2022, 2026))]
        p_t, p_dir = nulls(r, o, net, g, d)
        row.update(trades_yr=n / 14.8, win=100 * len(w) / n, rr=(w.mean() / -lo.mean()) if len(w) and len(lo) else np.nan,
                   net_pts=net.sum(), net2x=net2.sum(), usd_yr_mnq=2 * net.sum() / 14.8, t=t, p=p, p_timing=p_t, p_dir=p_dir,
                   p12_16=per[0], p17_21=per[1], p22_26=per[2])
        ok = net.sum() > 0 and net2.sum() > 0 and p < .05 / N and p_dir < .05 and (np.isnan(p_t) or p_t < .05) and sum(x > 0 for x in per) >= 2
        row["verdict"] = "PASS" if ok else "fail"; rows.append(row)
        print(f"{r['rid']:3d} {row['verdict']:4s} n={n:5d} win={row['win']:5.1f} net={net.sum():9.1f} t={t:5.2f} {r['name'][:70]}", flush=True)
    X = pd.DataFrame(rows); X.to_csv(OUT + "results.csv", index=False); print(f"\n{(X.verdict == 'PASS').sum()} of {N} pass  ({time.time() - t0:.0f}s)")
