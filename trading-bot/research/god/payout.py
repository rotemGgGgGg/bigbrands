"""Evaluation → funded → first payouts, LucidFlex 50K rules (Lucid help center, Oct 2026):
 eval: +$3,000 target, $2,000 EOD-trailing max loss, 50 % consistency, ≥ 2 days.
 funded: same max loss; payout cycle needs 5 days with ≥ $150 profit and positive net; request = 50 % of profit, min $500,
 max $2,000; the first request locks the max-loss floor at start + $100; 90 % split; paid ≤ 2 business days.
Portfolio = final bot rules (No-Wick 1, GapFB 1, Pre-Fade 2, Opex 2 micros; skip trades with stop risk > $150/micro; netting).
Every trading day of 2024-26 (and 2020-23) is tried as a start date. Intraday breach uses realized P&L in exit order."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prop import load, book


def run(x, lo, target=3000, dd=2000, mind=150, cap=2000, n_pay=3, req=1000.0):
    out = []
    for s in range(len(x)):
        bal = peak = best = 0.0; d = s; ok = False
        while d < len(x):                                     # evaluation
            if bal + lo[d] <= peak - dd: break
            bal += x[d]; best = max(best, x[d])
            if bal <= peak - dd: break
            peak = max(peak, bal); d += 1
            if bal >= target and best <= 0.5 * bal and d - s >= 2: ok = True; break
        if not ok: out.append(dict(start=s, passed=False)); continue
        e_days = d - s; bal = peak = 0.0; floor = -dd; locked = False; good = 0; cyc = 0.0; pays = []; f0 = d; dead = False
        while d < len(x) and len(pays) < n_pay:               # funded
            if bal + lo[d] <= floor: dead = True; break
            bal += x[d]; cyc += x[d]; good += x[d] >= mind
            if bal <= floor: dead = True; break
            if not locked: peak = max(peak, bal); floor = max(floor, min(peak - dd, 100.0))
            d += 1
            if good >= 5 and cyc > 0 and bal >= req:
                amt = min(0.5 * bal, cap); pays.append((d - f0, amt)); bal -= amt
                locked = True; floor = 100.0                   # max loss locks at start + $100 (balance is after the withdrawal)
                good = 0; cyc = 0.0
        out.append(dict(start=s, passed=True, eval_days=e_days, busted=dead, n_pays=len(pays),
                        first_pay_day=pays[0][0] if pays else np.nan, first_pay=pays[0][1] if pays else 0,
                        paid_total=sum(a for _, a in pays)))
    return pd.DataFrame(out)


if __name__ == "__main__":
    T = load(); D = book(T, (1, 1, 2, 2), 150, 0)
    for req in (1000.0, 2000.0, 3000.0, 4000.0):
     print("request payout when funded profit >= $%d" % req)
     for nm, m in (("2020-23 starts", D.index.year <= 2023), ("2024-26 starts", D.index.year >= 2024)):
        d = D[m]; R = run(d.pnl.values, d.low.values, req=req); P = R[R.passed]
        print(f"  {nm}: n={len(R)} pass {100 * R.passed.mean():.0f}% | eval days median {P.eval_days.median():.0f} | "
              f"reached 1st payout {100 * (P.n_pays >= 1).mean():.0f}% (median {P.first_pay_day.median():.0f} trading days after funding, "
              f"median gross ${P[P.n_pays >= 1].first_pay.median():.0f}) | 3 payouts {100 * (P.n_pays >= 3).mean():.0f}% | "
              f"busted before 3 payouts {100 * P.busted.mean():.0f}% | median paid (3 requests) ${P.paid_total.median():.0f}")
