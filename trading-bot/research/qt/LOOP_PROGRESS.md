# Quarterly Theory / Atlantis research loop — progress

## Sources read
- Atlantis Pine (QT Atlas v1.4): SSMT across 90-min quarters vs ES/YM, hidden SSMT (closes), tCISD, retest entry, 2R + BE.
- Cycles.pdf: 4y / yearly / monthly(weeks) / weekly(Mon–Thu) / daily(Asia, London, AM, PM) / session(4×90m) / 90m(4×22.5m).
- quarterly_theory_playbook_v2_3.docx: AMDX, True Opens (Q2 open of each cycle), STS, SMT/SSMT, YM weak asset,
  hidden SMT, SSMT fills (3 types), PSP, 90-min cycle times, two-stage model, IFVG entry, targets.

## ES / YM data (free)
- Dukascopy USA500IDXUSD (S&P CFD) 1-min works but is rate-limited (HTTP 429): ~3 days/min → background download,
  newest first (scratchpad/es). USATECH / USA30 also 429 for now.
- Next: Yahoo ES=F / NQ=F / YM=F — 1h for 730 days, 5m for 60 days (free, fast).

## Iteration 1 results — NQ-only claims (2020–2026)
| Claim | Result | Verdict |
|---|---|---|
| AMDX: Q2 sweeps one side of Q1 → Q3 reverses | 49.5 % / 52.8 % vs 51.8 % base | ❌ no effect |
| True daily open: discount → up by 12:00 | 55.0 % vs 54.4 % base | ❌ no effect |
| True session open: discount → up | 54.3 % | ❌ |
| Premium → down | 46 % (worse than coin) | ❌ |
| Weekly high/low made Mon–Tue (Q1/Q2) | high: Fri 35 %, low: Mon 35 % — extremes cluster at week edges | ❌ as stated |
| Monthly week 3 = trend week | W3 trend ratio 0.50 = W1 | ❌ |
| STS long (below weekly+daily+session opens) | 58.5 % up, +15.1 pt to 12:00 (n 378) vs +2.0 base | ⚠️ candidate |
| STS short (above all three) | avg −15.1 pt to 12:00 (n 404) | ⚠️ candidate |

## Iteration 2 — SMT family on Yahoo 1h NQ/ES/YM (May 2024 → Oct 2026), STS re-test
- ⚠️ Correction: iteration-1 STS used the Monday 18:00 weekly open on Monday mornings (look-ahead). Fixed.
| Test | Result | Verdict |
|---|---|---|
| Daily-cycle SSMT NQ/ES (wick) | 50 % 1h, 46 % to session end (n 1,073) | ❌ |
| Daily-cycle hidden SSMT (closes) | 49–50 % | ❌ |
| Daily-cycle NQ/YM, ES/YM ("YM rule") | 49–51 % | ❌ |
| Weekly-cycle SSMT (days) | 48–51 % | ❌ |
| PSP 1h low → long | 59 % at +3h, +7.6 pt (n 344) vs same-colour swing 52.5 % / +2.1 | ⚠️ candidate (long only; PSP high → short fails) |
| PSP 4h | 42–49 % | ❌ |
| STS (look-ahead fixed) | ≈ +$6/trade, 4/7 years | ❌ (was an artefact of my bug) |
Files: qt_smt_1h.py (+results), qt_sts.py (+results).
