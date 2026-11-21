# AVP-zone (LVN rejection) rule, reverse-engineered from allo's screenshots — NQ 2012-2026
Rule: LVN zones from a composite time-at-price profile of the previous N sessions; a 5-min bar from above trades into the
LVN top and closes back above -> long (mirror short); stop beyond zone/wick; targets 2R / 3R / 1% / session extreme / 15:55.
Base (5 sessions, LVN < 35% of local peak): ~106 trades/yr, win 41-59%, avg R between -0.04 and +0.02 in every target,
7/15 years positive. Versus the same rule on randomly shifted zones (allo's own test): p = 0.07-0.67 -> no better than chance.
12 profile variants (1/3/10 sessions x 2 thresholds x 2 targets): none with |t| > 1.5 in both periods.
Caveat: volume is a time-at-price proxy (no real volume in HistData); real MNQ volume could differ.

## Honest optimisation (avp2.py): 540 settings, choose 2012-19, check 2020-26, then shifted-zone baseline
Grid: stop wick+buffer / zone edge x max risk 0.15% / 0.3% / none x target 1/2/3/5/12R x London / NY / both x trend none / 50-day / day x 1 or 3 trades a day.
- 450 settings with >= 100 trades. Passing 2012-19 (t >= 2.5, >= 5/8 years): 0. Best 2012-19 t = 1.6 (zone stop, 3R, London, with the day) -> 2020-26 -0.06R.
- Every family is negative out of sample: wick stop -0.21R (tight stops get swept), zone stop -0.01R; London -0.20R, NY -0.05R; 1:12 target -0.09R.
- No finalist reached the random-baseline stage. Pine defaults changed to the least-bad setting (zone-edge stop, no risk cap).
