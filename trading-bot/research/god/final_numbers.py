"""Final numbers for the valid portfolio (GapFB + Pre-Fade + Opex; No-Wick removed — look-ahead), one account, netting rule.
Per year: trades, win %, R:R (avg win / avg loss in $), $ with 1 MNQ per trade and with the prop sizing (GapFB 1, Pre-Fade 2,
Opex 2), % of a $50,000 account. LucidFlex 50K: trading days to funded and to first payout, counted on ALL trading days."""
import os
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
T = pd.read_csv(os.path.join(HERE, "trades_netting.csv"), parse_dates=["entry", "exit"])
T = T[T.kept & (T.comp != "No-Wick")].copy()
T["usd_1"] = T.usd1                                                   # 1 micro on every trade
T["usd_p"] = T.usd1 * T.comp.map({"GapFB": 1, "Pre-Fade": 2, "Opex": 2})
T["date"] = T.entry.dt.normalize()
ALL = pd.bdate_range(T.date.min(), "2026-10-06")


def yearly(col):
    rows = []
    for y, g in T.groupby(T.entry.dt.year):
        w = g[col][g[col] > 0]; l = g[col][g[col] <= 0]
        rows.append(dict(year=y, trades=len(g), win_pct=round(100 * (g[col] > 0).mean(), 1), rr=round(w.mean() / -l.mean(), 2),
                         usd=round(g[col].sum()), pct_50k=round(100 * g[col].sum() / 50000, 1)))
    return pd.DataFrame(rows)


def prop(col, start, target=3000, dd=2000, mind=150, req=3000.0):
    idx = ALL[ALL >= start]; g = T[T.date >= start].sort_values("exit")
    pnl = g.groupby("date")[col].sum().reindex(idx).fillna(0).values
    low = g.groupby("date")[col].apply(lambda s: min(0.0, s.cumsum().min())).reindex(idx).fillna(0).values
    ev, pay, bust = [], [], []
    for s in range(len(idx)):
        bal = peak = best = 0.0; d = s; ok = False
        while d < len(idx):
            if bal + low[d] <= peak - dd: break
            bal += pnl[d]; best = max(best, pnl[d])
            if bal <= peak - dd: break
            peak = max(peak, bal); d += 1
            if bal >= target and best <= 0.5 * bal and d - s >= 2: ok = True; break
        if d >= len(idx) and not ok: continue                         # window ran out of data: not counted
        ev.append(d - s if ok else np.nan)
        if not ok: continue
        bal = peak = 0.0; floor = -dd; good = 0; cyc = 0.0; f0 = d; dead = False; got = np.nan
        while d < len(idx):
            if bal + low[d] <= floor: dead = True; break
            bal += pnl[d]; cyc += pnl[d]; good += pnl[d] >= mind
            if bal <= floor: dead = True; break
            peak = max(peak, bal); floor = max(floor, min(peak - dd, 100.0)); d += 1
            if good >= 5 and cyc > 0 and bal >= req: got = d - f0; break
        if not dead and np.isnan(got): continue
        pay.append(got); bust.append(dead)
    ev = np.array(ev); pay = np.array(pay)
    return dict(pass_pct=round(100 * np.mean(~np.isnan(ev)), 1), days_to_funded=np.nanmedian(ev),
                days_funded_to_payout=np.nanmedian(pay), days_start_to_payout=np.nanmedian(ev) + np.nanmedian(pay),
                bust_before_payout_pct=round(100 * np.mean(bust), 1))


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    for col, nm in (("usd_1", "1 micro per trade"), ("usd_p", "prop sizing GapFB1 / Pre-Fade2 / Opex2")):
        Y = yearly(col); Y.to_csv(os.path.join(HERE, f"final_yearly_{col}.csv"), index=False)
        print(f"\n=== {nm}"); print(Y.to_string(index=False))
        a = T[col]; w = a[a > 0]; l = a[a <= 0]
        print(f"ALL: trades {len(a)}  win {100 * (a > 0).mean():.1f}%  R:R {w.mean() / -l.mean():.2f}  $/yr {a.sum() / 16.3:.0f}")
        for st in ("2020-01-01", "2024-01-01"):
            print(" prop from", st, prop(col, st))
