"""Dininri 369 (spec: DININRI_369_FULL_SPEC.md) — full backtest + variant grid on 16 years of NQ/MNQ 1-minute data.
Grid: NQ 2010-06 → 2019 (user Databento NQ), MNQ 2020 → 2026-10 (Databento), 24 h session rows 18:00 → 16:59 NY (sess24 cache).
3-minute bars are clock-aligned (minute % 3 == 0), same as TradingView.

Rules as coded (spec section in brackets):
  bias  [4]  previous day's 12:00-12:45 high/low; touches tracked minute by minute from 12:45 prev day; last touch wins
             (low touched → LONG, high touched → SHORT; both in one minute → keep previous). No touch → no trade.
  window[5]  entries on 3-min bars that START between 09:30 and the window end (10:01 spec / 10:30 / 11:00).
  grid  [6]  marked candles 3, 6, 12, 24, 48 (+96) bars back from the live bar (= 9/18/36/72/144/288 min).
  level [7]  LONG: nearest of {high, body top} of the marked candles BELOW the live bar's open; SHORT mirrored.
             variants: 'both' (spec) / 'wick' only / 'body' only.
  order [8]  limit at that level, lives one 3-min bar; walked on 1-minute bars (fill = low ≤ level, or ≤ level − 1 tick strict).
  risk  [9]  fixed stop S points (spec 10); 1 unit = 5 contracts; result reported in R (= 5 × S points).
             variant 'scaled': S is defined at NQ 25,000 and scaled with price (10 pt in 2026 ≈ 1 pt in 2010).
  mgmt  [10] BE after +be×S (spec 1R, active from the next minute); partial 2 of 5 at +p×S (spec 5R); runner to the opposite
             bias level (spec) / fixed 5R / 10R / no target; flat 15:55.  Stop-first inside a minute; no target on the fill minute.
  limits[11] max N counted trades a day (BE closes don't count); one position at a time.
Costs per contract round trip: $0.35×2 commission = 0.35 pt, + 1 tick slippage on every stop / end-of-day market exit."""
import sys, os, itertools, time
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gapfb")]
import numpy as np, pandas as pd
from numba import njit
from multiprocessing import Pool
from sess24 import build, t2m

T930, LUN0, LUN1, EOD = t2m("09:30"), t2m("12:00"), t2m("12:45"), t2m("15:55")
GRIDS = {"369": np.array([3, 6, 12, 24, 48, 96]), "ctrl": np.array([2, 5, 10, 20, 40, 80])}   # control = non-369 offsets


def load():
    S = build(); d = pd.DatetimeIndex(np.r_[S["A"][0], S["B"][0]]); X = np.concatenate([S["A"][1], S["B"][1]]).astype(np.float64)
    prev_ok = np.r_[False, (d[1:] - d[:-1]).days <= 4]
    return d, X, prev_ok


@njit(cache=True)
def bias_table(X, prev_ok, nb):
    """bias at the start of each 3-min bar from 09:30 (nb bars): +1 long, -1 short, 0 none; plus lunch hi/lo."""
    n = X.shape[0]; B = np.zeros((n, nb), np.int64); LH = np.full(n, np.nan); LL = np.full(n, np.nan)
    for d in range(1, n):
        if not prev_ok[d]: continue
        P = X[d - 1]; lh = P[LUN0:LUN1, 1].max(); ll = P[LUN0:LUN1, 2].min(); LH[d] = lh; LL[d] = ll
        st = 0
        for m in range(LUN1, 1380):
            a = P[m, 2] <= ll; b = P[m, 1] >= lh
            if a and not b: st = 1
            elif b and not a: st = -1
        C = X[d]; k = 0
        for m in range(0, T930 + 3 * nb):
            if m >= T930 and (m - T930) % 3 == 0: B[d, k] = st; k += 1
            a = C[m, 2] <= ll; b = C[m, 1] >= lh
            if a and not b: st = 1
            elif b and not a: st = -1
    return B, LH, LL


@njit(cache=True)
def sim(X, BIAS, LH, LL, offs, nlev, S0, be, part, runner, wend, levmode, maxn, biasmode, thru, scaled):
    n = X.shape[0]; od = np.empty(4 * n, np.int64); oR = np.empty(4 * n); ob = np.empty(4 * n, np.int64); nt = 0
    for d in range(n):
        if np.isnan(LH[d]): continue
        C = X[d]; counted = 0; free_at = T930
        S = max(1.0, np.round(S0 * C[T930, 0] / 25000.0 * 4) / 4) if scaled else S0
        for k in range(wend):
            t0 = T930 + 3 * k
            if t0 < free_at or counted >= maxn: continue
            s = BIAS[d, k] * biasmode
            if s == 0: continue
            p = C[t0, 0]; L = np.nan
            for q in range(nlev):
                b0 = t0 - 3 * offs[q]
                if b0 < 0: continue
                o = C[b0, 0]; c = C[b0 + 2, 3]; h = max(C[b0, 1], C[b0 + 1, 1], C[b0 + 2, 1]); l = min(C[b0, 2], C[b0 + 1, 2], C[b0 + 2, 2])
                for j in range(2):
                    if s == 1:
                        v = h if j == 0 else max(o, c)
                        if (levmode == 1 and j == 1) or (levmode == 2 and j == 0): continue
                        if v < p and (np.isnan(L) or v > L): L = v
                    else:
                        v = l if j == 0 else min(o, c)
                        if (levmode == 1 and j == 1) or (levmode == 2 and j == 0): continue
                        if v > p and (np.isnan(L) or v < L): L = v
            if np.isnan(L): continue
            f = -1
            for m in range(t0, t0 + 3):
                if (C[m, 2] <= L - thru) if s == 1 else (C[m, 1] >= L + thru):
                    f = m; break
            if f < 0: continue
            e = L; stop = e - s * S
            if runner == 0:
                T = LH[d] if s == 1 else LL[d]
                if s * (T - e) < S: T = np.nan
            elif runner == 1: T = e + s * 5 * S
            elif runner == 2: T = e + s * 10 * S
            else: T = np.nan
            P1 = e + s * part * S if part > 0 else np.nan
            qty = 5.0; pnl = 0.0; slip = 0.0; parted = False; bearm = False; m = f; end = -1
            while True:
                lo = C[m, 2]; hi = C[m, 1]; op = C[m, 0]
                if (lo <= stop) if s == 1 else (hi >= stop):
                    px = (min(op, stop) if s == 1 else max(op, stop)) if m > f else stop
                    pnl += qty * s * (px - e); slip += qty * 0.25; end = m; break
                if m > f:
                    if (not parted) and not np.isnan(P1) and ((hi >= P1) if s == 1 else (lo <= P1)):
                        px = max(op, P1) if s == 1 else min(op, P1); pnl += 2 * s * (px - e); qty -= 2; parted = True
                    if not np.isnan(T) and ((hi >= T) if s == 1 else (lo <= T)):
                        px = max(op, T) if s == 1 else min(op, T); pnl += qty * s * (px - e); qty = 0; end = m; break
                if bearm: stop = e if s == 1 else e
                if be > 0 and ((hi >= e + be * S) if s == 1 else (lo <= e - be * S)): bearm = True
                if m >= EOD - 1:
                    pnl += qty * s * (C[m, 3] - e); slip += qty * 0.25; end = m; break
                m += 1
            R = (pnl - 5 * 0.35 - slip) / (5 * S)
            is_be = (not parted) and abs(pnl) < 1e-9 and bearm
            if not is_be: counted += 1
            od[nt] = d; oR[nt] = R; ob[nt] = 1 if is_be else 0; nt += 1
            free_at = end + 1
    return od[:nt], oR[:nt], ob[:nt]


GRID = dict(S=(5.0, 7.5, 10.0, 15.0, 20.0), be=(0.0, 1.0, 2.0), part=(0.0, 3.0, 5.0), runner=(0, 1, 2, 3),
            wend=(11, 20, 30), levmode=(0, 1, 2), maxn=(1, 3), nlev=(5, 6), scaled=(0, 1))
RUNNER = {0: "opposite bias", 1: "5R", 2: "10R", 3: "no target (15:55)"}
LEV = {0: "wick or body (spec)", 1: "wick only", 2: "body only"}
WEND = {11: "10:01", 20: "10:30", 30: "11:00"}
SPEC = dict(S=10.0, be=1.0, part=5.0, runner=0, wend=11, levmode=0, maxn=3, nlev=5, scaled=0)

_G = {}


def init():
    d, X, ok = load(); B, LH, LL = bias_table(X, ok, 30); _G.update(d=d, X=X, B=B, LH=LH, LL=LL, yr=d.year.values)


def stats(yr, R, isbe):
    out = {}
    for nm, m in (("tr", yr <= 2019), ("va", (yr >= 2020) & (yr <= 2023)), ("te", yr >= 2024), ("all", yr > 0)):
        r = R[m]; ny = len(np.unique(yr[m])) or 1
        out[nm + "_n"] = len(r); out[nm + "_yr"] = len(r) / ny; out[nm + "_win"] = 100 * (r > 0.05).mean() if len(r) else np.nan
        out[nm + "_be"] = 100 * isbe[m].mean() if len(r) else np.nan
        out[nm + "_R"] = r.mean() if len(r) else np.nan; out[nm + "_tot"] = r.sum()
        out[nm + "_t"] = r.mean() / r.std() * np.sqrt(len(r)) if len(r) > 2 and r.std() > 0 else np.nan
        eq = np.cumsum(r); out[nm + "_dd"] = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max() if len(r) else 0
        w = r[r > 0.05]; l = r[r < -0.05]; out[nm + "_avgW"] = w.mean() if len(w) else np.nan; out[nm + "_avgL"] = l.mean() if len(l) else np.nan
    for Y in range(2010, 2027): out[f"y{Y}"] = R[yr == Y].sum()
    out["yrs_pos"] = int(sum(R[yr == Y].sum() > 0 for Y in np.unique(yr)))
    return out


def one(cfg, grid="369", biasmode=1, thru=0.0):
    od, R, be = sim(_G["X"], _G["B"], _G["LH"], _G["LL"], GRIDS[grid], cfg["nlev"], cfg["S"], cfg["be"], cfg["part"], cfg["runner"],
                    cfg["wend"], cfg["levmode"], cfg["maxn"], biasmode, thru, cfg["scaled"])
    return od, R, be


def job(chunk):
    if not _G: init()
    rows = []
    for cfg, grid, bm in chunk:
        od, R, be = one(cfg, grid, bm); rows.append(dict(cfg, grid=grid, bias=("spec" if bm == 1 else "reversed"), **stats(_G["yr"][od], R, be.astype(bool))))
    return rows


if __name__ == "__main__":
    t0 = time.time()
    tasks = [(dict(zip(GRID, v)), g, bm) for v in itertools.product(*GRID.values()) for g in GRIDS for bm in (1, -1)]
    print(len(tasks), "runs", flush=True)
    chunks = [tasks[i::32] for i in range(32)]; out = []
    with Pool(4) as P:
        for rows in P.imap_unordered(job, chunks):
            out += rows; print(len(out), f"{time.time() - t0:.0f}s", flush=True)
    G = pd.DataFrame(out)
    G.to_csv("/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/dininri_grid.csv.gz", index=False)
    print("done", len(G))
