"""Escalating levels for the 127 classic strategies (published parameters, nothing tuned). A strategy must pass every level to reach
the next one. Coin flips = (daily) circular shift of the holding series + random sign per trade; (intraday) the same trades on
random days of the window + random direction at the same fill. 500 draws each; p < 0.05 on BOTH flips to pass.
  L1  2015-2017            net > 0 after costs, >= 15 trades
  L2  2012-2017            net > 0, beats both coin flips
  L3  2018-2020 (unseen)   net > 0
  L4  2021-2023 (unseen)   net > 0 at 2x costs; and over 2012-2023 beats both coin flips
  L5  2012-2023            Bonferroni over all 127 (one-sided t p < 0.05/127) + lookbacks x0.75 and x1.25 both net > 0
  L6  2024-2026-10         holdout, looked at once: net > 0"""
import math, time, numpy as np, pandas as pd
import pdata, engine as E, strats as T
OUT = "/home/user/bigbrands/trading-bot/research/papers/"
RNG = np.random.default_rng(124); DRAWS = 500
D = pdata.load(); YR = D["days"].year.values; RET = E.day_returns(D); CACHE = {}


def get(r, s):
    k = (r["sid"], s)
    if k not in CACHE:
        o = r["fn"](D, s)
        CACHE[k] = o if o[0] == "d" else ("i", E.intraday_trades(D, o[1]), E.intraday_trades(D, o[1], 2.0))
    return CACHE[k]


def ev(r, y0, y1, cx=1.0, s=1.0, null=False):
    o = get(r, s); m = (YR >= y0) & (YR <= y1)
    if o[0] == "d":
        _, hold, mode = o; h, rt, px = hold[m], RET[mode][m], D["do"][m]
        net, g, dpn, st = E.daily_eval(h, rt, mode, px, cx); yrs = YR[m][st] if len(st) else np.zeros(0, int)
        p_a = p_b = np.nan
        if null: _, p_a, p_b = E.daily_null(h, rt, mode, px, DRAWS, RNG)
    else:
        Tr = o[1] if cx == 1.0 else o[2]
        if Tr is None: return dict(n=0, net=0.0)
        k = m[Tr["d"]]; Tk = {a: v[k] for a, v in Tr.items()}; net = Tk["net"]; yrs = YR[Tk["d"]]; p_a = p_b = np.nan
        if null and len(net): _, p_a, p_b = E.intraday_null(D, Tk, np.nonzero(m)[0], DRAWS, RNG)
    n = len(net)
    if n == 0: return dict(n=0, net=0.0)
    w, lo = net[net > 0], net[net <= 0]; sd = net.std(ddof=1) if n > 1 else np.nan
    t = net.mean() / sd * math.sqrt(n) if n > 1 and sd > 0 else 0.0
    return dict(n=n, net=net.sum(), avg=net.mean(), win=100 * len(w) / n, rr=(w.mean() / -lo.mean()) if len(w) and len(lo) and lo.mean() < 0 else np.nan,
                t=t, p_t=0.5 * math.erfc(t / math.sqrt(2)), p_timing=p_a, p_dir=p_b, yr=pd.Series(net).groupby(yrs).sum().to_dict())


if __name__ == "__main__":
    t0 = time.time(); rows = []; N = len(T.REG)
    for r in T.REG:
        row = dict(sid=r["sid"], name=r["name"], src=r["src"], kind=r["kind"], level=0)
        a = ev(r, 2015, 2017); row.update(L1_n=a["n"], L1_net=a["net"])
        if not (a["n"] >= 15 and a["net"] > 0): rows.append(row); continue
        row["level"] = 1
        b = ev(r, 2012, 2017, null=True); row.update(L2_net=b["net"], L2_ptime=b["p_timing"], L2_pdir=b["p_dir"])
        if not (b["net"] > 0 and b["p_timing"] < .05 and b["p_dir"] < .05): rows.append(row); continue
        row["level"] = 2
        c = ev(r, 2018, 2020); row.update(L3_net=c["net"])
        if not c["net"] > 0: rows.append(row); continue
        row["level"] = 3
        d = ev(r, 2021, 2023, cx=2.0); e = ev(r, 2012, 2023, null=True)
        row.update(L4_net2x=d["net"], L4_ptime=e["p_timing"], L4_pdir=e["p_dir"])
        if not (d["net"] > 0 and e["p_timing"] < .05 and e["p_dir"] < .05): rows.append(row); continue
        row["level"] = 4
        rob = [ev(r, 2012, 2023, s=s)["net"] for s in (0.75, 1.25)] if r["params"] else [np.nan, np.nan]
        row.update(L5_t=e["t"], L5_p=e["p_t"], L5_rob075=rob[0], L5_rob125=rob[1])
        if not (e["p_t"] < .05 / N and (not r["params"] or min(rob) > 0)): rows.append(row); continue
        row["level"] = 5
        h = ev(r, 2024, 2026); row.update(L6_n=h["n"], L6_net=h["net"], L6_win=h.get("win"), L6_rr=h.get("rr"))
        if h["net"] > 0: row["level"] = 6
        rows.append(row); print(r["sid"], r["name"], row["level"], f"{time.time() - t0:.0f}s", flush=True)
    R = pd.DataFrame(rows); R.to_csv(OUT + "levels.csv", index=False)
    print("\npassed level:", {k: int((R.level >= k).sum()) for k in range(1, 7)})
    print(R[R.level >= 3].drop(columns=["src"]).round(3).to_string())
