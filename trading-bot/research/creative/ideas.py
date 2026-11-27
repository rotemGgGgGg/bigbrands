"""11 mechanism-first NQ intraday ideas (who is forced to trade, when). Each has 2-4 variants written down before testing.
Data: HistData NSXUSD 1-min (NY time) 00:00-16:00; USDJPY / DAX Dukascopy 1-min (for cross-asset ideas). Cost 1.3 bp per trade.
Judged: choose on 2012-19, check 2020-26 and the last 2 years.
 H1  LONDON COMPRESSION  : tiny London range (< 0.6 x its 60-day median) -> first 5-min close outside it after 09:30, hold to 15:55
 H2  OVERNIGHT INVENTORY : big overnight move (> x ATR) + open in the top/bottom 20% of the overnight range -> fade 09:30-10:00/10:30
 H3  LEVERAGED-ETF REBAL : NQ up/down > x% at 15:30 -> LETFs must buy/sell into the close -> trade 15:30-15:59 with the day
 H4  ROUND-NUMBER PIN    : at 15:00 within 0.3 ATR of a 100 / 250 multiple -> trade toward it, exit on touch or 15:55 (0DTE pinning)
 H5  LUNCH REVERSAL      : 10:00-12:00 move > 0.3 ATR -> fade it 12:00-14:00 (liquidity drains at lunch)
 H6  YEN LEAD            : USDJPY up overnight (risk-on) while NQ fell (or reverse) -> NQ catches up 09:30-12:00 / 15:55
 H7  DAX LEAD            : DAX 03:00-09:30 move vs NQ same window disagree -> NQ follows DAX 09:30-12:00
 H8  POST-SHOCK DAY      : yesterday's range > 2 ATR -> fade today's first 30 minutes 10:00-12:00
 H9  ONE-SIDED OPEN      : >=20 new highs and <=2 new lows in the first 30 min (or mirror) -> trend day, hold 10:00-15:55
 H10 MOC IMBALANCE       : 15:00-15:50 move sign -> trade 15:50-15:59 with / against it
 H11 NARROW IB           : 09:30-10:30 range < 0.35 ATR -> first break of it after 10:30, stop at IB middle, hold to 15:55"""
import os as _os; DATA = _os.path.join(_os.path.expanduser(_os.environ.get("EDGE_DATA", "~/edge-data")), "")  # raw data + caches (set EDGE_DATA to move it)
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../spmodel")); sys.path.insert(0, os.path.join(H, "../multi"))
sys.path.insert(0, os.path.join(H, "../vidstrats"))
from lbr import days
import mdata
SP = DATA; BP = 1.3
G = days("NSXUSD"); DAYS = sorted(G)
RNG_RTH = pd.Series({d: G[d][1][570:960].max() - G[d][2][570:960].min() for d in DAYS}); ATR = RNG_RTH.rolling(14).mean().shift(1)
CLOSE = pd.Series({d: G[d][3][959] for d in DAYS}); PREV = CLOSE.shift(1)
LR = pd.Series({d: G[d][1][:360].max() - G[d][2][:360].min() for d in DAYS}); LRMED = LR.rolling(60).median().shift(1)


def pnl(side, ent, ex): return side * (ex / ent - 1) * 1e4 - BP


def bracket(d, side, i0, ent, stop, tgt, i1):
    o, h, l, c = G[d]; hh, ll = h[i0:i1], l[i0:i1]
    hs = np.nonzero(ll <= stop)[0] if side > 0 else np.nonzero(hh >= stop)[0]
    ht = (np.nonzero(hh >= tgt)[0] if side > 0 else np.nonzero(ll <= tgt)[0]) if tgt is not None else np.array([], int)
    ts, tt = (hs[0] if len(hs) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
    px = stop if ts <= tt and ts < 10 ** 9 else (tgt if tt < 10 ** 9 else c[i1 - 1])
    return pnl(side, ent, px)


def cross(sym):
    """per NY day: price at prev 16:00 (minute 959 of prev day), 03:00, 09:29"""
    f = SP + f"ideas_{sym}.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    from vs import frame
    df = frame(sym, "America/New_York"); m = df.index.hour * 60 + df.index.minute; d = df.index.normalize()
    out = pd.DataFrame({k: df.c[m == mm].groupby(d[m == mm]).last() for k, mm in (("p1559", 959), ("p0300", 180), ("p0929", 569))})
    out["prev1559"] = out.p1559.shift(1); pd.to_pickle(out, f); return out


def ideas():
    R = {}
    def add(name, d, v):
        R.setdefault(name, {})[d] = v
    UJ, DX = cross("USDJPY"), cross("DEUIDXEUR")
    mon = pd.Series(DAYS, index=DAYS).groupby(pd.DatetimeIndex(DAYS).to_period("M")).transform("max")
    for d in DAYS:
        A = ATR.get(d); pc = PREV.get(d)
        if not np.isfinite(A) or not np.isfinite(pc): continue
        o, h, l, c = G[d]; op = o[570]
        # H1
        lm = LRMED.get(d)
        if np.isfinite(lm):
            LH, LL = h[:360].max(), l[:360].min(); comp = LR[d] < 0.6 * lm
            for i in range(574, 720, 5):
                if c[i] > LH or c[i] < LL:
                    s = 1 if c[i] > LH else -1; ent = o[i + 1]; stop = (LH + LL) / 2
                    add("H1 compressed London: breakout to 15:55" if comp else "H1 control (normal London): breakout", d, bracket(d, s, i + 1, ent, stop, None, 955))
                    break
        # H2
        onH, onL = h[:570].max(), l[:570].min(); mv = (op - pc) / A; pos = (op - onL) / (onH - onL) if onH > onL else .5
        for th, ex in itertools.product((0.3, 0.5), (600, 630)):
            if mv > th and pos > 0.8: add(f"H2 overnight inventory fade x{th} exit {ex//60}:{ex%60:02d}", d, pnl(-1, op, c[ex - 1]))
            elif mv < -th and pos < 0.2: add(f"H2 overnight inventory fade x{th} exit {ex//60}:{ex%60:02d}", d, pnl(1, op, c[ex - 1]))
        # H3
        dm = c[929] / pc - 1
        for x in (0.01, 0.02):
            if abs(dm) > x: add(f"H3 LETF into close |day|>{int(x*100)}%", d, pnl(np.sign(dm), o[930], c[958]))
        # H4
        p15 = o[900]
        for step in (100, 250):
            rn = round(p15 / step) * step; dist = rn - p15
            if 0 < abs(dist) < 0.3 * A:
                s = np.sign(dist); add(f"H4 pin to {step}s from 15:00", d, bracket(d, s, 900, p15, p15 - s * abs(dist), rn, 955))
        # H5
        r1 = c[719] - o[600]
        if abs(r1) > 0.3 * A: add("H5 lunch reversal 12-14", d, pnl(-np.sign(r1), o[720], c[839]))
        # H6
        if d in UJ.index and np.isfinite(UJ.loc[d, "prev1559"]):
            uj = UJ.loc[d, "p0929"] / UJ.loc[d, "prev1559"] - 1; nq = op / pc - 1
            if np.sign(uj) != np.sign(nq) and abs(uj) > 0.002:
                for ex in (720, 955): add(f"H6 yen lead (USDJPY sign, |move|>0.2%) to {ex//60}:{ex%60:02d}", d, pnl(np.sign(uj), op, c[ex - 1]))
        # H7
        if d in DX.index and np.isfinite(DX.loc[d, "p0300"]):
            dx = DX.loc[d, "p0929"] / DX.loc[d, "p0300"] - 1; nq = c[569] / o[180] - 1
            if np.sign(dx) != np.sign(nq) and abs(dx) > 0.004: add("H7 DAX lead (|DAX 03-09:30|>0.4%, NQ disagrees) to 12:00", d, pnl(np.sign(dx), op, c[719]))
        # H8
        pr = RNG_RTH.shift(1).get(d)
        if np.isfinite(pr) and pr > 2 * A:
            f30 = c[599] - op
            if f30: add("H8 post-shock: fade first 30 min, 10-12", d, pnl(-np.sign(f30), o[600], c[719]))
        # H9
        hh, ll = h[570:600], l[570:600]; nh = int((hh[1:] > np.maximum.accumulate(hh)[:-1]).sum()); nl = int((ll[1:] < np.minimum.accumulate(ll)[:-1]).sum())
        if nh >= 20 and nl <= 2: add("H9 one-sided open -> trend to 15:55", d, pnl(1, o[600], c[954]))
        elif nl >= 20 and nh <= 2: add("H9 one-sided open -> trend to 15:55", d, pnl(-1, o[600], c[954]))
        # H10
        m10 = c[949] - o[900]
        if m10:
            add("H10 MOC with 15:00-15:50 move", d, pnl(np.sign(m10), o[950], c[958]))
            add("H10 MOC against 15:00-15:50 move", d, pnl(-np.sign(m10), o[950], c[958]))
        # H11
        ibh, ibl = h[570:630].max(), l[570:630].min()
        narrow = (ibh - ibl) < 0.35 * A
        for i in range(630, 900):
            if h[i] > ibh or l[i] < ibl:
                s = 1 if h[i] > ibh else -1; ent = ibh if s == 1 else ibl
                add("H11 narrow IB breakout to 15:55" if narrow else "H11 control (normal IB) breakout", d, bracket(d, s, i, ent, (ibh + ibl) / 2, None, 955))
                break
    return {k: pd.Series(v).sort_index() for k, v in R.items()}


def st(s):
    t = lambda x: x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0
    Y = s.index.year; I, O, L2 = s[Y <= 2019], s[Y >= 2020], s[s.index >= "2024-10-24"]; w, l = s[s > 0], s[s < 0]
    return dict(per_yr=len(s) / 14.8, win=100 * (s > 0).mean(), rr=w.mean() / -l.mean() if len(l) else np.nan, IS_bp=I.mean(), IS_t=t(I),
                OOS_bp=O.mean(), OOS_t=t(O), last2y_bp=L2.mean(), pos_yrs=f"{int((s.groupby(Y).sum() > 0).sum())}/15")


if __name__ == "__main__":
    R = ideas(); T = pd.DataFrame({k: st(v) for k, v in R.items() if len(v) >= 40}).T.sort_values("IS_t", ascending=False)
    pd.set_option("display.width", 230); print(T.round(2).to_string()); T.to_csv(SP + "creative_ideas.csv")
    pd.to_pickle(R, SP + "creative_series.pkl")
