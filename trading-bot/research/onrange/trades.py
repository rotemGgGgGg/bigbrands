"""Tradeable versions of the ON-range idea. At 09:30 open, side chosen by zone; target = ON level (or fraction of the way),
stop = k x target distance on the other side; whatever is hit first (same minute -> stop), else exit at close.
P&L in bp of price net of the market's round-trip cost. Grid chosen on 2012-19 only; OOS 2020-26 reported once."""
import sys, math, itertools, numpy as np, pandas as pd
from onrange import build, SP
def sh(x): return x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else 0

def run(sym, zone, mode, tf, k, entry_min=0):
    Z = build(sym); A = pd.read_pickle(SP + sym + "_A.pkl"); out = {}
    for day, r in A.iterrows():
        lo, hi = zone
        if not (lo <= r.pos < hi): continue
        i = int(r.i); h, l, c = Z["h"][i], Z["l"][i], Z["c"][i]; o = Z["o"][i, entry_min]
        near_low = r.pos < .5; lvl = r.onl if near_low else r.onh
        d = abs(o - lvl) * tf
        if d <= 0: continue
        side = (-1 if near_low else 1) * (1 if mode == "toward" else -1)
        tgt, stp = o + side * d, o - side * d * k
        up, dn = (tgt, stp) if side > 0 else (stp, tgt)
        hu = np.nonzero(h[entry_min:] >= up)[0]; ld = np.nonzero(l[entry_min:] <= dn)[0]
        tu = hu[0] if len(hu) else 999; td = ld[0] if len(ld) else 999
        if tu == 999 and td == 999: px = c[-1]
        else:
            hit_up = tu < td or (tu == td and side < 0)            # tie -> stop
            px = up if hit_up else dn
        out[day] = side * (px - o) / o * 1e4 - Z["bp"]
    return pd.Series(out, dtype=float)

if __name__ == "__main__":
    syms = sys.argv[1:] or ["NSXUSD", "SPXUSD"]
    zones = {"lowhalf/highhalf": (0, 1), "Q1/Q4": None, "Q2/Q3": None}
    rows = []
    for sym in syms:
        for zn, zone in [("all", (0, 1.0001)), ("outer quarters", "outer"), ("inner quarters", "inner")]:
            for mode in ("toward", "away"):
                for tf in (.5, 1.0):
                    for k in (.5, 1, 2):
                        if zone == "outer": s = pd.concat([run(sym, (0, .25), mode, tf, k), run(sym, (.75, 1.0001), mode, tf, k)]).sort_index()
                        elif zone == "inner": s = run(sym, (.25, .75), mode, tf, k)
                        else: s = run(sym, zone, mode, tf, k)
                        Y = s.index.year; S, O = s[Y <= 2019], s[Y >= 2020]
                        rows.append(dict(sym=sym, zone=zn, mode=mode, tf=tf, k=k, n=len(s), win=100*(s > 0).mean(),
                                         rr=s[s > 0].mean() / -s[s < 0].mean(), IS_bp=S.mean(), IS_t=S.mean()/S.std()*math.sqrt(len(S)),
                                         OOS_bp=O.mean(), OOS_t=O.mean()/O.std()*math.sqrt(len(O))))
    T = pd.DataFrame(rows); T.to_csv(SP + "grid.csv", index=False)
    pd.set_option("display.width", 200); print(T.round(2).sort_values("IS_t", ascending=False).to_string(index=False))
