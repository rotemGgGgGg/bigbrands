# Model 1 deep test — Gotobi fix, exact EA calendar (last day of month, Mondays included). Full output: deep_output.txt
Book 1 lot x USDJPY+EURJPY+GBPJPY, $100K, costs ~ IC spread + $7/lot:
- vendor window 2018-Jul 2026: +$77,542 (vendor +$83,888), PF 1.63, win days 60.9%, avg win $542 / loss $519, max DD -$7,440
- 2012-2017 (never shown): +$92,957, PF 1.94. 2012-2026: +$175,397, PF 1.78, win 61.7%, RR 1.10, ~$11.7K/yr. 15/15 years positive.
- Ordinary-day control negative on all pairs; placebo 1000 random day sets p < 0.001; 95% CI 4.6-8.4 pips/day/pair.
- Variation grid (100): vendor params already near the top; best-by-2012-19 variant does worse OOS than vendor's.
- Overlays: nominal-day weighting slight gain (OOS Sharpe/day 0.194 -> 0.217); stops, run-into-fix filter, vol sizing,
  mean-variance weights, 08:00 start: no gain. USDJPY+EURJPY only ~ equal to 3 pairs.
- 2026: short-leg edge moved before 09:55 (front-running), matches vendor's own warning.
