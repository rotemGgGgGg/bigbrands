# Gotobi Tokyo-fix reversal (Ito & Yamada 2017) — USDJPY, Dukascopy 1-min, 2012-2026, cost 1 bp/trade

Published rules (sell 09:55 Tokyo, exit 10:20, stop 0.15%):
- Gotobi: 1059 trades, +1.37 bp/trade, t 4.63, win 56.8%, PF 1.54. Non-Gotobi control: -0.22 bp, t -1.34.
- Vendor window Sep 2016-Aug 2026: t 5.30, win 58.2%, PF 1.72 (~$7.8K at $100 risk; vendor claims $8.35K) — replicates.
- 2012-Aug 2016: +0.64 bp, t 0.98 — weak before their window. 2012-19 IS t 1.75; 2020-26 OOS t 5.24. 12/15 years positive.
- Placebo digit pairs: 1/6 t 2.39, 2/7 1.43, 3/8 -0.26, 4/9 1.14 — Gotobi strongest by far.
- Timing is critical: entry 09:55 OOS t ~5; 09:56 ~3; 10:00 negative. Must sell at the fix minute.
- Stop size barely matters; exit 10:20 best, 10:05-10:55 all positive. 85/100 neighbourhood variants positive OOS.

Portfolio (equal risk, 10% vol, OOS 2020-26):
- OLD 0.73 | OLD+LB 0.85 | **OLD+GOTOBI 1.73 (t 4.61, maxDD -8.6%)** | OLD+LB+GOTOBI 1.67 (maxDD -8.0%), 7/7 years positive.
- Correlation of Gotobi with everything ~0.01.
- Prop 50K, all three @5% vol: 90% payout / 0% fail (~250 days); @8% vol: 73% / 21% (~126 days).
