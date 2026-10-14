"""90-minute-quarter SSMT on Yahoo 5m NQ/ES/YM (Aug → Oct 2026, ~50 sessions/day-sets). Session cycle = 4×90m
from 18:00 NY. Event study + a simple trade: enter at the close of the bar where the divergence appears, stop beyond
the sweeping asset's extreme so far, target 2R, exit at quarter end. NQ points; cost 1.25 pt."""
import numpy as np, pandas as pd
S = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"
A = {k: pd.read_pickle(S + f"yf_{k}_5m.pkl") for k in ("NQ", "ES", "YM")}
idx = A["NQ"].index.intersection(A["ES"].index).intersection(A["YM"].index)
A = {k: v.loc[idx] for k, v in A.items()}
mins = ((idx.hour * 60 + idx.minute - 18 * 60) % 1440)            # minutes since 18:00
qid = ((idx + pd.Timedelta(hours=6)).normalize().astype("int64") // 10**9) * 100 + mins // 90
keys = pd.unique(qid); pos = {k: np.where(qid == k)[0] for k in keys}
nq = A["NQ"]; o, h, l, c = (nq[x].values for x in ("open", "high", "low", "close"))
def run(pa, pb, hidden=False, window=None):
    out = []
    for j in range(1, len(keys)):
        cur, prv = pos[keys[j]], pos[keys[j - 1]]
        if keys[j] - keys[j - 1] != 1 or len(prv) < 15 or len(cur) < 15: continue
        if window and not (window[0] <= (mins[cur[0]] + 18 * 60) % 1440 < window[1]): continue
        for d in (1, -1):
            col = "close" if hidden else ("low" if d == 1 else "high")
            ra = (A[pa][col].values[prv].min() if d == 1 else A[pa][col].values[prv].max())
            rb = (A[pb][col].values[prv].min() if d == 1 else A[pb][col].values[prv].max())
            sa, sb = A[pa][col].values[cur], A[pb][col].values[cur]
            ta = np.cumsum((sa < ra) if d == 1 else (sa > ra)) > 0; tb = np.cumsum((sb < rb) if d == 1 else (sb > rb)) > 0
            div = np.where(ta != tb)[0]; both = np.where(ta & tb)[0]
            if not len(div) or (len(both) and both[0] <= div[0]): continue
            k = div[0]
            if k >= len(cur) - 1: continue
            i = cur[k]; e = c[i]
            ext = l[cur[:k + 1]].min() if d == 1 else h[cur[:k + 1]].max()
            risk = (e - ext) * d + 0.25
            if risk <= 0: continue
            px = c[cur[-1]]
            for jj in cur[k + 1:]:
                if (l[jj] <= e - d * risk) if d == 1 else (h[jj] >= e - d * risk): px = e - d * risk; break
                if (h[jj] >= e + d * 2 * risk) if d == 1 else (l[jj] <= e + d * 2 * risk): px = e + d * 2 * risk; break
            out.append(dict(t=idx[i], d=d, pts=(px - e) * d - 1.25, R=((px - e) * d - 1.25) / risk, fwd_end=(c[cur[-1]] - e) * d))
    return pd.DataFrame(out)
def show(name, t):
    if t.empty: print(name, "no events"); return
    print(f"{name:42} n {len(t):3} | to quarter end win {100*(t.fwd_end>0).mean():4.1f}% avg {t.fwd_end.mean():+5.1f}pt | trade 2R: win {100*(t.R>0).mean():4.1f}% avg {t.R.mean():+.3f}R ${2*t.pts.sum():+,.0f}/MNQ")
print(f"data {idx[0]} → {idx[-1]}")
show("90m SSMT NQ/ES wick (all quarters)", run("NQ", "ES"))
show("90m SSMT NQ/ES hidden (closes)", run("NQ", "ES", True))
show("90m SSMT NQ/YM wick", run("NQ", "YM"))
show("90m SSMT ES/YM wick (YM rule)", run("ES", "YM"))
show("90m SSMT NQ/ES wick, 09:00–10:30 quarter only", run("NQ", "ES", window=(540, 630)))
show("90m SSMT NQ/ES wick, NY AM session 06:00–12:00", run("NQ", "ES", window=(360, 720)))
