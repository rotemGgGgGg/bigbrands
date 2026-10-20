"""LICO model (Instagram reel by ksbtrades, 2026-10) on 16 years of NQ 1-minute data.
Video rules: before 09:30 mark draws on liquidity (session highs/lows + swing highs/lows, 15-minute chart); between 09:30 and
10:30 NY wait for a liquidity Sweep of one of them, then an IFVG / CISD on the 1-minute chart in the opposite direction;
stop beyond the sweep extreme, target the opposite liquidity (LICO = Liquidity sweep, IFVG, CISD, market Open).
Mechanical version tested here:
  levels  : Asia 18:00-23:59, London 02:00-04:59, overnight 18:00-09:29, prior-day RTH high/low, 15-min fractal swings
            (2 bars each side) of the overnight; only levels still untouched at 09:29 count.
  sweep   : 09:30-10:30, first 1-min bar trading through a valid level.
  CISD    : close beyond the open of the run of opposite-colour candles that delivered price into the sweep extreme.
  IFVG    : (optional) a close beyond the far edge of a fair-value gap created inside that leg.
  entry   : next bar open; stop = sweep extreme ∓ 1 tick; target = 'dol' (nearest opposite valid level ≥ 1R away),
            'origin' (extreme of the move from 09:30 into the sweep), or fixed 2R / 3R; time exit 15:59. One trade per day.
Costs max(2.25 pt × price/17000, 0.75 pt) per round trip, stop-first when stop and target share a bar, no look-ahead."""
import sys, itertools; sys.path[:0] = ["../gapfb", "..", "../longhist"]
import numpy as np, pandas as pd
from sess24 import build, t2m

T930, T1030, TEX = t2m("09:30"), t2m("10:30"), t2m("15:59")
RTH0, RTH1 = t2m("09:30"), t2m("15:59")


def levels(X, i, prev_ok):
    """Pre-09:30 liquidity of day i → (highs, lows) still untouched at 09:29."""
    o, h, l, c = (X[i, :, k] for k in range(4))
    cand = []                                                  # (price, side, formed_at)
    for a, b in ((0, 360), (480, 660), (0, T930)):
        j = a + int(np.argmax(h[a:b])); cand.append((h[j], 1, j))
        j = a + int(np.argmin(l[a:b])); cand.append((l[j], -1, j))
    if prev_ok:
        P = X[i - 1]; cand += [(P[RTH0:RTH1 + 1, 1].max(), 1, -1), (P[RTH0:RTH1 + 1, 2].min(), -1, -1)]
    H15 = h[:T930].reshape(-1, 15).max(1); L15 = l[:T930].reshape(-1, 15).min(1)
    for k in range(2, len(H15) - 2):
        if H15[k] > H15[k - 2:k].max() and H15[k] > H15[k + 1:k + 3].max(): cand.append((H15[k], 1, 15 * k + 14))
        if L15[k] < L15[k - 2:k].min() and L15[k] < L15[k + 1:k + 3].min(): cand.append((L15[k], -1, 15 * k + 14))
    hi, lo = [], []
    for p, s, t in cand:
        seg = slice(t + 1, T930)
        if s == 1 and (t + 1 >= T930 or h[seg].max() < p): hi.append(p)
        if s == -1 and (t + 1 >= T930 or l[seg].min() > p): lo.append(p)
    return np.unique(hi), np.unique(lo)


def day(X, i, prev_ok, target, ifvg, minstop):
    o, h, l, c, a = (X[i, :, k].astype(float) for k in range(5))
    hi, lo = levels(X, i, prev_ok)
    st = {}                                                    # side → state after a sweep (side = trade direction)
    for k in range(T930, T1030 + 1):
        if 1 not in st and len(lo) and l[k] < lo.max():        # swept a low → look for a long
            st[1] = dict(k0=k, ext=k)
        if -1 not in st and len(hi) and h[k] > hi.min():       # swept a high → look for a short
            st[-1] = dict(k0=k, ext=k)
        for s, S in st.items():
            if (l[k] < l[S["ext"]]) if s == 1 else (h[k] > h[S["ext"]]): S["ext"] = k
            e = S["ext"]
            if k <= e: continue
            j = e if ((c[e] < o[e]) if s == 1 else (c[e] > o[e])) else e - 1
            run0 = j
            while run0 - 1 >= T930 - 60 and ((c[run0 - 1] < o[run0 - 1]) if s == 1 else (c[run0 - 1] > o[run0 - 1])): run0 -= 1
            if not ((c[j] < o[j]) if s == 1 else (c[j] > o[j])): continue
            cisd = o[run0]
            if not ((c[k] > cisd) if s == 1 else (c[k] < cisd)): continue
            if ifvg:                                           # FVG created inside the leg, closed through now
                lg0 = max(T930 - 60, run0 - 30); ok = False
                for g in range(lg0 + 2, k):
                    if s == 1 and h[g] < l[g - 2] and c[k] > l[g - 2]: ok = True; break
                    if s == -1 and l[g] > h[g - 2] and c[k] < h[g - 2]: ok = True; break
                if not ok: continue
            if k + 1 > TEX: return None
            ent = o[k + 1]; stop = (l[e] - 0.25) if s == 1 else (h[e] + 0.25); risk = s * (ent - stop)
            if risk <= 0 or risk < minstop * a[k]: continue
            if target == "dol":
                opp = hi if s == 1 else lo
                cand = [p for p in opp if s * (p - ent) >= risk]
                if not cand: continue
                tp = min(cand) if s == 1 else max(cand)
            elif target == "origin":
                seg = slice(min(run0, T930), e + 1); tp = h[seg].max() if s == 1 else l[seg].min()
                if s * (tp - ent) < risk: continue
            else: tp = ent + s * target * risk
            px = None
            for m in range(k + 1, TEX + 1):
                if (l[m] <= stop) if s == 1 else (h[m] >= stop): px = (min(o[m], stop) if s == 1 else max(o[m], stop)); break
                if (h[m] >= tp) if s == 1 else (l[m] <= tp): px = max(o[m], tp) if s == 1 else min(o[m], tp); break
            if px is None: px = c[TEX]
            cost = max(2.25 * ent / 17000, 0.75)
            return s, (s * (px - ent) - cost) / risk, s * (tp - ent) / risk, risk
    return None


def run(days, X, **cfg):
    out = []
    for i in range(len(days)):
        prev_ok = i > 0 and (days[i] - days[i - 1]).days <= 4
        r = day(X, i, prev_ok, **cfg)
        if r: out.append((days[i], *r))
    T = pd.DataFrame(out, columns=["date", "side", "R", "plan", "risk"]); T["date"] = pd.to_datetime(T.date); return T


def stats(T):
    if not len(T): return dict(n=0)
    R = T.R.values; eq = np.cumsum(R); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    yrs = (T.date.iloc[-1] - T.date.iloc[0]).days / 365.25 or 1
    return dict(n=len(R), per_yr=len(R) / yrs, win=100 * (R > 0).mean(), plan_rr=T.plan.median(),
                avgW=R[R > 0].mean() if (R > 0).any() else 0, avgL=R[R <= 0].mean() if (R <= 0).any() else 0,
                R=R.mean(), tot=R.sum(), dd=dd, t=R.mean() / R.std() * np.sqrt(len(R)))


GRID = dict(target=("dol", "origin", 2.0, 3.0), ifvg=(False, True), minstop=(0.0, 1.0))

if __name__ == "__main__":
    S = build(); rows, keep = [], {}
    for nm, (days, X) in S.items():
        for vals in itertools.product(*GRID.values()):
            cfg = dict(zip(GRID, vals)); T = run(days, X, **cfg); keep[(nm, vals)] = T
            for per, sub in (("2010-19", T[T.date.dt.year <= 2019]), ("2020-23", T[(T.date.dt.year >= 2020) & (T.date.dt.year <= 2023)]),
                             ("2024-26", T[T.date.dt.year >= 2024])):
                if len(sub): rows.append(dict(cfg, period=per, **stats(sub)))
            print(nm, cfg, len(T), flush=True)
    G = pd.DataFrame(rows); G.to_csv("lico_grid.csv", index=False)
    pd.set_option("display.width", 250); print(G.round(3).to_string(index=False))
    allT = {v: pd.concat([keep[("A", v)], keep[("B", v)]]) for v in itertools.product(*GRID.values())}
    pd.to_pickle(allT, "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/lico_trades.pkl")
