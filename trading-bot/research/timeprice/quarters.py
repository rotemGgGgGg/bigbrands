"""Quarterly Theory (time divided into 4, fractally) on NQ 1-minute, New York time, 2012-2026. Cost 1.3 bp per trade.
Levels (block -> 4 quarters), anchored at 18:00 NY:
  W  week   : Mon / Tue / Wed / Thu trading days (Fri = 'X', ignored)
  D  day    : 18-24 / 00-06 / 06-12 / 12-18
  S  session: 6h sessions split into 90-minute quarters (all four sessions; NY AM = 06:00-12:00 -> 06:00/07:30/09:00/10:30)
  M  micro  : 90-minute blocks split into 22.5-minute quarters
True open (TO) = open of quarter 2. 'Aligning time with price' rules, entry at the open of Q3:
  REV   : trade against price vs TO (below TO = discount -> long)
  CONT  : trade with price vs TO
  AMD   : Q2 sweeps Q1's low and closes back above it -> long (mirror short); stop = Q2 extreme
  AMD+TO: AMD and price on the 'right' side of TO (long only below TO, short only above)
Exits: end of Q3, or end of Q4. Placebo for the time grid: the same rules on grids shifted by 1/8..7/8 of a block
(if time alignment is the secret, the real grid must beat every shifted grid). Choose on 2012-19, judge 2020-26."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../multi"))
import mdata
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/"; BP = 1.3


def grid():
    f = SP + "qt_nq.npz"
    if os.path.exists(f): z = np.load(f); return z["t0"].item(), z["o"], z["h"], z["l"], z["c"], z["ok"]
    df = mdata.histdata("NSXUSD"); df = df[~df.index.duplicated()].sort_index()
    t = df.index.values.astype("datetime64[m]").astype(np.int64); t0 = int(t[0]); n = int(t[-1] - t0 + 1)
    o, h, l, c = (np.full(n, np.nan) for _ in range(4)); i = t - t0
    o[i], h[i], l[i], c[i] = df.o.values, df.h.values, df.l.values, df.c.values; ok = ~np.isnan(c)
    c = pd.Series(c).ffill().values
    for a in (o, h, l): a[~ok] = c[~ok]
    np.savez(f, t0=t0, o=o, h=h, l=l, c=c, ok=ok); return t0, o, h, l, c, ok


T0, O, Hh, Lw, C, OK = grid(); N = len(C)
ANCH = int(np.datetime64("2012-01-01T18:00").astype("datetime64[m]").astype(np.int64)) - T0      # a Sunday 18:00
while ANCH < 0: ANCH += 7 * 1440


def blocks(level, shift):
    """yield (start indices of the 4 quarters, end index) for every block"""
    if level == "W":
        for s in range(ANCH + int(shift * 4 * 1440), N - 5 * 1440, 7 * 1440):
            yield [s + k * 1440 for k in range(4)], s + 4 * 1440
        return
    L = {"D": 1440, "S": 360, "M": 90}[level]; q = L / 4
    for s in range(ANCH + int(shift * L), N - L, L):
        yield [int(s + k * q) for k in range(4)], s + L


def qstats(a, b):
    if b <= a or OK[a:b].mean() < 0.6: return None
    return O[a], Hh[a:b].max(), Lw[a:b].min(), C[b - 1]


def run(level, shift):
    out = {r: {} for r in ("REV|3", "REV|4", "CONT|3", "CONT|4", "AMD|3", "AMD|4", "AMDTO|3", "AMDTO|4")}
    for qs, end in blocks(level, shift):
        bounds = qs + [end]; Q = [qstats(bounds[k], bounds[k + 1]) for k in range(4)]
        if any(x is None for x in Q): continue
        (o1, h1, l1, c1), (o2, h2, l2, c2), (o3, h3, l3, c3), (o4, h4, l4, c4) = Q
        TO = o2; e = o3; day = (T0 + qs[2]) // 1440
        def pnl(side, stop, ex):
            a, b = bounds[2], bounds[ex]
            if stop is not None:
                hit = np.nonzero(Lw[a:b] <= stop)[0] if side > 0 else np.nonzero(Hh[a:b] >= stop)[0]
                if len(hit): return side * (stop - e) / e * 1e4 - BP
            return side * (C[b - 1] - e) / e * 1e4 - BP
        d = np.sign(e - TO)
        for ex in (3, 4):
            if d:
                out[f"REV|{ex}"][day] = out[f"REV|{ex}"].get(day, 0) + pnl(-d, None, ex)
                out[f"CONT|{ex}"][day] = out[f"CONT|{ex}"].get(day, 0) + pnl(d, None, ex)
            lo_sw = l2 < l1 and c2 > l1; hi_sw = h2 > h1 and c2 < h1
            if lo_sw != hi_sw:
                side, stop = (1, l2) if lo_sw else (-1, h2)
                p = pnl(side, stop, ex); out[f"AMD|{ex}"][day] = out[f"AMD|{ex}"].get(day, 0) + p
                if (side > 0 and e < TO) or (side < 0 and e > TO): out[f"AMDTO|{ex}"][day] = out[f"AMDTO|{ex}"].get(day, 0) + p
    return {k: pd.Series(list(v.values()), index=pd.to_datetime(np.array(list(v.keys())) * 86400, unit="s")) for k, v in out.items()}


def tst(x): return x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0.0


if __name__ == "__main__":
    rows = []
    for level in ("W", "D", "S", "M"):
        res = {sh: run(level, sh / 8) for sh in range(8)}
        for rule in res[0]:
            s = res[0][rule].sort_index(); Y = s.index.year; I, Oo = s[Y <= 2019], s[Y >= 2020]
            if len(s) < 50: continue
            pl = [res[sh][rule].mean() for sh in range(1, 8)]
            rows.append(dict(level=level, rule=rule, days_yr=len(s) / 14.8, win=100 * (s > 0).mean(),
                             rr=s[s > 0].mean() / -s[s < 0].mean(), IS=I.mean(), IS_t=tst(I), OOS=Oo.mean(), OOS_t=tst(Oo),
                             pos_yrs=int((s.groupby(Y).sum() > 0).sum()), shifted_grids_beaten=f"{sum(p < s.mean() for p in pl)}/7"))
        print(level, "done", flush=True)
    T = pd.DataFrame(rows); pd.set_option("display.width", 250); T.to_csv(SP + "qt_grid.csv", index=False)
    print(T.round(2).to_string(index=False))
