"""Validation tools for finalists (frozen configs).
  trades(cfg, d0, d1, cx)          full trade log of a config (cx = cost multiplier)
  random_entry(T, cfg, n)          null 1: same days/sides/stop distance/target R/time exit, random entry minute inside the window
  flip_direction(T, cfg, n)        null 2: same entry minutes, direction flipped at random (p=0.5)
  walk_forward(pool, years)        re-select the best config of a fixed candidate pool on the trailing 4 years, trade the next year
  pbo(M)                           probability of backtest overfitting (CSCV, 16 blocks) on a configs×days matrix
  dsr(sr, n_trials, sr_var, T, skew, kurt)   deflated Sharpe ratio
  bootstrap_dd(R, n)               trade-order bootstrap of max drawdown
  neighbours(cfg)                  one-step parameter perturbations (stability)"""
import itertools, json
import numpy as np, pandas as pd
from numba import njit
from scipy.stats import norm, skew, kurtosis
import data, search as S, ict_engine as E
from space import CHOICES, WINDOWS, make, COST_PTS, SLIP_PTS


def G():
    if not S._G: S.init()
    return S._G


def params(cfg, cx=1.0): return make(cfg["w"], cfg["mask"], cx=cx, **{k: cfg[k] for k in CHOICES})


def trades(cfg, d0=0, d1=None, cx=1.0):
    g = G(); d1 = g["h"] if d1 is None else d1; P = params(cfg, cx)
    d, t, s, R, rk, pts = E.run(g["X"], g["LV"], g["E2"], g["prev"], P, d0, d1)
    D = data.load()
    return pd.DataFrame(dict(day=d, date=D["days"][d], minute=t, side=s, R=R, risk=rk, pts=pts))


@njit(cache=True)
def _sim(X, day, t0, side, risk, tpr, te, cost, slip):
    out = np.empty(len(day))
    for q in range(len(day)):
        d = day[q]; t = t0[q]; s = side[q]; o = X[d, :, 0]; h = X[d, :, 1]; l = X[d, :, 2]; c = X[d, :, 3]
        e = o[t]; st = e - s * risk[q]; tg = e + s * tpr * risk[q]; px = c[te]; ex = slip
        for k in range(t, te + 1):
            if (l[k] <= st) if s == 1 else (h[k] >= st):
                px = st if k == t else (min(o[k], st) if s == 1 else max(o[k], st)); ex = slip; break
            if k > t and ((h[k] >= tg + 0.25) if s == 1 else (l[k] <= tg - 0.25)):
                px = tg; ex = 0.0; break
        out[q] = (s * (px - e) - cost - slip - ex) / risk[q]
    return out


def random_entry(T, cfg, n=1000, seed=0):
    g = G(); P = params(cfg); ws, we, te = int(P[E.WS]), int(P[E.WE]), int(P[E.TEXIT]); rng = np.random.default_rng(seed)
    tpr = P[E.TPR]; out = np.empty(n)
    for i in range(n):
        tt = rng.integers(ws, min(we, te - 1) + 1, len(T))
        out[i] = _sim(g["X"], T.day.values, tt, T.side.values, T.risk.values, tpr, te, P[E.COST], P[E.SLIP]).mean()
    return out


def flip_direction(T, cfg, n=1000, seed=0):
    g = G(); P = params(cfg); te = int(P[E.TEXIT]); rng = np.random.default_rng(seed); tpr = P[E.TPR]; out = np.empty(n)
    for i in range(n):
        sd = np.where(rng.random(len(T)) < 0.5, -T.side.values, T.side.values)
        out[i] = _sim(g["X"], T.day.values, T.minute.values, sd, T.risk.values, tpr, te, P[E.COST], P[E.SLIP]).mean()
    return out


def daily_series(cfg, d0=0, d1=None):
    T = trades(cfg, d0, d1); D = data.load(); n = (G()["h"] if d1 is None else d1)
    s = np.zeros(n); np.add.at(s, T.day.values, T.R.values); return s[d0:]


def pbo(M, blocks=16):
    """M: configs × days. CSCV: for every half/half split of the blocks pick the in-sample best and record its OOS rank."""
    nb = M.shape[1] // blocks; B = [np.arange(i * nb, (i + 1) * nb) for i in range(blocks)]; logits = []
    for comb in itertools.combinations(range(blocks), blocks // 2):
        ins = np.concatenate([B[i] for i in comb]); oos = np.concatenate([B[i] for i in range(blocks) if i not in comb])
        sr_i = M[:, ins].mean(1) / (M[:, ins].std(1) + 1e-12); sr_o = M[:, oos].mean(1) / (M[:, oos].std(1) + 1e-12)
        b = int(np.argmax(sr_i)); w = (sr_o < sr_o[b]).mean() + 0.5 / len(sr_o)
        logits.append(np.log(w / (1 - w)))
    logits = np.array(logits); return float((logits <= 0).mean()), logits


def dsr(sr, n_trials, sr_var, T, sk, ku):
    g = 0.5772156649
    e_max = np.sqrt(sr_var) * ((1 - g) * norm.ppf(1 - 1 / n_trials) + g * norm.ppf(1 - 1 / (n_trials * np.e)))
    return float(norm.cdf((sr - e_max) * np.sqrt(T - 1) / np.sqrt(1 - sk * sr + (ku - 1) / 4 * sr ** 2))), float(e_max)


def bootstrap_dd(R, n=5000, seed=0):
    rng = np.random.default_rng(seed); out = np.empty(n)
    for i in range(n):
        eq = np.cumsum(rng.permutation(R)); out[i] = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    return out


def neighbours(cfg):
    out = []
    for k, vals in CHOICES.items():
        i = vals.index(cfg[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals): c = dict(cfg); c[k] = vals[j]; out.append((f"{k}={vals[j]}", c))
    for b in range(9):
        m = cfg["mask"] ^ (1 << b)
        if m: c = dict(cfg); c["mask"] = m; out.append((f"mask^{b}", c))
    for w in range(len(WINDOWS)):
        if w != cfg["w"]: c = dict(cfg); c["w"] = w; out.append((f"w={WINDOWS[w]}", c))
    return out
