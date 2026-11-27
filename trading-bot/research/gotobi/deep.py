"""Model 1 deep test: the Gotobi fix (Strange Labs Case 01) exactly as the PDF/EA states, then variations.
Calendar: 5,10,15,20,25 and LAST day of month, shifted back to the previous Japanese bank day (EA ShiftBack/IsGotobi).
Legs: long 03:00 Tokyo -> 09:55, short 09:55 -> 10:30. No stop. Mondays included (long from the Sunday open).
Units: pips (0.01), costs per leg round trip in pips ~ their IC spread + $7/lot: USDJPY 1.6, EURJPY 1.7, GBPJPY 1.9.
Data: Dukascopy 1-min bid 2012-2026 (their data: IC Markets 2018-Jul 2026). 2012-2017 is data the vendor never showed.
Sections: A exact replication; B statistics (placebo 1000 random day-sets, bootstrap CI, decay by year);
C variation grid chosen on 2012-19 and judged on 2020-26; D math overlays (day weights, run-into-fix conditioning,
mean-variance pair weights, vol targeting, trend filter, catastrophe stop); E sizing (Kelly, drawdown, $ per year)."""
import os as _os; DATA = _os.path.join(_os.path.expanduser(_os.environ.get("EDGE_DATA", "~/edge-data")), "")  # raw data + caches (set EDGE_DATA to move it)
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
from full import load
from gotobi import is_bd
PAIRS = ["USDJPY", "EURJPY", "GBPJPY"]; CP = {"USDJPY": 1.6, "EURJPY": 1.7, "GBPJPY": 1.9}
RNG = np.random.default_rng(55)
def tk(hhmm):                                   # Tokyo clock -> index in the 18:00-UTC grid (03:00 Tokyo = 0)
    h, m = map(int, hhmm.split(":")); return (h - 3) * 60 + m


def gotobi_days(y0=2012, y1=2026):
    out = set()
    for y in range(y0, y1 + 1):
        for mth in range(1, 13):
            last = (pd.Timestamp(y, mth, 1) + pd.offsets.MonthEnd(0)).day
            for d in (5, 10, 15, 20, 25, last):
                t = pd.Timestamp(y, mth, d)
                while not is_bd(t): t -= pd.Timedelta(days=1)
                out.add(t)
    return sorted(d for d in out if d <= pd.Timestamp("2026-11-13"))


def nominal_of(d, G):
    """which nominal gotobi date a trade day stands for (5,10,15,20,25,'E')"""
    for k in range(0, 6):
        t = d + pd.Timedelta(days=k)
        if t.month != d.month and k > 0 and t.day > 3: break
        last = (t + pd.offsets.MonthEnd(0)).day
        if t.day == last: return "E"
        if t.day in (5, 10, 15, 20, 25):
            back = t
            while not is_bd(back): back -= pd.Timedelta(days=1)
            if back == d: return str(t.day)
    return "?"


DATA = {p: load(p) for p in PAIRS}
GOT = gotobi_days(); GS = set(GOT)
ORD = [d for d in pd.bdate_range("2012-01-02", "2026-11-13") if is_bd(d) and d not in GS]


def legs(p, days, l_in="03:00", flip="09:55", s_in=None, s_out="10:30", stop_pips=None):
    """per-day long pips and short pips (net of cost). s_in defaults to flip."""
    A = DATA[p]; c = CP[p]; li, fi, si, so = tk(l_in), tk(flip), tk(s_in or flip), tk(s_out); L, S = {}, {}
    for d in days:
        a = A.get(d)
        if a is None: continue
        o, h, l, cl = a
        e, x = o[li], o[fi]
        if stop_pips:
            hit = np.nonzero(l[li:fi] <= e - stop_pips / 100)[0]
            if len(hit): x = e - stop_pips / 100
        L[d] = (x - e) * 100 - c
        e, x = o[si], o[so]
        if stop_pips:
            hit = np.nonzero(h[si:so] >= e + stop_pips / 100)[0]
            if len(hit): x = e + stop_pips / 100
        S[d] = (e - x) * 100 - c
    return pd.Series(L, dtype=float), pd.Series(S, dtype=float)


def usd_per_pip(d):
    a = DATA["USDJPY"].get(d); return 1000.0 / (a[0][415] if a is not None else 130.0)   # 1 lot: 1000 JPY per pip


def tst(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0


def desc(x, lab):
    w, l = x[x > 0], x[x < 0]
    return (f"{lab:38s} n {len(x):5d} | {x.mean():6.2f} pips | t {tst(x):5.2f} | win {100*(x>0).mean():5.1f}% | "
            f"RR {w.mean()/-l.mean():4.2f} | PF {w.sum()/-l.sum():4.2f}")


if __name__ == "__main__":
    pd.set_option("display.width", 250); out = []
    print("===== A. exact replication (pips/day per pair, both legs)")
    book = {}
    for p in PAIRS:
        L, S = legs(p, GOT); T = (L + S).dropna(); book[p] = T
        Lo, So = legs(p, ORD); To = (Lo + So).dropna()
        for lab, x in (("2018-Jul2026 (vendor window)", T[(T.index >= "2018-01-01") & (T.index <= "2026-07-15")]),
                       ("2012-2017 (never shown)", T[T.index < "2018-01-01"]), ("2023-2026", T[T.index >= "2023-01-01"]),
                       ("ordinary days 2012-26 (control)", To)):
            print(f"{p} " + desc(x, lab))
        print(f"{p} legs 2012-26: long {L.mean():.2f} (t {tst(L):.2f}) | short {S.mean():.2f} (t {tst(S):.2f})")
    B = pd.DataFrame(book).fillna(0); usd = pd.Series({d: usd_per_pip(d) for d in B.index}); BK = B.sum(1) * usd
    for a, b, lab in (("2018-01-01", "2026-07-15", "vendor window"), ("2012-01-01", "2017-12-31", "2012-2017"), ("2012-01-01", "2026-12-31", "all")):
        x = BK[(BK.index >= a) & (BK.index <= b)]; cs = x.cumsum()
        print(f"BOOK $ 1 lot x3 {lab:14s}: net ${x.sum():,.0f} | PF {x[x>0].sum()/-x[x<0].sum():.2f} | win days {100*(x>0).mean():.1f}% | "
              f"avg win ${x[x>0].mean():.0f} / avg loss ${-x[x<0].mean():.0f} (RR {x[x>0].mean()/-x[x<0].mean():.2f}) | maxDD ${(cs-cs.cummax()).min():,.0f}")
    print("per year $:", BK.groupby(BK.index.year).sum().round(-2).astype(int).to_dict())

    print("\n===== B. statistics")
    Bp = B.mean(1)                                                  # average pips per pair per day
    pl = []
    for _ in range(1000):
        days = RNG.choice(len(ORD), size=len(GOT), replace=False); dd = [ORD[i] for i in days]
        x = pd.concat([sum(legs(p, dd)) for p in PAIRS], axis=1).mean(1); pl.append(x.mean())
    pl = np.array(pl); print(f"placebo 1000 random ordinary-day sets: mean {pl.mean():.2f}, 99.9th {np.percentile(pl, 99.9):.2f} pips | gotobi {Bp.mean():.2f} -> p < {max(1, (pl >= Bp.mean()).sum())/1000:.3f}")
    bs = [Bp.sample(len(Bp), replace=True, random_state=i).mean() for i in range(2000)]
    print(f"bootstrap 95% CI of pips/day/pair: [{np.percentile(bs, 2.5):.2f}, {np.percentile(bs, 97.5):.2f}]")
    yr = Bp.groupby(Bp.index.year).agg(["mean", "count", lambda x: tst(x)]); yr.columns = ["pips", "n", "t"]
    print("by year (avg pips/pair/day):\n", yr.round(2).T.to_string())
    Ls = pd.concat([legs(p, GOT)[0] for p in PAIRS], axis=1).mean(1); Ss = pd.concat([legs(p, GOT)[1] for p in PAIRS], axis=1).mean(1)
    Lo = pd.concat([legs(p, ORD)[0] for p in PAIRS], axis=1).mean(1); So = pd.concat([legs(p, ORD)[1] for p in PAIRS], axis=1).mean(1)
    edge = pd.DataFrame({"long_minus_ord": Ls.groupby(Ls.index.year).mean() - Lo.groupby(Lo.index.year).mean(),
                         "short_minus_ord": Ss.groupby(Ss.index.year).mean() - So.groupby(So.index.year).mean()})
    print("leg edge over ordinary days, by year (pips):\n", edge.round(2).T.to_string())
    # slope of decay: OLS of yearly edge on year
    for c in edge:
        y = edge[c].values; x = edge.index.values - 2012; b = np.polyfit(x, y, 1)[0]
        r = y - np.polyval(np.polyfit(x, y, 1), x); se = math.sqrt((r @ r) / (len(x) - 2) / ((x - x.mean()) @ (x - x.mean())))
        print(f"  trend of {c}: {b:+.2f} pips per year (t {b/se:.2f})")
    # where the fix-minute edge sits each year: best short entry minute
    print("short leg (to 10:30) by entry minute, gotobi minus ordinary, by period:")
    for a, b in ((2012, 2017), (2018, 2022), (2023, 2025), (2026, 2026)):
        dg = [d for d in GOT if a <= d.year <= b]; do = [d for d in ORD if a <= d.year <= b]; row = {}
        for m in ("09:45", "09:50", "09:53", "09:54", "09:55", "09:56", "10:00"):
            g = np.mean([legs(p, dg, s_in=m)[1].mean() for p in PAIRS]); o = np.mean([legs(p, do, s_in=m)[1].mean() for p in PAIRS]); row[m] = g - o
        print(f"  {a}-{b}:", {k: round(v, 2) for k, v in row.items()})

    print("\n===== C. variation grid (avg of 3 pairs; choose on 2012-19, judge 2020-26 and 2023-26)")
    rows = []
    for li, fl, so in itertools.product(("03:00", "05:00", "07:00", "08:00", "09:00"), ("09:50", "09:53", "09:54", "09:55"), ("10:05", "10:15", "10:20", "10:30", "10:45")):
        x = pd.concat([sum(legs(p, GOT, li, fl, None, so)) for p in PAIRS], axis=1).mean(1); Y = x.index.year
        rows.append(dict(long_in=li, flip=fl, short_out=so, IS=x[Y <= 2019].mean(), IS_t=tst(x[Y <= 2019]), OOS=x[Y >= 2020].mean(),
                         OOS_t=tst(x[Y >= 2020]), y23_26=x[Y >= 2023].mean(), win=100 * (x > 0).mean()))
    R = pd.DataFrame(rows).sort_values("IS_t", ascending=False); print(R.head(12).round(2).to_string(index=False))
    base = R[(R.long_in == "03:00") & (R.flip == "09:55") & (R.short_out == "10:30")]; print("vendor params:\n", base.round(2).to_string(index=False))
    print(f"variants OOS>0: {(R.OOS > 0).sum()}/{len(R)} | best-IS variant OOS {R.iloc[0].OOS:.2f} vs vendor {base.OOS.iloc[0]:.2f}")

    print("\n===== D. math overlays (each: rule fixed on 2012-19, judged 2020-26; base = vendor rules)")
    T = {p: legs(p, GOT) for p in PAIRS}; base = pd.concat([T[p][0] + T[p][1] for p in PAIRS], axis=1).mean(1); Y = base.index.year; I, O = Y <= 2019, Y >= 2020
    def rep(lab, x):
        x = x.reindex(base.index).fillna(0); print(f"  {lab:46s} IS {x[I].mean():5.2f} t {tst(x[I]):5.2f} | OOS {x[O].mean():5.2f} t {tst(x[O]):5.2f} | "
                                                   f"OOS Sharpe/day {x[O].mean()/x[O].std():.3f} | 23-26 {x[Y>=2023].mean():5.2f}")
    rep("base (vendor rules)", base)
    # D1 day weights: shrunk IS t per nominal day, weight = max(0, t)/mean
    nom = pd.Series({d: nominal_of(d, None) for d in base.index}); st = base[I].groupby(nom[I]).apply(tst)
    print("  IS t by nominal day:", st.round(2).to_dict(), "| OOS mean by day:", base[O].groupby(nom[O]).mean().round(2).to_dict())
    w = nom.map((st.clip(lower=0) / st.clip(lower=0).mean()).to_dict()).fillna(0); rep("D1 weight by nominal day (IS t)", base * w)
    # D2 run-into-fix conditioning of the short leg: run = 08:00->09:54 move in pips (avg pairs); short only if run > 0
    run = pd.concat([pd.Series({d: (DATA[p][d][3][tk("09:54")] - DATA[p][d][0][tk("08:00")]) * 100 for d in GOT if d in DATA[p]}) for p in PAIRS], axis=1).mean(1)
    Sx = pd.concat([T[p][1] for p in PAIRS], axis=1).mean(1); Lx = pd.concat([T[p][0] for p in PAIRS], axis=1).mean(1)
    b = np.polyfit(run[I.astype(bool)[:len(run)]] if False else run[run.index.year <= 2019], Sx[Sx.index.year <= 2019], 1)
    print(f"  short-leg pips vs run-into-fix (IS slope {b[0]:+.3f} pips per pip of run)")
    rep("D2 short only if price ran up 08:00-09:54", Lx + Sx.where(run > 0, 0))
    rep("D2b short sized by run (clip 0..2x, IS-scaled)", Lx + Sx * (run / run[run.index.year <= 2019].abs().mean()).clip(0, 2))
    # D3 mean-variance pair weights on IS
    M = pd.DataFrame({p: T[p][0] + T[p][1] for p in PAIRS}).fillna(0); mu, Sg = M[I].mean().values, M[I].cov().values
    wv = np.linalg.solve(Sg, mu); wv = np.clip(wv, 0, None); wv = wv / wv.sum() * 3
    print("  D3 IS mean-variance weights:", dict(zip(PAIRS, wv.round(2)))); rep("D3 mean-variance pair weights", (M * wv).mean(1))
    rep("D3b USDJPY+EURJPY only", M[["USDJPY", "EURJPY"]].mean(1))
    # D4 vol targeting: size ~ 1/(20-day avg of |long pips|) (known before the day)
    vol = M.abs().mean(1).rolling(20).mean().shift(1); rep("D4 inverse-vol sizing", base * (vol[I].mean() / vol).clip(0, 2))
    # D5 trend filter: long leg only when USDJPY 20-gotobi-day trend up (close of fix)
    fx = pd.Series({d: DATA["USDJPY"][d][0][415] for d in GOT if d in DATA["USDJPY"]}); tr = (fx / fx.shift(10) - 1).shift(1)
    rep("D5 long leg only in USDJPY uptrend", Lx.where(tr > 0, 0) + Sx)
    rep("D5b long leg only in downtrend", Lx.where(tr <= 0, 0) + Sx)
    # D6 catastrophe stop and plain stops
    for sp in (15, 25, 50):
        x = pd.concat([sum(legs(p, GOT, stop_pips=sp)) for p in PAIRS], axis=1).mean(1); rep(f"D6 stop {sp} pips each leg", x)
    # D7 short leg only (the sharp part) and long only
    rep("D7 short leg only", Sx); rep("D7b long leg only", Lx)
    # D8 swap-free long (23:00 UTC = 08:00 Tokyo) as the vendor tried
    x = pd.concat([sum(legs(p, GOT, "08:00")) for p in PAIRS], axis=1).mean(1); rep("D8 long from 08:00 Tokyo", x)

    print("\n===== E. sizing, 1 lot x 3 pairs on $100K, vendor rules")
    x = BK; mu, sd = x.mean(), x.std(); f = mu / sd ** 2
    print(f"  per gotobi day: mean ${mu:.0f}, sd ${sd:.0f}; per-day Sharpe {mu/sd:.3f}; ~71 days/yr -> annual Sharpe {mu/sd*math.sqrt(71):.2f}")
    print(f"  worst day ${x.min():,.0f} ({x.idxmin().date()}); 1-in-100 day ${np.percentile(x, 1):,.0f}; $/yr ~ ${mu*71:,.0f} (= {mu*71/1000:.1f}% on 100K)")
    print(f"  full-Kelly fraction of $ variance: {f*1e5:.1f}x 1-lot-sets per $100K (use 1/4 Kelly -> {f*1e5/4:.1f}x)")
    BK.to_pickle(DATA + "gotobi_book_usd.pkl")
