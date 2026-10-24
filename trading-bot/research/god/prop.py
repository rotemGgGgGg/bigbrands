"""Prop-account fit of the final portfolio (Lucid Flex rules), searched on the MNQ era.
Levers (all live-bot implementable): micros per component, skip a trade when its stop risk per micro > cap,
bot daily loss limit (no new entries once the day's realized P&L ≤ −L), netting rule (skip opposite-side trades).
Eval rules: profit target, EOD-trailing max loss (breach checked intraday on realized P&L in exit order), 50 % consistency,
≥ 2 days. Funded: same max loss, 250-day survival. DESIGN = paths inside 2020-23 only; TEST = paths inside 2024-26 only."""
import os, itertools, time
import numpy as np, pandas as pd
from numba import njit
HERE = os.path.dirname(os.path.abspath(__file__))
ACC = {"50K": (3000, 2000), "100K": (6000, 3000), "150K": (9000, 4500)}
COMP = ["No-Wick", "GapFB", "Pre-Fade", "Opex"]


def load():
    T = pd.read_csv(os.path.join(HERE, "trades_netting.csv"), parse_dates=["entry", "exit"])
    T = T[T.entry.dt.year >= 2020].sort_values("entry").reset_index(drop=True)
    T["ci"] = T.comp.map({c: i for i, c in enumerate(COMP)}); return T


def book(T, size, cap, L):
    """apply bot rules in time order → daily (sum, intraday low) of kept trades."""
    ent = T.entry.values; ext = T.exit.values; sd = T.side.values; u1 = T.usd1.values; r1 = T.risk1.values; ci = T.ci.values
    day = T.entry.dt.normalize().values
    keep = []; open_ = []; cur = None; realized = []
    for i in range(len(T)):
        q = size[ci[i]]
        if q == 0 or r1[i] > cap: continue
        if day[i] != cur: cur = day[i]; realized = []
        open_ = [(x, s) for x, s in open_ if x > ent[i]]
        if any(s != sd[i] for _, s in open_): continue
        if L and sum(v for x, v in realized if x <= ent[i]) <= -L: continue
        open_.append((ext[i], sd[i])); realized.append((ext[i], q * u1[i])); keep.append((day[i], ext[i], q * u1[i]))
    K = pd.DataFrame(keep, columns=["day", "exit", "usd"]).sort_values(["day", "exit"])
    g = K.groupby("day").usd
    return pd.DataFrame(dict(pnl=g.sum(), low=g.apply(lambda s: min(0.0, s.cumsum().min()))))


@njit(cache=True)
def evalsim(x, lo, target, dd, horizon):
    n = len(x); npass = 0; nfail = 0; days = np.zeros(n); k = 0; bust = 0; nf = 0
    for s in range(n):
        bal = 0.0; peak = 0.0; best = 0.0; out = 0
        for j in range(s, n):
            if bal + lo[j] <= peak - dd: out = -1; break
            bal += x[j]; best = max(best, x[j])
            if bal <= peak - dd: out = -1; break
            peak = max(peak, bal)
            if bal >= target and best <= 0.5 * bal and j - s + 1 >= 2: out = j - s + 1; break
        if out > 0: npass += 1; days[k] = out; k += 1
        elif out < 0: nfail += 1
        if s + horizon <= n:
            bal = 0.0; peak = 0.0; nf += 1
            for j in range(s, s + horizon):
                if bal + lo[j] <= peak - dd: bust += 1; break
                bal += x[j]
                if bal <= peak - dd: bust += 1; break
                peak = max(peak, bal)
    med = np.median(days[:k]) if k else 999.0
    return 100.0 * npass / max(npass + nfail, 1), med, 100.0 * bust / max(nf, 1)


def score(D, acc):
    tg, dd = ACC[acc]; out = {}
    for nm, m in (("des", (D.index.year >= 2020) & (D.index.year <= 2023)), ("tst", D.index.year >= 2024)):
        d = D[m]; p, md, b = evalsim(d.pnl.values, d.low.values, tg, dd, 250)
        out.update({f"{nm}_pass": p, f"{nm}_days": md, f"{nm}_bust": b, f"{nm}_usd_day": d.pnl.sum() / max(len(d), 1)})
    return out


GRID = dict(nw=(1, 2), gfb=(0, 1, 2), pf=(0, 1, 2), opx=(0, 1, 2), cap=(1e9, 100, 150, 200, 250, 300), L=(0, 250, 400, 600, 900))

if __name__ == "__main__":
    t0 = time.time(); T = load(); rows = []
    combos = list(itertools.product(*GRID.values()))
    for n, (nw, gfb, pf, opx, cap, L) in enumerate(combos):
        D = book(T, (nw, gfb, pf, opx), cap, L)
        for acc in ACC: rows.append(dict(acc=acc, nw=nw, gfb=gfb, pf=pf, opx=opx, cap=cap, L=L, **score(D, acc)))
        if n % 100 == 0: print(n, len(combos), f"{time.time() - t0:.0f}s", flush=True)
    R = pd.DataFrame(rows); R.to_csv(os.path.join(HERE, "prop_search.csv"), index=False)
    pd.set_option("display.width", 250)
    for acc in ACC:
        r = R[(R.acc == acc) & (R.des_pass >= 95) & (R.des_bust <= 5)].sort_values("des_days").head(8)
        print(f"\n{acc}: design pass>=95 & funded bust<=5, fastest"); print(r.round(1).to_string(index=False))
