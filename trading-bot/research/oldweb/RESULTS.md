# Old-web strategy finder (1750 - 2002 sources -> NQ 2012-2026)

**Corpus:** 37 Usenet groups from archive.org (the Wayback Machine is blocked from this environment): misc.invest.*, alt.invest.*, comp.ai.neural-nets, sci.*,
Japanese fj.* / japan.finance.*, Taiwanese tw.*, German de.etc.finanz.boerse*, uk.finance.stockmarket, plus 14 public-domain books (1884-1927).
That is about 700k posts dated 1980-2002. They were mined into about 23k candidate posts and 1,395 distinct conditional rule sentences.
Those were read and coded into **45 testable rules**, using the posters' own numbers (point sizes converted to % of price). Nothing was tuned.

**Test:** NSXUSD 1-minute data, 2012 - 2026-10. Every rule predates the data, so the whole period is out-of-sample. A rule passes only if all of these hold:
- net > 0 at 1x and 2x costs;
- t-test p < 0.05/45 (t >= 3.06);
- both coin flips p < 0.05 (1,000 draws each);
- net > 0 in at least 2 of the 3 sub-periods.

**Result: 0 of 45 pass.** The closest:

| rule (source) | trades/yr | win | R:R | $/yr 1 MNQ | t |
|---|---|---|---|---|---|
| Long Monday open -> close (misc.invest.futures 1999) | 45 | 58% | 1.05 | 1,260 | 2.98 |
| Turn of month: buy close of the 2nd-to-last day, sell close of day 4 (misc.invest) | 12 | 65% | 1.04 | 2,040 | 2.23 |
| 200-day SMA long/flat (misc.invest.futures 2002) | 2 | 26% | 22.7 | 3,150 | 2.04 |
| Month-end window dressing, 月末ドレッシング買い (fj.soc.economy 1999) | 12 | 57% | 1.20 | 870 | 1.40 |

All of the near-misses are long-only calendar or trend rules: they mostly harvest NQ's 2012-2026 bull drift, and most of their profit is in 2022-26.
Intraday pattern rules (OOPS, NR4/NR7, gap fades, opening-range tricks, stochastic/RSI/pivot) are all within noise of zero after costs.
See results.csv for every rule, with its source sentence.

## Round 2 - older sources (before Usenet)
- **235 open-access books from 1850-1975** (archive.org; Wyckoff, Nelson, Hamilton, Selden, Clews, Gann-era texts and others): 590 sentences mentioning buying or selling.
  Almost all of them are anecdotes or advice; the only codable rule was the Dow/Hamilton "line" breakout with a Wyckoff 3-day time stop.
- **699 BBS files from textfiles.com (1980s - early 90s):** no trading rules, only investing FAQs and price lists.
- **Japanese / Chinese archive search:** returned newspapers and unrelated books.
  Instead, the 18th-century Dojima rice-market rules (Sakata five methods, Homma Munehisa) were coded from the tradition itself.

| new rule | trades | win | t |
|---|---|---|---|
| 三空 three gaps -> fade | 83 | 40% | -2.13 |
| 赤三兵/黒三兵 three soldiers / crows | 78 | 45% | -1.29 |
| 三川 morning / evening star | 40 | 55% | -0.60 |
| engulfing at a 10-day extreme | 70 | 34% | -2.59 |
| Homma: 5 down closes -> buy | 262 | 39% | -1.09 |
| Dow line breakout + Wyckoff time stop | 149 | 30% | -1.20 |

**Final: 0 of 51 pass** (Bonferroni bar t >= 3.10). The oldest rules do worse than the 1990s ones.
