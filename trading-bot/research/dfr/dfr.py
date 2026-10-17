"""DFR: Asia 21:00–00:00 NY range (H, L, R = H − L). Fibonacci drawn low→high and high→low with levels −1, −2, −2.5, −4:
  upper levels  U_k = H + k·R ,  lower levels  D_k = L − k·R   (k = 1, 2, 2.5, 4)   [TradingView negative fib = beyond the end].
Tested: both plays (FADE the level / BREAK through it), both sides, every level, 5 trading windows, 3 stops, 5 targets,
range-size filters. Entries: fade = limit at the level (fill only if traded through by 1 tick); break = stop order at the level.
Exits on 1-minute bars, stop first on ties, flat at 15:55. Costs 2.25 pt. Data: Databento MNQ 1-minute 24h 2020-01 → 2026-10."""
import sys, itertools; sys.path.insert(0, "..")
import numpy as np, pandas as pd
from engine import S
COST, TICK = 2.25, 0.25
full = pd.read_pickle(S + "full1m.pkl"); full = full[~full.index.duplicated()]
mm = (full.index.hour * 60 + full.index.minute).values
O, H, L, C = (full[k].values for k in ("open", "high", "low", "close"))
sess = (full.index + pd.Timedelta(hours=6)).normalize()          # 18:00 → next calendar day
grp = pd.Series(np.arange(len(full))).groupby(sess.values).agg(["first", "last"])
DAYS = []
for d, (a, b) in grp.iterrows():
    if d.weekday() >= 5: continue
    seg = mm[a:b + 1]
    asia = np.nonzero((seg >= 1260) & (seg < 1440))[0] + a
    day = np.nonzero(seg < 960)[0] + a                       # 00:00 → 15:59 of the session date
    day = day[mm[day] < 960]
    if len(asia) < 150 or len(day) < 800: continue
    hh, ll = H[asia].max(), L[asia].min()
    DAYS.append((d, hh, ll, day))
print("days", len(DAYS), file=sys.stderr)
R_ALL = np.array([x[1] - x[2] for x in DAYS]); RQ = np.quantile(R_ALL[:int(len(R_ALL) * 0.6)], [1 / 3, 2 / 3])

WINDOWS = {"london 00-05": (0, 300), "pre 05-0930": (300, 570), "nyam 0930-12": (570, 720), "nypm 12-1555": (720, 955), "all 00-1555": (0, 955)}
LEVELS = (1.0, 2.0, 2.5, 4.0)
STOPS = (0.5, 1.0, 1.5)                                       # in Asia ranges beyond the entry level
TARGETS = ("prev_level", "range_edge", "mid", "1R", "2R")
def simulate(idx, side, e, sl, tp):
    for k in idx:
        if mm[k] >= 955: return side * (O[k] - e) - COST
        if (side == 1 and L[k] <= sl) or (side == -1 and H[k] >= sl): return side * ((min(O[k], sl) if side == 1 else max(O[k], sl)) - e) - COST
        if (side == 1 and H[k] >= tp + TICK) or (side == -1 and L[k] <= tp - TICK): return side * (tp - e) - COST
    return side * (C[idx[-1]] - e) - COST
rows = []
for d, hh, ll, day in DAYS:
    R = hh - ll
    if R < 4: continue
    rb = int(np.searchsorted(RQ, R))
    for wname, (w0, w1) in WINDOWS.items():
        wi = day[(mm[day] >= w0) & (mm[day] < w1)]
        if len(wi) < 10: continue
        for lv, upper, play in itertools.product(LEVELS, (True, False), ("fade", "break")):
            lvl = hh + lv * R if upper else ll - lv * R
            touch = np.nonzero(H[wi] >= lvl + (TICK if play == "fade" else 0))[0] if upper else np.nonzero(L[wi] <= lvl - (TICK if play == "fade" else 0))[0]
            if not len(touch): continue
            k0 = wi[touch[0]]
            if play == "fade": side = -1 if upper else 1; e = lvl; first_bar_inclusive = True
            else: side = 1 if upper else -1; e = max(O[k0], lvl) if upper else min(O[k0], lvl)
            rest = day[day >= k0]
            prev_lvl = (hh + (LEVELS[LEVELS.index(lv) - 1] if lv > 1 else 0) * R) if upper else (ll - (LEVELS[LEVELS.index(lv) - 1] if lv > 1 else 0) * R)
            for st in STOPS:
                sl = e - side * st * R
                for tg in TARGETS:
                    if tg == "prev_level": tp = prev_lvl if play == "fade" else (hh + LEVELS[min(LEVELS.index(lv) + 1, 3)] * R if upper else ll - LEVELS[min(LEVELS.index(lv) + 1, 3)] * R)
                    elif tg == "range_edge": tp = (hh if upper else ll) if play == "fade" else e + side * R
                    elif tg == "mid": tp = (hh + ll) / 2 if play == "fade" else e + side * 2 * R
                    elif tg == "1R": tp = e + side * st * R
                    else: tp = e + side * 2 * st * R
                    if (tp - e) * side <= 0: continue
                    # fade fill bar: only the stop counts on the entry minute (conservative)
                    if play == "fade" and ((side == 1 and L[k0] <= sl) or (side == -1 and H[k0] >= sl)):
                        pts = side * (sl - e) - COST
                    else:
                        pts = simulate(rest[1:] if play == "fade" else rest, side, e, sl, tp) if len(rest) > 1 else -COST
                    rows.append((d, wname, lv, "upper" if upper else "lower", play, st, tg, rb, side, pts, st * R, abs(tp - e)))
T = pd.DataFrame(rows, columns=["date", "window", "level", "edge", "play", "stop_R", "target", "rbucket", "side", "pts", "risk", "reward"])
T.to_pickle(S + "dfr_trades.pkl"); print("trade rows", len(T), file=sys.stderr)
