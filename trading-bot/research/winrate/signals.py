"""Signals with a real directional edge, then payoff shaping (small target / wider stop) for a high win rate.
Scale = typical daily move: 14-day mean of |close(15:59)/open(09:30) − 1| × price (no look-ahead)."""
import sys; sys.path.insert(0, "..")
import pickle, numpy as np, pandas as pd
from engine import S, walk, COST_PTS, IS_END
D = pickle.load(open(S + "D.pkl", "rb")); N = len(D.days)
move = np.abs(D.c / D.o[:, :1] - 1)
day_sig = pd.Series(move[:, 389]).rolling(14).mean().shift().values      # previous 14 days only
pc = np.r_[np.nan, D.c[:-1, 389]]; ppc = np.r_[np.nan, np.nan, D.c[:-2, 389]]
valid = ~(D.roll | (D.prev_gap_days > 4))
marks = [29 + 30 * j for j in range(12)]

def sig_na_first():
    out = []
    for i in range(14, N):
        if not valid[i]: continue
        sig = move[i - 14:i].mean(0); o0 = D.o[i, 0]
        ub, lb = max(o0, pc[i]) * (1 + sig), min(o0, pc[i]) * (1 - sig)
        for k in marks:
            cc = D.c[i, k]
            if cc > ub[k] or cc < lb[k]:
                out.append((i, k + 1, 1 if cc > ub[k] else -1, None)); break
    return out

def sig_na_fvg(window=60):
    """After the first Noise-Area break, enter on the first retrace into a 1-min FVG in the trend direction."""
    out = []
    for i, k0, s, _ in sig_na_first():
        h, l = D.h[i], D.l[i]
        gap = None
        for j in range(k0 + 2, min(k0 + window, 388)):
            if gap is None:
                if s == 1 and h[j - 2] < l[j]: gap = l[j]          # bullish FVG top
                if s == -1 and l[j - 2] > h[j]: gap = h[j]         # bearish FVG bottom
                continue
            if (l[j] <= gap) if s == 1 else (h[j] >= gap):
                out.append((i, j, s, gap)); break
    return out

def sig_afternoon():
    out = []
    r = D.c[:, 329] / pc - 1
    sd = pd.Series(r).rolling(20).std().shift().values
    for i in range(N):
        if valid[i] and not np.isnan(sd[i]) and abs(r[i]) > sd[i]:
            out.append((i, 330, 1 if r[i] > 0 else -1, None))
    return out

def sig_rebound():
    rp = pc / ppc - 1
    return [(i, 0, 1, None) for i in range(N) if valid[i] and i >= 2 and not D.roll[i - 1] and rp[i] < -0.01]

def sig_gap(lo=0.001, hi=0.003):
    g = D.o[:, 0] / pc - 1
    return [(i, 0, -1 if g[i] > 0 else 1, None) for i in range(N) if valid[i] and lo <= abs(g[i]) <= hi]

def sig_tom():
    dts = pd.to_datetime(D.days); out = []
    for i in range(N):
        last = i + 1 < N and dts[i + 1].month != dts[i].month
        first3 = i >= 3 and (dts[i].month != dts[i - 1].month or dts[i].month != dts[i - 2].month or dts[i].month != dts[i - 3].month)
        if last or first3: out.append((i, 0, 1, None))
    return out

SIGNALS = {"Noise-Area first break": sig_na_first, "Noise-Area + FVG retrace": sig_na_fvg, "Afternoon momentum 15:00": sig_afternoon,
           "Rebound after −1% day": sig_rebound, "Small gap fade 0.1–0.3%": sig_gap, "Turn of month": sig_tom}

def bracket(sigs, a, b, last=384):
    rows = []
    for i, j, s, lim in sigs:
        if np.isnan(day_sig[i]) or j > last: continue
        e = lim if lim is not None else D.o[i, j]
        sc = day_sig[i] * e
        tp = e + s * a * sc if a else None
        sl = e - s * b * sc if b else None
        px, _, _ = walk(D.o[i], D.h[i], D.l[i], D.c[i], j, s, e, sl, tp, last, at_open=lim is None)
        rows.append((D.days[i], (px - e) * s - COST_PTS))
    return pd.DataFrame(rows, columns=["date", "pts"])

if __name__ == "__main__":
    res = []
    for name, fn in SIGNALS.items():
        sg = fn()
        for a in (None, 0.15, 0.25, 0.4, 0.6, 1.0):
            for b in (None, 0.5, 1.0, 1.5, 2.5):
                t = bracket(sg, a, b)
                if len(t) < 50: continue
                y = pd.to_datetime(t.date); isd = y < IS_END; p = t.pts
                res.append(dict(signal=name, tp=a, sl=b, n=len(t), win=100 * (p > 0).mean(), avg=2 * p.mean(),
                                IS_win=100 * (p[isd] > 0).mean(), IS_avg=2 * p[isd].mean(), OOS_win=100 * (p[~isd] > 0).mean(),
                                OOS_avg=2 * p[~isd].mean(), yrs=int((p.groupby(y.dt.year).sum() > 0).sum()),
                                maxdd=2 * (p.cumsum() - p.cumsum().cummax()).min()))
        print(name, "done", len(sg), "signals", flush=True)
    r = pd.DataFrame(res).round(1); r.to_csv("winrate_grid.csv", index=False)
    # IS-only selection: best IS avg among IS win ≥ 70 %
    sel = r[r.IS_win >= 70].sort_values("IS_avg", ascending=False).groupby("signal").head(2)
    print("\nIS-selected (IS win ≥ 70 %, best IS avg), with OOS:\n", sel.to_string(index=False))
    print("\nNo-bracket baselines:\n", r[r.tp.isna() & r.sl.isna()].to_string(index=False))
