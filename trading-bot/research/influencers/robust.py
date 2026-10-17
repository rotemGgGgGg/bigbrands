"""Neighbourhood + direction check for the intraday survivors (Williams volatility breakout, Crabel NR7)."""
from strategies import *
def wvb(k, st, side_only=0):
    cands = defaultdict(list)
    for i in range(1, N):
        if not okprev[i]: continue
        r = RANGE[i - 1]; up, dn = DO[i] + k * r, DO[i] - k * r
        a, b = stop_fill(i, 1, 384, up, 1), stop_fill(i, 1, 384, dn, -1)
        fs = [x for x in ((a, 1), (b, -1)) if x[0] and (not side_only or x[1] == side_only)]
        f = min(fs, key=lambda x: x[0][0], default=None)
        if f: (m, px), s = f; cands[i].append((m, s, px - s * st * r, None, px, False))
    return summarize(f"WVB k{k} stop{st} side{side_only}", "Williams", run_seq(cands))
rows = [wvb(k, st) for k in (0.4, 0.5, 0.6, 0.7, 0.8) for st in (0.3, 0.5, 0.8)]
rows += [wvb(0.6, 0.5, 1), wvb(0.6, 0.5, -1)]
def nr(n, orm):
    cands = defaultdict(list)
    for i in range(n + 1, N):
        if not okprev[i] or RANGE[i - 1] > RANGE[i - n:i].min(): continue
        hi, lo = h[i, :orm].max(), l[i, :orm].min()
        a, b = stop_fill(i, orm, 384, hi + TICK, 1), stop_fill(i, orm, 384, lo - TICK, -1)
        f = min([x for x in ((a, 1), (b, -1)) if x[0]], key=lambda x: x[0][0], default=None)
        if f: (m, px), s = f; cands[i].append((m, s, lo if s == 1 else hi, None, px, False))
    return summarize(f"NR{n} OR{orm}", "Crabel", run_seq(cands))
rows += [nr(n, orm) for n in (4, 5, 7, 10) for orm in (15, 30, 60)]
pd.set_option("display.width", 250); print(pd.DataFrame(rows)[["strategy", "n", "win", "avg_win", "avg_loss", "rr", "usd", "usd_IS", "usd_OOS", "yrs_pos", "pf", "t"]].to_string(index=False))
