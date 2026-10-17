"""Iter 43 (queue 47) — weekly-structure folklore ('Turnaround Tuesday', Monday after a down Friday, Wednesday after two down
days, Friday after a down/up week) → same trade grid as iter 30 (entry 09:30/10:00/13:30/15:00 × long/short/follow/fade × stop k·σ,
target 2×, exit close). Three periods."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools
exec(open("iter26_web.py").read().split("res = []")[0])
def cal(days):
    d = pd.DatetimeIndex(days); wd = d.weekday.values
    return dict(tue_after_down_mon=CTX["tue_dm"], tue_after_up_mon=CTX["tue_um"], mon_after_down_fri=CTX["mon_df"],
                mon_after_up_fri=CTX["mon_uf"], wed_after_2down=CTX["wed_2d"], fri_after_down_week=CTX["fri_dw"],
                fri_after_up_week=CTX["fri_uw"], all_days=np.ones(len(d), bool))

res = []
P = {}
for per, o, h, l, c, dow in grids():
    if per == "2012-19":
        f0 = frame("NSXUSD"); days = RTH(f0[f0.index.notna()][:"2019-12-31"]).days
    else:
        import lib; days = lib.DAYS[(lib.YR < 2024) if per == "2020-23" else (lib.YR >= 2024)]
    assert len(days) == len(o)
    dd = pd.DatetimeIndex(days); wd = dd.weekday.values; R1 = np.r_[np.nan, c[:-1, 389] / o[:-1, 0] - 1]
    R2 = np.r_[np.nan, np.nan, c[:-2, 389] / o[:-2, 0] - 1]
    wk = pd.Series(c[:, 389], index=dd); wret = (wk / wk.groupby(dd.to_period("W")).transform("first") - 1).values
    W1 = np.r_[np.nan, wret[:-1]]
    CTX = dict(tue_dm=(wd == 1) & (R1 < 0), tue_um=(wd == 1) & (R1 > 0), mon_df=(wd == 0) & (R1 < 0), mon_uf=(wd == 0) & (R1 > 0),
               wed_2d=(wd == 2) & (R1 < 0) & (R2 < 0), fri_dw=(wd == 4) & (W1 < 0), fri_uw=(wd == 4) & (W1 > 0))
    C = cal(days); N = len(o)
    full = np.isfinite(c[:, 389]) & np.isfinite(o[:, 0])
    mv = np.abs(c[:, 389] / o[:, 0] - 1); sig = pd.Series(mv).rolling(14).mean().shift().values
    for cn, mask in C.items():
        for em, side, k in itertools.product((0, 30, 240, 330), ("long", "short", "follow", "fade"), (0.15, 0.25, 0.4)):
            if em == 0 and side in ("follow", "fade"): continue
            R = []
            for i in np.nonzero(mask & full)[0]:
                if i < 15 or not np.isfinite(sig[i]): continue
                e = o[i, em]
                if not np.isfinite(e): continue
                if side == "long": s = 1
                elif side == "short": s = -1
                else:
                    mvv = c[i, em - 1] - o[i, 0]
                    if mvv == 0: continue
                    s = int(np.sign(mvv)) * (1 if side == "follow" else -1)
                st = k * sig[i] * o[i, 0]
                px, _, _ = walk(o[i], h[i], l[i], c[i], em, s, e, e - s * st, e + s * 2 * st, 389)
                R.append((s * (px - e) - 2.25 * e / 17000) / st)
            R = np.array([r for r in R if np.isfinite(r)])
            if len(R) < 15: continue
            res.append(dict(per=per, cond=cn, em=em, side=side, k=k, n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
T = pd.DataFrame(res); T.to_csv("iter43_weekly.csv", index=False)
W = T.pivot_table(index=["cond", "em", "side", "k"], columns="per", values=["win", "R", "n"])
W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
pd.set_option("display.width", 250)
print(W.sort_values("minR", ascending=False).head(25).round(3).to_string())
print("\nmax min-win:", W["minwin"].max(), "  rows with minwin>=70:", (W["minwin"] >= 70).sum())
base = W.xs("all_days", level="cond")
print("rows minR>0:", (W["minR"] > 0).sum(), "of", len(W), " | all_days baseline minR>0:", (base["minR"] > 0).sum(), "of", len(base))
