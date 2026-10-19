"""Iter 83 (queue 84) — Pre-Fade quality, walk-forward: features at 08:59 — |z|, overnight move (18:00→07:59) agreeing with the
pre-move, yesterday's RTH candle agreeing, pre-move vs 20-day ATR, VIX, weekday; logistic re-fit every 2 years on past trades only,
keep trades above the training median; compare with all trades."""
import sys; sys.path[:0] = ["..", "../longhist"]
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
from sess24 import build, t2m
S = build(); t8, t9, t13 = t2m("08:00"), t2m("09:00"), t2m("13:00"); R0, X1 = t2m("09:30"), t2m("15:59")
V = pd.read_csv("../quant_loop/vix.csv"); V.columns = ["date", "vix"]; V["date"] = pd.to_datetime(V.date); V = V.set_index("date").vix.apply(pd.to_numeric, errors="coerce").dropna()
rows = []
for key in ("A", "B"):
    days, X = S[key]; o, h, l, c = (X[:, :, i] for i in range(4))
    pre = c[:, t9 - 1] / o[:, t8] - 1; sd = pd.Series(pre).rolling(20).std().shift().values
    for i in range(21, len(days)):
        if not sd[i] > 0 or abs(pre[i] / sd[i]) <= 2: continue
        mv = c[i, t9 - 1] - o[i, t8]; s = -1 if mv > 0 else 1; e = o[i, t9]; size = abs(mv); sl = e - s * size; tp = e + s * 0.5 * size; px = None
        for k in range(t9, t13 + 1):
            if (l[i, k] <= sl) if s == 1 else (h[i, k] >= sl): px = min(o[i, k], sl) if s == 1 else max(o[i, k], sl); break
            if (h[i, k] >= tp) if s == 1 else (l[i, k] <= tp): px = tp; break
        if px is None: px = c[i, t13]
        d = days[i]; vx = V[:d - pd.Timedelta(days=1)]
        rows.append(dict(day=d, R=(s * (px - e) - 2.25 * e / 17000) / size, z=abs(pre[i] / sd[i]),
                         on=np.sign(c[i, t8 - 1] - o[i, 0]) * np.sign(mv), yd=np.sign(c[i - 1, X1] - o[i - 1, R0]) * np.sign(mv),
                         vix=vx.iloc[-1] if len(vx) else np.nan, dow=d.weekday()))
T = pd.DataFrame(rows).dropna().sort_values("day"); T["yr"] = T.day.dt.year; F = ["z", "on", "yd", "vix", "dow"]
out = []
for y0 in range(2014, 2027, 2):
    tr, te = T[T.yr < y0], T[(T.yr >= y0) & (T.yr < y0 + 2)]
    if len(te) == 0: continue
    mu, sdv = tr[F].mean(), tr[F].std() + 1e-9
    m = LogisticRegression(C=0.3, max_iter=2000).fit(((tr[F] - mu) / sdv).values, (tr.R > 0).astype(int))
    pt = m.predict_proba(((tr[F] - mu) / sdv).values)[:, 1]; pe = m.predict_proba(((te[F] - mu) / sdv).values)[:, 1]
    k = te[pe >= np.median(pt)]; out.append(dict(window=y0, n_all=len(te), R_all=te.R.mean(), n_wf=len(k), R_wf=k.R.mean()))
X = pd.DataFrame(out); print(X.round(3).to_string(index=False))
for c in ("all", "wf"): print(c, f"{(X[f'R_{c}'] * X[f'n_{c}']).sum() / X[f'n_{c}'].sum():+.3f}", f"windows+ {(X[f'R_{c}'] > 0).sum()}/{len(X)}")
