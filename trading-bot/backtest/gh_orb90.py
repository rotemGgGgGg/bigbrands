"""giovannibrusco/nq-intraday-breakout re-run on MNQ 1-minute data (2020–2026).

Rules (from the repo): range = 09:30–11:00 ET. Stop orders at the range high (long) / low (short), entries
11:00–15:30 ET, max 2 trades a day, one at a time. Stop 100 pts, target 200 pts. Published version: longs held up
to 5 sessions, shorts flat at the close. `intraday=True` = everything flat 15:55 (prop-firm rules).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PT_USD, COST_USD = 2.0, 2.0


def run(d1: pd.DataFrame, stop=100.0, target=200.0, pct=False, intraday=True, max_trades=2, hold_days=5):
    t = d1.index
    o, h, l, c = (d1[k].values for k in ("open", "high", "low", "close"))
    m = t.hour * 60 + t.minute
    day = np.array(t.date)
    out = []
    i, n = 0, len(t)
    days = pd.Index(sorted(set(day[(m >= 570) & (m < 960)])))
    pos_day = {dd: k for k, dd in enumerate(days)}
    starts = np.searchsorted(t.values, pd.DatetimeIndex([pd.Timestamp(dd).tz_localize(t.tz) for dd in days]).values)
    busy_until = -1
    for k, dd in enumerate(days):
        s0 = starts[k]
        s1 = starts[k + 1] if k + 1 < len(days) else n
        rng = np.where((m[s0:s1] >= 570) & (m[s0:s1] < 660))[0] + s0
        if len(rng) < 80:
            continue
        hi, lo = h[rng].max(), l[rng].min()
        trades = 0
        j = rng[-1] + 1
        while j < s1 and trades < max_trades:
            if m[j] > 15 * 60 + 30:
                break
            if j <= busy_until:
                j = busy_until + 1
                continue
            side = 1 if h[j] >= hi + 0.25 else -1 if l[j] <= lo - 0.25 else 0
            if not side:
                j += 1
                continue
            lvl = hi + 0.25 if side == 1 else lo - 0.25
            e = max(o[j], lvl) if side == 1 else min(o[j], lvl)          # stop fill, gap-aware
            sd = e * stop / 100 if pct else stop
            td = e * target / 100 if pct else target
            sl, tp = e - side * sd, e + side * td
            last = k + (hold_days - 1 if (side == 1 and not intraday) else 0)
            x = j
            res = None
            while x < n:
                dx = pos_day.get(day[x])
                if (l[x] <= sl) if side == 1 else (h[x] >= sl):
                    px = min(o[x], sl) if side == 1 else max(o[x], sl)
                    res = (px - e) * side; break
                if (h[x] >= tp) if side == 1 else (l[x] <= tp):
                    res = (tp - e) * side; break
                if m[x] >= 15 * 60 + 55 and (dx is None or dx >= last):
                    res = (c[x] - e) * side; break
                x += 1
            if res is None:
                break
            out.append(dict(date=dd, side=side, pts=res, risk=sd, overnight=day[x] != dd))
            trades += 1
            busy_until = x
            j = x + 1
    tr = pd.DataFrame(out)
    tr["usd"] = tr.pts * PT_USD - COST_USD
    tr["r"] = tr.usd / (tr.risk * PT_USD)
    return tr
