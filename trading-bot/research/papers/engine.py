"""Two causal engines + coin-flip baselines for the classic-papers study.
Daily: a holding array per day (+1/-1/0, fractional allowed) and a return mode
   'oo'  signal at close t -> held open t+1 -> open t+2 (strategies whose rule uses today's close; no same-close execution)
   'cc'  close d-1 -> close d (calendar rules only: the decision never depends on price)
   'oc'  open d -> close d (decided at the open)       'co'  close d-1 -> open d (overnight)
Intraday: one trade per day on the 1-minute RTH grid: market / stop / limit entry, stop, target, time exit.
Stop wins a stop+target tie inside one minute; limits need 1 tick through; stop entries fill at the worse of level/open.
Cost per round trip: 2.25 pt x price/17000 (the research standard used in every earlier study), x2 at the stress level."""
import numpy as np
TICK = 0.25
M = np.arange(390)


def rt_cost(px, cx=1.0): return 2.25 * px / 17000.0 * cx


# ---------------------------------------------------------------- daily
def day_returns(D):
    o, c = D["do"], D["dc"]; n = len(c); r = {}
    oo = np.full(n, np.nan); oo[:-1] = o[1:] - o[:-1]; r["oo"] = oo
    cc = np.full(n, np.nan); cc[1:] = c[1:] - c[:-1]; r["cc"] = cc
    r["oc"] = c - o
    co = np.full(n, np.nan); co[1:] = o[1:] - c[:-1]; r["co"] = co
    return r


def daily_eval(hold, ret, mode, px, cx=1.0, sign=None):
    """hold/ret/px restricted to a window. Returns per-trade net pts, per-trade gross pts, per-day net pts, trade start idx."""
    h = np.nan_to_num(hold); r = np.nan_to_num(ret); cost_rt = rt_cost(px, cx)
    if mode in ("oc", "co"):
        k = np.nonzero(h)[0]; g = h[k] * r[k]; c = np.abs(h[k]) * cost_rt[k]
        if sign is not None: g = g * sign
        day = np.zeros(len(h)); day[k] = g - c; return g - c, g, day, k
    dh = np.abs(np.diff(h, prepend=0.0)); cst = dh * cost_rt / 2
    dpn = h * r - cst
    # trades = runs of the same non-zero holding
    brk = np.r_[True, h[1:] != h[:-1]]; run = np.cumsum(brk) - 1; nz = h != 0
    ids = np.unique(run[nz])
    if len(ids) == 0: return np.zeros(0), np.zeros(0), dpn, np.zeros(0, int)
    g = np.bincount(run[nz], weights=(h * r)[nz], minlength=run.max() + 1)[ids]
    start = np.searchsorted(run, ids); c = np.abs(h[start]) * cost_rt[start]   # one full round trip per trade
    return g - c, g, dpn, start


def daily_null(hold, ret, mode, px, draws, rng):
    """coin flips: (a) circular shift of the holding series (same exposure, random timing), (b) random sign per trade."""
    n = len(hold); real = daily_eval(hold, ret, mode, px)[2].sum()
    sh = np.empty(draws)
    for i in range(draws):
        k = rng.integers(5, max(n - 5, 6)); sh[i] = daily_eval(np.roll(hold, k), ret, mode, px)[2].sum()
    net, g, _, _ = daily_eval(hold, ret, mode, px); cost = (g - net).sum()
    S = rng.choice([-1.0, 1.0], size=(draws, len(g))); fl = S @ g - cost
    return real, (1 + (sh >= real).sum()) / (draws + 1), (1 + (fl >= real).sum()) / (draws + 1)


# ---------------------------------------------------------------- intraday
def _first(mask):
    a = mask.any(1); return np.where(a, mask.argmax(1), 9999)


def fill(D, d, dr, e, kind, lvl, tx):
    """returns fill minute (9999 = none) and fill price for single-direction orders. kind 0 mkt @open[e], 1 stop, 2 limit, 3 at lvl."""
    O, H, L = D["o"][d], D["h"][d], D["l"][d]; r = np.arange(len(d)); e = e.astype(int)
    if kind in (0, 3):
        fm = np.where(e <= tx, e, 9999); fp = O[r, np.minimum(e, 389)] if kind == 0 else lvl.copy(); return fm, fp
    el = (M[None] >= e[:, None]) & (M[None] <= tx[:, None])
    if kind == 1: hit = np.where(dr[:, None] > 0, H >= lvl[:, None], L <= lvl[:, None])
    else: hit = np.where(dr[:, None] > 0, L <= lvl[:, None] - TICK, H >= lvl[:, None] + TICK)
    fm = _first(el & hit); om = O[r, np.minimum(fm, 389)]
    if kind == 1: fp = np.where(dr > 0, np.maximum(lvl, om), np.minimum(lvl, om))
    else: fp = np.where(dr > 0, np.minimum(lvl, om), np.maximum(lvl, om))
    return fm, fp


def exits(D, d, dr, fm, fp, stop, tgt, tx):
    O, H, L, C = D["o"][d], D["h"][d], D["l"][d], D["c"][d]; r = np.arange(len(d))
    after = (M[None] >= fm[:, None]) & (M[None] <= tx[:, None])
    st = np.where(np.isnan(stop), np.where(dr > 0, -1e12, 1e12), stop)
    tg = np.where(np.isnan(tgt), np.where(dr > 0, 1e12, -1e12), tgt)
    sh = after & np.where(dr[:, None] > 0, L <= st[:, None], H >= st[:, None])
    th = after & (M[None] > fm[:, None]) & np.where(dr[:, None] > 0, H >= tg[:, None] + TICK, L <= tg[:, None] - TICK)
    ms, mt = _first(sh), _first(th)
    om = O[r, np.minimum(ms, 389)]
    # a stop already beyond the fill price (open gapped past it) exits at the fill, never at the better stop level
    sp = np.where(ms > fm, np.where(dr > 0, np.minimum(st, om), np.maximum(st, om)), np.where(dr > 0, np.minimum(st, fp), np.maximum(st, fp)))
    xp = np.where(ms <= mt, sp, tg); xm = np.minimum(ms, mt)
    tex = xm > tx; xp = np.where(tex, C[r, tx], xp); xm = np.where(tex, tx, xm)
    return xp, xm


def intraday_trades(D, spec, cx=1.0):
    """spec: dict of per-day arrays (all days): dir (0/±1/2=OCO), e, lvlL, lvlS, stopL, stopS, tgtL, tgtS, tx; kind scalar."""
    n = len(D["days"]); dr0 = spec["dir"]; kind = spec["kind"]; tx_all = spec.get("tx", np.full(n, 389)).astype(int)
    out = []
    for side in (1, -1):
        d = np.nonzero((dr0 == side) | (dr0 == 2))[0]
        if len(d) == 0: out.append(None); continue
        lv = spec["lvlL" if side > 0 else "lvlS"][d] if kind else np.full(len(d), np.nan)
        dr = np.full(len(d), side); fm, fp = fill(D, d, dr, spec["e"][d], kind, lv, tx_all[d])
        out.append((d, fm, fp))
    rows = {}
    for side, o in zip((1, -1), out):
        if o is None: continue
        for dd, fm, fp in zip(*o):
            if fm >= 9999: continue
            p = rows.get(dd)
            if p is None: rows[dd] = (side, fm, fp)
            elif p != "x":          # OCO: earliest fill wins, same-minute = ambiguous -> skip the day
                rows[dd] = "x" if p[1] == fm else (p if p[1] < fm else (side, fm, fp))
    keep = sorted(k for k, v in rows.items() if v not in (None, "x"))
    if not keep: return None
    d = np.array(keep); dr = np.array([rows[k][0] for k in keep]); fm = np.array([rows[k][1] for k in keep]); fp = np.array([rows[k][2] for k in keep], float)
    stop = np.where(dr > 0, spec["stopL"][d], spec["stopS"][d]); tgt = np.where(dr > 0, spec["tgtL"][d], spec["tgtS"][d]); tx = tx_all[d]
    xp, xm = exits(D, d, dr, fm, fp, stop, tgt, tx)
    g = dr * (xp - fp); net = g - rt_cost(fp, cx)
    return dict(d=d, dir=dr, fm=fm, fp=fp, sd=np.abs(fp - stop), td=np.abs(tgt - fp), tx=tx, gross=g, net=net)


def resim(D, d, dr, fm, fp, sd, td, tx, kind):
    stop = np.where(np.isnan(sd), np.nan, fp - dr * sd); tgt = np.where(np.isnan(td), np.nan, fp + dr * td)
    if kind == 0: fp = D["o"][d, np.minimum(fm, 389)]; stop = np.where(np.isnan(sd), np.nan, fp - dr * sd); tgt = np.where(np.isnan(td), np.nan, fp + dr * td)
    xp, xm = exits(D, d, dr, fm, fp, stop, tgt, tx); return dr * (xp - fp) - rt_cost(fp)


def intraday_null(D, T, win_days, draws, rng):
    """(a) random direction per trade at the same fill (mirrored stop/target distances); (b) same trades placed on random days of
    the window (market entry at the same minute, same direction / distances)."""
    real = T["net"].sum(); fl = np.empty(draws); rd = np.empty(draws); n = len(T["d"])
    for i in range(draws):
        s = rng.choice([-1, 1], size=n)
        fl[i] = resim(D, T["d"], T["dir"] * s, T["fm"], T["fp"], T["sd"], T["td"], T["tx"], 3).sum()
        dd = rng.choice(win_days, size=n, replace=n > len(win_days))
        rd[i] = resim(D, dd, T["dir"], T["fm"], T["fp"], T["sd"], T["td"], T["tx"], 0).sum()
    return real, (1 + (rd >= real).sum()) / (draws + 1), (1 + (fl >= real).sum()) / (draws + 1)
