"""'Time & price' on NQ (HistData NSXUSD 1-min, New York time, 2012-2026, cost 1.3 bp round trip). Three readings:
H1 TIME-BASED PRICE LEVELS (ICT): the 00:00 NY 'midnight open' and the 08:30 open as fair value. At T (09:30/09:45/10:00), if
   price is more than k x ATR away from the level, trade back to it (fade) - or away from it (continue). Target = the level,
   stop = s x distance, flat at 12:00 or 16:00.
H2 MACROS (ICT): 20-30 minute windows 08:50, 09:50, 10:50, 11:50, 13:10, 15:15. Rule: trade the window in the direction of
   price vs the midnight open (or vs 09:30 open), continuation or fade. Control: the same rule on every other 20-min window.
H3 GANN SQUARE OF 9: levels (sqrt(prev close) + j*0.25)^2 (45-degree steps). First RTH touch of a level -> fade it,
   stop 0.25 step, target 0.5 / 1 step, flat 16:00. Placebo: the same with the level grid shifted by random fractions.
Every rule: choose on 2012-19, judge 2020-26."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi"))
import mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
BP = 1.3; RNG = np.random.default_rng(3)


def days():
    f = SP + "tp_nq.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    df = mdata.histdata("NSXUSD"); df = df[~df.index.duplicated()].sort_index(); m = df.index.hour * 60 + df.index.minute; d = df.index.normalize()
    sel = m < 16 * 60; x = df[sel]; mm = m[sel]; dd = d[sel]; G = {}
    for day, idx in pd.Series(np.arange(len(x)), index=dd).groupby(level=0):
        if day.weekday() >= 5: continue
        g = x.iloc[idx.values].set_index(mm[idx.values]).reindex(range(960))
        if g.c.iloc[570:960].notna().sum() < 300: continue
        g["c"] = g.c.ffill().bfill()
        for k in "ohl": g[k] = g[k].fillna(g.c)
        G[day] = g[list("ohlc")].values.T
    pd.to_pickle(G, f); return G


G = days(); DAYS = sorted(G)
RTH_RANGE = pd.Series({d: G[d][1][570:960].max() - G[d][2][570:960].min() for d in DAYS}); ATR = RTH_RANGE.rolling(14).mean().shift(1)
PCLOSE = pd.Series({d: G[d][3][959] for d in DAYS}).shift(1)
def tst(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0


def sim(o, h, l, c, i0, side, ent, stop, tgt, i1):
    hh, ll = h[i0:i1], l[i0:i1]
    hs = np.nonzero(ll <= stop)[0] if side > 0 else np.nonzero(hh >= stop)[0]
    ht = np.nonzero(hh >= tgt)[0] if side > 0 else np.nonzero(ll <= tgt)[0]
    ts, tt = (hs[0] if len(hs) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
    px = stop if ts <= tt and ts < 10 ** 9 else (tgt if tt < 10 ** 9 else c[i1 - 1])
    return side * (px - ent) / ent * 1e4 - BP


def summ(lab, s):
    Y = s.index.year; I, O = s[Y <= 2019], s[Y >= 2020]; w, l = s[s > 0], s[s < 0]
    return dict(rule=lab, n_yr=len(s) / 14.8, win=100 * (s > 0).mean(), rr=w.mean() / -l.mean() if len(l) else np.nan,
                IS=I.mean(), IS_t=tst(I), OOS=O.mean(), OOS_t=tst(O), pos_yrs=int((s.groupby(Y).sum() > 0).sum()))


def h1():
    rows = []
    for lvl, T, k, s, ex, mode in itertools.product(("midnight", "0830"), (570, 585, 600), (0.1, 0.25), (0.5, 1.0), (720, 960), ("fade", "cont")):
        out = {}
        for d in DAYS:
            a = ATR.get(d)
            if not np.isfinite(a): continue
            o, hi, lo, c = G[d]; L = o[0] if lvl == "midnight" else o[510]; ent = o[T]; dist = ent - L
            if abs(dist) < k * a: continue
            side = -np.sign(dist) if mode == "fade" else np.sign(dist)
            tgt = L if mode == "fade" else ent + side * abs(dist); stp = ent - side * s * abs(dist)
            out[d] = sim(o, hi, lo, c, T, side, ent, stp, tgt, ex)
        rows.append(summ(f"H1 {lvl} T{T//60}:{T%60:02d} k{k} s{s} exit{ex//60} {mode}", pd.Series(out)))
    return pd.DataFrame(rows)


MACROS = [(530, 20), (590, 20), (650, 20), (710, 20), (790, 30), (915, 30)]
def h2():
    rows = []
    wins = [(st, 20) for st in range(570, 940, 10)]
    for ref, mode in itertools.product(("midnight", "0930"), ("cont", "fade")):
        res = {"macro": {}, "other": {}}
        for d in DAYS:
            o, hi, lo, c = G[d]; R = o[0] if ref == "midnight" else o[570]
            for st, ln in MACROS + [w for w in wins if w not in MACROS]:
                if ref == "0930" and st < 570: continue
                ent = o[st]; sd = np.sign(ent - R) * (1 if mode == "cont" else -1)
                if sd == 0: continue
                p = sd * (c[st + ln - 1] / ent - 1) * 1e4 - BP
                key = "macro" if (st, ln) in MACROS else "other"; res[key].setdefault(d, 0.0); res[key][d] += p
        for key in res: rows.append(summ(f"H2 {key} windows, ref {ref}, {mode}", pd.Series(res[key])))
        # per macro
        for st, ln in MACROS:
            out = {}
            for d in DAYS:
                if ref == "0930" and st < 570: continue
                o, hi, lo, c = G[d]; R = o[0] if ref == "midnight" else o[570]; ent = o[st]
                sd = np.sign(ent - R) * (1 if mode == "cont" else -1)
                if sd: out[d] = sd * (c[st + ln - 1] / ent - 1) * 1e4 - BP
            if out: rows.append(summ(f"H2 macro {st//60}:{st%60:02d} ref {ref} {mode}", pd.Series(out)))
    return pd.DataFrame(rows)


def gann(offset, tgt_steps, stop_steps=0.25, step=0.25):
    out = {}
    for d in DAYS:
        pc = PCLOSE.get(d)
        if not np.isfinite(pc): continue
        o, hi, lo, c = G[d]; r = math.sqrt(pc); lv = np.array([(r + (j + offset) * step) ** 2 for j in range(-8, 9)])
        p0 = o[570]
        for i in range(571, 930):                                         # first touch of any level from the open side
            up = lv[(lv > p0) & (lv <= hi[i])]; dn = lv[(lv < p0) & (lv >= lo[i])]
            if len(up) or len(dn):
                if len(up): L, side = up.min(), -1
                else: L, side = dn.max(), 1
                sp = (math.sqrt(L) + step) ** 2 - L
                out[d] = sim(o, hi, lo, c, i + 1, side, L, L - side * stop_steps * sp, L + side * tgt_steps * sp, 960); break
            p0 = c[i]
    return pd.Series(out)


def h3():
    rows = []
    for tg in (0.5, 1.0):
        s = gann(0.0, tg); rows.append(summ(f"H3 Gann sq9 fade, target {tg} step", s))
        pl = [gann(u, tg).mean() for u in RNG.uniform(0.1, 0.9, 60)]
        rows[-1]["placebo_beat%"] = 100 * np.mean(np.array(pl) < s.mean())
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    for fn in (h1, h2, h3):
        T = fn(); T.to_csv(SP + f"tp_{fn.__name__}.csv", index=False)
        print(f"\n===== {fn.__name__}: {len(T)} rules | positive IS {(T.IS>0).sum()} | IS t>=2 {(T.IS_t>=2).sum()} | OOS t>=2 {(T.OOS_t>=2).sum()}")
        print(T.sort_values("IS_t", ascending=False).head(12).round(2).to_string(index=False))
