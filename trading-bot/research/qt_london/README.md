# "London takes Friday's liquidity → Monday AM to the other side" (WhatsApp group rule, Aug 24 2026)
Script: london_sweep.py · results.csv (398 configs) · Databento MNQ 1-minute 24h, 2020-01 → 2026-10, costs 2.25 pt.

Exact rule (pre-specified by the group, not found by search): Monday; Friday's Globex high/low; London killzone 02:00–05:00 takes
ONE side → trade the other way in NY AM on the first 5-minute close beyond the previous 3 five-minute bars (09:30–11:00);
stop beyond the London extreme; target = Friday's opposite side; flat 16:00.
→ 40 trades, 65 % wins, planned R:R 1.63, realised 1.49, **+0.37 R**, 2020–23 +0.36 / 2024–26 +0.38, 7/7 years positive,
t = 2.50, bootstrap 95 % CI [+0.09, +0.67].
Fixed 1:2 target: 60 % wins, realised 1.65, +0.36 R, 6/7 years.
Neighbourhood: every Monday variant positive in both halves (+0.15 … +0.37 R); the same rule on Tue–Fri ≈ 0 or negative.
TDO filter hurts. Limit at 50 % (premium/discount) loses (−0.44 R).
Status: PROVISIONAL — real-looking, but only ~6 trades a year.
