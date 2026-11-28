# AVP Zones (the paid indicator): rules read from the user's screenshots, NQ1! 5m on OpenMarket

Chart axis is UTC. NY open = 13:30 UTC in Oct (EDT), 14:30 UTC from Nov 2 (EST). Indicator table: 24 trades, 46% win, +7.49R.

## Trade log so far (from screenshots; result read off the chart, W/L approximate)
| date | signal UTC (NY) | side | how | result |
|---|---|---|---|---|
| 2026-10-21 | 13:30 (09:30) | short | open bar closes below zone | flipped long ~15:00 |
| 2026-10-21 | ~15:00 (11:00) | long (flip) | close back above zone | W (2R) |
| 2026-10-23 | 13:30 (09:30) | long | open bar closes above zone | W |
| 2026-10-26 | 13:30 (09:30) | long | wick into zone, close above | W |
| 2026-11-04 | 14:35 (09:35) | long | huge bar closes far above zone (risk ~270pt) | ~-0.5R, flat at 16:00 NY |
| 2026-11-10 | 15:10 (10:10) | short | spike into zone, close back below | W |
| 2026-11-12 | 15:55 (10:55) | long | close above zone | L (flipped 13:50 NY) |
| 2026-11-12 | 18:50 (13:50) | short (flip) | close back below zone | ~0, flat at 16:00 NY |
| 2026-11-13 | 14:30 (09:30) | short | open bar closes below zone | W |
| 2026-11-18 | 14:40 (09:40) | short | close below zone | flipped |
| 2026-11-18 | 14:55 (09:55) | long (flip) | close above zone | L |
| 2026-11-19 | 15:35 (10:35) | short | breakdown close below zone | flipped |
| 2026-11-19 | 15:55 (10:55) | long (flip) | close above zone | L |
| 2026-11-20 | 15:00 (10:00) | short | rejection from zone bottom | W |
| 2026-10-27 | 14:20 (10:20) | long | dip to zone top, close above | W |
| 2026-10-28 | 13:55 (09:55) | long | flush below zone, close back above | W (late, ~16:00) |
| 2026-11-02 | 18:00 (13:00) | long | close above zone | L (flipped 13:30 NY) |
| 2026-11-02 | 18:30 (13:30) | short (flip) | close back below zone | W |
| 2026-11-03 | 14:30 (09:30) | long | open bar closes above zone | ~0, flat at 16:00 NY |
| 2026-10-20 | 14:20 (10:20) | long | strong rally closes above zone | L (flipped ~11:40 NY) |
| 2026-10-20 | ~15:40 (11:40) | short (flip) | close back into/below zone | L (stopped quickly, box short) |
| 2026-10-15 | 19:45 (15:45) | long | close above zone 15 min before the close | ~-0.5R, flat at 16:00 NY |
| 2026-10-09 | 14:25 (10:25) | long | flush into zone, close back above | ~+0.7R, flat at 16:00 NY |
Note: Oct 21 first short was at 13:40 UTC (09:40 NY), Oct 23 long at 13:40 UTC (big bar from below the zone closing above it).

Tally of the first 19 read: ~9 W (+2R each), ~7 L (about -1R; flips exit near the far edge), ~3 flat at 16:00.
First signal of the day 7 W / 14; flips 2 W / 5. Signals happen any time in RTH (one at 13:00 NY), most in the first hour.

## Rule as it looks (hypothesis to test)
- Zones: bands ~30-60 NQ points; red = above price (RZ), green = below (SZ), blue = the zone being traded.
  Price often consolidates for hours inside them -> they look like HIGH-volume nodes, not the low-volume (LVN)
  zones of our reconstruction (avp*.py). Table: anchor 31150 (= the high), 2597 profile rows -> ~2pt rows down to
  ~25950, i.e. one composite profile over all loaded history.
- Signal: a 5m RTH bar that trades into a zone and CLOSES outside it -> trade toward the side it closed on
  (both rejections and breakouts). One trade per zone.
- Entry: close of the signal bar. Stop: far edge of the zone. Target: ~2R (green box = 2x red box in every case measured).
- Flip: a later close back through the zone reverses the position. Flat at 16:00 NY.
- Most signals in the first ~90 minutes of RTH.

## Summary of 23 trades read (of 24)
~10 W at +2R, ~8 L at about -1R, ~5 flat at 16:00 NY (-0.5R to +0.75R). Roughly +12R before costs; the table says +7.49R
(our readings of the flat/flip exits are approximate). Signals fire any time 09:30-15:45 NY; time exit at 16:00 matters.
Next: rebuild this rule (high-volume zones from a composite profile, close-outside-zone signal, far-edge stop, 2R,
flip, flat 16:00) and test 2012-2026 with our gates.

## Zone prices read from screenshots (pixel -> price, calibrated)
Calibration (Nov 27 shot): user's hover on the drawn lines gave 27008 / 27058; my axis-label reading was ~5 pt low on
both edges (constant offset), so each screenshot is calibrated on a boxed price label. Zone = exactly 50 pt here.
Zone sets switch at 23:00 UTC = 18:00 NY (Globex session open): one set per trading day.
| session | zones (bottom-top, NQZ6) |
|---|---|
| Nov 26 (left part of the shot; only 2 visible) | 26362-26407, 26101-26148 |
| Nov 27 | 27008-27058, 26750-26798, 26490-26538 (all red = above / around price) |

## Zone ladder, Nov 19 - Nov 27 (from one zoomed-out shot, zones_from_shot.py, centres in NQZ6 points)
| session | above (R) | middle | below (G) | blue | step S | width |
|---|---|---|---|---|---|---|
| Nov 19 | 27808 27599 27383 | 27174 (blue) | 26979 26763 26554 | = middle | ~210 | ~45-55 |
| Nov 23 | 26857 26506 26155 | (25805, not drawn) | 25454 25103 24753 | 25286 | ~351 | ~80 |
| Nov 24 | 27821 27410 27012 | (26597, not drawn) | 26182 25791 25380 | 26844 | ~405 | ~80-95 |
| Nov 25 | 27612 27180 26756 | (~26331) | 25906 25468 25043 | 26263 | ~428 | ~80-95 |
| Nov 26 | 26385 26115 25873 | (25610, not drawn) | 25347 25077 24821 | 25994 | ~262 | ~54 |
| Nov 27 | 27033 26776 26507 | (26250, not drawn) | 25994 25738 25468 | - | ~262 | ~54 |
Findings: every session is a 7-slot ladder M + k*S (k = -3..3) with EQUAL spacing; the middle slot is often not drawn;
zone width ~0.2*S; S changes day to day (210 -> 351 -> 405 -> 428 -> 262), so it tracks volatility.
Hypothesis A (strongest): anchored VWAP with standard-deviation bands (M = VWAP from an anchor, S = sigma);
"AVP" may stand for anchored VWAP/volume profile. Hypothesis B: M = prior close/settle or POC, S = k*ATR(n).
Test both once 1-minute data with volume covering Nov 2026 is available.

## BREAKTHROUGH: the ladder's middle = the previous session's VWAP (OpenMarket VWAP, anchor Session, source Typical)
Read at the last bar of each Globex session (17:00 NY) vs the next session's zone ladder:
| session end | VWAP (end) | sigma (band spacing) | next day's middle M | next day's step S | S / sigma |
|---|---|---|---|---|---|
| Nov 20 | 25819 | ~418 | 25805 (Nov 23) | 351 | 0.84 |
| Nov 23 | 26605 | ~401 | 26597 (Nov 24) | 405 | 1.01 |
| Nov 24 | 26330 | ~214 | 26331 (Nov 25) | 428 | 2.00 |
| Nov 25 | 25603 | ~362 | 25610 (Nov 26) | 262 | 0.72 |
M matches the prior session's closing VWAP within 1-14 pt on 4/4 days. The step S is NOT the same session's sigma
(ratios 0.72-2.0). Next: read exact legend values (VWAP and band 1) at 16:00 NY (RTH close) and at other times, and
test S = RTH-only sigma, multi-session sigma, ATR or prior range once 1-minute data with volume is available.

## Exact VWAP legend values at 16:00 NY (session-anchored VWAP, Typical) vs next day's ladder
| day (16:00) | VWAP | sigma | next ladder middle M | next step S | S / sigma |
|---|---|---|---|---|---|
| Nov 23 | 26600.58 | 404.27 | 26597 (Nov 24) | ~405 | 1.00 (all 6 levels within 1-14 pt) |
| Nov 24 | 26330.97 | 215.27 | 26331 (Nov 25) | ~428 | 1.99 (levels = VWAP +/- 2,4,6 sigma, all within 12 pt) |
| Nov 25 | 25599.31 | 358.85 | 25610 (Nov 26) | ~262 | 0.73 |
Middle M = prior day's session VWAP: confirmed (within 1-11 pt). Step S: equals k*sigma with k = 1, 2, 0.73 -> the
multiplier is not fixed, so S is computed some other way (candidates: RTH-only sigma, sigma of the volume profile
rows, multi-day sigma, ATR, a floor/cap or rounding rule). Needs 1-minute data with volume to fit.
Blue zone (not on the ladder): Nov 23 25286, Nov 24 26844, Nov 25 26263, Nov 26 25994 -> candidate: prior-day POC.

## From the seller's own video "How to use AVP indi" (transcript, Nov 28 2026; indicator id @alloresearch/avp-zones-2)
- Blue zones = the core. "Based on APs" (anchored profiles); "marks volume zones that are historically seen as great
  reaction zones, plots them again and every day recalculates the probability". He will not say how they are marked.
  -> blue = volume-profile nodes picked by their historical reaction rate (consistent with the stats table:
  anchor / profile rows = one composite profile over the loaded history). Few signals per day.
- Red/green (RZ/SZ) = "lower probability" zones, used as intraday support/resistance. These are the VWAP-sigma ladder
  we decoded (middle = previous session VWAP). Their signals are OFF by default.
- Signal: price on one side of the zone (below -> look for shorts). A candle pops INTO the zone, then an OPPOSING candle
  closes back out on the original side -> signal at that close. Stop: far end of the zone + a few ticks.
  Target: resting liquidity or a fixed R (the scoreboard uses 2R).
- Flip trades: if the stop is hit (price goes through the zone) the opposite trade is signalled.
- Void counter-close if zone breaks: when ON, a candle that goes through the whole zone and then comes back is NOT a signal.
- One trade per zone (default ON). Signals within a trade: optional.
- Use the 5-minute chart; RTH hours are best. Zones do not depend on the timeframe. He trades it with discretion and
  QQQ/NDX options heatmaps; signals are "a fixed mechanism ... for guidance".
Implication for the plan: the step-S question only matters for the low-probability ladder. The test that matters is
blue = high-volume node + rejection signal. Rebuild blue as composite-profile HVNs ranked by past reaction rate.

## Screenshots from the video (settings of avp-zones-2)
- Tooltip, "Void counter-close if zone breaks": ON = a counter-close only counts if no candle traded beyond the far side
  of the zone since the touch; the zone re-arms after a candle closes outside it. (Default OFF.)
- Video defaults: Signals ON, Past days' zones ON, Exits ON, Signals while in a trade OFF, Long/short boxes OFF,
  One trade per zone ON, Flip trades OFF, Void counter-close OFF, Target = Next zone, Enable RZ OFF, Enable SZ OFF.
- Trading hours (when signals may fire; zones do not change): All hours, RTH 09:30-16:00, NY AM 09:30-12:00,
  NY PM 12:00-16:00, London 03:00-09:30, Asia 18:00-03:00, Custom.
- Video chart, Nov 24-26 (NQZ6): two blue zones at ~26225-26295 and ~25975-26045 (~70 pt wide), both drawn across
  several days -> blue zones are multi-day levels (they match our Nov 25 blue ~26263 and Nov 26 blue ~25994).
  So blue = persistent volume levels kept while their "probability" stays high; the daily VWAP ladder is separate.
- Zones are identical on 5m / 1h / 4h; the timeframe only changes how fast a counter-close confirms.
