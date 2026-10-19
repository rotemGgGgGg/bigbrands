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
