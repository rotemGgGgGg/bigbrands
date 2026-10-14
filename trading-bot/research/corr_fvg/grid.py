"""Exhaustive Correlated-FVG study. Step 1: every NQ FVG event on 5m/15m/1h/4h with its attributes (correlation with ES/YM,
quarterly-theory quarter, session/killzone, HTF bias, size, displacement, NWOG/NDOG). Step 2: simulate every
entry × stop × R:R per event (conservative fills, 2.25 pt costs). Step 3: every filter combination = boolean masks → stats on
TRAIN (first 60 % of time) and TEST (last 40 %). One trade at a time is enforced when reporting finalists."""
import numpy as np, pandas as pd, itertools, pickle, sys, os
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
COST = 2.25
def load(tf):
    base = "5m" if tf in ("5m", "15m") else "1h"
    d = {s: pd.read_pickle(S + f"yf_{s}_{base}.pkl")[["open", "high", "low", "close"]] for s in ("NQ", "ES", "YM")}
    if tf in ("15m", "4h"):
        rule = "15min" if tf == "15m" else "4h"
        d = {s: x.resample(rule, origin=pd.Timestamp("2020-01-01 18:00", tz=x.index.tz)).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() for s, x in d.items()}
    idx = d["NQ"].index.intersection(d["ES"].index).intersection(d["YM"].index)
    return {s: x.loc[idx] for s, x in d.items()}
def fvg(x):
    h, l, c = x.high.values, x.low.values, x.close.values
    b = np.zeros(len(x), bool); s = np.zeros(len(x), bool)
    b[2:] = (l[2:] > h[:-2]) & (c[1:-1] > h[:-2]); s[2:] = (h[2:] < l[:-2]) & (c[1:-1] < l[:-2])
    return b, s
def quarter(ts, tf):
    """Quarterly-theory quarter (1..4, 0 = outside) and the time the quarter ends, per the indicator's cycle map."""
    t = ts.tz_convert("America/New_York"); sh = t - pd.Timedelta(hours=18)          # trading day starts 18:00
    if tf == "5m":   # 6h sessions, 90-min quarters
        mins = (sh.hour * 60 + sh.minute) % 360; q = mins // 90 + 1
        end = t + pd.to_timedelta(90 - mins % 90, unit="m")
    elif tf == "15m":  # daily cycle, 6h quarters
        mins = sh.hour * 60 + sh.minute; q = mins // 360 + 1; end = t + pd.to_timedelta(360 - mins % 360, unit="m")
    elif tf == "1h":   # weekly: Mon..Thu trading days
        wd = (sh + pd.Timedelta(days=0)).dayofweek; q = np.where(wd <= 3, wd + 1, 0)
        end = (sh.normalize() + pd.Timedelta(days=1) + pd.Timedelta(hours=18)).tz_localize(None).tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward")
    else:              # 4h: monthly, weeks 1..4
        q = np.minimum((sh.day - 1) // 7 + 1, 4); end = t + pd.Timedelta(days=7)
    return np.asarray(q), pd.DatetimeIndex(end)
def session(ts):
    t = ts.tz_convert("America/New_York"); m = t.hour * 60 + t.minute
    return np.select([(m >= 1080) | (m < 120), (m >= 120) & (m < 300), (m >= 570) & (m < 720), (m >= 810) & (m < 960)], ["asia", "london", "nyam", "nypm"], "other")

def build(tf):
    d = load(tf); nq = d["NQ"]; idx = nq.index
    o, h, l, c = (nq[k].values for k in ("open", "high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc))); atr = pd.Series(tr).ewm(alpha=1 / 14).mean().values
    ema = pd.Series(c).ewm(span=50).mean().values
    t_ny = idx.tz_convert("America/New_York")
    day_open = pd.Series(np.where((t_ny.hour == 18) & (t_ny.minute == 0), o, np.nan), index=idx).ffill().values
    nb, ns = fvg(nq); others = {s: fvg(d[s]) for s in ("ES", "YM")}
    oth_far = {s: (d[s].high.shift(2).values, d[s].low.shift(2).values, d[s].close.values) for s in ("ES", "YM")}
    q, qend = quarter(idx, tf); sess = session(idx)
    gapbreak = np.r_[False, False, np.diff(idx.asi8)[1:] > 3 * np.median(np.diff(idx.asi8))] | np.r_[False, np.diff(idx.asi8) > 3 * np.median(np.diff(idx.asi8))]
    EV = []
    for t in range(60, len(nq) - 2):
        for side, flag in ((1, nb[t]), (-1, ns[t])):
            if not flag: continue
            ce = {}
            for s in ("ES", "YM"): ce[s] = (others[s][0] if side == 1 else others[s][1])[t]
            near = l[t] if side == 1 else h[t]; far = h[t - 2] if side == 1 else l[t - 2]; gap = abs(near - far)
            body = abs(c[t - 1] - o[t - 1])
            EV.append(dict(t=t, ts=idx[t], side=side, near=near, far=far, gap_atr=gap / atr[t], disp_atr=body / atr[t], atr=atr[t],
                           es=ce["ES"], ym=ce["YM"], q=int(q[t]), qend=qend[t], sess=sess[t],
                           bias_ema=int(np.sign(c[t] - ema[t]) == side), bias_dopen=int(np.sign(c[t] - day_open[t]) == side),
                           ndog=bool(gapbreak[t] or gapbreak[t - 1])))
    return d, pd.DataFrame(EV), (o, h, l, c, atr)

def simulate(ev, arrs, idx, entry, stop, rr, expire, after_q, d, alive_req):
    o, h, l, c, atr = arrs; t = int(ev.t); side = ev.side; near, far = ev.near, ev.far; gap = abs(near - far)
    e = {"near": near, "ce": (near + far) / 2, "far": far}.get(entry)
    start = t + 1
    if after_q:
        start = int(np.searchsorted(idx.asi8, ev.qend.value)) if pd.notna(ev.qend) else len(idx)
        if start <= t: start = t + 1
    if entry == "market":
        fill = start
        if fill >= len(o): return np.nan
        e = o[fill]
    else:
        fill = None
        for k in range(start, min(start + expire, len(o))):
            # a touch fills the order FIRST — a bar that closes through the gap has traded through the entry (no look-ahead cancel)
            if (side == 1 and l[k] <= e) or (side == -1 and h[k] >= e): fill = k; break
            if (side == 1 and c[k] < far) or (side == -1 and c[k] > far): return np.nan
        if fill is None:
            # if the window passed before the quarter ended, gap may already be mitigated: check
            return np.nan
    if after_q:   # the gap must still be un-mitigated when the quarter closes (bars BEFORE the fill bar only)
        seg = c[t + 1:start]
        if len(seg) and ((side == 1 and (seg < far).any()) or (side == -1 and (seg > far).any())): return np.nan
    if alive_req:  # a matching gap in ES or YM must still be alive (not closed through) at the fill
        ok = False
        for s in ("ES", "YM"):
            if not getattr(ev, s.lower()): continue
            x = d[s]; ofar = (x.high.values[t - 2] if side == 1 else x.low.values[t - 2]); oc = x.close.values[t + 1:fill]   # bars CLOSED before the fill only
            if not ((side == 1 and (oc < ofar).any()) or (side == -1 and (oc > ofar).any())): ok = True
        if not ok: return np.nan
    sl = {"edge": far - side * 0.1 * gap, "atr05": far - side * 0.5 * atr[t], "atr1": e - side * 1.0 * atr[t], "c1": (l[t - 1] if side == 1 else h[t - 1])}[stop]
    risk = (e - sl) * side
    if risk < 2 or not np.isfinite(risk): return np.nan
    tp = e + side * rr * risk
    for k in range(fill, min(fill + 400, len(o))):
        if (side == 1 and l[k] <= sl) or (side == -1 and h[k] >= sl):
            px = sl if (k == fill and entry != "market") else (min(o[k], sl) if side == 1 else max(o[k], sl)); return (side * (px - e) - COST) / risk
        if (k > fill or entry == "market") and ((side == 1 and h[k] >= tp) or (side == -1 and l[k] <= tp)): return (side * (tp - e) - COST) / risk
    return (side * (c[min(fill + 399, len(o) - 1)] - e) - COST) / risk

if __name__ == "__main__":
    tf = sys.argv[1]
    d, EV, arrs = build(tf); idx = d["NQ"].index
    expire = {"5m": 36, "15m": 24, "1h": 24, "4h": 12}[tf]
    print(tf, "FVG events", len(EV), "corr any", int((EV.es | EV.ym).sum()), flush=True)
    sims = {}
    for entry, stop, rr, aq, alive in itertools.product(("near", "ce", "far", "market"), ("edge", "atr05", "atr1", "c1"), (1.0, 1.5, 2.0, 3.0), (False, True), (False, True)):
        sims[(entry, stop, rr, aq, alive)] = np.array([simulate(ev, arrs, idx, entry, stop, rr, expire, aq, d, alive) for ev in EV.itertuples(index=False)])
    pickle.dump((EV, sims, idx[0], idx[-1]), open(S + f"cfvg_{tf}.pkl", "wb"))
    print(tf, "simulated", len(sims), "exit configs", flush=True)
