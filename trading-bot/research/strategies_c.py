"""Group C: GMM regime strategies (ranks 13, 14). The sources leave feature formulas and the regime mapping
partly unspecified; every such choice is marked "interp:". Models are fit on past data only (walk-forward)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from engine import walk


def _z(s, n):
    return (s - s.rolling(n).mean()) / s.rolling(n).std()


# ---------------------------------------------------------------- 13. London GMM regime-transition long
def london_gmm(full: pd.DataFrame, seed=0):
    b = full.resample("15min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    tr = pd.concat([b.high - b.low, (b.high - b.close.shift()).abs(), (b.low - b.close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    ret = b.close.pct_change()
    f = pd.DataFrame({
        "atr_ratio": atr / atr.rolling(96).mean(),                      # interp: ATR14 / its 1-day mean
        "vol_z": _z(b.volume, 50),
        "close_pos": (b.close - b.low) / (b.high - b.low).replace(0, np.nan),
        "ret": ret,
        "dir_cons": np.sign(ret).rolling(4).mean(),                     # interp: signed share of last 4 bars
    })
    f = f.apply(lambda s: _z(s, 100))                                   # rolling z-score, then StandardScaler
    m = b.index.hour * 60 + b.index.minute
    lon = (m >= 180) & (m < 510)
    f = f[lon].dropna()
    years = sorted(set(f.index.year))
    rows = []
    for ty in years[1:]:
        trn, tst = f[f.index.year < ty], f[f.index.year == ty]
        if len(trn) < 2000 or tst.empty:
            continue
        sc = StandardScaler().fit(trn.values)
        g = GaussianMixture(3, random_state=seed).fit(sc.transform(trn.values))
        mu = pd.DataFrame(sc.inverse_transform(g.means_), columns=f.columns)
        r1 = int(mu.vol_z.idxmax())                                     # interp: extreme volatility = highest vol z
        rest = [k for k in range(3) if k != r1]
        r2 = max(rest, key=lambda k: mu.dir_cons[k])                    # bullish drift = higher directional consistency
        r0 = [k for k in rest if k != r2][0]
        lab = pd.Series(g.predict(sc.transform(tst.values)), index=tst.index)
        lab = lab.map({r0: 0, r1: 1, r2: 2})
        for i in range(2, len(lab) - 1):
            t = lab.index[i]
            if lab.iloc[i] == 2 and lab.iloc[i - 1] == 0 and 1 not in lab.iloc[i - 2:i].values:
                start = t + pd.Timedelta(minutes=15)
                end = min(start + pd.Timedelta(minutes=60), t.normalize() + pd.Timedelta(minutes=510))
                seg = full.loc[start:end - pd.Timedelta(minutes=1)]
                if len(seg) < 10:
                    continue
                e = seg.open.iloc[0]
                px, _, _ = walk(seg.open.values, seg.high.values, seg.low.values, seg.close.values, 0, 1, e, e - 20, None, len(seg) - 1)
                rows.append((t.date(), 1, px - e, 20.0))
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])


# ---------------------------------------------------------------- 14. RTH confluence (GMM + Markov + volume)
def rth_confluence(full: pd.DataFrame, atr1: pd.Series, seed=0, fit_years=1):
    m1 = full.index.hour * 60 + full.index.minute
    b = full[(m1 >= 570) & (m1 < 960)].resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    scale = b.close / 12500.0                                           # interp: 2022 point values scaled by price
    a = atr1.reindex(b.index + pd.Timedelta(minutes=4)).values          # 1-min ATR at the 5-min bar's last minute
    ratio = np.clip(a / (10.34 * scale.values), 0.5, 2.0)
    f = pd.DataFrame({"atr_ratio": ratio, "vol_z": _z(b.volume, 50).values,
                      "close_pos": ((b.close - b.low) / (b.high - b.low).replace(0, np.nan)).values,
                      "ret": b.close.pct_change().values}, index=b.index).dropna()
    first = f.index[0].year
    trn = f[f.index.year < first + fit_years]
    sc = StandardScaler().fit(trn.values)
    g = GaussianMixture(3, random_state=seed).fit(sc.transform(trn.values))
    order = np.argsort(sc.inverse_transform(g.means_)[:, 0])            # interp: regimes by mean ATR ratio
    remap = {int(order[0]): 0, int(order[1]): 1, int(order[2]): 2}
    lab = pd.Series(g.predict(sc.transform(f.values)), index=f.index).map(remap)
    prev = lab.shift()
    is1 = (prev == 1).astype(float)
    t12 = ((prev == 1) & (lab == 2)).astype(float)
    p12 = (t12.rolling(200).sum() / is1.rolling(200).sum()).shift()      # prior bars only
    vz = _z(b.volume.reindex(f.index), 50).shift()
    test = f.index.year >= first + fit_years
    rows = []
    bb = b.reindex(f.index)
    days = pd.Series(f.index.date, index=f.index)
    for d, idx in days[test].groupby(days[test]).groups.items():
        di = bb.loc[idx]
        L = lab.loc[idx].values
        P, V, R = p12.loc[idx].values, vz.loc[idx].values, pd.Series(ratio, index=b.index).reindex(idx).values
        sc_d = (di.close / 12500.0).values
        i = 0
        n = len(di)
        while i < n - 2:
            if L[i] == 1 and P[i] > 0.15 and V[i] > 0.5:
                pb = 25 * R[i] * sc_d[i]
                lvl = di.close.iloc[i] - pb
                hit = next((k for k in range(i + 1, min(i + 7, n - 1)) if di.low.iloc[k] <= lvl), None)
                if hit is None:
                    i += 1
                    continue
                k = hit + 1
                e = di.open.iloc[k]
                stop = e - 80 * R[i] * sc_d[i]
                last = min(i + 13, n) - 1
                seg = full.loc[di.index[k]:di.index[last] + pd.Timedelta(minutes=4)]
                px, _, _ = walk(seg.open.values, seg.high.values, seg.low.values, seg.close.values, 0, 1, e, stop, None, len(seg) - 1)
                rows.append((d, 1, px - e, e - stop))
                i = last + 1
                continue
            i += 1
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])
