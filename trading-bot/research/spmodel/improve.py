"""What would make the SP model better? Honest version: every change is chosen on 2012-19 and only then checked on 2020-26.
Part 1 (diagnose): where the baseline (London 00:00-06:00) wins/loses: scenario, side, entry hour, weekday, leg size, VA ratio,
        daily trend (NQ above/below its 50-day average), London range size.
Part 2 (re-simulate): bracket changes (target at fib 0.267/0 or the -0.27 extension; stop at 0.702/0.816 or the 1.0) x
        scenario sets (all / S2 only / S2+S3), then post-filters (entry before 11:00, with-trend only)."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "../multi"))
from run_sp import bars5, stats, v, SP
import mdata

D = mdata.load("NSXUSD"); dc = pd.Series(D["dc"], index=D["days"]); trend = (dc > dc.rolling(50).mean()).shift(1)
def feats(tr):
    tr = tr.copy(); et = tr.entry_time
    tr["hour"] = et.dt.hour + (et.dt.minute >= 30) * 0.5; tr["wd"] = et.dt.dayofweek; tr["Y"] = et.dt.year
    tr["leg_pts"] = (tr.a1 - tr.a0).abs(); tr["d"] = np.where(tr.side == "LONG", 1, -1)
    up = trend.reindex(pd.DatetimeIndex(et.dt.tz_localize(None).dt.normalize())).values
    tr["with_trend"] = np.where(pd.isna(up), np.nan, np.where(up.astype(float) == 1, tr.d == 1, tr.d == -1))
    return tr

def row(lab, x):
    I, O = x[x.Y <= 2019], x[x.Y >= 2020]; s = stats(x); si, so = stats(I), stats(O)
    return dict(slice=lab, n_yr=s.get("per_yr", 0), win=s.get("win"), rr=s.get("rr"), IS_R=si.get("avgR"), IS_t=si.get("t"),
                OOS_R=so.get("avgR"), OOS_t=so.get("t"))

if __name__ == "__main__":
    pd.set_option("display.width", 220)
    tr = pd.read_csv(SP + "sp_trades_A.csv", parse_dates=["entry_time"]); tr["entry_time"] = pd.to_datetime(tr.entry_time, utc=True).dt.tz_convert("America/New_York")
    tr = feats(tr); rows = []
    for g, lab in (("scenario", "S"), ("side", ""), ("hour", "h"), ("wd", "wd"), ("level", "@"), ("with_trend", "trend")):
        for k, x in tr.groupby(g): rows.append(row(f"{lab}{k}", x))
    tr["legq"] = pd.qcut(tr.leg_pts.rank(pct=True), 4, labels=["leg small", "leg 2", "leg 3", "leg big"])
    for k, x in tr.groupby("legq"): rows.append(row(str(k), x))
    print("===== Part 1: baseline A sliced (avg R; choose on IS, check OOS)\n", pd.DataFrame(rows).round(2).to_string(index=False), flush=True)

    df = bars5(); base = dict(v.LEVELS); out = []
    TG = {"base": (0.267, 0.36), "fib0": (0.0, 0.0), "ext-0.27": (-0.27, -0.27)}
    ST = {"base": (0.702, 0.816), "fib1.0": (1.0, 1.0)}
    SC = {"all": dict(), "S2 only": dict(use_s1=False, use_s3=False), "S2+S3": dict(use_s1=False)}
    for (tn, tg), (sn, st), (cn, cp) in itertools.product(TG.items(), ST.items(), SC.items()):
        v.LEVELS.clear(); v.LEVELS.update({0.5: (st[0], tg[0]), 0.588: (st[1], tg[1])})
        r = v.run(df, v.Params(check=False, **cp)); t = pd.DataFrame(r.trades)
        if t.empty: continue
        t["entry_time"] = pd.to_datetime(t.entry_time, utc=True).dt.tz_convert("America/New_York"); t = feats(t)
        for fl, m in (("none", t.r.notna()), ("before 11:00", t.hour < 11), ("with trend", t.with_trend == 1),
                      ("before 11 + trend", (t.hour < 11) & (t.with_trend == 1))):
            x = t[m]
            if len(x) < 100: continue
            rr = row(f"tgt {tn} | stop {sn} | {cn} | {fl}", x); yy = x.groupby("Y").r.sum(); rr["pos_yrs"] = int((yy > 0).sum()); out.append(rr)
        print(tn, sn, cn, "done", flush=True)
    v.LEVELS.clear(); v.LEVELS.update(base)
    T = pd.DataFrame(out).sort_values("IS_t", ascending=False); T.to_csv(SP + "sp_improve.csv", index=False)
    print("\n===== Part 2: re-simulated variants (sorted by 2012-19 t)\n", T.round(2).to_string(index=False))
