# GapFB bot — reconstructed from its Discord alerts and backtested

## Rules (read off the alerts, verified on Databento MNQ July 2026)
- Gap = 09:30 open vs prior 15:59 close; qualifies at |gap| ≥ ~0.3 % (alerts 0.33 %+, no alert on −0.26 % / −0.02 %).
  Our gap numbers match the alerts (0.97 vs 0.98, 1.52 vs 1.52, −0.75, −1.52, 1.09, −0.86, 1.98, 1.23 %).
- OR = 09:30–09:34 high/low (matches to 1–2 ticks). Buy stop at OR high, sell stop at OR low.
- Stop = 2 × ATR(14) of 1-minute bars at the fill, target = 2 × stop (2:1). Up to 2 trades a day, both sides re-armed.
- Replication check: NQ trade sides for 7/17–7/30 match every posted alert (e.g. 7/20 long→short, 7/21 short→long,
  7/22 long,long, 7/23 long,long, 7/27 short,short, 7/28 short,short, 7/30 long,long).

## Result (costs 2.25 pt round trip) — no edge
| period | trades/yr | win | avg R |
|---|---|---|---|
| MNQ 2020–23 | ~324 | 34.1 % | −0.04 |
| MNQ 2024–26 | ~292 | 34.0 % | −0.06 |
| NSX CFD 2012–19 | ~245 | 35.4 % | −0.05 |
34 % at 2:1 is the random-entry barrier (1/3); before costs ≈ 0 R. Threshold 0.5 %, entry cut-off 12:00, time exit 12:00,
trade #1 / #2 only: all ≈ −0.03…−0.10 R. `python3 gapfb.py` reproduces everything.

## The author's real variant (from his YouTube video): stop only, NO take-profit, time exit
Data: the user's Databento NQ 1-minute file 2010-06 → 2026-07 (front month by prior-session volume; matches our MNQ
to a median 0.25 pt over 2.3 M overlapping minutes) for 2010–19, Databento MNQ for 2020–26. `notp.py`, `notp_check.py`,
`notp_years.py`.

Same entries (gap ≥ 0.3 %, 5-min OR stop entries), stop 3 × ATR(14, 1-min) at the fill, no target, exit 15:55, 1 trade a day:
| period | trades/yr | win | R:R (avg win / avg loss) | avg R |
|---|---|---|---|---|
| 2010–19 | ~130 | 24.2 % | 3.70 | +0.14 |
| 2020–23 | ~160 | 25.3 % | 3.67 | +0.19 |
| 2024–26 | ~150 | 27.0 % | 3.00 | +0.08 |
- Robust: gap ≥ 0.2 / 0.3 / 0.5 % all positive in every period; exit 12:00 also positive (31 % win, 1:2.5).
- Placebo: the same trade on NON-gap days (|gap| < 0.3 %) is negative in 2010–19 and 2020–23 → the gap filter carries the edge.
- 15 of 17 calendar years positive (2015 −31 R, 2025 −9 R). Total +336 R over 2,287 trades.
- Risk: max drawdown 50.7 R, longest losing streak 31 trades. On a $2K trailing-drawdown eval that means ≤ ~$40 risk per trade,
  below 1 MNQ at a 3×ATR stop (~60 NQ pts ≈ $120) — fine for a personal account sized for 50 R, hard for a prop eval.
