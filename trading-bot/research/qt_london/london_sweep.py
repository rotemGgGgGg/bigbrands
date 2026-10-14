"""'London takes liquidity → NY AM draws to the opposite liquidity' (from the WhatsApp group, Aug 24 2026):
  "London took SSL, so I come bullish into AM and look for longs up to Friday's BSL."
Rules tested (NY time, Databento MNQ 1-minute 24h, 2020-01 → 2026-10):
  ref levels  : 'pd'  = previous Globex session (18:00→17:00) high/low  (on Mondays that is Friday = the post)
                'asia'= Asia range 18:00→00:00 high/low   ·  'pdrth' = previous RTH 09:30–16:00 high/low
  London      : 02:00–05:00 (killzone) or 00:00–08:30 (full).  Sweep = London trades beyond ONE side only.
  Direction   : SSL taken → long, target = ref HIGH (BSL).  BSL taken → short, target = ref LOW.
  Entry       : 'open'  = 09:30 market · 'mss5'/'mss15' = first 5/15-min close beyond the highest high (lowest low) of the
                previous 3 bars between 09:30 and 11:00 · 'disc' = limit at the 50 % level of [London extreme, target]
                (premium/discount) between 08:30 and 11:00.
  Stop        : London extreme ∓ 0.05 × daily σ.   Exit: target, stop, or 16:00.   Also a fixed 1:2 target variant.
  Filters     : mondays-only ('Friday' wording) · TDO (entry below/above the 00:00 True Day Open in the trade's favour).
  Skip if the target was already hit before the entry. Costs 1.25 pt + 1 pt stress. Stop wins ties."""
import sys, itertools; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S
COST, TICK = 2.25, 0.25
full = pd.read_pickle(S + "full1m.pkl"); full = full[~full.index.duplicated()]
m = (full.index.hour * 60 + full.index.minute).values
sess = (full.index + pd.Timedelta(hours=6)).normalize()          # Globex session date (18:00 → next day)
O, H, L, C = (full[k].values for k in ("open", "high", "low", "close"))
groups = pd.Series(np.arange(len(full))).groupby(sess.values).agg(["first", "last"])
dates = list(groups.index); rows = []
sig = pd.Series({d: np.nan for d in dates})
rth_move = {}
for d, (a, b) in groups.iterrows():
    mm = m[a:b + 1]; r = (mm >= 570) & (mm < 960)
    if r.sum() > 300: rth_move[d] = abs(C[a:b + 1][r][-1] / O[a:b + 1][r][0] - 1)
sig = pd.Series(rth_move).rolling(14).mean().shift()
def win_idx(a, b, lo, hi, wrap=False):
    mm = m[a:b + 1]
    if wrap: k = np.nonzero((mm >= lo) | (mm < hi))[0]
    else: k = np.nonzero((mm >= lo) & (mm < hi))[0]
    return k + a
def trade(side, e, sl, tp, k0, kend):
    for k in range(k0, kend + 1):
        if (side == 1 and L[k] <= sl) or (side == -1 and H[k] >= sl):
            px = sl if k == k0 else (min(O[k], sl) if side == 1 else max(O[k], sl)); return (side * (px - e) - COST) / abs(e - sl), k
        if k > k0 and ((side == 1 and H[k] >= tp + TICK) or (side == -1 and L[k] <= tp - TICK)): return (side * (tp - e) - COST) / abs(e - sl), k
    return (side * (C[kend] - e) - COST) / abs(e - sl), kend
for di in range(1, len(dates)):
    d, dp = dates[di], dates[di - 1]
    if d.weekday() >= 5 or (d - dp).days > 4 or d not in sig.index or not np.isfinite(sig.get(d, np.nan)): continue
    a, b = groups.loc[d]; pa, pb = groups.loc[dp]
    sg = sig[d] * C[a]
    ref = {"pd": (H[pa:pb + 1].max(), L[pa:pb + 1].min())}
    k = win_idx(pa, pb, 570, 960)
    if len(k) > 300: ref["pdrth"] = (H[k].max(), L[k].min())
    k = win_idx(a, b, 1080, 1440)
    if len(k) > 200: ref["asia"] = (H[k].max(), L[k].min())
    tdo_k = win_idx(a, b, 0, 1)
    tdo = O[tdo_k[0]] if len(tdo_k) else np.nan
    rth = win_idx(a, b, 570, 960)
    if len(rth) < 300: continue
    kend = rth[-1]
    for (lname, (l0, l1)), (rname, (rh, rl)) in itertools.product((("kz", (120, 300)), ("full", (0, 510))), ref.items()):
        lk = win_idx(a, b, l0, l1)
        if len(lk) < 60: continue
        lh, ll = H[lk].max(), L[lk].min()
        took_ssl, took_bsl = ll < rl - TICK, lh > rh + TICK
        if took_ssl == took_bsl: continue
        side = 1 if took_ssl else -1
        ext = ll if side == 1 else lh; tgt = rh if side == 1 else rl
        sl = ext - side * 0.05 * sg
        # did price already reach the target between London end and each entry? computed per entry
        for entry in ("open", "mss5", "mss15", "disc"):
            if entry == "open": ke = rth[0]; e = O[ke]
            elif entry in ("mss5", "mss15"):
                n = 5 if entry == "mss5" else 15; ke = None
                bars = [(rth[j:j + n]) for j in range(0, 90, n)]
                for t in range(3, len(bars)):
                    prev = np.concatenate(bars[t - 3:t]); cur = bars[t]
                    if side == 1 and C[cur[-1]] > H[prev].max(): ke = cur[-1] + 1; break
                    if side == -1 and C[cur[-1]] < L[prev].min(): ke = cur[-1] + 1; break
                if ke is None: continue
                e = O[ke]
            else:
                lvl = (ext + tgt) / 2; ke = None
                for k in win_idx(a, b, 510, 660):
                    if k <= lk[-1]: continue
                    if (side == 1 and L[k] <= lvl - TICK) or (side == -1 and H[k] >= lvl + TICK): ke = k; break
                if ke is None: continue
                e = lvl
            seg = slice(lk[-1] + 1, ke)
            if (side == 1 and (H[seg].max(initial=-1e18) >= tgt or L[seg].min(initial=1e18) <= sl)) or \
               (side == -1 and (L[seg].min(initial=1e18) <= tgt or H[seg].max(initial=-1e18) >= sl)): continue
            if (side == 1 and not (sl < e < tgt)) or (side == -1 and not (tgt < e < sl)): continue
            risk = abs(e - sl)
            if risk < 3: continue
            tdo_ok = (side == 1 and e < tdo) or (side == -1 and e > tdo)
            for tmode in ("liq", "rr2"):
                tp = tgt if tmode == "liq" else e + side * 2 * risk
                R, kx = trade(side, e, sl, tp, ke if entry != "disc" else ke, kend)
                rows.append(dict(date=d, dow=d.weekday(), london=lname, ref=rname, entry=entry, tmode=tmode, side=side,
                                 planned_rr=round(abs(tp - e) / risk, 2), R=R, tdo_ok=tdo_ok))
T = pd.DataFrame(rows); T.to_pickle(S + "qt_london_trades.pkl")
def summ(x):
    if len(x) < 15: return None
    w, lo = x.R[x.R > 0], x.R[x.R <= 0]; y = x.date.dt.year if hasattr(x.date, "dt") else pd.to_datetime(x.date).year
    return dict(n=len(x), win=round(100 * (x.R > 0).mean(), 1), plan_rr=round(x.planned_rr.median(), 2),
                real_rr=round(w.mean() / -lo.mean(), 2) if len(lo) and len(w) else np.nan, exp_R=round(x.R.mean(), 3),
                IS=round(x.R[y < 2024].mean(), 3), OOS=round(x.R[y >= 2024].mean(), 3), yrs_pos=int((x.R.groupby(y).sum() > 0).sum()))
T["date"] = pd.to_datetime(T.date)
out = []
for keys, g in T.groupby(["london", "ref", "entry", "tmode"]):
    for filt, gg in (("all", g), ("monday", g[g.dow == 0]), ("tdo", g[g.tdo_ok]), ("monday+tdo", g[(g.dow == 0) & g.tdo_ok])):
        for sd, g3 in (("both", gg), ("long", gg[gg.side == 1]), ("short", gg[gg.side == -1])):
            s = summ(g3)
            if s: out.append(dict(zip(["london", "ref", "entry", "tmode"], keys), filt=filt, side=sd, **s))
R = pd.DataFrame(out); R.to_csv("results.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 100)
print("configs:", len(R))
print("\n— exactly the WhatsApp rule (Monday, Friday levels = 'pd', London killzone, target = Friday BSL/SSL):")
print(R[(R.ref == "pd") & (R.filt == "monday") & (R.london == "kz") & (R.tmode == "liq") & (R.side == "both")].to_string(index=False))
print("\n— best 15 by IS expectancy (n≥40), with OOS:")
print(R[R.n >= 40].sort_values("IS", ascending=False).head(15).to_string(index=False))
print("\n— any config with win ≥ 70 % and planned RR ≥ 2 (n≥30):"); print(R[(R.n >= 30) & (R.win >= 70) & (R.plan_rr >= 2)].to_string(index=False))
