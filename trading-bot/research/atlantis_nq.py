"""Own strategy from 'Atlantis' (QT) concepts, NQ-only (no SMT partner data):
90-min quarters (6h sessions from 18:00 NY → 06:00 session: 06:00/07:30/09:00/10:30). Window 09:00–10:30.
Bias = daily signature (prev day vs day before, + candle colour). Sweep of previous-quarter low (long) / high (short).
CISD ref = sweep candle if opposite colour, else last opposite candle before it. tCISD = later close beyond ref open.
Retest = wick back into the ref body with a small rejection (≤0.25 ATR), closing beyond ref open, in-direction candle.
Filters: displacement candle after tCISD (body ≥0.5 ATR & ≥60% range), true open (07:30 open) beyond the extreme.
Stop = extreme ∓ 1 tick, target 2R, BE at 1R, flat 10:30, one trade a day. Costs 1.25 pt."""
import numpy as np, pandas as pd
from engine import S, COST_PTS, IS_END
full = pd.read_pickle(S + "full1m.pkl")
tr_ = pd.concat([full.high - full.low, (full.high - full.close.shift()).abs(), (full.low - full.close.shift()).abs()], axis=1).max(axis=1)
atr = tr_.ewm(alpha=1 / 14, adjust=False).mean().shift().values
o, h, l, c = (full[k].values for k in ("open", "high", "low", "close"))
T = full.index; m = (T.hour * 60 + T.minute).values; d = np.array(T.date)
# daily bars (Globex day 18:00→17:00) for bias
gd = (T + pd.Timedelta(hours=6)).date
day = full.groupby(gd).agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
def bias_for(dd):
    k = day.index.get_indexer([dd])[0]
    if k < 2: return 0
    p, pp = day.iloc[k - 1], day.iloc[k - 2]
    sig = 1 if p.c > pp.h else -1 if p.c < pp.l else 1 if (p.l < pp.l and p.h <= pp.h and pp.l <= p.c <= pp.h) else -1 if (p.h > pp.h and p.l >= pp.l and pp.l <= p.c <= pp.h) else 0
    col = 1 if p.c > p.o else -1 if p.c < p.o else 0
    return sig if sig == col else 0

def run(use_bias=True, use_to=True, use_disp=True, rr=2.0):
    out = []
    idx = pd.Series(np.arange(len(full))).groupby(d).agg(["first", "last"])
    for dd, (a, b) in idx.iterrows():
        if pd.Timestamp(dd).weekday() >= 5: continue
        mm = m[a:b + 1]
        q2 = np.where((mm >= 450) & (mm < 540))[0] + a          # 07:30–09:00 previous quarter
        w = np.where((mm >= 540) & (mm < 630))[0] + a           # 09:00–10:30 window
        if len(q2) < 80 or len(w) < 80: continue
        qh, ql = h[q2].max(), l[q2].min(); to = o[q2[0]]
        bias = bias_for(gd[w[0]]) if use_bias else 0
        sides = [bias] if use_bias else [1, -1]
        if use_bias and bias == 0: continue
        best = None
        for s in sides:
            sw = next((i for i in w if (l[i] < ql if s == 1 else h[i] > qh)), None)
            if sw is None: continue
            # CISD reference candle
            ref = sw if ((c[sw] < o[sw]) if s == 1 else (c[sw] > o[sw])) else next((j for j in range(sw - 1, sw - 80, -1) if ((c[j] < o[j]) if s == 1 else (c[j] > o[j]))), None)
            if ref is None: continue
            rO, rC = o[ref], c[ref]; ext = l[sw] if s == 1 else h[sw]; conf = None; imp = False
            for i in range(sw + 1, w[-1] + 1):
                ext = min(ext, l[i]) if (s == 1 and conf is None) else (max(ext, h[i]) if conf is None else ext)
                if conf is None:
                    if (c[i] - rO) * s > 0: conf = i; vext = ext
                    else: continue
                body = abs(c[i] - o[i])
                if (c[i] - o[i]) * s > 0 and body >= 0.5 * atr[i] and body >= 0.6 * (h[i] - l[i]): imp = True
                if i == conf: continue
                inside = (rC <= l[i] <= rO) if s == 1 else (rO <= h[i] <= rC)
                rej = (min(o[i], c[i]) - l[i]) if s == 1 else (h[i] - max(o[i], c[i]))
                retest = inside and (o[i] - rO) * s >= 0 and (c[i] - rO) * s > 0 and (c[i] - o[i]) * s > 0 and 0 < rej <= 0.25 * atr[i]
                if not retest: continue
                if use_disp and not imp: continue
                if use_to and not ((to - vext) * s > 0): break
                best = (i, s, vext); break
            if best: break
        if not best: continue
        i, s, vext = best; e = c[i]; stop = vext - s * 0.25; risk = (e - stop) * s
        if risk < 1: continue
        tgt = e + s * rr * risk; be = False; px = None
        for j in range(i + 1, w[-1] + 1):
            if (l[j] <= stop) if s == 1 else (h[j] >= stop): px = stop if not ((o[j] <= stop) if s == 1 else (o[j] >= stop)) else o[j]; break
            if (h[j] >= tgt) if s == 1 else (l[j] <= tgt): px = tgt; break
            if not be and ((h[j] - e) * s >= risk if s == 1 else (e - l[j]) >= risk): be = True; stop = e
        if px is None: px = c[w[-1]]
        out.append((dd, s, (px - e) * s, risk))
    return pd.DataFrame(out, columns=["date", "side", "pts", "risk"])

def rep(name, t):
    r = (t.pts - COST_PTS) / t.risk; u = (t.pts - COST_PTS) * 2; y = pd.to_datetime(t.date)
    w, lo = u[u > 0], u[u <= 0]
    print(f"{name:34} trades {len(t):4} ({len(t)/81:.1f}/mo) win {100*(u>0).mean():4.1f}% RR {w.mean()/-lo.mean():.2f} avg {r.mean():+.3f}R "
          f"net ${u.sum():+,.0f}/MNQ PF {w.sum()/-lo.sum():.2f} IS {r[y<IS_END].mean():+.3f}R OOS {r[y>=IS_END].mean():+.3f}R yrs+ {(r.groupby(y.dt.year).sum()>0).sum()}/7")
rep("Atlantis-NQ (bias+TO+displacement)", run())
rep("  no bias (both directions)", run(use_bias=False))
rep("  no filters", run(False, False, False))
rep("  bias+filters, 3R", run(rr=3.0))
