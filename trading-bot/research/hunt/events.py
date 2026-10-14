"""Stage 2 — event triggers: first touch of a reference level during RTH → continuation or fade.
Levels: prior close (gap fill), PDH, PDL, ONH, ONL, opening range (5/15/30/60) high/low, VWAP±k·sigma, open ± k·sigma.
Entry: at the level (limit, filled only if price trades through by 1 tick) or at the next bar open after a close beyond.
Exit grid: target/stop in multiples of daily sigma, flat 15:55. Selection on 2020–23 only."""
import numpy as np, pandas as pd, sys
from feat import load
F, D = load()
N = len(D.days); yr = F.index.year.values; IS = yr < 2024
o, h, l, c, v = D.o, D.h, D.l, D.c, D.v
COST, TICK, LAST = 1.25, 0.25, 384
sig = F.sig.values; valid = F.valid.values & ~np.isnan(sig)

def bracket(i, j, s, e, a, b, at_open):
    """Walk day i from minute j. Target a·sig·e, stop b·sig·e (b None = no stop). Stop first on ties."""
    sc = sig[i] * e; tp = e + s * a * sc; sl = None if b is None else e - s * b * sc
    hh, ll, oo = h[i], l[i], o[i]
    for x in range(j, LAST + 1):
        if sl is not None and ((ll[x] <= sl) if s == 1 else (hh[x] >= sl)):
            return s * (((min(oo[x], sl) if s == 1 else max(oo[x], sl)) if (x > j or at_open) else sl) - e)
        if (x > j or at_open) and ((hh[x] >= tp + TICK) if s == 1 else (ll[x] <= tp - TICK)):
            return s * (tp - e)
    return s * (c[i, LAST] - e)

def levels(i):
    out = {"PC": F.pc.values[i], "PDH": None, "PDL": None, "ONH": F.onh.values[i], "ONL": F.onl.values[i]}
    if i > 0 and not D.roll[i]:
        out["PDH"], out["PDL"] = h[i - 1].max(), l[i - 1].min()
    return out

def gen_events():
    """(name, i, j_touch, level, approach_side) — approach_side +1 = price came from below (level above open)."""
    ev = []
    for i in range(N):
        if not valid[i]: continue
        o0 = o[i, 0]
        L = levels(i)
        for n in (5, 15, 30, 60):
            L[f"OR{n}H"] = h[i, :n].max(); L[f"OR{n}L"] = l[i, :n].min()
        for k in (0.5, 1.0, 1.5):
            L[f"O+{k}s"] = o0 * (1 + k * sig[i]); L[f"O-{k}s"] = o0 * (1 - k * sig[i])
        for name, lv in L.items():
            if lv is None or np.isnan(lv): continue
            start = int(name[2:-1]) if name.startswith("OR") else 1
            ref = c[i, start - 1] if start > 1 else o0
            if ref < lv: hit = np.nonzero(h[i, start:LAST] >= lv + TICK)[0]; side = 1
            elif ref > lv: hit = np.nonzero(l[i, start:LAST] <= lv - TICK)[0]; side = -1
            else: continue
            if len(hit): ev.append((name, i, start + hit[0], lv, side))
    return pd.DataFrame(ev, columns=["lvl", "i", "j", "px", "app"])

if __name__ == "__main__":
    E = gen_events(); print("events", len(E), file=sys.stderr)
    rows = []
    T_BINS = [(0, 30), (30, 90), (90, 210), (210, 330)]
    for (name, mode), g in E.groupby(["lvl", E.app]):
        for t0, t1 in T_BINS:
            gg = g[(g.j >= t0) & (g.j < t1)]
            if len(gg) < 80: continue
            for play in ("cont", "fade"):
                s = gg.app.values * (1 if play == "cont" else -1)
                for a in (0.1, 0.2, 0.3, 0.5):
                    for b in (0.25, 0.5, 1.0, 2.0):
                        # fade: limit at the level (touched); cont: stop-entry at the level (touched by definition)
                        p = np.array([bracket(i, j, si, px, a, b, False) for i, j, si, px in zip(gg.i, gg.j, s, gg.px)]) - COST
                        isd = IS[gg.i.values]
                        pi, po = p[isd], p[~isd]
                        if len(po) < 20: continue
                        rows.append(dict(lvl=name, app=mode, t=f"{t0}-{t1}", play=play, a=a, b=b, nIS=len(pi), nOOS=len(po),
                                         IS=2 * pi.mean(), OOS=2 * po.mean(), winIS=(pi > 0).mean(), winOOS=(po > 0).mean(),
                                         tIS=pi.mean() / pi.std() * np.sqrt(len(pi)), tOOS=po.mean() / po.std() * np.sqrt(len(po))))
        print(name, mode, len(rows), file=sys.stderr, flush=True)
    R = pd.DataFrame(rows); R.to_pickle("/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/hunt_R2.pkl")
    print("tests", len(R))
    for th in (2, 2.5, 3):
        s = R[R.tIS > th]; print(th, len(s), "OOS>0", round((s.OOS > 0).mean(), 3), "base", round((R.OOS > 0).mean(), 3))
    pd.set_option("display.width", 250)
    print(R[(R.tIS > 2.5) & (R.tOOS > 1.5)].sort_values("tOOS", ascending=False).head(50).round(2).to_string())
