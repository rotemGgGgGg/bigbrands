"""MATH ENGINE - one strategy built only from statistics of returns and from known, scheduled money flows. No chart patterns.
Every parameter is a textbook default fixed BEFORE looking at results (no grid search), so there is nothing to overfit.

Sleeves (each produces a daily return series, net of costs):
  S1 GOTOBI   - calendar flow: long JPY crosses 03:00->09:55 Tokyo, short 09:55->10:30 on Gotobi days (Ito & Yamada 2017).
  S2 IMOM     - intraday momentum (Gao, Han, Li & Zhou 2018): sign of (prev close -> first 30 min) return, held over the
                last 30 minutes of the session. NQ, S&P, DAX, Nikkei.
  S3 TSMOM    - time-series momentum (Moskowitz, Ooi & Pedersen 2012): average sign of 20/60/120-day log returns,
                position scaled to 10% annual vol by 20-day realised vol. 8 markets. Turnover costed.
  S4 SEASON   - intraday periodicity (Heston, Korajczyk & Sadka 2010): each half-hour of the session is traded in the
                direction of its own average over the previous 40 days, only when that average is > 2 standard errors.
  S5 REVERSAL - short-term reversal on equity indices: fade a day whose return exceeds 2 sigma (20-day), held next day.
Combination (walk-forward, no look-ahead): every sleeve vol-scaled to 10% by trailing 60-day vol; each January the weights
are re-set by risk parity over sleeves whose trailing (expanding) Sharpe is > 0 with at least 3 years of history;
portfolio vol-targeted to 10%; leverage capped at 3x. Everything before 2016 is warm-up; 2016-2026 is fully out of sample."""
import os as _os; DATA = _os.path.join(_os.path.expanduser(_os.environ.get("EDGE_DATA", "~/edge-data")), "")  # raw data + caches (set EDGE_DATA to move it)
import sys, os, math, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi")); sys.path.insert(0, os.path.join(H, "../combo15"))
import mdata
SP = DATA
IDX = ["NSXUSD", "SPXUSD", "DEUIDXEUR", "JPNIDXJPY"]; ALL = IDX + ["XAUUSD", "USDJPY", "EURUSD", "LIGHTCMDUSD"]
DATA = {s: mdata.load(s) for s in ALL}
def ser(D, x): return pd.Series(x, index=D["days"])


def s1_gotobi():
    return (pd.read_pickle(SP + "gotobi_book_usd.pkl") / 100000.0).rename("GOTOBI")          # 1 lot x 3 pairs on $100K


def s2_imom():
    out = []
    for s in IDX:
        D = DATA[s]; c, o = D["c"], D["o"]; pc = np.r_[np.nan, D["dc"][:-1]]
        r1 = c[:, 29] / pc - 1; ent, ex = o[:, 360], c[:, 389]
        pnl = np.sign(r1) * (ex / ent - 1) - D["bp"] / 1e4 * (r1 != 0)
        out.append(ser(D, np.nan_to_num(pnl)).rename(s))
    return pd.concat(out, axis=1).fillna(0).mean(1).rename("IMOM")


def s3_tsmom():
    out = []
    for s in ALL:
        D = DATA[s]; p = ser(D, D["dc"]); lr = np.log(p).diff()
        sig = sum(np.sign(lr.rolling(n).sum()) for n in (20, 60, 120)) / 3
        vol = lr.rolling(20).std() * math.sqrt(252); w = (sig * 0.10 / vol).clip(-3, 3).shift(1)          # decided yesterday
        pnl = w * (p.pct_change()) - (w.diff().abs() * D["bp"] / 1e4 / 2)
        out.append(pnl.fillna(0).rename(s))
    return pd.concat(out, axis=1).fillna(0).mean(1).rename("TSMOM")


def s4_season():
    out = []
    for s in ALL:
        D = DATA[s]; c, o = D["c"], D["o"]; b = np.arange(0, 390, 30)
        R = np.stack([c[:, min(x + 29, 389)] / o[:, x] - 1 for x in b], 1)                      # 13 half-hour returns
        Rd = pd.DataFrame(R, index=D["days"]); m = Rd.rolling(40).mean().shift(1); se = Rd.rolling(40).std().shift(1) / math.sqrt(40)
        pos = np.sign(m) * (m.abs() > 2 * se)
        pnl = (pos * Rd).sum(1) - pos.abs().sum(1) * D["bp"] / 1e4
        out.append(pnl.rename(s))
    return pd.concat(out, axis=1).fillna(0).mean(1).rename("SEASON")


def s5_reversal():
    out = []
    for s in IDX:
        D = DATA[s]; p = ser(D, D["dc"]); r = p.pct_change(); z = r / r.rolling(20).std().shift(1)
        w = (-np.sign(z) * (z.abs() > 2)).shift(1); pnl = w * r - w.abs() * D["bp"] / 1e4
        out.append(pnl.fillna(0).rename(s))
    return pd.concat(out, axis=1).fillna(0).mean(1).rename("REVERSAL")


def s6_fix():
    """month-end London 4pm fix (Melvin & Prins 2015): foreign equity holders re-hedge. If US equities rose over the month,
    USD is sold into the 16:00 London fix on the last business day: long EURUSD, short USDJPY, long gold (reverse if fell).
    Window 11:00 -> 16:00 London."""
    import sys as _s; _s.path.insert(0, os.path.join(H, "../vidstrats")); from vs import frame
    f = SP + "me_fix.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    spx = ser(DATA["SPXUSD"], DATA["SPXUSD"]["dc"]); out = []
    for sym, sgn in (("EURUSD", 1), ("USDJPY", -1), ("XAUUSD", 1)):
        df = frame(sym, "Europe/London"); d = df.index.normalize(); m = df.index.hour * 60 + df.index.minute
        a = df[m == 11 * 60].o.groupby(d[m == 11 * 60]).first(); b = df[m == 16 * 60].o.groupby(d[m == 16 * 60]).first()
        r = (b / a - 1).dropna(); bd = r.index[r.index.dayofweek < 5]
        last = pd.Series(bd, index=bd).groupby(bd.to_period("M")).max().values
        res = {}
        for day in map(pd.Timestamp, last):
            prev = spx[spx.index < day]; mstart = prev[prev.index < day.replace(day=1)]
            if len(mstart) == 0 or len(prev) == 0: continue
            mret = prev.iloc[-1] / mstart.iloc[-1] - 1
            res[day] = sgn * np.sign(mret) * r[day] - mdata.MK[sym][2] / 1e4
        out.append(pd.Series(res).rename(sym))
    x = pd.concat(out, axis=1).fillna(0).mean(1).rename("FIX"); pd.to_pickle(x, f); return x


def s7_tom():
    """turn of the month (Ariel 1987; Lakonishok & Smidt 1988): long equity indices from the close two days before month end
    to the close of the 3rd trading day of the new month (returns of last day, +1, +2, +3). One round trip cost."""
    out = []
    for s in ["NSXUSD", "SPXUSD", "DEUIDXEUR"]:
        D = DATA[s]; p = ser(D, D["dc"]); r = p.pct_change(); ix = p.index; per = ix.to_period("M")
        last = pd.Series(ix, index=ix).groupby(per).transform("max").values == ix.values
        rank = pd.Series(1, index=ix).groupby(per).cumsum().values
        hold = last | (rank <= 3); entry = np.r_[last[1:], False]                      # first held day is the last day
        pnl = r.where(hold, 0.0) - pd.Series(np.where(last, D["bp"] / 1e4, 0.0), index=ix)
        out.append(pnl.fillna(0).rename(s))
    return pd.concat(out, axis=1).fillna(0).mean(1).rename("TOM")


def sh(x): return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0.0


def combine(SL):
    """walk-forward risk parity over sleeves with positive expanding Sharpe (>=3y history), portfolio at 10% vol"""
    X = SL.copy(); vol = X.rolling(60, min_periods=40).std().shift(1) * math.sqrt(252)
    Z = (X * (0.10 / vol)).clip(-0.2, 0.2).fillna(0)                                         # each sleeve ~10% vol
    W = pd.DataFrame(0.0, index=Z.index, columns=Z.columns)
    for y in range(2015, 2027):
        hist = Z[Z.index.year < y]; cur = Z.index.year == y
        ok = [c for c in Z if hist[c].ne(0).any() and (y - hist[c][hist[c] != 0].index[0].year) >= 3 and sh(hist[c]) > 0]
        if ok: W.loc[cur, ok] = 1.0 / len(ok)
    P = (Z * W).sum(1); pv = P.rolling(60, min_periods=40).std().shift(1) * math.sqrt(252)
    lev = (0.10 / pv).clip(0, 3).fillna(1); return P * lev, W


if __name__ == "__main__":
    SL = pd.concat([s1_gotobi(), s2_imom(), s3_tsmom(), s4_season(), s5_reversal(), s6_fix(), s7_tom()], axis=1).sort_index()
    SL = SL[SL.index >= "2012-01-01"].fillna(0); Y = SL.index.year
    print("===== sleeves alone (no selection, textbook parameters)")
    for c in SL:
        x = SL[c]; xs = x[x != 0]
        print(f"{c:9s} Sharpe 2012-15 {sh(x[Y<=2015]):5.2f} | 2016-19 {sh(x[(Y>=2016)&(Y<=2019)]):5.2f} | 2020-26 {sh(x[Y>=2020]):5.2f} | "
              f"win days {100*(xs>0).mean():4.1f}% | RR {xs[xs>0].mean()/-xs[xs<0].mean():.2f} | pos years {(x.groupby(Y).sum()>0).sum()}/15")
    print("\nOOS correlation 2016-26:\n", SL[Y >= 2016].corr().round(2).to_string())
    P, W = combine(SL); o = P[P.index.year >= 2016]; cs = (1 + o).cumprod()
    print("\n===== MATH ENGINE portfolio (walk-forward weights, 10% vol target), 2016-2026 fully out of sample")
    print(f"Sharpe {sh(o):.2f} | t {o.mean()/o.std()*math.sqrt(len(o)):.2f} | CAGR {100*(cs.iloc[-1]**(252/len(o))-1):.1f}% | "
          f"max DD {100*(cs/cs.cummax()-1).min():.1f}% | win days {100*(o[o!=0]>0).mean():.1f}% | RR {o[o>0].mean()/-o[o<0].mean():.2f}")
    print("per year %:", (100 * o.groupby(o.index.year).apply(lambda r: (1 + r).prod() - 1)).round(1).to_dict())
    print("weights used each year:\n", W.groupby(W.index.year).mean().loc[2015:].round(2).to_string())
    pd.to_pickle(dict(SL=SL, P=P, W=W), SP + "mathengine.pkl")
    import combo3 as K
    O = (P.index.year >= 2016); days = np.nonzero(O)[0]; st = days[:-60:5]
    for vol in (.05, .08, .10):
        T = K.prop((P * vol / .10 * 50000).values, st); pv = T[T.r == "payout"]
        print(f"prop 50K @ {int(vol*100)}% vol: payout {100*len(pv)/len(T):.0f}% fail {100*(T.r=='fail').mean():.0f}% days to payout {pv.d_payout.median()}")
