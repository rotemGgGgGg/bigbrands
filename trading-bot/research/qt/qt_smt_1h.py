"""SMT family tests on Yahoo 1h NQ/ES/YM (May 2024 → Oct 2026). Event study: forward NQ move in the signal's
direction after the divergence is first visible (bar close), horizons 1h/3h/to cycle end. Cost not included (points)."""
import numpy as np, pandas as pd
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
nq, es, ym = (pd.read_pickle(S + f"yf_{k}_1h.pkl") for k in ("NQ", "ES", "YM"))
idx = nq.index.intersection(es.index).intersection(ym.index)
nq, es, ym = nq.loc[idx], es.loc[idx], ym.loc[idx]
h = idx.hour
def cycle_keys(kind):
    if kind == "daily":       # sessions: Asia 18-24, London 0-6, AM 6-12, PM 12-18 → key = session start
        start = idx.floor("6h") if False else None
        sess = ((h - 18) % 24) // 6                       # 0 Asia,1 London,2 AM,3 PM
        day = (idx + pd.Timedelta(hours=6)).normalize()
        return day.astype("int64") // 10**9 * 10 + sess
    if kind == "weekly":      # each trading day (18:00 → 17:00) is a quarter
        return ((idx + pd.Timedelta(hours=6)).normalize()).astype("int64") // 10**9
def events(kind, a, b, hidden=False):
    k = pd.Series(cycle_keys(kind), index=idx)
    out = []
    keys = k.unique()
    pos = {kk: np.where(k.values == kk)[0] for kk in keys}
    for j in range(1, len(keys)):
        cur, prv = pos[keys[j]], pos[keys[j - 1]]
        if len(prv) < 4 or len(cur) < 3: continue
        for direction in (1, -1):   # 1 = bullish (lows), -1 = bearish (highs)
            if hidden:
                ra = a.close.values[prv].min() if direction == 1 else a.close.values[prv].max()
                rb = b.close.values[prv].min() if direction == 1 else b.close.values[prv].max()
                sa = a.close.values[cur]; sb = b.close.values[cur]
            else:
                ra = a.low.values[prv].min() if direction == 1 else a.high.values[prv].max()
                rb = b.low.values[prv].min() if direction == 1 else b.high.values[prv].max()
                sa = a.low.values[cur] if direction == 1 else a.high.values[cur]
                sb = b.low.values[cur] if direction == 1 else b.high.values[cur]
            ta = (sa < ra) if direction == 1 else (sa > ra)
            tb = (sb < rb) if direction == 1 else (sb > rb)
            # first bar where exactly one has taken its level so far (cumulative)
            ca, cb = np.cumsum(ta) > 0, np.cumsum(tb) > 0
            div = np.where(ca != cb)[0]
            both = np.where(ca & cb)[0]
            if len(div) and (not len(both) or div[0] < both[0]):
                i = cur[div[0]]; typ = "SMT"
            elif len(both):
                i = cur[both[0]]; typ = "both"
            else:
                continue
            if i + 1 >= len(idx): continue
            c0 = nq.close.values[i]
            f1 = (nq.close.values[min(i + 1, len(idx) - 1)] - c0) * direction
            f3 = (nq.close.values[min(i + 3, len(idx) - 1)] - c0) * direction
            fe = (nq.close.values[cur[-1]] - c0) * direction
            out.append(dict(t=idx[i], dir=direction, typ=typ, f1=f1, f3=f3, fend=fe))
    return pd.DataFrame(out)
def show(name, ev):
    for typ in ("SMT", "both"):
        e = ev[ev.typ == typ]
        if len(e) == 0: continue
        print(f"{name:40} {typ:5} n {len(e):4} | 1h win {100*(e.f1>0).mean():4.1f}% avg {e.f1.mean():+6.1f} | 3h win {100*(e.f3>0).mean():4.1f}% avg {e.f3.mean():+6.1f} | to cycle end win {100*(e.fend>0).mean():4.1f}% avg {e.fend.mean():+6.1f}")
for kind in ("daily", "weekly"):
    show(f"{kind} cycle NQ/ES wick SSMT", events(kind, nq, es))
    show(f"{kind} cycle NQ/ES hidden (close) SSMT", events(kind, nq, es, hidden=True))
    show(f"{kind} cycle NQ/YM wick SSMT", events(kind, nq, ym))
    show(f"{kind} cycle ES/YM wick SSMT (YM rule)", events(kind, es, ym))
# PSP on 1h and 4h: opposite candle colours NQ vs ES on a 3-bar swing of either → trade away from the swing
for tf in ("1h", "4h"):
    A = nq.resample(tf, offset="2h" if tf == "4h" else None).agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() if tf == "4h" else nq
    B = es.resample(tf, offset="2h").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() if tf == "4h" else es
    j = A.index.intersection(B.index); A, B = A.loc[j], B.loc[j]
    opp = np.sign(A.close - A.open) * np.sign(B.close - B.open) < 0
    sh = (A.high > A.high.shift()) & (A.high > A.high.shift(-1)) | (B.high > B.high.shift()) & (B.high > B.high.shift(-1))
    sl = (A.low < A.low.shift()) & (A.low < A.low.shift(-1)) | (B.low < B.low.shift()) & (B.low < B.low.shift(-1))
    for name, mask, d in (("PSP high → short", opp & sh & ~sl, -1), ("PSP low → long", opp & sl & ~sh, 1), ("swing high, same colour → short", ~opp & sh & ~sl, -1), ("swing low, same colour → long", ~opp & sl & ~sh, 1)):
        k = np.where(mask.values)[0]; k = k[k + 4 < len(A)]
        # confirmed at the close of the NEXT bar (swing needs it) → measure from there
        c0 = A.close.values[k + 1]
        for hz in (1, 3):
            f = (A.close.values[k + 1 + hz] - c0) * d
            print(f"PSP {tf} {name:32} n {len(k):4} +{hz} bars win {100*(f>0).mean():4.1f}% avg {f.mean():+6.1f}")
