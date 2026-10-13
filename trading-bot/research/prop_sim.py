"""LucidFlex 50K lifecycle simulator. Rules (third-party summaries of Lucid's rulebook, Oct 2026 — verify at checkout):
EVAL  target +$3,000 · max loss $2,000 EOD-trailing (breach intraday), locks at +$100 once an EOD balance ≥ +$2,100
      · consistency: best day ≤ 50 % of total profit at the pass · fee $146 (list).
FUNDED same MLL · payout needs 5 days ≥ $150 and a positive cycle · request min $500, max 50 % of profit, ≤ $2,000
      · trader keeps 90 % · a request locks the MLL at +$100 · up to 5 payouts (then live, discretionary → stop counting).
Flat every day by 16:00 (Noise-Area exits 16:00 < 16:45 cutoff)."""
import pickle, numpy as np, pandas as pd
from engine import S, COST_PTS, PT_USD, IS_END
from prop_paths import D, noise_area

def na_days(stop_usd=None):
    """Noise-Area per-day (pnl, low) for 1 MNQ with an optional intraday flatten at −stop_usd (day P&L incl. costs)."""
    move = np.abs(D.c / D.o[:, :1] - 1)
    marks = [29 + 30 * j for j in range(12)]
    rows = []
    for i in range(14, len(D.days)):
        if D.roll[i] or D.prev_gap_days[i] > 4:
            rows.append((D.days[i], 0.0, 0.0)); continue
        sig = move[i - 14:i].mean(0)
        o0, pc = D.o[i, 0], D.c[i - 1, 389]
        ub, lb = max(o0, pc) * (1 + sig), min(o0, pc) * (1 - sig)
        o, h, l, c = D.o[i], D.h[i], D.l[i], D.c[i]
        p, ent, real, low, stopped = 0, 0.0, 0.0, 0.0, False
        for idx, k in enumerate(marks):
            # walk minutes from the previous mark to this mark with the current position
            start = marks[idx - 1] + 1 if idx else 30
            if p and not stopped:
                for j in range(start, k + 1):
                    worst = (l[j] - ent) * p if p == 1 else (ent - h[j])
                    if stop_usd is not None and (real + worst * PT_USD) <= -stop_usd:
                        real = -stop_usd - 0.5; low = min(low, real); p = 0; stopped = True; break
                    low = min(low, real + worst * PT_USD)
            if stopped:
                break
            want = p; cc = c[k]
            if p == 1 and cc < lb[k]: want = 0
            if p == -1 and cc > ub[k]: want = 0
            if cc > ub[k]: want = 1
            elif cc < lb[k]: want = -1
            if want != p:
                px = o[k + 1]
                if p: real += (px - ent) * p * PT_USD - COST_PTS * PT_USD
                p, ent = want, px
        if p and not stopped:
            for j in range(marks[-1] + 1, 390):
                worst = (l[j] - ent) if p == 1 else (ent - h[j])
                if stop_usd is not None and (real + worst * PT_USD) <= -stop_usd:
                    real = -stop_usd - 0.5; low = min(low, real); p = 0; stopped = True; break
                low = min(low, real + worst * PT_USD)
            if p:
                real += (c[389] - ent) * p * PT_USD - COST_PTS * PT_USD
        rows.append((D.days[i], real, min(low, real)))
    return pd.DataFrame(rows, columns=["date", "pnl", "low"])

def lifecycle(pnl, low, start, n=1, fee=146.0, max_payouts=5, cons=0.5):
    """Returns (status, payouts_usd_to_trader, days_used). status: eval_fail | funded_fail | done | open."""
    L = len(pnl)
    # ---- evaluation
    bal = peak = 0.0; mll = -2000.0; best = 0.0; i = start
    while True:
        if i >= L: return "open", 0.0, i - start
        if bal + low[i] * n <= mll: return "eval_fail", 0.0, i - start
        bal += pnl[i] * n; best = max(best, pnl[i] * n)
        if mll < 100:
            peak = max(peak, bal); mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
        i += 1
        if bal >= 3000 and best <= cons * bal: break
    # ---- funded
    bal = peak = 0.0; mll = -2000.0; paid = 0.0; npay = 0; qd = 0; cyc = 0.0
    while i < L:
        if bal + low[i] * n <= mll: return "funded_fail", paid, i - start
        d = pnl[i] * n; bal += d; cyc += d
        if d >= 150: qd += 1
        if mll < 100:
            peak = max(peak, bal); mll = 100.0 if peak >= 2100 else max(mll, peak - 2000)
        i += 1
        if qd >= 5 and cyc > 0 and bal >= 1000:
            req = min(0.5 * bal, 2000.0)
            bal -= req; paid += 0.9 * req; npay += 1; qd = 0; cyc = 0.0; mll = 100.0
            if npay >= max_payouts: return "done", paid, i - start
    return "open_funded", paid, i - start

def evaluate(days, n=1, fee=146.0, starts=None):
    pnl, low = days.pnl.values, days.low.values
    res = [lifecycle(pnl, low, s, n, fee) for s in starts]
    df = pd.DataFrame(res, columns=["status", "paid", "days"])
    closed = df[~df.status.isin(["open"])]
    pass_rate = 100 * (closed.status != "eval_fail").mean()
    paid_any = 100 * (closed.paid > 0).mean()
    ev = closed.paid.mean() - fee
    return dict(n_starts=len(closed), pass_eval=round(pass_rate, 1), got_payout=round(paid_any, 1),
                avg_paid=round(closed.paid.mean()), ev_per_attempt=round(ev), five_payouts=round(100 * (closed.status == "done").mean(), 1),
                med_days_eval=int(closed.days.median()))

if __name__ == "__main__":
    import sys
    out = []
    dates = None
    for stop in (None, 300, 500, 700, 1000):
        days = na_days(stop)
        dts = pd.to_datetime(days.date)
        is_starts = [k for k in range(len(days)) if dts[k] < pd.Timestamp(IS_END)]
        oos_starts = [k for k in range(len(days)) if dts[k] >= pd.Timestamp(IS_END)]
        for n in (1, 2, 3):
            a = evaluate(days, n, starts=is_starts); b = evaluate(days, n, starts=oos_starts)
            row = dict(day_stop=stop, mnq=n, **{f"IS_{k}": v for k, v in a.items()}, **{f"OOS_{k}": v for k, v in b.items()})
            out.append(row)
            print(f"stop {str(stop):5} mnq {n}: IS pass {a['pass_eval']:5}% payout {a['got_payout']:5}% EV ${a['ev_per_attempt']:5} | OOS pass {b['pass_eval']:5}% payout {b['got_payout']:5}% EV ${b['ev_per_attempt']:5} 5x {b['five_payouts']}% days {b['med_days_eval']}", flush=True)
    pd.DataFrame(out).to_csv("prop_sim_na.csv", index=False)
