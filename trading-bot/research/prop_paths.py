"""Per-day P&L paths (1 MNQ contract, $) for the candidate strategies, minute by minute, costs included.
Output: dict name -> DataFrame(date, pnl, low) where low = worst intraday open+closed P&L that day."""
import pickle, numpy as np, pandas as pd
from engine import S, COST_PTS, PT_USD

D = pickle.load(open(S + "D.pkl", "rb"))

def path_from_positions(i, pos):
    """pos[k] = position held during minute k (entered at o[k], exited at o[k+1] or c[389])."""
    o, c = D.o[i], D.c[i]
    nxt = np.r_[o[1:], c[389]]
    pnl_min = pos * (nxt - o)                         # P&L earned during each minute (open→next open)
    # intraday low using bar lows/highs while in position
    low_k = np.where(pos > 0, D.l[i] - o, np.where(pos < 0, o - D.h[i], 0.0)) * np.abs(pos)
    changes = np.abs(np.diff(np.r_[0, pos, 0])).sum() / 2      # round trips (a reversal counts 1 exit + 1 entry)
    cum = np.cumsum(pnl_min)
    before = np.r_[0, cum[:-1]]
    low = min(0.0, (before + low_k).min())
    return cum[-1] * PT_USD - changes * COST_PTS * PT_USD, low * PT_USD - changes * COST_PTS * PT_USD

def noise_area(look=14):
    move = np.abs(D.c / D.o[:, :1] - 1)
    marks = [29 + 30 * j for j in range(12)]
    out = []
    for i in range(look, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4:
            out.append((D.days[i], 0.0, 0.0)); continue
        sig = move[i - look:i].mean(0)
        o0, pc = D.o[i, 0], D.c[i - 1, 389]
        ub, lb = max(o0, pc) * (1 + sig), min(o0, pc) * (1 - sig)
        pos = np.zeros(390); p = 0
        for k in marks:
            c = D.c[i, k]; want = p
            if p == 1 and c < lb[k]: want = 0
            if p == -1 and c > ub[k]: want = 0
            if c > ub[k]: want = 1
            elif c < lb[k]: want = -1
            p = want
            nxt = marks[marks.index(k) + 1] if k != marks[-1] else 389
            pos[k + 1: nxt + 1 if k != marks[-1] else 390] = p
        pnl, low = path_from_positions(i, pos)
        out.append((D.days[i], pnl, low))
    return pd.DataFrame(out, columns=["date", "pnl", "low"])

if __name__ == "__main__":
    na = noise_area()
    na.to_pickle(S + "path_na.pkl")
    t = na[na.pnl != 0]
    print(len(na), "days,", len(t), "active; total $", round(na.pnl.sum()), "per MNQ; worst intraday low $", round(na.low.min()),
          "; best day $", round(na.pnl.max()), "worst day $", round(na.pnl.min()))
