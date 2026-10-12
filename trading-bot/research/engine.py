"""Shared engine for the top-20 strategy study (MNQ 1-minute, Databento GLBX MNQ.c.0, 2020-01 → 2026-10).

No look-ahead: every signal uses bars that are closed at decision time; fills are at the next bar's open,
at a resting limit/stop price, or at the bar open when the bar gaps through the level.
Exits are walked minute by minute; if stop and target fall in the same minute the stop is taken.
Costs (per MNQ round trip): commission $1.50 + 1 tick slippage per side ($1.00) = $2.50 = 1.25 points.
Stress test: 2 ticks per side extra → 2.25 points.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
PT_USD = 2.0
COST_PTS = 1.25
STRESS_PTS = 2.25
IS_END = "2024-01-01"          # in-sample 2020–2023, out-of-sample 2024–2026-10


class Data:
    """RTH days on a full 390-minute grid (09:30–15:59 bar opens) + the full 24h frame."""

    def __init__(self):
        full = pd.read_pickle(S + "full1m.pkl")
        instr = pd.read_pickle(S + "instr.pkl")
        self.full = full
        m = full.index.hour * 60 + full.index.minute
        rth = full[(m >= 570) & (m < 960)]
        days, arr = [], {k: [] for k in ("o", "h", "l", "c", "v")}
        rid = instr[(instr.index.hour * 60 + instr.index.minute >= 570) & (instr.index.hour * 60 + instr.index.minute < 960)]
        dmode = rid.groupby(rid.index.date).agg(lambda x: x.mode()[0])
        for d, g in rth.groupby(rth.index.date):
            if g.index[0].weekday() >= 5 or len(g) < 370:
                continue
            mins = g.index.hour * 60 + g.index.minute - 570
            if mins.max() < 385:                       # half day
                continue
            grid = pd.DataFrame(index=range(390))
            gg = g.set_index(mins)
            grid = grid.join(gg)
            grid["close"] = grid.close.ffill().bfill()
            for k in ("open", "high", "low"):
                grid[k] = grid[k].fillna(grid.close)
            grid["volume"] = grid.volume.fillna(0)
            days.append(d)
            arr["o"].append(grid.open.values); arr["h"].append(grid.high.values)
            arr["l"].append(grid.low.values); arr["c"].append(grid.close.values); arr["v"].append(grid.volume.values)
        self.days = days
        for k, v in arr.items():
            setattr(self, k, np.array(v))              # shape (ndays, 390)
        cid = dmode.reindex(days).values
        self.roll = np.r_[True, cid[1:] != cid[:-1]]  # first day of a new contract (cross-day prices invalid)
        self.prev_gap_days = np.r_[99, np.diff(pd.to_datetime(days)).astype("timedelta64[D]").astype(int)]

    def bars(self, i, tf):
        """tf-minute bars of RTH day i (tf divides 390): o,h,l,c,v arrays."""
        o, h, l, c, v = self.o[i], self.h[i], self.l[i], self.c[i], self.v[i]
        n = 390 // tf
        return (o[::tf][:n], h.reshape(n, tf).max(1), l.reshape(n, tf).min(1), c[tf - 1::tf][:n], v.reshape(n, tf).sum(1))

    def vwap(self, i):
        tp = (self.h[i] + self.l[i] + self.c[i]) / 3
        cv = np.cumsum(self.v[i])
        return np.where(cv > 0, np.cumsum(tp * self.v[i]) / np.maximum(cv, 1e-9), self.c[i])


def walk(o, h, l, c, i0, side, entry, stop=None, target=None, last=389, at_open=True, be_at=None):
    """Walk minutes i0..last. Returns (exit_price, exit_index, reason).
    at_open=True: the entry happened at bar i0's open, so the whole bar is after the entry.
    at_open=False: entry inside bar i0 (limit/stop) — only the stop is checked on that bar (conservative)."""
    sl = stop
    for j in range(i0, last + 1):
        if sl is not None:
            if side == 1 and l[j] <= sl:
                return (min(o[j], sl) if j > i0 or at_open else sl), j, "stop"
            if side == -1 and h[j] >= sl:
                return (max(o[j], sl) if j > i0 or at_open else sl), j, "stop"
        if target is not None and (j > i0 or at_open):
            if side == 1 and h[j] >= target:
                return (max(o[j], target) if j > i0 else target), j, "target"
            if side == -1 and l[j] <= target:
                return (min(o[j], target) if j > i0 else target), j, "target"
        if be_at is not None and sl is not None:
            fav = (h[j] - entry) if side == 1 else (entry - l[j])
            if fav >= be_at:
                sl = max(sl, entry) if side == 1 else min(sl, entry)
    return c[last], last, "time"


def summarize(name, tr: pd.DataFrame, cost=COST_PTS) -> dict:
    """tr: date, side, pts (gross points per 1 contract), risk (points, NaN if none)."""
    if tr is None or len(tr) == 0:
        return dict(name=name, n=0)
    tr = tr.copy()
    tr["net"] = tr.pts - cost
    tr["net_s"] = tr.pts - STRESS_PTS
    y = pd.to_datetime(tr.date).dt.year
    daily = tr.groupby("date").net.sum()
    dd = (daily.cumsum() - daily.cumsum().cummax()).min()
    wins, losses = tr.net[tr.net > 0], tr.net[tr.net <= 0]
    isd = pd.to_datetime(tr.date) < IS_END
    def sh(x):
        x = x.groupby(tr.date[x.index]).sum()
        return float(x.mean() / x.std() * np.sqrt(252)) if len(x) > 2 and x.std() > 0 else np.nan
    has_r = tr.risk.notna().any() if "risk" in tr else False
    rr = (wins.mean() / -losses.mean()) if len(wins) and len(losses) else np.nan
    yrs = tr.groupby(y).net.sum()
    out = dict(name=name, n=len(tr), per_month=round(len(tr) / ((pd.to_datetime(tr.date).max() - pd.to_datetime(tr.date).min()).days / 30.4), 1),
               win=round(100 * (tr.net > 0).mean(), 1), rr=round(rr, 2),
               pf=round(wins.sum() / -losses.sum(), 2) if len(losses) and losses.sum() < 0 else np.nan,
               avg_pts=round(tr.net.mean(), 2), avg_usd=round(tr.net.mean() * PT_USD, 1),
               tot_usd=round(tr.net.sum() * PT_USD), maxdd_usd=round(dd * PT_USD),
               sharpe=round(sh(tr.net), 2), IS_avg=round(tr.net[isd].mean(), 2), OOS_avg=round(tr.net[~isd].mean(), 2),
               IS_sh=round(sh(tr.net[isd]), 2), OOS_sh=round(sh(tr.net[~isd]), 2),
               stress_avg=round(tr.net_s.mean(), 2), yrs_pos=f"{int((yrs > 0).sum())}/{len(yrs)}",
               years=round((pd.to_datetime(tr.date).max() - pd.to_datetime(tr.date).min()).days / 365.25, 1))
    if has_r:
        r = tr.net / tr.risk
        out["avg_R"] = round(r.mean(), 3)
    return out
