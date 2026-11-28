# AVP Zones reverse-engineering: full plan (Nov 28, 2026)

Goal: rebuild the paid AVP Zones indicator closely enough to reproduce its trades, then judge the rule on
2012-2026 NQ with our usual gates. Indicator access ends **Dec 5, 2026**, so everything that needs the live
indicator (steps 1, 3 check, 6) comes first.

Inputs we already have: 23 of 24 trades read from screenshots (`AVP_REAL_NOTES.md`), the settings panel
(Signals, Past days' zones, Exits, One trade per zone, Flip trades, Target = Next zone, RZ/SZ, RTH 09:30-16:00),
the stats table (anchor 31150, profile rows 2597, 7 zones, 24 trades, 46%, +7.49R).

---

## Step 0. Data (blocking)
- Run `python multi/duka.py USATECHIDXUSD` on Rotem's PC (now runs to yesterday). Check: one row per year, errors near 0,
  2026 includes Oct-Nov.
- If Dukascopy refuses: HistData NSXUSD zips (manual, see DATA.md). Note HistData lags; Oct-Nov 2026 may be missing ->
  then the zone-matching step needs another source for those two months (TradingView/OpenMarket CSV export by the user,
  if allowed).
- **Basis problem.** NQ futures trade above the cash/CFD index (basis ~ +50 to +300 pt, shrinking to expiry).
  For matching zone prices in Oct-Nov 2026, estimate the daily offset = NQ price in a screenshot (O/H/L/C shown at a
  timestamp) minus the CFD price at the same minute. Use 3-5 readings per contract month; check the offset is stable
  (sd < 5 pt). If it is not stable, match zones in relative terms (distance from the day's open) instead of absolute.
- **Volume problem.** Dukascopy volume is CFD tick volume, not CME volume. Profile peaks may sit in slightly different
  places. Measure it in step 2 (zone overlap). If overlap is poor only because of volume, try a time-at-price (TPO)
  profile as well: earlier work showed TPO and real volume give similar zones.

## Step 1. Ground truth to collect while access lasts (needs Rotem)
1. Zone edges: for ~10 days (spread Oct 9 - Nov 20), hover the top and bottom of every zone drawn that day and write
   the prices. Also note colour (red above / green below / blue active) and when a zone appears/disappears.
2. All 19 settings (General, Style, Visibility tabs) as screenshots, including the defaults we have not seen
   (zone count, lookback, width, profile type if exposed).
3. The 24th trade (missing).
4. Discord members channel: copy any guide text (how zones are built, which to trade, filters).
5. Optional: change one setting at a time (e.g. Target, Flip trades OFF) and note how the table (trades / win / net R)
   changes. Each change tells us exactly what that switch does.

## Step 2. Rebuild the zones (the main unknown). Test several hypotheses, pick by fit
Score each hypothesis by how well its zones overlap the observed ones (IoU per zone, % of observed zones matched within
10 pt per edge), across the ~10 recorded days.
- H1 Composite profile over all loaded history: rows from the anchor (31150 = top) down; 2597 rows ->
  row size = (31150 - lowest loaded price) / 2597 (~2 pt if history goes down to ~25,950). Zones = top-K high-volume
  nodes (HVN), K = 7, each zone = contiguous rows above X% of the node's peak.
- H2 Rolling profile of the last N sessions (N = 1, 3, 5, 10, 20), HVN peaks, K = 7 nearest to price.
- H3 Same as H1/H2 but RTH-only volume vs 24h volume.
- H4 Value-area style: POC +/- a fixed width (e.g. 15-30 pt) per peak.
- H5 Time-at-price (TPO) instead of volume, for H1-H4.
- H6 LVN instead of HVN (our old reconstruction) as a control: expected to fit badly.
Decision: keep the best hypothesis if >= 70% of observed zones are matched. If none reaches 70%:
  (a) refine around the best (thresholds, merge distance, minimum width);
  (b) use step 1.5 experiments to pin parameters;
  (c) fall back to "observed zones only" for the trade-matching check and test the rule on a range of close
      hypotheses on history (report the spread of results, not one number).

## Step 3. Rebuild the signals and match the 23 trades
Rule hypothesis: 5m RTH bar trades into a zone and closes outside it -> enter at the close toward that side;
stop = far edge of the zone; target = 2R; one trade per zone; a later close back through the zone flips the
position; flat at 16:00 NY.
Ambiguities to test as variants (each scored by trades matched: same day, side, entry bar +/- 1):
- entry at signal close vs next bar open;
- "touched the zone" required vs any close beyond an edge;
- one trade per zone per day vs per zone lifetime;
- flip on close through the far edge vs any close back inside;
- target 2R fixed vs next zone (and min/max of the two);
- exits: 16:00 NY flat vs 15:55; same-bar stop/target ties resolved by 1-minute data (resolve1m method).
Pass: >= 18 of 23 trades matched and total R within +/-3R of the table's +7.49R (same window).
If it fails: list the mismatched trades, find the common cause (usually a zone mismatch -> back to step 2).

## Step 4. History test 2012-2026 (our gates, unchanged)
- Choose any variant/parameter only on 2012-2019. Judge 2020-2026 once.
- Costs: 1 NQ point round trip (plus a check at 2 pt). Futures basis does not matter for R.
- Placebo: same rule on random zones (same count and widths, random prices within the day's range), 1000 runs; p < 0.05.
- Monte Carlo bootstrap of trades for drawdown / risk of ruin; per-year table; t-stat.
- Pass bar: OOS avg R > 0 after costs with t >= 2, >= 5 of 7 OOS years positive, beats placebo (p < 0.05).
Branches:
- Pass -> step 5.
- Fail but one part looks strong (first signal of day, no flips, long only, wide zones, before 11:00 NY):
  test that part ONLY as a pre-registered hypothesis chosen on 2012-19, judged once on 2020-26.
- Fail everywhere -> write it up (Graveyard in Edge Lab), stop.

## Step 5. Robustness (only if step 4 passes)
- 1-minute re-resolution of same-bar stop/target; slippage on large signal bars (entry at close of a big bar).
- MNQ vs NQ costs; prop-firm simulation (daily loss limit, trailing drawdown) with the existing prop_sim scripts.
- Stability: parameters +/-20%, different zone thresholds; the result must not hinge on one setting.

## Step 6. Live forward check (Nov 30 - Dec 4, while access lasts)
- Each RTH day: our engine's signals vs the indicator's signals in real time (Rotem screenshots at day end).
- This is the cleanest out-of-sample check of the reconstruction itself.

## Step 7. Deliver
- Registry entry in research/lab (build.py), Edge Lab page republished with data.json and learn.js, and a Learn lesson
  update per CLAUDE.md (volume-profile zones, reverse-engineering, why placebo matters).
- If it passes: our own indicator script (Pine / OpenMarket kScript) so Rotem keeps it after Dec 5.
- Final verdict to Rotem in 5 lines.

## Order and timing
Now: step 0 (download running) + step 1 (Rotem, before Dec 5).
Then: steps 2 -> 3 (iterate until matched) -> 4 -> 5/6 -> 7.
