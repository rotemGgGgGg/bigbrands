# My final theory — built from the QT / Atlantis material, then kept only what the data supports

**Data:** NQ/MNQ 1-min 2020–2026 (Databento); ES/YM from Yahoo (1h 2024–26, 5m Aug–Oct 2026).
Costs $2.50 per MNQ round trip. Every rule chosen on 2020–23 and checked on 2024–26.

## What the QT material claims vs what the data shows
| Idea from the material | Test | Result |
|---|---|---|
| SMT / SSMT (NQ vs ES/YM) at 90m, session, daily, weekly cycles | 516–1,938 events per test | 47–52 % — no edge |
| Hidden SMT, YM "weak asset" rule | same | no edge |
| AMDX: Q2 manipulation → Q3 distribution | 1,226 days | 49.5–52.8 % — no edge |
| True Open premium/discount, STS | 1,700 days | no edge (STS edge was my look-ahead bug) |
| Weekly cycle (Mon/Tue extremes), monthly week 3 | 7 years | not as described |
| PSP (1h) | 344 lows | 59 % long — but PSP highs fail → likely bull drift |
| Sweep of liquidity then reclaim → reversal | daily & weekly | longs ≈ baseline; shorts lose |

## The theory the data supports: "momentum inside the day, reversal between days"
1. **Inside the session, abnormal moves continue.** When price leaves its normal intraday noise band, it keeps going
   (Noise-Area, 976 trades, 7/7 years) — and a strong day keeps going in the afternoon (15:00–15:30, 6/7 years).
2. **Between days, sell-side liquidity taken on the daily scale gets bought.** After a day that falls >1 %, the next
   morning (09:30→12:00) rises on average (+$27/trade, 6/7 years, in- and out-of-sample positive).
3. **Time quarters and SMT do not predict direction** in NQ — time windows matter only as *when* momentum shows up.

## The book (1 MNQ per leg)
| Book | Net 2020–26 | Max DD | Sharpe | Years + | Lucid pass (IS / OOS) | EV per attempt (IS / OOS) |
|---|---|---|---|---|---|---|
| Noise-Area + Afternoon momentum | $38,860 | −$3,476 | 1.47 | 7/7 | 68 % / 87 % | +$1,380 / +$786 |
| + Rebound leg | $47,724 | −$4,071 | 1.59 | 7/7 | 65 % / 70 % | +$1,075 / +$895 |
Rebound is uncorrelated with the other two (0.03) — better Sharpe, but its no-stop morning swings lower the prop pass rate.
