"""QUARTER SEQUENCE MAP - an original time x price state model on NQ (1-minute, NY time, 2012-2026, cost 1.3 bp per trade).
Every 90-minute quarter gets a state:
   TIME : session (Asia 18-24, London 00-06, NY AM 06-12, NY PM 12-18) x quarter inside the session (1..4)
   PRICE: band of the quarter's opening price inside the PREVIOUS session's range cut in four
          (below / Q1 / Q2 / Q3 / Q4 / above)  +  side of the reference (session open for Q1, true open = Q2 open after)
   SEQ  : the up/down sequence of the quarters already finished in this session (0..3 signs)
Model A = time x price (192 states); Model B = time x price x sequence (720 states).
Learning: on 2012-19 the mean forward return of the next quarter for each state. A state is traded (in the sign of its mean)
only if its 2012-19 t-stat beats the Bonferroni line for the number of states (A: |t|>3.5, B: |t|>3.8), plus a looser
|t|>2.5 version. Out of sample 2020-26: enter at the quarter open, exit at the quarter close.
Placebo: the whole procedure on time grids shifted by 1/8..7/8 of a quarter (does the real clock matter?).
Also the same at day level (6h quarters, previous day's range) as a second scale."""
import os as _os; DATA = _os.path.join(_os.path.expanduser(_os.environ.get("EDGE_DATA", "~/edge-data")), "")  # raw data + caches (set EDGE_DATA to move it)
import sys, os, math, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
from quarters import T0, O, Hh, Lw, C, OK, N, ANCH, BP


def rows(block, shift_q):
    """block 360 (session level) or 1440 (day level); quarters of block/4; shift in quarters (0..1)"""
    q = block // 4; start0 = ANCH + int(shift_q * q); out = []
    starts = range(start0 + block, N - block, block)
    for s in starts:
        ps = s - block
        if OK[ps:s].mean() < 0.6 or OK[s:s + block].mean() < 0.6: continue
        PH, PL = Hh[ps:s].max(), Lw[ps:s].min(); rg = PH - PL
        if rg <= 0: continue
        sess = ((s - ANCH) // block) % (1440 // block) if block < 1440 else 0
        signs = []; ref = O[s]
        for k in range(4):
            a, b = s + k * q, s + (k + 1) * q
            if OK[a:b].mean() < 0.5: break
            if k == 1: ref = O[a]
            p = O[a]; band = int(np.clip(np.floor(4 * (p - PL) / rg) + 1, 0, 5)); side = int(p >= ref)
            r = (C[b - 1] / p - 1) * 1e4
            day = pd.Timestamp((T0 + a) * 60, unit="s")
            out.append((day, sess, k, band, side, "".join("u" if x > 0 else "d" for x in signs), r))
            signs.append(C[b - 1] - O[a])
    return pd.DataFrame(out, columns=["t", "sess", "k", "band", "side", "seq", "r"])


def evaluate(R, cols, thr):
    R = R.copy(); R["state"] = R[cols].astype(str).agg("|".join, axis=1); Y = R.t.dt.year
    I = R[Y <= 2019]; g = I.groupby("state").r.agg(["mean", "std", "count"]); g = g[g["count"] >= 30]
    g["t"] = g["mean"] / g["std"] * np.sqrt(g["count"]); pick = g[g.t.abs() > thr]
    sgn = np.sign(pick["mean"]).to_dict()
    R["pnl"] = R.state.map(sgn).fillna(0) * R.r - R.state.map(sgn).abs().fillna(0) * BP
    tr = R[R.state.isin(sgn)]; d = tr.groupby(tr.t.dt.normalize()).pnl.sum()
    Yd = d.index.year; i, o = d[Yd <= 2019], d[Yd >= 2020]
    tt = lambda x: x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0
    to = tr[tr.t.dt.year >= 2020].pnl
    return dict(states=len(g), picked=len(pick), trades_yr=len(tr) / 14.8, IS_bp_day=i.mean(), IS_t=tt(i), OOS_bp_day=o.mean(),
                OOS_t=tt(o), OOS_win=100 * (to > 0).mean() if len(to) else np.nan,
                OOS_rr=(to[to > 0].mean() / -to[to < 0].mean()) if len(to) else np.nan,
                OOS_pos_yrs=f"{(o.groupby(o.index.year).sum() > 0).sum()}/7" if len(o) else "-"), pick


if __name__ == "__main__":
    pd.set_option("display.width", 250); res = []
    for block, lab in ((360, "session x 90min"), (1440, "day x 6h")):
        for shift in [0] + [x / 8 for x in range(1, 8)]:
            R = rows(block, shift)
            for model, cols, thr in (("A time x price", ["sess", "k", "band", "side"], 3.5), ("A loose", ["sess", "k", "band", "side"], 2.5),
                                     ("B +sequence", ["sess", "k", "band", "side", "seq"], 3.8), ("B loose", ["sess", "k", "band", "side", "seq"], 2.5)):
                st, pick = evaluate(R, cols, thr); st.update(level=lab, shift=shift, model=model); res.append(st)
                if shift == 0 and len(pick): print(f"\n{lab} {model}: picked states (2012-19):\n", pick.round(2).to_string())
            print(lab, "shift", shift, "done", flush=True)
    T = pd.DataFrame(res)
    real = T[T["shift"] == 0]; print("\n===== REAL CLOCK\n", real.round(2).to_string(index=False))
    pl = T[T["shift"] > 0].groupby(["level", "model"]).OOS_t.agg(["median", "max"]).round(2)
    print("\n===== shifted-clock placebo, OOS t (median / max over 7 shifts)\n", pl.to_string())
    T.to_csv(DATA + "sequence.csv", index=False)
