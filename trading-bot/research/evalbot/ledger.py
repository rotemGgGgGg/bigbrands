"""Trade ledger for the eval engine: every trade of the five 2020+ edges with entry/exit minute (minutes from 09:30; negative =
pre-market), net P&L per MNQ in points (2.25 pt costs) and intraday MAE in points. MNQ 1-minute, Databento 2020-01 → 2026-10.
Edges: WVB (Williams volatility breakout), NA (Noise-Area first break → close), PF (Pre-Open Fade 76 % version),
PM (Afternoon momentum 15:00 → close), FVG (NA-FVG 92 % variant: TP 0.10σ / SL 1.5σ)."""
import sys, os; H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(H, ".."), os.path.join(H, "../influencers"), os.path.join(H, "../winrate"), os.path.join(H, "../hunt")]
import numpy as np, pandas as pd
from engine import walk, S
from lib import o, h, l, c, N, DAYS, VALID, okprev, RANGE, DO, SIG, stop_fill, TICK
import signals as W
COST = 2.25
OUT = os.path.join(H, "ledger.pkl")
def run(i, j0, side, e, stop, tgt, at_open=True, last=384):
    px, jx, _ = walk(o[i], h[i], l[i], c[i], j0, side, e, stop, tgt, last, at_open=at_open)
    seg = slice(j0, jx + 1); mae = (l[i, seg].min() - e) if side == 1 else (e - h[i, seg].max())
    return side * (px - e) - COST, min(mae, 0.0), jx
def build():
    rows = []
    for i in range(1, N):                                   # WVB
        if not okprev[i]: continue
        r_ = RANGE[i - 1]; a, b = stop_fill(i, 1, 384, DO[i] + 0.6 * r_, 1), stop_fill(i, 1, 384, DO[i] - 0.6 * r_, -1)
        f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
        if f:
            (m, px), s = f; pts, mae, jx = run(i, m, s, px, px - s * 0.5 * r_, None, at_open=False); rows.append(("WVB", i, m, jx, s, pts, mae))
    for i, k0, s, _ in W.sig_na_first():                    # NA
        pts, mae, jx = run(i, k0, s, o[i, k0], None, None); rows.append(("NA", i, k0, jx, s, pts, mae))
    for i, j, s, _ in W.sig_afternoon():                    # PM
        pts, mae, jx = run(i, j, s, o[i, j], None, None); rows.append(("PM", i, j, jx, s, pts, mae))
    for i, j, s, gap in W.sig_na_fvg():                     # FVG 92 %: conservative fill = trade-through by a tick
        if np.isnan(W.day_sig[i]): continue
        jj = next((x for x in range(j, 384) if ((l[i, x] <= gap - TICK) if s == 1 else (h[i, x] >= gap + TICK))), None)
        if jj is None: continue
        sc = W.day_sig[i] * o[i, 0]; pts, mae, jx = run(i, jj, s, gap, gap - s * 1.5 * sc, gap + s * 0.10 * sc, at_open=False)
        rows.append(("FVG", i, jj, jx, s, pts, mae))
    from prefade import pre_move, DAYS as PD                 # PF: 09:00 entry on the 24h frame, exit 13:00 / bracket
    s_, z = pre_move(60); dmap = {d: k for k, d in enumerate(pd.to_datetime(DAYS))}
    for d in z[z.abs() > 2].index:
        i = dmap.get(pd.Timestamp(d.date()))
        if i is None: continue
        gm, oo, hh, ll, cc = PD[d]; j0 = np.nonzero(gm >= 540)[0][0]; side = -int(np.sign(s_[d])); size = abs(s_[d]); e = oo[j0]
        tp, sl = e + side * 0.5 * size, e - side * 1.0 * size; px = None; jx = j0
        for k in range(j0, len(gm)):
            jx = k
            if gm[k] >= 780: px = oo[k]; break
            if (ll[k] <= sl) if side == 1 else (hh[k] >= sl): px = (min(oo[k], sl) if side == 1 else max(oo[k], sl)); break
            if (hh[k] >= tp + TICK) if side == 1 else (ll[k] <= tp - TICK): px = tp; break
        if px is None: px = cc[-1]
        mae = min(((ll[j0:jx + 1].min() - e) if side == 1 else (e - hh[j0:jx + 1].max())), 0.0)
        rows.append(("PF", i, int(gm[j0] - 570), int(gm[jx] - 570), side, side * (px - e) - COST, mae))
    L = pd.DataFrame(rows, columns=["edge", "i", "t_in", "t_out", "side", "pts", "mae"])
    L["date"] = pd.to_datetime([DAYS[k] for k in L.i]); L.to_pickle(OUT); return L
def load():
    return pd.read_pickle(OUT) if os.path.exists(OUT) else build()
if __name__ == "__main__":
    L = load()
    print(L.groupby("edge").agg(n=("pts", "size"), win=("pts", lambda x: round(100 * (x > 0).mean(), 1)), usd=("pts", lambda x: round(2 * x.mean(), 1)),
                                worst_mae_usd=("mae", lambda x: round(2 * x.min()))).to_string())
