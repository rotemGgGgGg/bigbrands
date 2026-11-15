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

## Full vendor version (GotobiFixALL: long 18:00 UTC prev day -> fix, short fix -> +35 min, no stop), 3 pairs, 1 lot each
| pair | 2018-26 t / PF | 2012-17 (not shown by vendor) t / PF |
|---|---|---|
| USDJPY | 4.07 / 1.58 | 5.38 / 2.33 |
| EURJPY | 4.31 / 1.66 | 4.13 / 1.79 |
| GBPJPY | 2.30 / 1.35 | 3.02 / 1.61 |
Non-Gotobi control negative on all three.
$ (1 lot each): 2018-01..2026-11 **+$55,680, PF 1.56, max DD -$5,249** (vendor: +$83,888, PF 1.71); 2012-17: +$72,674, PF 1.92.
Per year $: 2012 7.1K, 2013 22.9K, 2014 4.8K, 2015 7.6K, 2016 19.5K, 2017 10.8K, 2018 9.7K, 2019 10.0K, 2020 6.1K, 2021 6.6K,
2022 9.8K, 2023 -1.3K, 2024 6.5K, 2025 7.7K, 2026 0.5K.
Pairs correlate 0.62-0.75 daily: three pairs = mostly the same yen bet x3, not diversification.
Edge real, decaying (long leg fading since 2023); our costs (1.0-1.4 bp/leg) explain much of the gap to the vendor's number.
