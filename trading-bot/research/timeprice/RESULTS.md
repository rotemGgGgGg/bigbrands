# 'Time & price' on NQ, 2012-2026 (choose 2012-19, judge 2020-26), cost 1.3 bp
H1 ICT time-based levels (midnight open / 08:30 open), 96 rules: none with 2012-19 t>=2.
   Best lead: at 09:30, if price is >0.25 ATR from the 08:30 open, fade back to it (stop 0.5-1x distance):
   ~31 trades/yr, win 40-54%, RR 1.1-1.9, IS t 1.5-2.0, OOS t 1.0-1.75, 10-12/15 years positive. Weak, not proven.
H2 ICT macros (08:50, 09:50, 10:50, 11:50, 13:10, 15:15): every rule negative; macro windows no different from other windows.
H3 Gann square of 9 (45-degree levels from prior close), fade first touch: negative, and no better than randomly shifted levels.

# Quarterly Theory (time / 4, fractal) - quarters.py
Levels week (Mon-Thu), day (6h), session (90 min), micro (22.5 min), anchored 18:00 NY; true open = Q2 open.
Rules at Q3 open: reversal vs true open, continuation, AMD (Q2 sweeps Q1 then reclaims; stop at Q2 extreme), AMD + true-open side.
Placebo: identical rules on grids shifted 1/8..7/8 of a block.
32 rule x level combinations: none positive with significance; 2012-19 t from -17.7 to +0.38; 2020-26 best t 1.43 (week AMD+TO, 6 trades/yr).
Session-level reversal beats all shifted grids (time alignment carries a little information, ~1.6-2 bp gross in NY AM)
but is below costs: NY AM net +0.3 to +0.8 bp, t < 0.7. No tradeable edge.

# Quarter Sequence Map (original time x price state model) - sequence.py
States: session x 90-min quarter x price band in previous session's range (6) x side of true open (x up/down sequence).
Learned on 2012-19, Bonferroni-corrected; judged 2020-26; placebo = shifted clocks.
Only one state passes Bonferroni: NY AM quarter 1 (06:00-07:30 NY) opening in the BOTTOM quarter of the London (00:00-06:00) range -> long.
- NQ: 53 trades/yr, 2012-19 +2.1 bp t 2.3 (state t 3.8), 2020-26 +1.9 bp t 1.2, win 55%, 12/15 years positive.
- Real clock OOS t 1.16 > every shifted clock (max 0.61).
- Mirror (top quarter): NQ falls next 90 min (long side 0/15 years) but the short is ~0 after costs.
- S&P: 13/15 years positive but 2020-26 t 0.3. DAX, gold: nothing (06:00 NY is not their session).
Sequence (up/down history) adds nothing robust. Verdict: a real but small effect (~2 bp/trade), not proven out of sample.
