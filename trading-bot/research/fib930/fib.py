"""9:30 one-minute candle Fib fade (user spec). h = half the 9:30 candle range, M = its midpoint.
Two readings of the drawing (TradingView puts level 0 at the END point of the drag):
  'tv'  drag M->High: 0 = High, 1 = M, level x = High - x*h  -> short limit above the high at High + 2h, stop High + 4h, TP High
        drag M->Low mirrored -> long limit at Low - 2h, stop Low - 4h, TP Low
  'alt' 0 at M:      short limit M + 2h (= High + h), stop M + 4h, TP M  (and the mirror for longs)
Entries from 09:31 (after the candle closes); limits need 1 tick through; stop wins ties; costs 2.25 pt x price/17000.
Variant grid -> pick on 2012-2019, check 2020-2023, holdout 2024-2026 once, coin flips on the pick."""
import sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, "../papers"); import pdata, engine as E
D = pdata.load(); YR = D["days"].year.values; n = len(YR)
H0, L0 = D["h"][:, 0], D["l"][:, 0]; Mid = (H0 + L0) / 2; h = (H0 - L0) / 2; ok = h > 0


def trades(read, ent, stp, tgt, tx, side):
    out = []
    for sd in ((1, -1) if side == 0 else (side,)):
        base = (H0 if sd < 0 else L0) if read == "tv" else Mid       # level 0
        # level x (negative = beyond the candle): short side above, long side below
        L = lambda x: base - x * h if sd < 0 else base + x * h
        sp = dict(dir=np.where(ok, sd, 0).astype(int), e=np.ones(n, int), kind=2, tx=np.full(n, tx),
                  lvlL=np.full(n, np.nan), lvlS=np.full(n, np.nan), stopL=np.full(n, np.nan), stopS=np.full(n, np.nan),
                  tgtL=np.full(n, np.nan), tgtS=np.full(n, np.nan))
        k = "L" if sd > 0 else "S"; sp["lvl" + k] = L(ent); sp["stop" + k] = L(stp) if stp is not None else np.full(n, np.nan); sp["tgt" + k] = L(tgt)
        T = E.intraday_trades(D, sp)
        if T: out.append(T)
    if not out: return None
    return {k: np.concatenate([t[k] for t in out]) for k in out[0]}


def stats(T, m):
    if T is None: return dict(n=0, pts=0.0)
    k = m[T["d"]]; x = T["net"][k]
    if len(x) < 2: return dict(n=len(x), pts=x.sum())
    w, l = x[x > 0], x[x <= 0]
    return dict(n=len(x), pts=x.sum(), win=100 * len(w) / len(x), rr=w.mean() / -l.mean() if len(l) and len(w) else np.nan,
                t=x.mean() / x.std(ddof=1) * np.sqrt(len(x)))


if __name__ == "__main__":
    TR, VA, HO = (YR <= 2019), (YR >= 2020) & (YR <= 2023), (YR >= 2024)
    rows = []
    for read, ent, stp, tgt, tx, side in itertools.product(("tv", "alt"), (-1, -1.5, -2, -2.25, -2.5, -3), (-3, -3.5, -4, -5, -6, None),
                                                          (0, -0.5, -1, 0.5, 1), (90, 150, 389), (0, 1, -1)):
        if stp is not None and stp >= ent: continue
        if tgt <= ent: continue
        T = trades(read, ent, stp, tgt, tx, side)
        r = dict(read=read, ent=ent, stop=stp, tp=tgt, exit_min=tx, side=side)
        for nm, m in (("tr", TR), ("va", VA), ("ho", HO)): r.update({f"{nm}_{a}": v for a, v in stats(T, m).items()})
        rows.append(r)
    R = pd.DataFrame(rows); R.to_csv("grid.csv", index=False)
    print("variants:", len(R), "| profitable in-sample:", (R.tr_pts > 0).sum(), "| also >0 in 2020-23:", ((R.tr_pts > 0) & (R.va_pts > 0)).sum())
    print("user spec exactly (tv & alt, both sides, hold to close):")
    print(R[(R.ent == -2) & (R.stop == -4) & (R.tp == 0) & (R.side == 0) & (R.exit_min == 389)].round(2).to_string())
    top = R[R.tr_n >= 200].sort_values("tr_t", ascending=False).head(10); print("\nbest 10 by in-sample t:"); print(top.round(2).to_string())
