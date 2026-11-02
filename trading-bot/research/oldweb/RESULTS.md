# Old-web strategy finder (pre-2002 internet -> NQ 2012-2026)

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
