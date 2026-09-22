# Dropshipping product validation — 3 named candidates + 5 proposed
**Date of research:** 2026-09-22 · **Market:** US · **Audience assumed:** 35–60

---

## 0. Read this before the product sections

### 0.1 The criterion I could not test at all
**Landed cost under $8 is untestable with the sources you allowed, for every candidate on this page.**
You told me never to estimate a supplier cost, and no allowed source (pytrends, Reddit, retailer pages) publishes supplier or landed cost. So for all 8 products below, "landed cost" = **unknown**. That means no product here can be validated as "keep" on margin — the most any of them earns is "keep pending a real quote + freight + duty number." Every verdict below is therefore a verdict on *demand, price ceiling, competitive lock-in and product risk only*. [Certain — this is a property of the source list, not of the products.]

### 0.2 Two of your three required source types were unreachable
| Source | Result | Evidence |
|---|---|---|
| Reddit JSON API (`old.reddit.com/r/X/search.json`) | **Blocked.** HTTP 302 → `https://old.reddit.com/login/?reason=lor2&dest=...` on every request, incl. `hot.json` and site-wide `search.json`. With browser UA + `-L`, HTTP 200 returns the HTML page titled "Welcome to Reddit" (login wall), not JSON. `api.reddit.com` returns HTTP 403. | Reddit rate-limits/login-walls unauthenticated JSON from datacenter IPs. Reddit is also blocked for this session's fetch tool ("unable to fetch from old.reddit.com" / "www.reddit.com") and for web search (`reddit.com` not accessible to the search user agent). |
| Amazon review pages | **Blocked.** `https://www.amazon.com/product-reviews/B08K1B1JMG/` → HTTP 503 via fetch tool; via direct request → HTTP 200 but a 3,781-byte page whose body contains "Captcha" and "automated access". | You asked me to try and say so if blocked. It is blocked. |
| Google Trends via pytrends | **Worked** (after downgrading `urllib3` to <2 — pytrends 4.9.2 passes the removed `method_whitelist` arg). | Numbers below are real pulls. |
| Retailer pages | **Partly worked.** target.com: fetchable, incl. review text. walmart.com: CAPTCHA ("Robot or human?"). homedepot.com: HTTP 403 to the fetch tool; direct request returns a bot-block page. lowes.com: HTTP 403 "Access Denied". acehardware.com: HTTP 403. | |

**Consequence:** the "5 recurring complaints" for each product come from **Target.com product-page reviews**, not Reddit and not Amazon. Target reviews skew to mass-retail buyers, are far lower in volume, and contain almost no problem-language ("why does my shower leave film on the glass") — only product-failure language. **You have no voice-of-customer / ad-angle language in this document.** That gap is not fixable with the allowed source list from this environment. [Certain]

Also: the Target review quotes below were extracted by a page-reading tool that returns condensed text, so treat them as **paraphrase, not verbatim transcription** — confidence Medium on exact wording, High on substance (star ratings, dates and complaint category were returned together with each).

### 0.3 A Google Trends artifact you must not trade on
Every single 12-month series I pulled — nine unrelated keywords — peaks in the **same two weeks, 2026-04-05 / 2026-04-12**, at 85–100:

`shower filter 100 · hard water shower filter 100 · toe spacers 93 · grout pen 91 · fabric shaver 88 · electric spin scrubber 99 · faucet water filter 94 · electric callus remover 100 · lint shaver 85`

Nine unrelated consumer categories do not spike 3–5× in the same fortnight. [Likely] This is an indexing/sampling artifact in the 12-month pull, not demand. **I have discarded the April 2026 peak everywhere** and read direction from the 5-year series and from level-vs-level comparisons instead. Any read of the 12m charts that treats April as real demand is wrong. Low-volume terms (grout pen, fabric shaver, spin scrubber, callus remover, lint shaver) also return long runs of `0` in the 90-day series — that is sub-threshold sampling noise, i.e. **these terms are too small for Trends to measure reliably.** [Certain]

All Trends figures: pytrends, `geo='US'`, `cat=0`, web search, pulled 2026-09-22. Index is relative (0–100 within each pull), never absolute volume. Source: https://trends.google.com/

---

## 1. Hard water shower filter

**Trends** (pytrends, US)
- `shower filter` 5y: first-quartile mean **8.2** → last-quartile mean **30.7**. Peak 2026-04-05 (artifact). Latest value 21. → **rising, ~3.7× over 5 years.**
- `hard water shower filter` 5y: first-quartile mean **21.8** → last-quartile mean **47.8**; latest 31. → **rising, ~2.2×.**
- `shower filter` 90d: first-quartile 49.8 → last-quartile 22.5, latest 18. `hard water shower filter` 90d: 60.7 → 26.7. → **declining inside the last 90 days**, off the (artifact-adjacent) early-summer high.
- Read: structurally rising category, currently in a seasonal/post-spike trough. [Medium confidence — direction is clear over 5y; the 90d decline is partly measured against an inflated base.]

**Recurring complaints** (Target.com reviews; Reddit and Amazon unavailable per §0.2)
1. **Housing cracks or blows apart at the threads.** 1★, 2026-09-20: filter "just exploded in our shower with all the particles and made a mess," blamed on poor-quality material. https://www.target.com/p/mist-water-softening-15-stage-filtered-shower-head-with-5-settings-chrome-silver/-/A-94266771
2. **Snaps at the install point; PTFE tape makes it worse.** 1★, 2026-09-14: plastic "snapped and broke at the base point of install," tether tape made it hard to turn. Same URL.
3. **Flow stops outright.** 1★, 2026-06-28: "The water stopped flowing terrible threw it out." Same URL.
4. **Pressure loss is the category-wide objection.** Home Depot reviews (surfaced by search; the pages themselves return 403 to direct fetch, so **treat as Medium confidence**): shower pressure "dropping by 1/2"; a Lukvuzo shower head filter user reporting no pressure after 2 days. https://www.homedepot.com/p/reviews/Lukvuzo-Shower-Head-Water-Filtration-System-with-30-Stage-Filter-Reusable-to-Remove-Chlorine-Fluoride-in-Chrome-HSPH002FS008/330570347/1
5. **Cartridge life is the repeat-purchase hook and the trust risk.** iSpring buyers report 6+ months on one cartridge (5★, "installed it about 6 months ago and it's still working great"), i.e. **roughly 2 refills/year, not monthly.** https://www.target.com/p/ispring-sf2s-33-stage-universal-shower-filter-with-replaceable-filter-water-softener-shower-head-filter-vitamin-c-removes-99-of-chlorine/-/A-1010652415

**Observed prices** (target.com search page, 2026-09-22, https://www.target.com/s?searchTerm=shower+filter+hard+water)
- Devices: Mist 15-stage compact **$25.99**; Mist 15-stage **$29.99**; Mist 5-setting **$34.99**; Mist matte black **$20.99**; iSpring SF2S **$22.99** (https://www.target.com/p/ispring-sf2s-33-stage-universal-shower-filter-with-replaceable-filter-water-softener-shower-head-filter-vitamin-c-removes-99-of-chlorine/-/A-1010652415); iSpring SF1S **$29.99**; iSpring SF3S **$28.99**; Everglow **$24.99**; Sumerain hard-water head **$30.91**; Garvee 20-stage **$28.99**.
- Refills: Mist replacement filters **$15.99–$44.25** https://www.target.com/p/replacement-shower-filter-for-mist-showerhead-filters-mss081-mss082-mss083-mss085-4-pack/-/A-1008105176 ; Sumerain 4-pack hand-shower filter replacements **$18.30**.
- AquaBliss SF100 replacement cartridge listed at **$17.99 on Walmart** — price came from a search snippet, the Walmart page itself returns CAPTCHA, so **unverified by direct fetch**: https://www.walmart.com/ip/Replacement-Cartridge-AquaBliss-SF100-High-Output-Multi-Stage-Shower-Filter-Removes-Chemicals-Chlorine-Heavy-Metals-Restores-PH-Balance-Glowing-Skin/927227045

**Verdict: KEEP — conditional, and it is the only survivor on this page.**
Why it survives: retail band **$20.99–$34.99** sits inside your $25–40 window, so $34.99 is defensible rather than absurd; the refill is a **proprietary-fit cartridge you control** (unlike a glue board or a battery); it ships light; the trend is up ~2–4× over 5 years; and the buyer age skews to homeowners. [Medium-High confidence on demand and price ceiling.]
What kills it if you don't check first, in order: (a) **landed cost unknown** — if it exceeds $8 the whole thing is dead; (b) **failure mode is a water fitting on a customer's wall** — the three 1★ reviews above are cracked housings and flow stoppage, i.e. chargeback-and-water-damage complaints, not "didn't like it"; demand a brass or reinforced-thread inlet, not plain ABS; (c) **refill cadence is ~6 months, not monthly** — the repeat-purchase math is ~2 reorders/year, so do not model this as a subscription business; (d) **skin/hair/eczema claims are the whole category's marketing and they are health claims** — your own rule bans medical claims, and the honest, non-medical version ("reduces chlorine and sediment") is a weaker hook. [Certain on (b) and (d) as risks; Medium on (c).]

---

## 2. Electric indoor insect / fruit-fly trap

**Trends** (pytrends, US)
- `fruit fly trap` 5y: first-quartile mean **42.3** → last-quartile mean **48.3**; strongly seasonal (annual late-summer peaks: 2021-09 88, 2023-09 82, 2025-09 90), winter troughs ~10–16. Latest 64. → **flat-to-slightly-up, violently seasonal.**
- `flying insect trap` 5y: 14.6 → **33.9**, latest 32. → rising.
- `bug zapper indoor` 5y: 14.8 → 25.1, latest 11; 90d series is mostly `0` = too small to measure.
- 90d, `fruit fly trap`: 52.8 → 75.7, peak 2026-09-06. → **in-season right now, and about to fall off a cliff:** the same series read 11–16 every January.
- Read: real demand, but you would be buying inventory at the top of a season that historically collapses ~80% by December. [High confidence — four consecutive years of the same shape.]

**Recurring complaints** (Target.com reviews)
1. **Catch rate is inconsistent.** 3★: "Kind of works. Some bugs deem attracted to it but many completely ignore." https://www.target.com/p/zevo-indoor-flying-insect-trap-for-fruit-flies-gnats-and-house-flies-1-plug-in-base-1-refill-cartridge/-/A-81471738
2. **Total failure reports even on the category leader.** 1★ on refills: "Not one small flying bug caught in over a week." https://www.target.com/p/zevo-flying-insect-trap-refills-6ct/-/A-93252387
3. **Ugly and obtrusive in a kitchen.** 4★: trap is "very large and the blue light is not subtle," wants a discreet design.
4. **Disposal is gross.** Same review: wants a way "to dispose of the insert without seeing all of the trapped creatures."
5. **Refill cost resentment.** 3★ on the 6-ct refill pack: "A little pricey" — at **$21.99 / 6 cartridges** with a stated **45-day** replacement interval.

**Observed prices** (https://www.target.com/s?searchTerm=fruit+fly+trap+indoor+insect+trap, 2026-09-22)
- Zevo base + 1 cartridge **$19.99**; Zevo 1 trap + 3 refills **$25.49**; Zevo Max 1 device + 2 cartridges **$34.99**; Zevo 2 traps + 2 refills **$38.49**; Zevo compact starter **$18.39**; STEM starter **$12.89**; STEM starter kits **$15.49–$28.99**; Safer Home starter **$14.99**; STEM electric fan trap + 5 glue traps **$39.99**.
- Refills: Zevo 6-ct **$21.99**; Zevo compact 2-ct **$7.19**; STEM 2-ct **$6.99**; STEM 3-pk **$8.29–$9.99**; Safer Home 3-pk **$7.39**.

**Verdict: KILL.**
Three independent reasons, any one sufficient. **(1) The category is owned by two consumer-packaged-goods giants with national retail distribution** — Zevo (P&G) and STEM (SC Johnson) — occupying essentially the entire first page of a major retailer at **$12.89–$38.49**, i.e. the whole of your target price band, with 18,244 and 3,168-review ratings of 4.64 and 4.77. A generic plug-in trap sold to a 35–60 US audience at $29 is asking a customer to pay more than Zevo for an unbranded copy of Zevo. [High confidence] **(2) The refill lock-in isn't yours.** Zevo's economics work because the cartridge is proprietary; a generic trap's consumable is a glue board or UV bulb that anyone sells, so the repeat purchase leaks away. [Medium-High] **(3) You would be entering at the seasonal peak** — `fruit fly trap` runs ~75 now and ~11–16 every January, so the ad account gets 8–10 weeks before CPA collapses. [High] Landed cost: unknown, and irrelevant — it fails on competition before margin.

---

## 3. Toe spacers

**Trends** (pytrends, US)
- `toe spacers` 5y: first-quartile mean **20.4** → last-quartile mean **44.1**; latest 33. → **rising ~2.2× over 5 years, genuine.** [High confidence — this is the cleanest upward series of the nine terms I pulled.]
- 90d: first-quartile 65.1 → last-quartile 38.3, latest 36 → declining within the quarter.

**Recurring complaints** (Target.com reviews, ZenToes silicone separators, 4.1★ / 124 reviews; https://www.target.com/p/zentoes-silicone-toe-separators-for-correct-toe-alignment-black/-/A-86119266)
1. **Spacing is too aggressive out of the box.** 3★, 2026-07: "Too much spacing to start out with and is uncomfortable." 3★, 2023-09: "The spacing between toes is too extreme...very uncomfortable."
2. **Circulation cut-off — the dangerous one.** 1★, 2025-08: "They also cut off the circulation to the tips of my toes almost instantly...tips of my toes blue." 1★, 2026-01: "These turned my toes purple so I returned them."
3. **Material degrades fast.** 2★, 2024-12: "The material is already fraying so I'm not that impressed with the longevity."
4. **Sticky/uncomfortable in wear.** 1★, 2026-08, sarcastic: "So uncomfortable and sticky."
5. **Perceived as a dollar-store commodity.** 1★, 2026-09, titled "Junk dollar store."

**Observed prices** (https://www.target.com/s?searchTerm=toe+spacers, 2026-09-22)
- up&up gel toe spacers 2-pk **$4.59** https://www.target.com/p/gel-toe-spacers-2pk-up-38-up-8482/-/A-50391004
- ZenToes silicone separators **$9.99–$10.19**; ZenToes gel toe caps 3-ct **$9.99**
- Dr. Scholl's bunion relief & toe corrector **$10.39** https://www.target.com/p/dr-scholl-39-s-bunion-relief-38-toe-corrector-1-pair/-/A-88942392

**Verdict: KILL.**
**(1) No consumable, none, ever.** A silicone spacer is a one-time purchase with no refill, no wear part and no cartridge — it fails your repeat-purchase criterion outright, and no packaging trick changes that. [Certain] **(2) The price ceiling is set at ~$10 by a national retailer**, including by Dr. Scholl's, a brand your 35–60 audience trusts; selling moulded silicone at $29 into that comparison is a one-click refund. [High] **(3) It cannot be sold without medical claims.** The reason anyone searches this is bunions, plantar pain and alignment — Target's own top bunion SKU is named "Bunion Relief & Toe Corrector" — and your criteria ban medical claims; strip the claims and there is no ad. [High] **(4) Product-harm exposure:** two separate reviewers report toes turning blue/purple. A physical-harm complaint stream on a Facebook ad account is an account-level risk, not a return-rate line item. [Medium-High] Landed cost: unknown; irrelevant, it is dead four times over.

---

# Part 2 — Five further candidates, same test

Screened for: recurring household problem, genuine consumable, ships light, no medical claim, 35–60 US homeowner. All five were run through the same pytrends pull and the same retailer price check.

## 4. Faucet-mount water filter
- **Trends:** `faucet water filter` 5y first-quartile **17.5** → last-quartile **35.3** (latest 19) → rising ~2×; 90d 37.9 → 18.9, declining. [Medium]
- **Complaints** (Brita Tap, **3.72★ / 1,104 reviews** — the lowest-rated major SKU I found in any category here; https://www.target.com/p/brita-tap-water-faucet-filtration-system-chrome/-/A-526285): (1) leaks at the filter seam, described by a reviewer as a design fault not a gasket fault (1★, 2025-09); (2) won't stay attached / "falls off periodically" (1★, 2025-11); (3) "popped the faucet off my sink! Water flying everywhere" (1★, 2025-12); (4) filter-life indicator demanding replacement after 18 days (1★, 2025-12); (5) mechanism broke and jammed onto the faucet nozzle (1★, 2026-01).
- **Prices:** PUR horizontal **$29.99**; PUR PLUS **$39.99**; Brita Tap **$36.99**; Waterdrop **$28.57**. Refills: PUR 3-pk **$16.49–$54.99**; Brita 2-pk **$29.89–$37.49**; third-party 6-pk **$18.99–$43.99**. https://www.target.com/s?searchTerm=faucet+water+filter
- **Verdict: KILL.** Correct refill model, wrong fight: PUR and Brita occupy $29.99–$39.99 — your exact price band — with 742–1,104-review listings and shelf presence, and the category's own 3.72★ leader shows the failure mode is **water leaking onto a customer's counter from a fitting you shipped**. Aftermarket refill sellers have already commoditised the consumable at $3/filter. [High confidence] Landed cost: unknown.

## 5. Electric spin scrubber
- **Trends:** `electric spin scrubber` 5y first-quartile **12.7** → last-quartile **31.7**, but latest value **13** and the 90-day series is `0` for 8 of 14 sampled weeks — **below Trends' measurement threshold**. [Low confidence in the "rising" read; High confidence that search volume is small.]
- **Complaints** (Casabella Power Spin Scrubber, **3.89★ / 533 reviews**; https://www.target.com/p/casabella-extendable-power-scrubber/-/A-89743180): (1) "Broke after one use" (1★, 2026-09-17); (2) broke after ~5 uses (1★, 2026-09-04); (3) head attachment snapped, "rendering the whole thing worthless" (1★, 2026-06-13); (4) shuts off on a full charge (1★, 2026-06-18); (5) two units bought, neither span properly (1★, 2026-08-17).
- **Prices:** Casabella **$49.99**; Luminuxe 8-in-1 **$39.83**; Bell+Howell Pro **$39.99**; Bell+Howell **$35.99**; Rubbermaid manual **$15.99**. https://www.target.com/s?searchTerm=electric+spin+scrubber
- **Verdict: KILL.** It is a rechargeable lithium motor product: **heaviest and most fragile thing on this page, with battery shipping restrictions**, breaking your "ships light" criterion. The review record on the category's own 533-review SKU is a wall of mechanical failure inside weeks — that is a refund-rate business, not a margin business. The consumable (brush heads) is generic and re-sellable by anyone. [High]

## 6. Fabric shaver / lint remover
- **Trends:** `fabric shaver` 5y 15.6 → 31.1 but latest **14**; `lint shaver` 5y 14.3 → 25.4, latest **8**. 90-day series for both are majority `0`. → **too small to measure; no live momentum.** [High confidence on the smallness.]
- **Complaints** (Conair, 4.2★ / 1,399 reviews; https://www.target.com/p/conair-fabric-shaver-white/-/A-75662265): (1) dead in under 6 months (1★, 2026-08-26); (2) "my sweater looks the same" (2★, 2026-08-12); (3) wouldn't power on across several battery sets (1★, 2026-07-27); (4) stopped working after two swipes (1★, 2026-06-20); (5) leaked battery acid 24 hours after new batteries were installed (2★, 2026-06-17), plus a broken battery cover (3★, 2026-08-27).
- **Prices:** Conair **$8.99**; Gleener **$19.99**; Electrolux rechargeable **$35.99**; Nori Trim **$58.99**. https://www.target.com/s?searchTerm=fabric+shaver+lint+remover
- **Verdict: KILL.** Conair — a name this audience knows — sets the anchor at **$8.99**. Selling a generic shaver at $29 requires the customer never to have walked past a Target shelf. The blade is nominally a consumable, but Target's own listing shows no replacement-blade SKU, i.e. the category treats the whole device as disposable. [High]

## 7. Grout restoration pen
- **Trends:** `grout pen` 5y first-quartile **27.2** → last-quartile **27.8** — **dead flat over five years**; latest 22; 90-day series `0` for 10 of 14 sampled weeks. [High confidence: flat and small.]
- **Complaints:** **unverified.** Target does not carry grout pens (a search for "grout pen" returns scrub brushes and a "grout paint pen white" search returns craft supplies — https://www.target.com/s?searchTerm=grout+pen), and the retailers that do carry them (Home Depot 403, Lowe's 403, Walmart CAPTCHA) are unreachable, so I have **no review evidence at all** for this product. I am not going to invent five complaints.
- **Prices:** Grout Pen (Rainbow Chalk) listed at **$12.99 at Walmart** — from a search snippet, page not directly fetchable, so **Medium confidence**: https://www.walmart.com/ip/Grout-Pen-White-Ideal-to-Restore-the-Look-of-Tile-Grout-Lines/904433171 . Also stocked as Rejuvenate 2-pack pens (https://www.homedepot.com/p/Rejuvenate-4-oz-White-Interior-Water-Based-Grout-Restorer-Marker-Pens-2-Pack-HG-R05367-1/319046103) and Miracle Sealants 0.5-fl-oz (https://www.lowes.com/pd/Miracle-Sealants-MS-Grout-Pen-White-Each-Single/1000665997) — prices not retrievable from either.
- **Verdict: KILL.** Flat five-year demand, sub-threshold volume, a **$12.99 retail anchor** against a $25–40 target, and zero accessible review evidence. It is the one candidate here where the consumable *is* the product (pen runs out, buy another), which is the only attractive thing about it — not enough. [Medium-High]

## 8. Electric callus remover
- **Trends:** `electric callus remover` 5y first-quartile **5.8** → last-quartile **22.4** (rising off a tiny base), but **latest value 5** and the 90-day series is `0` for 11 of 14 sampled weeks. [High confidence: currently negligible.]
- **Complaints:** the two Target SKUs rate **4.52★ / 174** (Dr. Scholl's, https://www.target.com/p/dr-scholl-39-s-callus-remover-electronic-foot-file/-/A-92943117) and **4.91★ / 111** (Prospera, https://www.target.com/p/prospera-pl033-electric-foot-smoother-with-3-roller-heads/-/A-93640929) — I could not surface five recurring complaints, because at those ratings the complaint stream isn't there to surface. Recording that as **no evidence of an unsolved problem**, which is itself disqualifying: you sell the fix to a complaint, and there isn't one.
- **Prices:** Dr. Scholl's **$12.29**; Prospera 3-roller **$39.99** (reg. $59.99); Dr. Scholl's Pedi Perfect file **$24.99** with **refills 2-ct $12.99** (https://www.target.com/p/dr-scholl-39-s-pedi-perfect-foot-file-refills-2ct/-/A-94939229).
- **Verdict: KILL.** Demand is at the floor right now (index 5, mostly unmeasurable), Dr. Scholl's anchors the entry price at **$12.29** with its own refill line, and "callus/foot" advertising to a 35–60 audience walks straight into the health-claim line you drew. The roller refill is the one thing that works here. [High]

---

## Summary

| # | Product | 5y direction (first-q → last-q) | Now (90d) | Retail band observed | Real consumable? | Landed cost | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Hard water shower filter | **8.2 → 30.7** / 21.8 → 47.8 (rising) | declining | $20.99–$34.99 | Yes — proprietary cartridge, ~2×/yr | **unknown** | **KEEP (conditional)** |
| 2 | Electric insect / fruit-fly trap | 42.3 → 48.3 (flat, seasonal) | at seasonal peak | $12.89–$38.49 | Yes but not yours | unknown | KILL |
| 3 | Toe spacers | 20.4 → 44.1 (rising) | declining | $4.59–$10.39 | **No** | unknown | KILL |
| 4 | Faucet water filter | 17.5 → 35.3 (rising) | declining | $28.57–$39.99 | Yes but commoditised | unknown | KILL |
| 5 | Electric spin scrubber | 12.7 → 31.7 (unreliable) | unmeasurable | $35.99–$49.99 | Weak | unknown | KILL |
| 6 | Fabric shaver | 15.6 → 31.1 (unreliable) | unmeasurable | $8.99–$58.99 | Weak/none | unknown | KILL |
| 7 | Grout pen | 27.2 → 27.8 (flat) | unmeasurable | ~$12.99 (unverified) | Yes | unknown | KILL |
| 8 | Electric callus remover | 5.8 → 22.4 (tiny base) | unmeasurable | $12.29–$39.99 | Yes (rollers) | unknown | KILL |

**One survives, conditionally.** The recurring pattern across the seven kills is the same two facts: a national brand already sitting inside your $25–40 band with thousands of reviews, or no consumable at all. The shower filter escapes only because its refill is fit-locked to your housing and its retail band tops out at $34.99 rather than $10.

**What would change these verdicts, in priority order:** (1) real supplier quotes with freight and duty, which is the criterion none of this touches; (2) Reddit and Amazon access from an unblocked route — without it you have product-failure language but no customer problem language, and that is what ad copy is built from; (3) a second Trends pull after the April-2026 artifact has aged out of the 12-month window.
