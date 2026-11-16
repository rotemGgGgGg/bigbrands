# MATH ENGINE — one strategy from return statistics and scheduled flows only (no chart patterns)
Textbook parameters fixed in advance (no grid search). Walk-forward: weights re-set each January from past data only;
2016-2026 fully out of sample. Portfolio vol-targeted to 10%.

Sleeves alone (Sharpe 2012-15 / 2016-19 / 2020-26, positive years):
- GOTOBI (Ito & Yamada flow)       1.78 / 1.69 / 1.59  15/15  <- kept
- TSMOM 20/60/120d, 8 markets       0.62 / 0.35 / 0.57  11/15  <- kept
- REVERSAL >2 sigma days, indices   0.02 / 0.28 / 0.42  10/15  <- kept
- TOM turn of month, indices        0.30 / 0.01 / 0.70   9/15  <- kept
- IMOM intraday momentum            -1.0 / -1.3 / -2.0   1/15  <- dropped by the walk-forward (gross ~0, costs)
- SEASON half-hour periodicity      -1.9 / -2.1 / -0.7   2/15  <- dropped (costs)
- FIX month-end London 4pm          -0.7 / 0.1 / -0.1    8/15  <- dropped
Correlations between sleeves |r| <= 0.11.

Portfolio 2016-2026 OOS:
- equal risk:      Sharpe 1.24, t 4.14, CAGR 14.7%, max DD -18.7%, win days 55.4%, RR 1.06, 10/11 years positive
- Sharpe-weighted: Sharpe 1.28, t 4.29, CAGR 16.3%, max DD -20.0%, win days 55.2%, RR 1.16, 10/11 years positive (2024 -5.1%)
Prop 50K (Sharpe-weighted): 3% vol -> 71% payout / 22% fail (~360 days); 5% -> 47% / 50%.
Caveats: Gotobi was picked from a vendor's lead, not pre-registered here; CFD overnight financing not included for TSMOM/TOM.
