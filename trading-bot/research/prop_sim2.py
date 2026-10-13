import numpy as np, pandas as pd
from engine import S, COST_PTS, PT_USD, IS_END, walk
from prop_paths import D
from prop_sim import na_days

def ib_days():
    rows = {}
    for i in range(len(D.days)):
        hi, lo = D.h[i, :60].max(), D.l[i, :60].min(); rng = hi - lo
        o5, h5, l5, c5, _ = D.bars(i, 5); vw = D.vwap(i); used = set(); k = 12
        pnl = 0.0; low = 0.0
        while k < 60:
            vwk = vw[k * 5 + 4]; side = 0
            if c5[k] > hi and 1 not in used and c5[k] > vwk: side = 1
            elif c5[k] < lo and -1 not in used and c5[k] < vwk: side = -1
            if not side: k += 1; continue
            used.add(side); j0 = (k + 1) * 5; e = o5[k + 1]; stop = lo if side == 1 else hi
            tgt = (hi + 1.5 * rng) if side == 1 else (lo - 1.5 * rng)
            px, jx, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], j0, side, e, stop, tgt, 384)
            worst = ((D.l[i, j0:jx + 1].min() - e) if side == 1 else (e - D.h[i, j0:jx + 1].max()))
            worst = max(worst, (stop - e) * side)
            low = min(low, pnl + worst * PT_USD - COST_PTS * PT_USD)
            pnl += (px - e) * side * PT_USD - COST_PTS * PT_USD
            k = jx // 5 + 1
        rows[D.days[i]] = (pnl, min(low, pnl))
    return rows

def lifecycle(pnl, low, start, keep=0.0, fee=146.0, max_payouts=5, cons=0.5):
    L = len(pnl); bal = peak = 0.0; mll = -2000.0; best = 0.0; i = start
    while True:
        if i >= L: return "open", 0.0, 0
        if bal + low[i] <= mll: return "eval_fail", 0.0, 0
        bal += pnl[i]; best = max(best, pnl[i])
        if mll < 100:
            peak = max(peak, bal); mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
        i += 1
        if bal >= 3000 and best <= cons * bal: break
    bal = peak = 0.0; mll = -2000.0; paid = 0.0; npay = 0; qd = 0; cyc = 0.0
    while i < L:
        if bal + low[i] <= mll: return "funded_fail", paid, npay
        d = pnl[i]; bal += d; cyc += d
        if d >= 150: qd += 1
        if mll < 100:
            peak = max(peak, bal); mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
        i += 1
        req = min(0.5 * bal, 2000.0, bal - keep)
        if qd >= 5 and cyc > 0 and req >= 500:
            bal -= req; paid += 0.9 * req; npay += 1; qd = 0; cyc = 0.0; mll = 100.0
            if npay >= max_payouts: return "done", paid, npay
    return "open_funded", paid, npay

def evaluate(pnl, low, starts, keep, fee=146.0):
    df = pd.DataFrame([lifecycle(pnl, low, s, keep) for s in starts], columns=["status", "paid", "npay"])
    c = df[df.status != "open"]
    return dict(pass_eval=round(100 * (c.status != "eval_fail").mean(), 1), payout=round(100 * (c.paid > 0).mean(), 1),
                avg_npay=round(c.npay.mean(), 2), five=round(100 * (c.status == "done").mean(), 1), ev=round(c.paid.mean() - fee))

na = na_days(None).set_index("date")
ib = ib_days()
ibdf = pd.DataFrame.from_dict(ib, orient="index", columns=["pnl", "low"]).reindex(na.index).fillna(0)
books = {"NA 1": na, "NA 1 + IB 1": pd.DataFrame({"pnl": na.pnl + ibdf.pnl, "low": na.low + ibdf.low}),
         "IB 1": ibdf, "NA 1 + IB 2": pd.DataFrame({"pnl": na.pnl + 2 * ibdf.pnl, "low": na.low + 2 * ibdf.low})}
dts = pd.to_datetime(na.index)
IS = [k for k in range(len(dts)) if dts[k] < pd.Timestamp(IS_END)]
OOS = [k for k in range(len(dts)) if dts[k] >= pd.Timestamp(IS_END)]
rows = []
for name, b in books.items():
    for keep in (0, 1000, 1500, 2000, 2500):
        a = evaluate(b.pnl.values, b.low.values, IS, keep); o = evaluate(b.pnl.values, b.low.values, OOS, keep)
        rows.append(dict(book=name, keep=keep, **{"IS_" + k: v for k, v in a.items()}, **{"OOS_" + k: v for k, v in o.items()}))
        print(f"{name:12} keep {keep:5}: IS pass {a['pass_eval']:5} payout {a['payout']:5} npay {a['avg_npay']:4} 5x {a['five']:4} EV ${a['ev']:5} | OOS pass {o['pass_eval']:5} payout {o['payout']:5} npay {o['avg_npay']:4} 5x {o['five']:4} EV ${o['ev']:5}", flush=True)
pd.DataFrame(rows).to_csv("prop_sim2.csv", index=False)
