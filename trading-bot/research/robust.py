"""Robustness checks for the leaders: parameter neighbourhood (no re-optimisation), per-year, Lucid 50K sim."""
import pickle, json, sys
import numpy as np, pandas as pd
from engine import summarize, S, COST_PTS, PT_USD, IS_END
import strategies_a as A

D = pickle.load(open(S + "D.pkl", "rb"))

# --- Noise-Area with lookback / decision-interval knobs
def noise_area_p(D, look=14, every=30, vwap_entry=False, vwap_trail=False):
    move = np.abs(D.c / D.o[:, :1] - 1)
    rows = []
    marks = [k for k in range(390) if (k + 1) % every == 0 and k < 389 and k >= 29]
    for i in range(look, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4:
            continue
        sig = move[i - look:i].mean(0)
        o0, pc = D.o[i, 0], D.c[i - 1, 389]
        ub, lb = max(o0, pc) * (1 + sig), min(o0, pc) * (1 - sig)
        vw = D.vwap(i); c, o = D.c[i], D.o[i]
        pos, ent = 0, 0.0
        for k in marks:
            want = pos
            if pos == 1 and c[k] < (max(ub[k], vw[k]) if vwap_trail else lb[k]): want = 0
            if pos == -1 and c[k] > (min(lb[k], vw[k]) if vwap_trail else ub[k]): want = 0
            if c[k] > ub[k] and (not vwap_entry or c[k] > vw[k]): want = 1
            elif c[k] < lb[k] and (not vwap_entry or c[k] < vw[k]): want = -1
            if want != pos:
                px = o[k + 1]
                if pos: rows.append((D.days[i], pos, (px - ent) * pos, np.nan))
                pos, ent = want, px
        if pos: rows.append((D.days[i], pos, (c[389] - ent) * pos, np.nan))
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])

def crabel_p(D, mult=2.0, look=10):
    O, H, L = D.o[:, 0], D.h.max(1), D.l.min(1)
    noise = np.minimum(H - O, O - L)
    rows = []
    for i in range(25, len(D.days)):
        st = noise[i - look:i].mean() * mult
        up, dn = O[i] + st, O[i] - st
        hh, ll = D.h[i], D.l[i]
        j = next((j for j in range(390) if hh[j] >= up or ll[j] <= dn), None)
        if j is None or st <= 0: continue
        if hh[j] >= up and ll[j] <= dn:
            rows.append((D.days[i], 1, -(up - dn), up - dn)); continue
        side = 1 if hh[j] >= up else -1
        e = max(D.o[i, j], up) if side == 1 else min(D.o[i, j], dn)
        stop = dn if side == 1 else up
        px, _, _ = A.walk(D.o[i], hh, ll, D.c[i], j, side, e, stop, None, 389, at_open=False)
        rows.append((D.days[i], side, (px - e) * side, abs(e - stop)))
    return pd.DataFrame(rows, columns=["date", "side", "pts", "risk"])

def lucid(tr, usd_per_pt, target=3000.0, dd=2000.0):
    daily = ((tr.pts - COST_PTS) * usd_per_pt).groupby(tr.date).sum()
    days = list(daily.index); res = []; lens = []
    for i in range(len(days)):
        bal = peak = 0.0
        for k, d in enumerate(days[i:]):
            bal += daily[d]
            if bal <= peak - dd: res.append("fail"); break
            if bal >= target: res.append("pass"); lens.append(k + 1); break
            peak = max(peak, bal)
    n = len(res)
    return round(100 * res.count("pass") / max(n, 1)), int(np.median(lens)) if lens else None

def size_for(tr):
    """MNQ contracts so that in-sample daily P&L std = $300 (in-sample data only)."""
    d = (tr[pd.to_datetime(tr.date) < IS_END].pts - COST_PTS).groupby(tr.date).sum() * PT_USD
    return max(1, int(round(300 / d.std())))

out = []
def rec(name, tr):
    r = summarize(name, tr)
    n = size_for(tr)
    r["mnq"] = n
    r["lucid_pass"], r["days_to_pass"] = lucid(tr, PT_USD * n)
    y = tr.assign(y=pd.to_datetime(tr.date).dt.year, net=tr.pts - COST_PTS).groupby("y").net.sum().mul(PT_USD).round()
    r["by_year"] = y.to_dict()
    out.append(r); print(json.dumps(r, default=str), flush=True)

for look in (10, 14, 20):
    for every in (15, 30, 60):
        rec(f"NA base look{look} every{every}", noise_area_p(D, look, every))
for look in (10, 14, 20):
    rec(f"NA vwap look{look} every30", noise_area_p(D, look, 30, True, True))
for mult in (1.5, 2.0, 2.5):
    for look in (5, 10, 20):
        rec(f"Crabel x{mult} look{look}", crabel_p(D, mult, look))
rec("IB breakout close-entry", A.ib_breakout(D, True, True))
rec("IB breakout no-VWAP", A.ib_breakout(D, False, True))
for k in (0.2, 0.25, 0.3):
    rec(f"Williams k{k}", A.williams(D, k))
rec("5m ORB first candle 10R", A.orb5_first_candle(D))
rec("5m ORB first candle 5R", A.orb5_first_candle(D, 5.0))
rec("Gap fill zone", A.gap_fill(D))
pd.DataFrame(out).to_csv("robust.csv", index=False); print("DONE")
