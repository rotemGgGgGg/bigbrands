"""FRAMA & CPMA Strategy [CSM] — exact port of the open-source Pine (MPL-2.0, © chhagansinghmeena) and its library
BankNifty_CSM v3, run on MNQ with 1-minute exits (no guessing inside the 15-minute bar)."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "..")
from engine import S

def frama(src, L=21, mult=0.8):
    w = np.exp(np.log(mult) * np.arange(L) ** 2 / L ** 2)        # weight i applies to src[L-1-i] (i=0 → oldest)
    out = np.full(len(src), np.nan)
    for t in range(L - 1, len(src)):
        win = src[t - L + 1:t + 1]                                 # oldest … newest; src[L-1-i] = win[i]
        out[t] = (w * win).sum() / w.sum()
    return out

def cpma(b, L=21):
    c, o, h, l = b.close, b.open, b.high, b.low
    hl2, hlc3, ohlc4, hlcc4 = (h + l) / 2, (h + l + c) / 3, (o + h + l + c) / 4, (h + l + 2 * c) / 4
    ema = lambda s: s.ewm(span=L, adjust=False).mean()
    sma = lambda s: s.rolling(L).mean()
    raw = ((ema(c) + sma(hl2) + ema(o) + sma(h) + ema(l) + sma(ohlc4) + ema(hlc3) + sma(hlcc4)) / 8).values
    cv = c.values
    out = np.full(len(cv), np.nan)
    for t in range(len(cv)):
        if np.isnan(raw[t]):
            continue
        p = out[t - 1] if t else np.nan
        out[t] = raw[t] if np.isnan(p) else p + (cv[t] - p) / (L * (cv[t] / p) ** 4)
    return out

def signals(b):
    c = b.close.values
    F, C = frama(c), cpma(b)
    def cross(x, y):
        return (np.r_[False, (x[1:] > y[1:]) != (x[:-1] > y[:-1])]) & ~np.isnan(y) & np.r_[False, ~np.isnan(y[:-1])]
    lc = (cross(c, F) & (c > F)) | (cross(c, C) & (c > C))
    sc = (cross(c, F) & (c < F)) | (cross(c, C) & (c < C))
    sig = np.zeros(len(c)); s = 0
    out = np.zeros(len(c), int)
    for t in range(len(c)):
        new = 1 if lc[t] else -1 if sc[t] else s
        if new != s and (lc[t] or sc[t]):
            out[t] = new
        s = new
    return out, F, C

def run(full, tf="15min", tp=10.0, trail=0.5, sl=100.0, mode="real"):
    b = full.resample(tf, label="left", closed="left").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    sig, F, C = signals(b)
    t1 = full.index.values; o1, h1, l1, c1 = (full[k].values for k in ("open", "high", "low", "close"))
    step = pd.Timedelta(tf)
    trades = []
    pos = None
    sig_idx = np.where(sig != 0)[0]
    bt = b.index
    k = 0
    # iterate signal bars; each entry fills at the next 15-min bar open (first 1-min bar of it)
    for n, i in enumerate(sig_idx):
        if i + 1 >= len(bt): break
        side = sig[i]
        start = bt[i + 1]
        j = np.searchsorted(t1, start.to_datetime64())
        if j >= len(t1): break
        e = o1[j]
        act = b.close.values[i] + side * tp
        stop = (b.low.values[i] - sl) if side == 1 else (b.high.values[i] + sl)
        # walk minutes until stop / trailing exit; next signal handled by the loop above
        nxt = sig_idx[n + 1] if n + 1 < len(sig_idx) else None
        lim = np.searchsorted(t1, bt[nxt + 1].to_datetime64()) if nxt is not None and nxt + 1 < len(bt) else len(t1)
        active, best, why, px, x = False, None, None, None, j
        for x in range(j, lim):
            if side == 1:
                if not active and l1[x] <= stop: why, px = "stop", min(o1[x], stop) if x > j else stop; break
                if active and l1[x] <= best - trail: why, px = "trail", min(o1[x], best - trail); break
                if not active and h1[x] >= act:
                    active, best = True, act
                    if mode == "tv":                       # TradingView-style: assume the run to the high first
                        best = h1[x]
                    if c1[x] <= best - trail: why, px = "trail", best - trail; break
                if active: best = max(best, h1[x]) if mode == "tv" or x > j else best
            else:
                if not active and h1[x] >= stop: why, px = "stop", max(o1[x], stop) if x > j else stop; break
                if active and h1[x] >= best + trail: why, px = "trail", max(o1[x], best + trail); break
                if not active and l1[x] <= act:
                    active, best = True, act
                    if mode == "tv":
                        best = l1[x]
                    if c1[x] >= best + trail: why, px = "trail", best + trail; break
                if active: best = min(best, l1[x]) if mode == "tv" or x > j else best
        if why is None:
            if lim >= len(t1):
                break                                      # still open at the end of the data
            px = o1[lim]                                   # opposite signal: reversed at that bar's open
            trades.append(dict(entry_t=t1[j], side=side, e=e, exit=px, pts=(px - e) * side, why="reverse", exit_t=t1[lim]))
            pos = dict(e=e, side=side, exit_t=t1[lim])
        else:
            trades.append(dict(entry_t=t1[j], side=side, e=e, exit=px, pts=(px - e) * side, why=why, exit_t=t1[x]))
            pos = dict(e=e, side=side, exit_t=t1[x])
    tr = pd.DataFrame(trades).dropna(subset=["pts"])
    return tr, b, sig

if __name__ == "__main__":
    full = pd.read_pickle(S + "full1m.pkl")
    for mode in ("tv", "real"):
        tr, b, sig = run(full, mode=mode)
        tr.to_csv(f"frama_trades_{mode}.csv", index=False)
        net = tr.pts - 1.25
        y = pd.to_datetime(tr.entry_t).dt.year
        print(f"{mode:5} trades {len(tr)} win {100*(net>0).mean():.1f}% avg {net.mean():+.2f} pts (${2*net.mean():+.2f}/MNQ) "
              f"total ${2*net.sum():+.0f}/MNQ  avgW {net[net>0].mean():.1f} avgL {net[net<=0].mean():.1f}  by year {(2*net).groupby(y).sum().round().to_dict()}")
        print("   exits:", tr.why.value_counts().to_dict())
