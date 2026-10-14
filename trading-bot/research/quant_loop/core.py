"""Quant loop core: data, splits, 2R-vs-1R first-passage outcomes, logging.

Data: Databento MNQ.c.0 1-minute OHLCV, RTH 09:30–15:59 ET on a 390-minute grid, 2020-01 → 2026-10-06 (1,660 days).
No order book / tick / true delta exists in this project — anything "delta" is an OHLCV approximation and labelled so.
Splits (chronological): TRAIN < 2024-01-01 · VAL 2024-01-01 → 2025-06-30 · TEST ≥ 2025-07-01 (opened once, at the end).
Note: earlier research in this repo already looked at 2024–2026 for other ideas, so TEST is not perfectly virgin.
Execution: entry at the open of minute j (market) or at a resting limit (filled only if price trades through by 1 tick);
stop/target walked minute by minute, stop wins ties, flat at 15:55. Costs: $1.50 commission + 1 tick slippage each side
= 1.25 pt per MNQ round trip; stress = +1 pt.
"""
import os, sys, csv, json, time, pickle, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "../hunt")]
from feat import load

F, D = load()
N = len(D.days)
o, h, l, c, v = D.o, D.h, D.l, D.c, D.v
DAYS = pd.to_datetime(D.days)
SPLIT = np.where(DAYS < "2024-01-01", 0, np.where(DAYS < "2025-07-01", 1, 2))   # 0 train, 1 val, 2 test
SIG = F.sig.values                       # 14-day mean |close/open−1| (previous days only)
VALID = F.valid.values & ~np.isnan(SIG)
COST, STRESS, TICK, LAST = 1.25, 1.0, 0.25, 384
RR = 2.0

def first_passage(i, j, side, e, stop_pts, rr=RR, at_open=True):
    """Return (R, exit_minute). Target rr·stop, stop 1·stop. Ties → stop. Entry bar: only the stop counts if not at_open."""
    tp = e + side * rr * stop_pts; sl = e - side * stop_pts
    hh, ll, oo = h[i, j:LAST + 1], l[i, j:LAST + 1], o[i, j:LAST + 1]
    if side == 1:
        hit_s = ll <= sl; hit_t = hh >= tp + TICK
    else:
        hit_s = hh >= sl; hit_t = ll <= tp - TICK
    if not at_open: hit_t = hit_t.copy(); hit_t[0] = False
    ks = int(np.argmax(hit_s)) if hit_s.any() else 10**6
    kt = int(np.argmax(hit_t)) if hit_t.any() else 10**6
    if ks == 10**6 and kt == 10**6:
        px = c[i, LAST]; k = LAST - j
    elif ks <= kt:
        px = (min(oo[ks], sl) if side == 1 else max(oo[ks], sl)) if (ks > 0 or at_open) else sl; k = ks
    else:
        px = tp; k = kt
    return (side * (px - e) - COST) / stop_pts, j + k

LOG = os.path.join(HERE, "experiment_results.csv")
FIELDS = ["exp_id", "family", "config", "split", "n", "win", "avg_win_R", "avg_loss_R", "realized_rr", "exp_R", "exp_R_stress",
          "pf", "ci_win_lo", "ci_win_hi", "t", "status", "reason", "code_ver", "ts"]
CODE_VER = hashlib.md5(open(__file__, "rb").read()).hexdigest()[:8]

def wilson(k, n, z=1.96):
    if n == 0: return (np.nan, np.nan)
    p = k / n; d = 1 + z * z / n; m = p + z * z / (2 * n); s = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((m - s) / d, (m + s) / d)

def metrics(R, stop_pts=None):
    R = np.asarray(R, float); n = len(R)
    if n == 0: return dict(n=0)
    w, lo = R[R > 0], R[R <= 0]
    ci = wilson((R > 0).sum(), n)
    st = R - (STRESS / np.asarray(stop_pts) if stop_pts is not None else 0)
    return dict(n=n, win=round(100 * (R > 0).mean(), 1), avg_win_R=round(w.mean(), 3) if len(w) else 0,
                avg_loss_R=round(lo.mean(), 3) if len(lo) else 0,
                realized_rr=round(w.mean() / -lo.mean(), 2) if len(w) and len(lo) and lo.mean() < 0 else np.nan,
                exp_R=round(R.mean(), 3), exp_R_stress=round(st.mean(), 3),
                pf=round(w.sum() / -lo.sum(), 2) if len(lo) and lo.sum() < 0 else np.nan,
                ci_win_lo=round(100 * ci[0], 1), ci_win_hi=round(100 * ci[1], 1),
                t=round(R.mean() / R.std(ddof=1) * np.sqrt(n), 2) if n > 2 and R.std() > 0 else 0)

class Logger:
    """One CSV per worker (logs/<name>.csv) — merged into experiment_results.csv by merge_logs()."""
    def __init__(self, name="main"):
        os.makedirs(os.path.join(HERE, "logs"), exist_ok=True)
        path = os.path.join(HERE, "logs", f"{name}.csv"); new = not os.path.exists(path)
        self.f = open(path, "a", newline=""); self.w = csv.DictWriter(self.f, FIELDS)
        if new: self.w.writeheader()
        self.count = 0
    def log(self, family, config, split, m, status="", reason=""):
        self.count += 1
        row = dict(exp_id=f"{family}-{self.count}-{int(time.time()*1000)%10**8}", family=family, config=json.dumps(config, sort_keys=True),
                   split=split, status=status, reason=reason, code_ver=CODE_VER, ts=time.strftime("%Y-%m-%d %H:%M"))
        row.update({k: m.get(k, "") for k in FIELDS if k in m})
        self.w.writerow(row)
    def close(self): self.f.close()

def merge_logs():
    import glob
    fs = sorted(glob.glob(os.path.join(HERE, "logs", "*.csv")))
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True) if fs else pd.DataFrame(columns=FIELDS)
    df.to_csv(LOG, index=False); return df
