# AVP-zone (LVN rejection) rule, reverse-engineered from allo's screenshots — NQ 2012-2026
Rule: LVN zones from a composite time-at-price profile of the previous N sessions; a 5-min bar from above trades into the
LVN top and closes back above -> long (mirror short); stop beyond zone/wick; targets 2R / 3R / 1% / session extreme / 15:55.
Base (5 sessions, LVN < 35% of local peak): ~106 trades/yr, win 41-59%, avg R between -0.04 and +0.02 in every target,
7/15 years positive. Versus the same rule on randomly shifted zones (allo's own test): p = 0.07-0.67 -> no better than chance.
12 profile variants (1/3/10 sessions x 2 thresholds x 2 targets): none with |t| > 1.5 in both periods.
Caveat: volume is a time-at-price proxy (no real volume in HistData); real MNQ volume could differ.
