"""Re-resolve every SP v8 trade (5-minute simulation) on 1-minute bars.
The 5-minute simulation decides stop-vs-target inside one 5-minute bar by TradingView's broker-emulator order (open -> nearer
extreme -> other extreme); ~30% of trades open and close inside one 5-minute bar, so that guess decides a lot.
Here: fill = first 1-minute bar (from the entry bar on) that trades through the fill price; in that minute only the STOP
counts (a target touched in the fill minute may have happened before the fill); later minutes: stop first if both; flat 14:00."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "multi"); import mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
m = mdata.histdata("NSXUSD"); m = m[~m.index.duplicated()].sort_index(); idx = m.index; H, L, C = m.h.values, m.l.values, m.c.values


def resolve(k, fill_minute_target):
    d = pd.read_csv(SP + f"sp_trades_{k}.csv"); d["et"] = pd.to_datetime(d.entry_time, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    d["same"] = d.entry_time == d.exit_time; out = []
    for r in d.itertuples():
        s = idx.searchsorted(r.et); e = idx.searchsorted(r.et.normalize() + pd.Timedelta(hours=14)); dn = 1 if r.side == "LONG" else -1
        j = s
        while j < e and not (L[j] <= r.fill <= H[j]): j += 1
        if j >= e: out.append(np.nan); continue
        risk = abs(r.fill - r.stop); res = None
        for i in range(j, e):
            hs = L[i] <= r.stop if dn == 1 else H[i] >= r.stop
            ht = (H[i] >= r.target if dn == 1 else L[i] <= r.target) and (i > j or fill_minute_target)
            if hs: res = -1.0; break
            if ht: res = abs(r.target - r.fill) / risk; break
        out.append(res if res is not None else dn * (C[e - 1] - r.fill) / risk)
    d["r1"] = out; return d


if __name__ == "__main__":
    for k in "AB":
        d = resolve(k, False)
        for lab, x in (("2012-26", d), ("2012-19", d[d.et < "2020-01-01"]), ("2020-26", d[d.et >= "2020-01-01"]), ("last 3y", d[d.et >= "2023-10-27"])):
            x = x.dropna(subset=["r1"]); w = x.r1[x.r1 > 0]; l = x.r1[x.r1 < 0]; t = x.r1.mean() / x.r1.std() * np.sqrt(len(x))
            print(f"{k} {lab:8s} n {len(x):4d} | 5-min: win {100*(x.r>0).mean():.1f}% {x.r.mean():+.3f}R | 1-min: win {100*(x.r1>0).mean():.1f}% RR {w.mean()/-l.mean():.2f} {x.r1.mean():+.3f}R t {t:.2f}")
        y = d[d.et >= "2023-10-27"].dropna(subset=["r1"]); print("   last 3y by year:", y.groupby(y.et.dt.year).r1.sum().round(1).to_dict())
        d.to_pickle(SP + f"sp_1m_{k}.pkl")
