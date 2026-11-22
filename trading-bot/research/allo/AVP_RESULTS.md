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

## Exact Pine port on 14 years (avp_port.py, port_nq_results.txt) — NQ with real (Dukascopy) volume
Defaults of pine/avp_zones.pine, 24h sessions from 18:00 NY, Pine scoreboard (2R, flat next session open).
- 5/7/15/30/60/91 min, real volume, 2012-2026, NO costs: avg -0.026 to +0.021 R; 2012-19 negative in 5 of 6 timeframes; positive years 5-11/15.
- With costs (1 NQ point round trip): -0.044 to -0.082 R in every timeframe.
- Aug-Nov 2026 only (what TradingView shows): +0.03 to +0.22 R -> reproduces the user's table; that window is the exception.
- Random-zone baseline (5m, 2020-26): p = 0.42.  DAX / gold / TPO volume: same picture.

## The AVP equation (avp_eq.py) — meta-labelling fitted on 2012-19, judged once on 2020-26 (NQ 5m, real volume, after costs)
E[R] = -0.345 + 0.603*zone_width + 0.137*emptiness - 0.162*risk + 0.048*side + 0.021*day_move + 0.016*London + 0.013*trend + 0.003*NY + 0.0003*bar_volume
(zone_width and risk in ATR units; side +1 long / -1 short; trend and day_move signed by side.)
Take a signal only if E[R] > 0: 2012-19 46/yr +0.10R (fit period) -> 2020-26 50/yr +0.072R (t 1.23), 5/7 years positive,
random same-size picks p = 0.081 (not below 5%). Top-30% cut: ~0R. All signals: -0.14 / -0.02R.
Reading: the only strong term is zone width (wide LVNs much better), then smaller risk and longs.
