"""LucidFlex 50K evaluation simulator driven by the trade ledger.
Rules: pass at balance ≥ +$3,000 with best day ≤ 50 % of balance; fail when equity touches the max-loss limit (MLL) — MLL starts
at −$2,000, trails the END-OF-DAY balance peak by $2,000 and locks at +$100 once the peak reaches $2,100. Intraday equity is checked
with each trade's MAE (worst point) on top of the day's realised P&L (conservative: the MAE of an open trade is assumed to coincide
with the day's realised low). Policy: edges, base size, press (size × mult once balance ≥ press_at), daily profit cap (stop taking
new trades once the day is up ≥ cap — keeps consistency), daily loss stop, max trades per day."""
import numpy as np, pandas as pd
FEE = 150.0
class Book:
    def __init__(self, L):
        self.days = np.array(sorted(L.date.unique())); pos = {d: k for k, d in enumerate(self.days)}
        self.by_edge = {}
        for e, g in L.groupby("edge"):
            per = [[] for _ in self.days]
            for r in g.itertuples(): per[pos[r.date]].append((r.t_in, r.pts, r.mae))
            self.by_edge[e] = per
    def day_trades(self, k, edges):
        out = []
        for e in edges: out += self.by_edge[e][k]
        return sorted(out)
def attempt(book, start, pol, max_days=400):
    """Return (passed, days_used, n_trades, n_winning_trades, best_day, day_wins, day_count)."""
    bal = peak = best = 0.0; mll = -2000.0; nt = nw = dw = dc = 0
    for k in range(start, min(start + max_days, len(book.days))):
        q = pol["base"] * (pol["mult"] if pol["press_at"] is not None and bal >= pol["press_at"] else 1)
        day = 0.0; taken = 0
        for t_in, pts, mae in book.day_trades(k, pol["edges"]):
            if taken >= pol["max_trades"]: break
            if pol["cap"] is not None and day >= pol["cap"]: break
            if pol["stop"] is not None and day <= -pol["stop"]: break
            if bal + day + q * 2 * mae <= mll: return (False, k - start + 1, nt + 1, nw, best, dw, dc + 1)
            day += q * 2 * pts; taken += 1; nt += 1; nw += pts > 0
        if taken:
            dc += 1; dw += day > 0
        bal += day; best = max(best, day)
        if bal <= mll: return (False, k - start + 1, nt, nw, best, dw, dc)
        peak = max(peak, bal); mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
        if bal >= 3000 and best <= 0.5 * bal: return (True, k - start + 1, nt, nw, best, dw, dc)
    return (None, max_days, nt, nw, best, dw, dc)
def score(book, pol, starts):
    res = [attempt(book, s, pol) for s in starts]; res = [r for r in res if r[0] is not None]
    if not res: return None
    P = np.mean([r[0] for r in res]); dp = np.mean([r[1] for r in res if r[0]]) if P > 0 else np.nan
    df = np.mean([r[1] for r in res if not r[0]]) if P < 1 else 0.0
    nt = sum(r[2] for r in res); nw = sum(r[3] for r in res); dc = sum(r[6] for r in res); dw = sum(r[5] for r in res)
    return dict(pass_pct=round(100 * P, 1), days_pass=round(dp, 1), days_fail=round(df, 1),
                exp_days=round((1 - P) / P * df + dp, 1) if P > 0 else np.inf, exp_cost=round(FEE / P) if P > 0 else np.inf,
                trade_win=round(100 * nw / max(nt, 1), 1), day_win=round(100 * dw / max(dc, 1), 1), n_attempts=len(res))
