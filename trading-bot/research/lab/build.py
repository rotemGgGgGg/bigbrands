"""Builds data.json for the strategy-lab page: registry of every strategy we tested + series/Monte Carlo from series.json.
To add a test: append a dict to REG (and a series to series.json if it has trades), run this, republish the page."""
import json, datetime
S = json.load(open("series.json"))
REG = [
 dict(id="gotobi", name="Gotobi Fix", market="USDJPY · EURJPY · GBPJPY", status="LIVE", family="Calendar flow",
      rule="Long 03:00 Tokyo → 09:55, short 09:55 → 10:30 on 5/10/15/20/25/last day (prev. bank day).", rr=1.10, p="<0.001",
      note="Replicated vendor CASE01. +$175K 2012–26 at 1 lot ×3. Units: normalised R (1 = avg 2012–19 day).", series="gotobi"),
 dict(id="rdm", name="RDM", market="NQ", status="LIVE", family="Intraday momentum",
      rule="09:45: if 09:00→09:45 move disagrees with yesterday's RTH candle, trade today's direction to 15:55. Skip FOMC.", rr=1.25, p="0.004",
      note="Born in the theory factory (2.48M theories, 142 real vs 2 placebo). Units: normalised R.", series="rdm"),
 dict(id="rdm10", name="RDM 1:10", market="NQ", status="LIVE", family="Convex",
      rule="RDM entry, stop 0.15 × ATR(14 sessions), target 10R, flat 15:55. Cost 1 pt.", rr=10.0, p="0.000",
      note="Pine: rdm_convex.pine. 20% win, avg winner 5.1R, worst losing streak 34. Random-direction null median +0.16R.", series="rdm10"),
 dict(id="rdmtrail", name="RDM Runner", market="NQ", status="WATCH", family="Convex",
      rule="RDM entry, stop 0.25 × ATR, break-even at +2R then 2R trail, flat 15:55.", rr=None, p="—",
      note="Fixed 10R at 0.25 ATR scored +0.28R OOS (t 3.3, p 0.005); trail variant shown.", series="rdmtrail"),
 dict(id="avpeq", name="AVP Equation", market="NQ", status="WATCH", family="Meta-labelling",
      rule="AVP signal taken only if ridge E[R] > 0 (9 features, fit 2012–19).", rr=2.0, p="0.081",
      note="E[R] = −0.345 + 0.603·width + 0.137·emptiness − 0.162·risk + … Promising, not significant.", series="avpeq"),
 dict(id="pluto", name="Pluto Sequence", market="NQ", status="DEAD", family="Time & price",
      rule="Divide-by-4 time quarters, liquidity sweep entries.", rr=None, p="n.s.", note="Shifted-grid placebo matched it.", series="pluto"),
 dict(id="sp", name="SP Model v8", market="NQ", status="DEAD", family="ICT / sessions",
      rule="London range sweep → NY reversal. 00–06 and 02:00–09:30 windows.", rr=None, p="n.s.", note="−0.03R per trade both windows.", series="sp"),
 dict(id="avp", name="AVP Zones", market="NQ", status="DEAD", family="Volume profile",
      rule="Composite 5-session profile, LVN rejection, 2R. Exact Pine port, real volume.", rr=2.0, p="0.42",
      note="540-setting grid: 0 pass. Aug–Nov 2026 positive window reproduced, 14 years negative.", series="avp"),
 dict(id="crt", name="CRT Sweep", market="NQ · ES", status="DEAD", family="Candle range", rule="Candle range sweep / engulf, 31,716 variants.", rr=None, p="n.s.", note="Survivors equal to placebo count."),
 dict(id="lbr", name="London Break & Retest", market="NQ", status="DEAD", family="Sessions", rule="London range break, retest entry.", rr=None, p="n.s.", note="No OOS edge after costs."),
 dict(id="macro", name="Macro Events", market="NQ", status="DEAD", family="Event", rule="CPI / PPI / NFP / FOMC drift and fade.", rr=None, p="n.s.", note="Only useful as a filter: skip FOMC for RDM."),
 dict(id="onr", name="Overnight Quarters", market="NQ", status="DEAD", family="Time & price", rule="Overnight range split in 4, quarter levels as targets.", rr=None, p="n.s.", note="Shuffled-day placebo equal."),
 dict(id="ict", name="ICT Macros · Gann · QT", market="NQ", status="DEAD", family="Time & price", rule="Macro windows, Gann times, Quarterly Theory 90-min cycles.", rr=None, p="n.s.", note="Shifted time grids score the same."),
 dict(id="vid", name="Video Strategies", market="USDJPY · XAU · NQ", status="DEAD", family="Breakout", rule="London breakout, gold sweep, NY momentum.", rr=None, p="n.s.", note="Grid winners failed 2020–26."),
 dict(id="layers", name="Layers 13M (FVG multi-TF)", market="NQ", status="DEAD", family="Multi-timeframe",
      rule="D/4H/1H gap → touch → 15m confirm → 1m entry → stop → target × 960 filters = 13,271,040 strategies.", rr=None, p="n.s.",
      note="17 survivors vs 22 for random zones; 1 of 17 positive in 2022–26. Daily gaps beat random levels by ~0.1R, still ~0 after costs."),
 dict(id="multi", name="8-Market Portfolio", market="DAX · Gold · JPN · Oil …", status="DEAD", family="Portfolio", rule="Same sleeves on non-US markets.", rr=None, p="n.s.", note="Non-US sleeves fail OOS."),
]
BOOK = dict(name="Gotobi + RDM book", sharpe=1.71, cagr=22.6, maxdd=-18.5, pos_years="10/11", prop_pass=74, prop_zero=1, window="OOS 2016–26")
for r in REG:
    if r.get("series") in S: r.update(S[r["series"]])
SPD = json.load(open("sp.json"))
json.dump(dict(sp=SPD, updated=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), book=BOOK, strategies=REG,
               theories_tested=2480000 + 1850000 + 31716 + 540 + 13271040), open("data.json", "w"))
print("ok", len(REG))
