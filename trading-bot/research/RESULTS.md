# Top-20 NQ strategy study — final results

**Data:** Databento GLBX MNQ.c.0, 1-minute, 2020-01-02 → 2026-10-06 (6.8 years, 1,660 full RTH days; half-days dropped;
cross-day signals skipped on the 28 contract-roll days). **Costs:** $2.50 per MNQ round trip (commission $1.50 + 1 tick
slippage per side); stress = +1 more tick per side. **No look-ahead:** signals on closed bars, fills at next open / resting
price, exits walked minute by minute, stop wins ties. **Overfitting control:** source parameters only (no tuning);
in-sample 2020–23 vs out-of-sample 2024–26; parameter-neighbourhood check on the leaders; per-year results.
`win`/`rr` are after costs; rr = average win / average loss. Sharpe = annualised on daily P&L.

## Not testable
- #9 ICT 30-second FVG scalp — needs tick data (not owned).
- #16 NQ/ES pairs — needs ES data (paid; not purchased).
- #13/#14 GMM — tested, but feature formulas and regime mapping are partly unspecified in the source; my implementation is an interpretation.

## TOP 3 (by robustness and risk-adjusted performance)
| Rank | Strategy | Entry rules | RR | Win % | Years |
|---|---|---|---|---|---|
| 1 | Noise-Area Intraday Momentum (paper base) | At each :00/:30 from 10:00, long if close > max(open, prior close)×(1+σ), short if < min(…)×(1−σ); σ = 14-day mean abs move from the open at that minute. Exit on opposite band / reversal, flat 16:00 | 0.99 | 57.7 | 6.8 |
| 2 | Crabel Stretch ORB ×2 | Buy stop at open + 2×stretch, sell stop at open − 2×stretch (stretch = 10-day mean of min(H−O, O−L)); other side = stop; exit at the close | 0.99 | 53.9 | 6.8 |
| 3 | Initial Balance breakout + VWAP | 5-min close beyond the 09:30–10:30 range, on the VWAP side, 10:30–14:30; stop = other IB side; target 1.5×IB beyond the level; flat 15:55 | 0.92 (planned 1.5) | 54.8 | 6.8 |

Why this order: #1 Sharpe 1.65 (IS 1.97 / OOS 1.42), 7/7 years positive, all 9 neighbouring parameter sets positive (Sharpe 1.04–1.77),
Lucid 50K pass 69 % (zero-edge baseline ≈ 40 %). #2 Sharpe 0.79 (IS 0.66 / OOS 0.94), 6/7 years, all 9 neighbours positive (0.57–0.93),
Lucid 38–69 % depending on parameters. #3 Sharpe 0.69 (IS 0.67 / OOS 0.71), 6/7 years, all 9 neighbours positive but weaker (0.18–0.69), Lucid 54 %.

## Every test (base parameters)
| name                                   |     n |   win |   rr |   pf |   avg_usd |   maxdd_usd |   sharpe |   IS_sh |   OOS_sh |   stress_avg | yrs_pos   |   years |
|:---------------------------------------|------:|------:|-----:|-----:|----------:|------------:|---------:|--------:|---------:|-------------:|:----------|--------:|
| 01 Noise-Area (band only, paper base)  |   976 |  57.7 | 0.99 | 1.34 |      31   |       -3264 |     1.65 |    1.97 |     1.42 |        14.51 | 7/7       |     6.7 |
| 01 Noise-Area (VWAP entry+trail, code) |  1382 |  41.6 | 1.82 | 1.3  |      16.6 |       -3861 |     1.59 |    2.21 |     1.12 |         7.31 | 7/7       |     6.7 |
| 01 Noise-Area (band entry, VWAP trail) |  1345 |  40.6 | 1.86 | 1.27 |      16   |       -4408 |     1.48 |    2.11 |     0.98 |         6.99 | 7/7       |     6.7 |
| 15 Crabel stretch x2                   |  1396 |  53.9 | 0.99 | 1.16 |      15.7 |       -5127 |     0.81 |    0.7  |     0.94 |         6.86 | 6/7       |     6.7 |
| 12 IB breakout stop-entry              |   309 |  60.8 | 0.73 | 1.14 |       7.8 |       -3088 |     0.75 |    1.18 |     0.42 |         2.9  | 5/7       |     6.7 |
| 12 IB breakout close-entry             |  1634 |  54.8 | 0.92 | 1.11 |       9.4 |       -4424 |     0.69 |    0.67 |     0.71 |         3.72 | 6/7       |     6.8 |
| 06 Gap fill zone                       |   288 |  59.7 | 0.74 | 1.09 |       4.8 |       -1439 |     0.62 |    1.15 |     0.19 |         1.42 | 5/7       |     6.7 |
| 08 Silver Bullet AM                    |    69 |  24.6 | 3.33 | 1.09 |       4.9 |       -1024 |     0.49 |    1.1  |    -0.19 |         1.43 | 4/7       |     6.1 |
| 15 Crabel stretch x1 NR4               |   412 |  45.6 | 1.28 | 1.08 |       7.8 |       -3546 |     0.46 |   -0.28 |     1.32 |         2.88 | 5/7       |     6.6 |
| 15 Crabel stretch x1                   |  1627 |  43.3 | 1.4  | 1.07 |       7.7 |       -8328 |     0.42 |    0.06 |     0.79 |         2.83 | 6/7       |     6.7 |
| 18 Williams k=0.25                     |  1620 |  52.4 | 0.97 | 1.06 |       6.1 |       -6930 |     0.42 |    0.33 |     0.52 |         2.07 | 4/7       |     6.8 |
| 02 5m ORB first candle 10R             |  1518 |  25.5 | 3.14 | 1.07 |       5.2 |       -6229 |     0.39 |    0.47 |     0.31 |         1.61 | 5/7       |     6.8 |
| 15 Crabel stretch x1 NR7               |   250 |  48   | 1.14 | 1.05 |       4.8 |       -2277 |     0.31 |    0.07 |     0.62 |         1.42 | 4/7       |     6.6 |
| 17 Overnight drift 02-03               |  1743 |  50.1 | 1.02 | 1.03 |       0.5 |       -4433 |     0.14 |   -0.31 |     0.6  |        -0.74 | 3/7       |     6.8 |
| 04 VWAP trend always-in                | 26566 |  16.1 | 5.11 | 0.98 |      -0.3 |      -19646 |    -0.23 |    0.19 |    -0.67 |        -1.17 | 3/7       |     6.8 |
| 19 ORB 2TP (15m OR)                    |   877 |  61.6 | 0.6  | 0.97 |      -1.1 |       -2132 |    -0.24 |   -0.78 |     0.18 |        -1.54 | 3/7       |     6.8 |
| 03 Last-30min rROD                     |  1623 |  47.9 | 1.02 | 0.94 |      -2.3 |      -10876 |    -0.34 |    0.67 |    -1.56 |        -2.15 | 3/7       |     6.8 |
| 05 30m ORB hold 15 bars                |  2082 |  52.4 | 0.85 | 0.94 |      -3.7 |       -8295 |    -0.37 |   -0.29 |    -0.47 |        -2.84 | 2/7       |     6.8 |
| 07 Asia/London sweep + FVG             |  1194 |  18.1 | 4.23 | 0.93 |      -2.1 |       -5621 |    -0.37 |    0.56 |    -1.26 |        -2.03 | 2/7       |     6.7 |
| 03 Last-30min both                     |  1211 |  47.4 | 1.01 | 0.91 |      -3.3 |       -8911 |    -0.49 |   -0    |    -1.1  |        -2.63 | 3/7       |     6.8 |
| 03 Last-30min rONFH                    |  1623 |  47.4 | 1    | 0.9  |      -3.9 |      -12379 |    -0.57 |   -0.89 |    -0.19 |        -2.93 | 2/7       |     6.8 |
| 19 ORB 2TP (30m OR)                    |   530 |  58.1 | 0.66 | 0.91 |      -3.2 |       -2485 |    -0.69 |    0.29 |    -1.4  |        -2.59 | 3/7       |     6.8 |
| 10 HTF sweep & reclaim                 |  1910 |  49.6 | 0.93 | 0.91 |      -2.6 |       -7472 |    -0.87 |   -1.08 |    -0.7  |        -2.28 | 2/7       |     6.7 |
| 11 EMA 9/21 open + VWAP                |  1300 |  51.2 | 0.82 | 0.86 |      -3.1 |       -5167 |    -1.01 |   -0.28 |    -1.78 |        -2.55 | 2/7       |     6.8 |
| 05 30m ORB hold 1 bar                  |  2094 |  46.7 | 0.96 | 0.84 |      -2.9 |       -6007 |    -1.06 |   -0.81 |    -1.36 |        -2.44 | 1/7       |     6.8 |
| 20 VA 80% rule                         |   364 |  40.4 | 1.2  | 0.81 |      -9   |       -4522 |    -1.24 |    0.62 |    -3.85 |        -5.52 | 4/7       |     6.7 |
| 13 London GMM long                     |  4818 |  41.1 | 1.26 | 0.87 |      -2.5 |      -13018 |    -1.37 |   -1.34 |    -1.43 |        -2.23 | 0/6       |     5.8 |
| 14 RTH GMM confluence                  |    49 |  42.9 | 0.76 | 0.57 |     -48.8 |       -3102 |    -3.33 |    0.35 |    -6.84 |       -25.39 | 2/6       |     5.4 |

## Robustness runs
| name                    |    n |   win |   rr |   sharpe |   IS_sh |   OOS_sh | yrs_pos   |   maxdd_usd |   mnq |   lucid_pass |   days_to_pass |
|:------------------------|-----:|------:|-----:|---------:|--------:|---------:|:----------|------------:|------:|-------------:|---------------:|
| NA base look10 every15  | 1083 |  56   | 0.95 |     1.06 |    1.11 |     1.05 | 6/7       |       -4224 |     1 |           56 |             78 |
| NA base look10 every30  |  996 |  56.8 | 1.02 |     1.64 |    2.11 |     1.26 | 7/7       |       -3967 |     1 |           66 |             76 |
| NA base look10 every60  |  861 |  58.3 | 0.99 |     1.77 |    2.1  |     1.51 | 7/7       |       -2902 |     1 |           76 |             74 |
| NA base look14 every15  | 1065 |  56.5 | 0.93 |     1.04 |    1.08 |     1.05 | 6/7       |       -4264 |     1 |           59 |             73 |
| NA base look14 every30  |  976 |  57.7 | 0.99 |     1.65 |    1.97 |     1.42 | 7/7       |       -3264 |     1 |           69 |             69 |
| NA base look14 every60  |  850 |  59.8 | 0.92 |     1.69 |    1.93 |     1.54 | 7/7       |       -2342 |     1 |           77 |             82 |
| NA base look20 every15  | 1049 |  56   | 0.96 |     1.09 |    1.22 |     1    | 6/7       |       -4100 |     1 |           62 |             76 |
| NA base look20 every30  |  965 |  57   | 0.96 |     1.35 |    1.62 |     1.15 | 6/7       |       -3212 |     1 |           62 |             75 |
| NA base look20 every60  |  845 |  57.9 | 0.91 |     1.16 |    1.61 |     0.8  | 6/7       |       -3216 |     1 |           72 |             78 |
| NA vwap look10 every30  | 1402 |  41.8 | 1.8  |     1.56 |    2.49 |     0.83 | 7/7       |       -4364 |     2 |           80 |             46 |
| NA vwap look14 every30  | 1382 |  41.6 | 1.82 |     1.59 |    2.21 |     1.12 | 7/7       |       -3861 |     2 |           75 |             48 |
| NA vwap look20 every30  | 1323 |  41.2 | 1.85 |     1.58 |    2.44 |     0.9  | 7/7       |       -3230 |     2 |           79 |             42 |
| Crabel x1.5 look5       | 1548 |  49.4 | 1.14 |     0.62 |    0.38 |     0.88 | 6/7       |       -6923 |     1 |           44 |             84 |
| Crabel x1.5 look10      | 1542 |  50.1 | 1.14 |     0.76 |    0.49 |     1.05 | 6/7       |       -5768 |     1 |           42 |             65 |
| Crabel x1.5 look20      | 1550 |  50   | 1.1  |     0.57 |    0.49 |     0.67 | 6/7       |       -5770 |     1 |           39 |             62 |
| Crabel x2.0 look5       | 1394 |  53.6 | 1.02 |     0.89 |    0.98 |     0.83 | 6/7       |       -5486 |     1 |           52 |             76 |
| Crabel x2.0 look10      | 1391 |  53.8 | 0.99 |     0.79 |    0.66 |     0.94 | 6/7       |       -5127 |     1 |           69 |            100 |
| Crabel x2.0 look20      | 1379 |  53.6 | 0.98 |     0.66 |    0.59 |     0.76 | 6/7       |       -5135 |     1 |           38 |             72 |
| Crabel x2.5 look5       | 1216 |  52.6 | 1    |     0.58 |    0.23 |     0.92 | 5/7       |       -6120 |     1 |           37 |             67 |
| Crabel x2.5 look10      | 1201 |  55   | 0.98 |     0.93 |    1.07 |     0.85 | 5/7       |       -4592 |     1 |           55 |             72 |
| Crabel x2.5 look20      | 1192 |  55.1 | 0.93 |     0.68 |    0.86 |     0.57 | 5/7       |       -4611 |     1 |           42 |             93 |
| IB breakout close-entry | 1634 |  54.8 | 0.92 |     0.69 |    0.67 |     0.71 | 6/7       |       -4424 |     1 |           54 |            105 |
| IB breakout no-VWAP     | 1634 |  54.8 | 0.92 |     0.69 |    0.67 |     0.71 | 6/7       |       -4424 |     1 |           54 |            105 |
| Williams k0.2           | 1637 |  52   | 0.93 |     0.07 |    0.34 |    -0.22 | 3/7       |       -9623 |     2 |           24 |             27 |
| Williams k0.25          | 1620 |  52.4 | 0.97 |     0.42 |    0.33 |     0.52 | 4/7       |       -6930 |     1 |           35 |             85 |
| Williams k0.3           | 1579 |  54.2 | 0.92 |     0.58 |    0.2  |     1    | 5/7       |       -5577 |     1 |           45 |             89 |
| 5m ORB first candle 10R | 1518 |  25.5 | 3.14 |     0.39 |    0.47 |     0.31 | 5/7       |       -6229 |     2 |           31 |             35 |
| 5m ORB first candle 5R  | 1518 |  26.8 | 3    |     0.55 |    0.3  |     0.82 | 5/7       |       -4410 |     2 |           35 |             31 |
| Gap fill zone           |  288 |  59.7 | 0.74 |     0.62 |    1.15 |     0.19 | 5/7       |       -1439 |     3 |           38 |             45 |
