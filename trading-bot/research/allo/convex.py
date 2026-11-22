"""BIG R:R - convex NQ trades (NQ 5-min, Dukascopy real volume, 2012-2026, cost 1 point round trip). Three families:
 F1 AVP alone     : every AVP LVN rejection (exact Pine zones), stop under the WICK (+2 pts), exits 5R / 10R / 20R / runner.
 F2 RDM alone     : 09:45 direction (today vs 09:00 open disagrees with yesterday's RTH candle), tight stops:
                    beyond the 09:30-09:45 range, or 0.15 / 0.25 ATR; exits 5R / 10R / 20R / runner.
 F3 RDM + AVP     : only RDM days, only in the RDM direction, entry on the first LVN rejection between 09:45 and 13:00,
                    stop under the rejection bar's wick; exits 5R / 10R / 20R / runner.
Runner = trail: stop to break-even at +2R, then 2R behind the best price; flat 15:55.
Judged: choose on 2012-19, check 2020-26. Reported: win rate, average winner in R, avg R, longest losing streak, years."""
import sys, os, math, itertools, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import avp_port as P
from avp_eq import zones_d
B = P.bars("USATECHIDXUSD", 5); O, Hh, L, C, V = (B[k].values for k in "ohlcv"); T = B.index; S = B.sess.values
starts = np.r_[0, np.nonzero(S[1:] != S[:-1])[0] + 1]; ends = np.r_[starts[1:], len(B)]
MIN = T.hour * 60 + T.minute; COSTPT = 1.0
srange = np.array([Hh[a:b].max() - L[a:b].min() for a, b in zip(starts, ends)]); ATR = pd.Series(srange).rolling(14).mean().shift(1).values
ZON = {}


def exit_(i0, d, en, st, mode, iend):
    """walk bars i0..iend-1. mode: float R target, or 'run' (BE at +2R, then trail 2R)."""
    rk = abs(en - st); stop = st; best = en
    for i in range(i0, iend):
        if (d == 1 and L[i] <= stop) or (d == -1 and Hh[i] >= stop): return (d * (stop - en) - COSTPT) / rk
        if mode != "run":
            tg = en + d * mode * rk
            if (d == 1 and Hh[i] >= tg) or (d == -1 and L[i] <= tg): return (mode * rk - COSTPT) / rk
        else:
            best = max(best, Hh[i]) if d == 1 else min(best, L[i])
            if d * (best - en) >= 2 * rk: stop = max(stop, best - 2 * rk) if d == 1 else min(stop, best + 2 * rk); stop = max(stop, en) if d == 1 else min(stop, en)
    return (d * (C[iend - 1] - en) - COSTPT) / rk


def session_bounds(si):
    a, b = starts[si], ends[si]; m = (MIN[a:b] - 1080) % 1440            # minutes since the 18:00 session open
    def idx(mm):
        k = np.nonzero(m >= (mm - 1080) % 1440)[0]; return a + k[0] if len(k) else None
    return a, b, idx


def rth_candle(si):
    a, b, idx = session_bounds(si); i0, i1 = idx(570), idx(955)
    return (O[i0], C[i1 - 1]) if i0 is not None and i1 is not None and i1 > i0 else None


def run(family, stopk, mode):
    out = {}
    for si in range(6, len(starts)):
        a, b, idx = session_bounds(si); A = ATR[si]
        if not np.isfinite(A): continue
        iend = idx(955) or b
        if si not in ZON: ZON[si] = zones_d(Hh[starts[si - 5]:a], L[starts[si - 5]:a], V[starts[si - 5]:a])
        Z = ZON[si]
        if family == "F1":
            used = set()
            for i in range(max(a + 1, idx(120) or a), (idx(930) or b)):
                for k, (bot, top, _) in enumerate(Z):
                    for d in (1, -1):
                        if (k, d) in used: continue
                        if (d == 1 and C[i - 1] > top and L[i] <= top and C[i] > top) or (d == -1 and C[i - 1] < bot and Hh[i] >= bot and C[i] < bot):
                            used.add((k, d)); st = L[i] - 2 if d == 1 else Hh[i] + 2
                            if abs(C[i] - st) > 3: out[(T[i], d)] = exit_(i + 1, d, C[i], st, mode, iend)
            continue
        y = rth_candle(si - 1); i9, i945 = idx(540), idx(585)
        if y is None or i9 is None or i945 is None: continue
        yd = np.sign(y[1] - y[0]); td = np.sign(O[i945] - O[i9])
        if not yd or not td or yd == td: continue
        d = td
        if family == "F2":
            en = O[i945]; lo930, hi930 = L[idx(570):i945].min(), Hh[idx(570):i945].max()
            st = (lo930 - 2 if d == 1 else hi930 + 2) if stopk == "range" else en - d * stopk * A
            if d * (en - st) > 3: out[(T[i945], d)] = exit_(i945, d, en, st, mode, iend)
        else:
            for i in range(i945, idx(780) or b):
                hit = None
                for bot, top, _ in Z:
                    if d == 1 and C[i - 1] > top and L[i] <= top and C[i] > top: hit = L[i] - 2; break
                    if d == -1 and C[i - 1] < bot and Hh[i] >= bot and C[i] < bot: hit = Hh[i] + 2; break
                if hit is not None and abs(C[i] - hit) > 3:
                    out[(T[i], d)] = exit_(i + 1, d, C[i], hit, mode, iend); break
    s = pd.Series(out, dtype=float)
    if len(s): s.index = pd.DatetimeIndex([k[0] for k in s.index])
    return s


def stats(s):
    t = lambda x: x.mean() / x.std() * math.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else 0
    Y = s.index.year; I, Oo = s[Y <= 2019], s[Y >= 2020]; w = s[s > 0]
    streak = cur = 0
    for v in s.values: cur = cur + 1 if v < 0 else 0; streak = max(streak, cur)
    return dict(n_yr=len(s) / 14.8, win=100 * (s > 0).mean(), avg_win_R=w.mean(), IS=I.mean(), IS_t=t(I), OOS=Oo.mean(), OOS_t=t(Oo),
                last2y=s[s.index >= "2024-11-01"].mean(), lose_streak=streak, pos_yrs=f"{int((s.groupby(Y).sum() > 0).sum())}/15")


if __name__ == "__main__":
    rows = []
    for fam, stopk, mode in itertools.chain(
            itertools.product(["F1"], ["wick"], [5.0, 10.0, 20.0, "run"]),
            itertools.product(["F2"], ["range", 0.15, 0.25], [5.0, 10.0, 20.0, "run"]),
            itertools.product(["F3"], ["wick"], [5.0, 10.0, 20.0, "run"])):
        s = run(fam, stopk, mode); r = stats(s); r.update(family=fam, stop=stopk, exit=mode); rows.append(r); print(fam, stopk, mode, "done", flush=True)
    R = pd.DataFrame(rows)[["family", "stop", "exit", "n_yr", "win", "avg_win_R", "IS", "IS_t", "OOS", "OOS_t", "last2y", "lose_streak", "pos_yrs"]]
    pd.set_option("display.width", 220); print(R.round(3).to_string(index=False))
    R.to_csv("/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/convex.csv", index=False)
