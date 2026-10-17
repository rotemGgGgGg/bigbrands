"""Two Instagram strategies (frames only — no audio; rules read from the on-screen drawings).
A) TSR "9AM": 08:00–08:59 NY candle high/low. From 09:00 to 11:00, price sweeps one side; then a 1-minute CISD (close beyond the open
   of the run of opposite-colour candles that made the sweep) → enter next minute; stop = sweep extreme ± tick; target = other
   side of the 8:00 candle (also fixed 1:2 variant).
B) Reese "sponsored 5m gap": a 5-minute FVG whose displacement leg STARTED at a sweep of liquidity (prior-day / overnight high-low or
   the 08:00 candle extreme, within the previous 6 bars) → limit at the gap's near edge; stop beyond the sweep extreme; target the
   opposite liquidity (prior-day or overnight extreme in the trade direction) or 2R. Control: the same FVGs WITHOUT a sweep.
MNQ 1-minute 2020-01 → 2026-10 (24h frame for the 08:00 candle and overnight), costs 2.25 pt, TRAIN 2020–23 / TEST 2024–26."""
import sys, itertools; sys.path.insert(0, ".."); sys.path.insert(0, "../influencers")
import numpy as np, pandas as pd
from engine import S
from lib import o as RO, h as RH, l as RL, c as RC, N, DAYS, VALID, okprev, PDH, PDL, F, trade, limit_fill, TICK
full = pd.read_pickle(S + "full1m.pkl"); full = full[~full.index.duplicated()]
idxmap = {d: i for i, d in enumerate(DAYS)}
eight = full[(full.index.hour == 8)]; g8 = eight.groupby(eight.index.normalize().tz_localize(None))
H8 = g8.high.max(); L8 = g8.low.min()
rows = []
def rec(name, R):
    R = pd.DataFrame(R, columns=["i", "R", "rr"])
    if len(R) < 30: return
    tr = DAYS[R.i].year < 2024; w = R.R > 0
    rows.append(dict(strategy=name, n=len(R), per_yr=round(len(R) / 6.75), win_tr=round(100 * w[tr].mean(), 1), win_te=round(100 * w[~tr].mean(), 1),
                     R_tr=round(R.R[tr].mean(), 3), R_te=round(R.R[~tr].mean(), 3), plan_rr=round(R.rr.median(), 2),
                     real_rr=round(R.R[w].mean() / -R.R[~w].mean(), 2) if w.any() and (~w).any() else np.nan))
# ---------------- A) 9AM model, executed on the 24h frame 09:00–11:00 then RTH walk until 15:55
pre = full[(full.index.hour * 60 + full.index.minute >= 540) & (full.index.hour * 60 + full.index.minute < 570)]
for tmode in ("candle", "rr2", "rr1"):
    R = []
    for i in range(N):
        d = DAYS[i]
        if not VALID[i] or d not in H8.index: continue
        hi, lo = H8[d], L8[d]
        pm = pre[pre.index.normalize().tz_localize(None) == d]
        # stitch 09:00–09:29 (pre) + RTH minutes into one path
        O_ = np.r_[pm.open.values, RO[i]]; H_ = np.r_[pm.high.values, RH[i]]; L_ = np.r_[pm.low.values, RL[i]]; C_ = np.r_[pm.close.values, RC[i]]
        off = len(pm); end = off + 120                                    # until 11:00
        swept = None; ext = None
        for k in range(1, min(end, len(C_) - 1)):
            if swept is None:
                if L_[k] < lo: swept, ext = 1, L_[k]
                elif H_[k] > hi: swept, ext = -1, H_[k]
                continue
            ext = min(ext, L_[k]) if swept == 1 else max(ext, H_[k])
            # CISD: close beyond the open of the latest run of opposite-colour candles
            j = k - 1; run_open = None
            while j > 0 and ((C_[j] < O_[j]) if swept == 1 else (C_[j] > O_[j])): run_open = O_[j]; j -= 1
            if run_open is not None and ((C_[k] > run_open) if swept == 1 else (C_[k] < run_open)):
                e = O_[k + 1]; sl = ext - swept * TICK; risk = abs(e - sl)
                tgt = hi if swept == 1 else lo
                if tmode == "rr2": tgt = e + swept * 2 * risk
                if tmode == "rr1": tgt = e + swept * risk
                if risk < 2 or (tgt - e) * swept <= 0: break
                rr = abs(tgt - e) / risk; px = None
                for x in range(k + 1, len(C_)):
                    if x - off >= 384: px = C_[x]; break
                    if (swept == 1 and L_[x] <= sl) or (swept == -1 and H_[x] >= sl): px = (min(O_[x], sl) if swept == 1 else max(O_[x], sl)); break
                    if (swept == 1 and H_[x] >= tgt + TICK) or (swept == -1 and L_[x] <= tgt - TICK): px = tgt; break
                if px is None: px = C_[-1]
                R.append((i, (swept * (px - e) - 2.25) / risk, rr)); break
            if k > end: break
    rec(f"A 9AM model target={tmode}", R)
# ---------------- B) sponsored vs unsponsored 5m FVG (RTH 09:35–14:00)
for sponsored, tmode in itertools.product((True, False), ("liq", "rr2")):
    R = []
    for i in range(1, N):
        if not okprev[i]: continue
        d = DAYS[i]; levels_lo = [PDL[i], F.onl.values[i]] + ([L8[d]] if d in L8.index else []); levels_hi = [PDH[i], F.onh.values[i]] + ([H8[d]] if d in H8.index else [])
        o5 = RO[i, ::5][:78]; h5 = RH[i, :390].reshape(78, 5).max(1); l5 = RL[i, :390].reshape(78, 5).min(1); c5 = RC[i, 4::5][:78]
        for k in range(8, 54):
            for side in (1, -1):
                fvg = (h5[k - 2] < l5[k]) if side == 1 else (l5[k - 2] > h5[k])
                if not fvg: continue
                win = slice(k - 7, k - 1); ext = l5[win].min() if side == 1 else h5[win].max()
                had_sweep = any(ext < x for x in levels_lo) if side == 1 else any(ext > x for x in levels_hi)
                if had_sweep != sponsored: continue
                lvl = l5[k] if side == 1 else h5[k]; sl = ext - side * TICK
                f = limit_fill(i, (k + 1) * 5, (k + 1) * 5 + 60, lvl, side)
                if not f: break
                m, e = f; risk = abs(e - sl)
                if risk < 2: break
                if tmode == "liq":
                    cands = [x for x in (levels_hi if side == 1 else levels_lo) if (x - e) * side > risk]
                    if not cands: break
                    tgt = min(cands) if side == 1 else max(cands)
                else: tgt = e + side * 2 * risk
                r = trade(i, m, side, sl, tgt, entry=e, at_open=False)
                if r: R.append((i, r[0] / risk, abs(tgt - e) / risk))
                break
            else: continue
            break
    rec(f"B {'SPONSORED' if sponsored else 'unsponsored'} 5m FVG target={tmode}", R)
out = pd.DataFrame(rows); out.to_csv("results.csv", index=False); pd.set_option("display.width", 220); print(out.to_string(index=False))
