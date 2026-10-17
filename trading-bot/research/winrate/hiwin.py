"""Hunt for ≥90 % win-rate variants: every validated directional edge × tiny target × wide stop × entry style × day filter.
Selection on 2020–23 (IS) only; 2024–26 (OOS) reported. Costs 1.25 pt + 1 pt stress (2.25 pt). Stop wins ties.
Market entries: next-minute open. Limit entries: filled only if price trades THROUGH by 1 tick (conservative)."""
import sys; sys.path.insert(0, "..")
import numpy as np, pandas as pd, itertools
from signals import D, N, day_sig, valid, sig_na_first, sig_na_fvg, sig_afternoon, sig_rebound, sig_gap, IS_END
from engine import walk
COST, TICK = 2.25, 0.25
F = pd.read_pickle("/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/hunt_feat.pkl")[0]
volr = F.vol_ratio.values; r5 = F.ret5.values
def run(sigs, a, b, entry, last=384):
    rows = []
    for i, j, s, lim in sigs:
        if np.isnan(day_sig[i]) or j > last: continue
        o, h, l, c = D.o[i], D.h[i], D.l[i], D.c[i]
        sc = day_sig[i] * o[0]
        if lim is not None or entry == "pull":
            lv = lim if lim is not None else o[j] - s * 0.05 * sc       # 'pull' = limit 0.05σ better than the signal open
            jj = next((x for x in range(j, last) if ((l[x] <= lv - TICK) if s == 1 else (h[x] >= lv + TICK))), None)
            if jj is None: continue
            e, j0, at_open = lv, jj, False
        else:
            e, j0, at_open = o[j], j, True
        tp = e + s * a * sc; sl = e - s * b * sc if b else None
        px, _, _ = walk(o, h, l, c, j0, s, e, sl, tp, last, at_open=at_open)
        rows.append((i, s, (px - e) * s - COST))
    return pd.DataFrame(rows, columns=["i", "side", "pts"])
SIGS = {"NA first break": sig_na_first(), "NA-FVG": sig_na_fvg(), "Afternoon 15:00": sig_afternoon(), "Rebound −1%": sig_rebound(), "Gap fade small": sig_gap()}
FILT = {"none": lambda i, s: True, "calm (yday range < 1.2× typical)": lambda i, s: volr[i] < 1.2, "with 5-day trend": lambda i, s: np.sign(r5[i]) == s}
yrs = np.array([d.year for d in D.days]); rows = []
for (name, sg), (fn, ff), entry, a, b in itertools.product(SIGS.items(), FILT.items(), ("mkt", "pull"), (0.05, 0.075, 0.1, 0.125, 0.15, 0.2), (1.0, 1.5, 2.0, 3.0, None)):
    sg2 = [x for x in sg if ff(x[0], x[2])]
    t = run(sg2, a, b, entry)
    if len(t) < 60: continue
    p = t.pts.values; y = yrs[t.i.values]; isd = y < 2024; w, lo = p[p > 0], p[p <= 0]
    cs = np.cumsum(2 * p)
    rows.append(dict(signal=name, filt=fn, entry=entry, tp_sig=a, sl_sig=b if b else "none", n=len(p), per_yr=round(len(p) / 6.75),
                     win=round(100 * (p > 0).mean(), 1), win_IS=round(100 * (p[isd] > 0).mean(), 1), win_OOS=round(100 * (p[~isd] > 0).mean(), 1),
                     avg_win=round(2 * w.mean(), 1) if len(w) else 0, avg_loss=round(2 * lo.mean(), 1) if len(lo) else 0,
                     usd=round(2 * p.mean(), 2), usd_IS=round(2 * p[isd].mean(), 2), usd_OOS=round(2 * p[~isd].mean(), 2),
                     worst=round(2 * p.min()), maxdd=round((cs - np.maximum.accumulate(cs)).min()),
                     yrs_pos=int((pd.Series(p).groupby(y).sum() > 0).sum()), pf=round(w.sum() / -lo.sum(), 2) if lo.sum() < 0 else 99))
R = pd.DataFrame(rows); R.to_csv("hiwin_grid.csv", index=False)
pd.set_option("display.width", 260); pd.set_option("display.max_rows", 80)
print("configs:", len(R))
sel = R[(R.win_IS >= 90) & (R.usd_IS > 0)]
print("IS win ≥ 90 % & IS $ > 0:", len(sel), "| of which OOS win ≥ 90 % & OOS $ > 0:", int(((sel.win_OOS >= 90) & (sel.usd_OOS > 0)).sum()))
print(sel[(sel.win_OOS >= 90) & (sel.usd_OOS > 0)].sort_values("usd", ascending=False).head(25).to_string(index=False))
