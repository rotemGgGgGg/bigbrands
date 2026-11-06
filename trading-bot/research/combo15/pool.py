"""Stage 1 - the candidate pool: one net daily P&L series (NQ points, 1 contract, costs 2.25 pt x price/17000 per round trip)
for every strategy we have ever coded, on NSXUSD 1-minute 2012 - 2026-10:
  127 classic published strategies (papers/), 59 pre-2002 internet rules (oldweb/), and natively rebuilt survivors / practitioner
  edges (GapFB-C, pre-open fade, afternoon momentum, rebound after a -1% day, opex-Friday short, Turnaround Tuesday).
Multi-day trades are booked on their entry day. Output: scratchpad/combo15/pool.pkl (DataFrame days x strategies) + meta.csv."""
import sys, os, pickle, time
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, "../papers"), os.path.join(H, "../oldweb"), os.path.join(H, "../mega")]
import numpy as np, pandas as pd
import pdata, engine as E
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/combo15/"
D = pdata.load(); DAYS = D["days"].normalize(); N = len(DAYS); RET = E.day_returns(D)


def series_from(o):
    s = np.zeros(N)
    if o[0] == "d":
        _, hold, mode = o; _, _, dpn, _ = E.daily_eval(hold, RET[mode], mode, D["do"]); s = np.nan_to_num(dpn)
    elif o[0] == "i":
        T = E.intraday_trades(D, o[1])
        if T: np.add.at(s, T["d"], T["net"])
    else:
        for x in o[1]:
            d, sd, fp, xp = x[:4]
            if np.isfinite(fp) and np.isfinite(xp): s[d] += sd * (xp - fp) - E.rt_cost(fp)
    return s


# ---------------------------------------------------------------- native strategies on the 04:00-15:59 grid
def native():
    import grid
    G = grid.load("NSXUSD"); gd = pd.DatetimeIndex(G["days"]).normalize(); o, h, l, c = G["o"], G["h"], G["l"], G["c"]; R0 = grid.RTH
    cost = lambda p: 2.25 * p / 17000; pos = {d: i for i, d in enumerate(DAYS)}; out = {}
    pc = np.r_[np.nan, c[:-1, -1]]; ppc = np.r_[np.nan, pc[:-1]]; X = 715                         # 15:55
    tr = np.maximum(h - l, np.abs(h - np.c_[c[:, :1], c[:, :-1]])); tr = np.maximum(tr, np.abs(l - np.c_[c[:, :1], c[:, :-1]]))
    atr = pd.DataFrame(tr.T).rolling(14).mean().T.values                                          # ATR(14) of 1-minute bars
    def put(name, i, v):
        k = pos.get(gd[i]);
        if k is not None: out.setdefault(name, np.zeros(N))[k] += v

    def walk(i, sd, j0, fp, st, tg, xm):
        for j in range(j0, xm + 1):
            if (sd > 0 and l[i, j] <= st) or (sd < 0 and h[i, j] >= st): return (min(st, o[i, j]) if sd > 0 else max(st, o[i, j])) if j > j0 else st
            if tg is not None and j > j0 and ((sd > 0 and h[i, j] >= tg + .25) or (sd < 0 and l[i, j] <= tg - .25)): return tg
        return c[i, xm]

    for i in range(21, len(gd)):
        O = o[i, R0]; g = O / pc[i] - 1
        # GapFB-C: gap >= 0.3 %, 15-min OR stop entry in the gap's direction until 10:30, stop 2 x ATR(1m), no target, exit 15:55
        if abs(g) >= .003:
            sd = 1 if g > 0 else -1; lv = h[i, R0:R0 + 15].max() if sd > 0 else l[i, R0:R0 + 15].min()
            for j in range(R0 + 15, R0 + 61):
                if (sd > 0 and h[i, j] >= lv) or (sd < 0 and l[i, j] <= lv):
                    fp = max(lv, o[i, j]) if sd > 0 else min(lv, o[i, j]); st = fp - sd * 2 * atr[i, j - 1]
                    put("N:GapFB-C (gap>=0.3%, 15m OR in gap direction, 2xATR stop, exit 15:55)", i, sd * (walk(i, sd, j, fp, st, None, X) - fp) - cost(fp)); break
        # pre-open fade: 08:00->08:59 move, |z| > 2 vs the same window over the prior 20 days -> fade at 09:00, tgt 50 %, stop 100 %, exit 13:00
        mv = c[:, 299] - o[:, 240]; sdv = np.std(mv[i - 20:i])
        if sdv > 0 and abs(mv[i]) > 2 * sdv:
            sd = -1 if mv[i] > 0 else 1; fp = o[i, 300]; a = abs(mv[i])
            put("N:Pre-open fade (08:00-08:59 |z|>2, fade at 09:00, tgt 0.5, stop 1.0, exit 13:00)", i, sd * (walk(i, sd, 300, fp, fp - sd * a, fp + sd * .5 * a, 540) - fp) - cost(fp))
        # afternoon momentum: |09:30->14:59 move vs prior close| > its 20-day std -> follow at 15:00, exit 15:59
        r = c[:, R0 + 329] / pc - 1; s20 = np.nanstd(r[i - 20:i])
        if s20 > 0 and abs(r[i]) > s20:
            sd = 1 if r[i] > 0 else -1; fp = o[i, R0 + 330]; put("N:Afternoon momentum (15:00 follow the day's move > 1 sd)", i, sd * (c[i, -1] - fp) - cost(fp))
        # rebound: prior day < -1 % -> long at the open, exit 12:00
        if pc[i] / ppc[i] - 1 < -.01: put("N:Rebound after -1% day (long open -> 12:00)", i, c[i, R0 + 149] - O - cost(O))
    # opex Friday short 09:30, stop 0.4 sigma, target 0.8 sigma, exit 15:55 (sigma = 14-day mean |close/open - 1|)
    d = pd.DatetimeIndex(gd); opex = (d.weekday == 4) & (d.day >= 15) & (d.day <= 21)
    sg = pd.Series(np.abs(c[:, X] / o[:, R0] - 1)).rolling(14).mean().shift().values
    for i in np.nonzero(opex & np.isfinite(sg))[0]:
        e = o[i, R0]; st = .4 * sg[i] * e; put("N:Opex-Friday short (09:30, stop 0.4s, tgt 0.8s, exit 15:55)", i, e - walk(i, -1, R0, e, e + st, e - 2 * st, X) - cost(e))
    # Turnaround Tuesday (Balke / classic): Monday closes below Friday's close -> long Tuesday open -> close
    for i in range(2, len(gd)):
        if d[i].weekday() == 1 and d[i - 1].weekday() == 0 and c[i - 1, -1] < c[i - 2, -1]:
            put("N:Turnaround Tuesday (down Monday -> long Tuesday open->close)", i, c[i, -1] - o[i, R0] - cost(o[i, R0]))
    return out


if __name__ == "__main__":
    os.makedirs(SP, exist_ok=True); t0 = time.time(); cols = {}; meta = []
    import strats as T1, rules as T2
    for r in T1.REG:
        try: cols[f"P{r['sid']}:{r['name']}"] = series_from(r["fn"](D, 1.0)); meta.append(("papers", r["src"]))
        except Exception as e: print("skip", r["name"], e)
    for r in T2.REG:
        try: cols[f"W{r['rid']}:{r['name']}"] = series_from(r["fn"](D)); meta.append(("oldweb", r["src"]))
        except Exception as e: print("skip", r["name"], e)
    for k, v in native().items(): cols[k] = v; meta.append(("native", "rebuilt on NSXUSD"))
    P = pd.DataFrame(cols, index=DAYS); P.to_pickle(SP + "pool.pkl")
    pd.DataFrame(meta, index=P.columns, columns=["family", "src"]).to_csv(SP + "meta.csv")
    print(P.shape, f"{time.time() - t0:.0f}s")
