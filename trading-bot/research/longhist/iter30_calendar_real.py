"""Iter 30 on REAL NQ futures 2010-19 (+MNQ 2020-26) — — calendar microstructure at planned 1:2 (three periods: NSXUSD 2012–19 CFD; Databento MNQ 2020–23 / 2024–26).
Conditions: monthly opex (3rd Friday), quad witching (3rd Friday Mar/Jun/Sep/Dec = S&P / Nasdaq-100 rebalance days), Monday after
opex, opex week Mon–Thu, last trading day of month, first / second trading day of month, day before a market holiday.
Trade: entry at 09:30 / 10:00 / 13:30 / 15:00; side long / short / follow / fade the move since the open (follow/fade need entry > 09:30);
bracket stop k·σ (σ = 14-day mean |open→close|), target 2× stop, exit at the close. Cost 2.25 pt scaled to price."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
exec(open("iter26_web.py").read().split("res = []")[0])
sys.path.insert(0, "../gapfb")
from sess24 import build, t2m
_S = build(); _R0 = t2m("09:30")
def grids():
    for nm, key, msk in (("2010-19", "A", None), ("2020-23", "B", "lt"), ("2024-26", "B", "ge")):
        days, X = _S[key]
        if msk: m = (days.year < 2024) if msk == "lt" else (days.year >= 2024); days, X = days[m], X[m]
        R = X[:, _R0:_R0 + 390]; _DAYS[nm] = days
        yield nm, R[:, :, 0], R[:, :, 1], R[:, :, 2], R[:, :, 3], days.weekday.values
_DAYS = {}
def cal(days):
    d = pd.DatetimeIndex(days); s = pd.Series(range(len(d)), index=d)
    ym = d.year * 12 + d.month
    third_fri = (d.weekday == 4) & (d.day >= 15) & (d.day <= 21)
    # holiday-shifted opex (Thursday when Friday is closed) — take the last trading day <= 3rd Friday of the month
    opex = np.zeros(len(d), bool)
    for k in np.unique(ym):
        idx = np.nonzero(ym == k)[0]; y, m = divmod(k - 1, 12); m += 1
        first = pd.Timestamp(y, m, 1); tf = first + pd.Timedelta(days=(4 - first.weekday()) % 7 + 14)
        c = idx[d[idx] <= tf]
        if len(c): opex[c[-1]] = True
    quad = opex & np.isin(d.month, [3, 6, 9, 12])
    mon_after = np.r_[False, opex[:-1]] & (d.weekday == 0)
    opex_week = np.zeros(len(d), bool)
    for i in np.nonzero(opex)[0]:
        for j in range(max(0, i - 4), i):
            if (d[i] - d[j]).days <= 4: opex_week[j] = True
    last = np.r_[ym[1:] != ym[:-1], False]; first = np.r_[True, ym[1:] != ym[:-1]]; second = np.r_[False, first[:-1]]
    gap_next = np.r_[np.diff(d.values).astype("timedelta64[D]").astype(int), 1]
    pre_hol = ((gap_next > 1) & (d.weekday != 4)) | ((gap_next > 3) & (d.weekday == 4))
    return dict(opex=opex, quad=quad, opex_nonquad=opex & ~quad, mon_after_opex=mon_after, opex_week=opex_week,
                last_dom=last, first_dom=first, second_dom=second, pre_holiday=pre_hol, all_days=np.ones(len(d), bool))
res = []
P = {}
for per, o, h, l, c, dow in grids():
    days = _DAYS[per]
    C = cal(days); N = len(o)
    full = np.isfinite(c[:, 389]) & np.isfinite(o[:, 0])
    mv = np.abs(c[:, 389] / o[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
    for cn, mask in C.items():
        for em, side, k in itertools.product((0, 30, 240, 330), ("long", "short", "follow", "fade"), (0.15, 0.25, 0.4)):
            if em == 0 and side in ("follow", "fade"): continue
            R = []
            for i in np.nonzero(mask & full)[0]:
                if i < 15 or not np.isfinite(sig[i]): continue
                e = o[i, em]
                if not np.isfinite(e): continue
                if side == "long": s = 1
                elif side == "short": s = -1
                else:
                    mvv = c[i, em - 1] - o[i, 0]
                    if mvv == 0: continue
                    s = int(np.sign(mvv)) * (1 if side == "follow" else -1)
                st = k * sig[i] * o[i, 0]
                px, _, _ = walk(o[i], h[i], l[i], c[i], em, s, e, e - s * st, e + s * 2 * st, 389)
                R.append((s * (px - e) - 2.25 * e / 17000) / st)
            R = np.array([r for r in R if np.isfinite(r)])
            if len(R) < 15: continue
            res.append(dict(per=per, cond=cn, em=em, side=side, k=k, n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(res); T.to_csv("iter30_calendar_real.csv", index=False)
W = T.pivot_table(index=["cond", "em", "side", "k"], columns="per", values=["win", "R", "n"])
W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
pd.set_option("display.width", 250)
print(W.sort_values("minR", ascending=False).head(25).round(3).to_string())
print("\nmax min-win:", W["minwin"].max(), "  rows with minwin>=70:", (W["minwin"] >= 70).sum())
base = W.xs("all_days", level="cond")
print("rows minR>0:", (W["minR"] > 0).sum(), "of", len(W), " | all_days baseline minR>0:", (base["minR"] > 0).sum(), "of", len(base))
