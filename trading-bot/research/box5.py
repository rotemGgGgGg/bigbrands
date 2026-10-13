"""First 5-minute box (09:30–09:35). Break → trade in the break direction. Grid over entry / stop / target.
entry: 'close' = 5-min candle closes outside the box, enter at that close;
       'touch' = stop order at the box edge (+1 tick), enter on the touch.
stop:  'wick' = other extreme of the breakout candle (long: its low, short: its high)
       'body' = open of the breakout candle
       'box'  = other side of the box
       'mid'  = middle of the box
target: R multiple of the stop distance. One trade a day, entries until `cut`, flat 15:55."""
import pickle, sys, json
import numpy as np, pandas as pd
from engine import S, summarize, walk, COST_PTS, IS_END, PT_USD
D = pickle.load(open(S + "D.pkl", "rb"))

def run(entry="close", stop="wick", tgt=0.2, cut=11 * 60):
    rows = []
    last5 = (cut - 570) // 5
    for i in range(len(D.days)):
        o5, h5, l5, c5, _ = D.bars(i, 5)
        hi, lo = h5[0], l5[0]
        if hi - lo <= 0: continue
        if entry == "close":
            k = next((k for k in range(1, last5) if c5[k] > hi or c5[k] < lo), None)
            if k is None: continue
            side = 1 if c5[k] > hi else -1
            e, j0, at_open = c5[k], (k + 1) * 5, True
            bo, bh, bl = o5[k], h5[k], l5[k]
        else:
            j = next((j for j in range(5, cut - 570) if D.h[i, j] >= hi + .25 or D.l[i, j] <= lo - .25), None)
            if j is None: continue
            if D.h[i, j] >= hi + .25 and D.l[i, j] <= lo - .25: continue
            side = 1 if D.h[i, j] >= hi + .25 else -1
            lvl = hi + .25 if side == 1 else lo - .25
            e = max(D.o[i, j], lvl) if side == 1 else min(D.o[i, j], lvl)
            j0, at_open = j, False
            k = j // 5
            bo, bh, bl = o5[k], h5[k], l5[k]           # candle in progress (stop known only at its close → use box/mid for touch)
        if stop == "wick": sp = bl if side == 1 else bh
        elif stop == "body": sp = bo
        elif stop == "box": sp = lo if side == 1 else hi
        else: sp = (hi + lo) / 2
        risk = (e - sp) * side
        if risk < 1: continue
        px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], j0, side, e, sp, e + side * tgt * risk, 384, at_open=at_open)
        rows.append((D.days[i], side, (px - e) * side, risk))
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])

def lucid(tr, risk_usd=200, target=3000.0, dd=2000.0):
    r = (tr.pts - COST_PTS) / tr.risk
    daily = (r * risk_usd).groupby(tr.date).sum()
    days = list(daily.index); res = []
    for i in range(len(days)):
        bal = peak = 0.0
        for d in days[i:]:
            bal += daily[d]
            if bal <= peak - dd: res.append(0); break
            if bal >= target: res.append(1); break
            peak = max(peak, bal)
    return round(100 * np.mean(res)) if res else None

out = []
for entry, stops in (("close", ("wick", "body", "box", "mid")), ("touch", ("box", "mid"))):
    for stop in stops:
        for tgt in (0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0):
            tr = run(entry, stop, tgt)
            s = summarize(f"{entry}/{stop}/{tgt}R", tr)
            r = (tr.pts - COST_PTS) / tr.risk
            g = (tr.pts > 0).mean() * 100
            y = pd.to_datetime(tr.date) < IS_END
            row = dict(entry=entry, stop=stop, tgt=tgt, n=s["n"], win_gross=round(g, 1), win_net=s["win"],
                       avgR_net=round(r.mean(), 3), IS_R=round(r[y].mean(), 3), OOS_R=round(r[~y].mean(), 3),
                       med_risk_pts=round(tr.risk.median(), 1), cost_share=round(COST_PTS / (tgt * tr.risk.median()) * 100),
                       pf=s["pf"], yrs=s["yrs_pos"], maxDD_R=round((r.cumsum() - r.cumsum().cummax()).min(), 1),
                       streak=int(max((len(x) for x in "".join("w" if v > 0 else " " for v in r).split()), default=0)),
                       lucid=lucid(tr))
            out.append(row); print(json.dumps(row), flush=True)
pd.DataFrame(out).to_csv("box5_grid.csv", index=False); print("DONE")
