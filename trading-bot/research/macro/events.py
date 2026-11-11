"""Macro-event strategies: NFP, CPI/PPI (mid-month 8:30 releases), FOMC (14:00), on NQ, S&P, gold, USDJPY, EURUSD, 2012-2026.
Event days:
  FOMC - exact, from federalreserve.gov (fomc.py).
  NFP  - one per month: the Friday (day <= 10) with the largest 08:30 spike in USDJPY+EURUSD (one-per-month, so no selection
         on size beyond picking which candidate Friday was the release day).
  MID  - CPI/PPI/retail-sales window: per month, the 2 weekdays between the 9th and 17th with the largest 08:30 spike.
         Caveat: no free historical CPI/PPI calendar was reachable, so MID is detected from the price spike itself.
Spike = range of 08:30-08:31 bars / median 1-min range 08:00-08:29 (FX average). Trades enter strictly after the spike minute.
Strategies (per event x market): momentum / fade of the first k minutes after release, exits at several times; pre-event drift.
Costs = market bp round trip, doubled for entries within 5 minutes of a release (news spreads).
Selection uses 2012-19 only; 2020-26 is out of sample."""
import sys, os, math, pickle, itertools
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi")); sys.path.insert(0, os.path.join(H, "../vidstrats"))
import numpy as np, pandas as pd, mdata
from vs import frame
import fomc
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/macro/"
MKS = {"NQ": "NSXUSD", "SPX": "SPXUSD", "GOLD": "XAUUSD", "USDJPY": "USDJPY", "EURUSD": "EURUSD"}
T0 = 7 * 60                      # grid starts 07:00 NY, 600 minutes to 17:00


def grid(name):
    f = SP + f"grid_{name}.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    df = frame(MKS[name], "America/New_York"); m = df.index.hour * 60 + df.index.minute; d = df.index.normalize()
    sel = (m >= T0) & (m < T0 + 600); x = df[sel]; mm = (m[sel] - T0).values; dd = d[sel]
    C = {}
    for day, idx in pd.Series(np.arange(len(x)), index=dd).groupby(level=0):
        if day.weekday() >= 5 or len(idx) < 300: continue
        g = x.iloc[idx.values].set_index(mm[idx.values]).reindex(range(600)); g["c"] = g.c.ffill().bfill()
        for k in "ohl": g[k] = g[k].fillna(g.c)
        C[day] = np.stack([g.o.values, g.h.values, g.l.values, g.c.values])
    days = sorted(C); A = np.stack([C[d] for d in days])                  # (nd, 4, 600)
    # previous 16:00 close (minute 540 = 16:00) for overnight drift
    out = dict(days=pd.DatetimeIndex(days), A=A, bp=mdata.MK[MKS[name]][2]); pd.to_pickle(out, f); return out


def spikes():
    f = SP + "spikes.pkl"
    if os.path.exists(f): return pd.read_pickle(f)
    r = []
    for n in ("USDJPY", "EURUSD"):
        G = grid(n); A = G["A"]; rng = A[:, 1] - A[:, 2]; i0 = 90               # 08:30 = minute 90
        base = np.median(rng[:, 60:90], axis=1); sp = (A[:, 1, i0:i0 + 2].max(1) - A[:, 2, i0:i0 + 2].min(1)) / np.where(base > 0, base, np.nan)
        r.append(pd.Series(sp, index=G["days"]))
    s = pd.concat(r, axis=1).mean(1); pd.to_pickle(s, f); return s


def event_days():
    s = spikes(); df = pd.DataFrame({"sp": s}); df["ym"] = df.index.to_period("M"); df["dom"] = df.index.day; df["wd"] = df.index.weekday
    nfp = df[(df.wd == 4) & (df.dom <= 10)].groupby("ym").sp.idxmax().values
    mid = df[(df.dom >= 9) & (df.dom <= 17) & (df.wd <= 4)].groupby("ym").sp.nlargest(2).index.get_level_values(1)
    mid = [d for d in mid if d not in set(nfp)]
    return {"NFP": pd.DatetimeIndex(nfp), "MID": pd.DatetimeIndex(sorted(mid)), "FOMC": pd.DatetimeIndex(fomc.dates())}


def run_event(G, days, t_rel, kind, k, exit_m, bp):
    """kind: mom/fade (direction = sign of move from t_rel-1 close to t_rel+k-1 close; enter open of t_rel+k), long/short drift."""
    pos = G["days"].get_indexer(days); out = {}
    A = G["A"]
    for d, i in zip(days, pos):
        if i < 0: continue
        a = A[i]
        if kind in ("mom", "fade"):
            mv = a[3, t_rel + k - 1] - a[3, t_rel - 1]
            if mv == 0: continue
            side = np.sign(mv) * (1 if kind == "mom" else -1); e = t_rel + k
            ent, ex = a[0, e], a[3, exit_m - 1]
            cost = bp * (2 if k <= 5 else 1)
        else:                                                               # pre-event drift: enter at k minutes before release
            side = 1 if kind == "pre_long" else -1; ent, ex = a[0, t_rel - k], a[3, t_rel - 1]; cost = bp
        out[d] = side * (ex - ent) / ent * 1e4 - cost
    return pd.Series(out, dtype=float)


def tstat(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0


if __name__ == "__main__":
    E = event_days(); print({k: len(v) for k, v in E.items()})
    TR = {"NFP": 90, "MID": 90, "FOMC": 420}                                     # 08:30 / 14:00 in grid minutes
    EX = {"NFP": [120, 150, 180, 240, 540], "MID": [120, 150, 180, 240, 540], "FOMC": [450, 480, 539]}
    rows, ser = [], {}
    for mk in MKS:
        G = grid(mk)
        for ev, days in E.items():
            t = TR[ev]
            specs = [(kind, k, x) for kind in ("mom", "fade") for k in (1, 5, 15, 30) for x in EX[ev] if x > t + k]
            specs += [(kind, k, None) for kind in ("pre_long", "pre_short") for k in (30, 60, 90 if ev != "FOMC" else 240)]
            for kind, k, x in specs:
                s = run_event(G, days, t, kind, k, x, G["bp"])
                if len(s) < 30: continue
                Y = s.index.year; I, O = s[Y <= 2019], s[Y >= 2020]; yy = I.groupby(I.index.year).sum()
                key = f"{mk}|{ev}|{kind}|k{k}|x{x}"; ser[key] = s
                rows.append(dict(key=key, mk=mk, ev=ev, kind=kind, k=k, x=x, n=len(s), win=100 * (s > 0).mean(),
                                 rr=s[s > 0].mean() / -s[s < 0].mean(), IS_bp=I.mean(), IS_t=tstat(I), IS_pos=int((yy > 0).sum()),
                                 OOS_bp=O.mean(), OOS_t=tstat(O), OOS_win=100 * (O > 0).mean()))
    T = pd.DataFrame(rows); T.to_csv(SP + "events_grid.csv", index=False); pickle.dump(ser, open(SP + "events_ser.pkl", "wb"))
    pd.set_option("display.width", 250)
    el = T[(T.IS_t >= 2.0) & (T.IS_pos >= 5)]
    print(f"\n{len(T)} variants. IS-eligible (t>=2, >=5/8 yrs): {len(el)}; OOS positive: {(el.OOS_bp > 0).sum()}; OOS t>=1: {(el.OOS_t >= 1).sum()}")
    print(el.sort_values("IS_t", ascending=False).round(2).to_string(index=False))
    print("\nby event x kind, share of variants positive IS / OOS:")
    print(T.groupby(["ev", "kind"]).apply(lambda g: pd.Series(dict(n=len(g), IS_pos=(g.IS_bp > 0).mean(), OOS_pos=(g.OOS_bp > 0).mean(),
                                                                     IS_t=g.IS_t.median(), OOS_t=g.OOS_t.median()))).round(2).to_string())
