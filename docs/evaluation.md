# Evaluation

Honest numbers only. Anything marked TODO is not measured yet.

## Spike detection (S3)

**Method.** Daily counts per country x category (event date, UTC), compared with the median and MAD of the previous 28 days; flagged when the score is >= 3 and the count is >= 10 (see `docs/decisions.md`).

**Version A (counts event rows), first measurement, 2026-09-06 to 2026-10-07 (32 complete days, today excluded):**

- 502 spikes fired across 121 countries, about 16 per day.
- By category: Armed conflict 216, Threats & coercion 179, Protest & unrest 63, Force posture 32, Mass violence 12.
- 233 of 502 (46%) have fewer than 20 events; 52 used the quiet-baseline (Poisson) rule.

**Finding before the human check (measured, not opinion).** The detector counts event rows, but one article often produces several rows (different actor pairs, repeated mentions). Across the 502 backtest spikes, 203 (40%) rest on fewer than 10 distinct source articles, 188 (37%) have more than half of their rows duplicated from the same article, and the median spike has 0.53 articles per row. Example: spike 2 (Tunisia) is 17 rows from one article. Counting distinct articles instead of rows would remove or shrink many of these. This change has now been applied (version B below).

**Version B (counts distinct source articles), now the live behaviour.** Same period and thresholds (score >= 3, at least 10 *articles*); a row with no URL counts as its own article.

| | Version A: event rows | Version B: distinct articles |
|---|---|---|
| Spikes fired in 32 days | 502 | 298 (-41%) |
| Countries with a spike | 121 | 83 |
| Armed conflict / Threats / Protest / Force posture / Mass violence | 216 / 179 / 63 / 32 / 12 | 129 / 109 / 39 / 14 / 7 |
| Spikes with fewer than 20 events or articles | 233 (46%) | 181 (61%) |
| Spikes using the quiet-baseline rule | 52 | 14 |

What version B does to the 10 sampled version-A spikes below (5 of 10 stay flagged):

| # | Country | Category | Day | Version A count | Version B count | Typical (B) | Version B |
|---|---|---|---|---|---|---|---|
| 1 | Ethiopia | Armed conflict | 2026-09-25 | 120 rows | 26 articles | 2.0 | still flagged |
| 2 | Tunisia | Armed conflict | 2026-09-18 | 17 rows | 2 articles | 0.0 | no longer flagged |
| 3 | France | Protest & unrest | 2026-10-06 | 53 rows | 38 articles | 2.5 | still flagged |
| 4 | Greenland | Threats & coercion | 2026-09-18 | 11 rows | 8 articles | 1.0 | no longer flagged |
| 5 | Mozambique | Armed conflict | 2026-09-14 | 10 rows | 2 articles | 1.0 | no longer flagged |
| 6 | Poland | Armed conflict | 2026-09-14 | 22 rows | 17 articles | 4.0 | still flagged |
| 7 | Romania | Armed conflict | 2026-09-10 | 30 rows | 10 articles | 2.0 | still flagged |
| 8 | Pakistan | Armed conflict | 2026-09-18 | 214 rows | 97 articles | 35.0 | still flagged |
| 9 | Argentina | Armed conflict | 2026-09-30 | 17 rows | 7 articles | 2.0 | no longer flagged |
| 10 | Pakistan | Protest & unrest | 2026-09-24 | 19 rows | 10 articles | 4.5 | no longer flagged |

Reading it: the three spikes I suspected were duplicate or misread single articles (Tunisia, Mozambique, Argentina) all drop out, and the large real-looking ones (Ethiopia, France, Pakistan mosque bombing) stay. The cost: borderline cases also drop, such as Pakistan protests (10 articles vs a typical 4.5, which URLs suggested were real) and Greenland. Fewer, more trustworthy alerts, at the price of missing a few small genuine ones. The share of spikes with under 20 articles went up because the big inflated ones shrank into that range. The verdicts below were drawn from version A, so they test version A; a clean accuracy figure for version B needs a fresh sample from the B alerts (same method, new seed) once the A check is done.

**Spot-check (target: at least 7 of 10 match a real, reported change).** Sample drawn from version A with seed 42, stratified: 4 from the top third by score, 3 from the middle, 3 from the bottom, so weak alerts are tested too, not just the headline ones. Open the links for each spike and decide: do the articles describe a real increase in this kind of event in this country on this day? Put Yes / No / Unclear in the Verdict column.

| # | Stratum | Day (UTC) | Country | Category | Events | Typical day | Score | Verdict | Note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | top third by score | 2026-09-25 | Ethiopia (ET) | Armed conflict | 120 | 2.5 | 31.7 |  |  |
| 2 | top third by score | 2026-09-18 | Tunisia (TS) | Armed conflict | 17 | 0.0 | 17.0 |  |  |
| 3 | top third by score | 2026-10-06 | France (FR) | Protest & unrest | 53 | 4.0 | 11.0 |  |  |
| 4 | top third by score | 2026-09-18 | Greenland (GL) | Threats & coercion | 11 | 1.0 | 6.7 |  |  |
| 5 | middle third | 2026-09-14 | Mozambique (MZ) | Armed conflict | 10 | 1.0 | 6.1 |  |  |
| 6 | middle third | 2026-09-14 | Poland (PL) | Armed conflict | 22 | 5.0 | 5.7 |  |  |
| 7 | middle third | 2026-09-10 | Romania (RO) | Armed conflict | 30 | 5.0 | 5.6 |  |  |
| 8 | bottom third | 2026-09-18 | Pakistan (PK) | Armed conflict | 214 | 81.0 | 3.8 |  |  |
| 9 | bottom third | 2026-09-30 | Argentina (AR) | Armed conflict | 17 | 3.0 | 3.8 |  |  |
| 10 | bottom third | 2026-09-24 | Pakistan (PK) | Protest & unrest | 19 | 7.5 | 3.1 |  |  |

### Evidence links (best-sourced events behind each spike)

**1. Ethiopia, Armed conflict, 2026-09-25** (120 events, typical 2.5)

- Occupy territory | REBEL -> ? | Tigray, Tigray, Ethiopia | 2 source(s) | https://www.arabnews.com/world/heavy-fighting-internet-disruption-as-ethiopia-conflict-rages-3003067
- Occupy territory | REBEL -> ETHIOPIA | Tigray, Tigray, Ethiopia | 2 source(s) | https://www.arabnews.com/world/heavy-fighting-internet-disruption-as-ethiopia-conflict-rages-3003067
- Use conventional military force, not specified below | ETHIOPIA -> GOVERNMENT | Amhara, Amara, Ethiopia | 2 source(s) | https://keyt.com/news/national-world/cnn-world/2026/09/25/war-has-returned-to-ethiopias-tigray-and-former-enemies-are-now-fighting-together-what-changed/

**2. Tunisia, Armed conflict, 2026-09-18** (17 events, typical 0.0)

- Fight with small arms and light weapons | FRANCE -> PIRATE | Tunisia | 1 source(s) | https://www.thisdaylive.com/2026/09/18/a-man-for-all-seasons-2/
- Fight with small arms and light weapons | FRANCE -> PIRATE | Tunisia | 1 source(s) | https://www.thisdaylive.com/2026/09/18/a-man-for-all-seasons-2/
- Fight with small arms and light weapons | FRANCE -> PIRATE | Tunisia | 1 source(s) | https://www.thisdaylive.com/2026/09/18/a-man-for-all-seasons-2/

**3. France, Protest & unrest, 2026-10-06** (53 events, typical 4.0)

- Demonstrate or rally | FRANCE -> FRANCE | Paris, France (general), France | 6 source(s) | https://www.yourlocalguardian.co.uk/news/national/26610519.protesting-pupils-blockade-french-high-schools/
- Protest violently, riot | SCHOOL -> FRENCH | Paris, France (general), France | 2 source(s) | http://www.parisguardian.com/news/279355252/french-police-clash-with-high-school-protesters-demanding-change
- Demonstrate or rally | STUDENT -> ? | France | 1 source(s) | https://www.ncregister.com/cna/french-bishop-urges-peace-in-face-of-protest-violence

**4. Greenland, Threats & coercion, 2026-09-18** (11 events, typical 1.0)

- Threaten, not specified below | NATO -> GREENLAND | Greenland | 2 source(s) | https://www.timescall.com/2026/09/18/trump-greenland-deal/
- Threaten, not specified below | NATO -> GREENLAND | Greenland | 2 source(s) | https://www.timescall.com/2026/09/18/trump-greenland-deal/
- Impose curfew | GREENLAND -> ? | Greenland | 1 source(s) | https://scienceblog.com/sb-in-september-2017-a-research-team-aboard-the-icebreaker-polarstern-had-to-carefully-break-a-path-around-their-own-sea-floor-instrument-off-northeastern-greenland-after-the-sea-ice-had-quietly-clos/

**5. Mozambique, Armed conflict, 2026-09-14** (10 events, typical 1.0)

- Use conventional military force, not specified below | HUNTER -> MOZAMBIQUE | Zambezi, Zambéa, Mozambique | 1 source(s) | https://news.mongabay.com/short-article/2026/09/longest-african-mammal-movement-recorded-by-zambian-wild-dogs/
- Fight with small arms and light weapons | ASSAILANT -> ? | Chimoio, Manica, Mozambique | 1 source(s) | https://allafrica.com/stories/202609140050.html
- Fight with small arms and light weapons | ASSAILANT -> MOZAMBIQUE | Chimoio, Manica, Mozambique | 1 source(s) | https://allafrica.com/stories/202609140050.html

**6. Poland, Armed conflict, 2026-09-14** (22 events, typical 5.0)

- Use conventional military force, not specified below | RUSSIA -> DIPLOMAT | Poland | 1 source(s) | http://www.jpost.com/international/internationalrussia-ukraine-war/article-908471
- Occupy territory | POLAND -> ? | Poland | 1 source(s) | https://edition.cnn.com/2026/09/14/world/petraeus-boris-johnson-russia-ukraine-intl-hnk
- Occupy territory | WORKER -> BUSINESS | Poland | 1 source(s) | https://www.nwemail.co.uk/news/26536759.butchers-drapers-tea-stores-fascinating-photos-old-barrow/

**7. Romania, Armed conflict, 2026-09-10** (30 events, typical 5.0)

- Occupy territory | MOLDOVAN -> ROMANIA | Romania | 1 source(s) | https://economictimes.indiatimes.com/news/international/world-news/flight-carrying-zelenskyy-to-norway-was-delayed-in-moldova-because-of-drone-incursion/articleshow/133989525.cms
- Occupy territory | ? -> ROMANIA | Romania | 1 source(s) | https://www.kyivpost.com/post/84156
- Employ aerial weapons | UKRAINE -> MOLDOVA | Romania | 1 source(s) | https://www.yahoo.com/news/world/articles/zelenskyys-plane-almost-hit-russian-052224446.html

**8. Pakistan, Armed conflict, 2026-09-18** (214 events, typical 81.0)

- Use conventional military force, not specified below | PAKISTAN -> ? | Peshawar, North-West Frontier, Pakistan | 4 source(s) | https://www.queanbeyanage.com.au/story/9353315/attack-on-mosque-in-pakistan-kills-at-least-15/
- Use conventional military force, not specified below | TALIBAN -> PAKISTAN | Peshawar, North-West Frontier, Pakistan | 3 source(s) | https://www.winnipegfreepress.com/world/2026/09/18/bombing-at-mosque-near-police-offices-in-pakistan-kills-at-least-7-and-wounds-more-than-30
- Use conventional military force, not specified below | PAKISTAN -> TALIBAN | Peshawar, North-West Frontier, Pakistan | 3 source(s) | https://www.winnipegfreepress.com/world/2026/09/18/bombing-at-mosque-near-police-offices-in-pakistan-kills-at-least-7-and-wounds-more-than-30

**9. Argentina, Armed conflict, 2026-09-30** (17 events, typical 3.0)

- Use conventional military force, not specified below | JUDICIARY -> MEDIA | Buenos Aires, Distrito Federal, Argentina | 1 source(s) | https://aa.com.tr/en/americas/argentinas-ex-president-kirchner-asks-un-to-review-corruption-conviction-/4073188
- Use conventional military force, not specified below | MEDIA -> JUDICIARY | Buenos Aires, Distrito Federal, Argentina | 1 source(s) | https://aa.com.tr/en/americas/argentinas-ex-president-kirchner-asks-un-to-review-corruption-conviction-/4073188
- Use conventional military force, not specified below | ARGENTINA -> UNITED KINGDOM | Malvinas, TucumáAS, Argentina | 1 source(s) | http://www.zerohedge.com/geopolitical/argentina-threatens-uk-court-action-over-falklands-oil-drilling

**10. Pakistan, Protest & unrest, 2026-09-24** (19 events, typical 7.5)

- Demonstrate or rally | PESHAWAR -> POLICE | Peshawar, North-West Frontier, Pakistan | 1 source(s) | https://tribune.com.pk/story/2631103/police-security-taken-back-from-k-p-mpas
- Engage in political dissent, not specified below | DEMONSTRATOR -> SECURITY FORCE | Pakistan | 1 source(s) | https://theshillongtimes.com/2026/09/24/pok-unrest-deepens-rising-killings-fuel-protests/
- Demonstrate or rally | ISLAMABAD -> PAKISTANI | Islamabad, Islamabad, Pakistan | 1 source(s) | https://en.dailypakistan.com.pk/24-Sep-2026/pti-long-march-is-govt-ruling-out-army-deployment-ahead-of-islamabad-showdown

**Result:** TODO (fill in once the Verdict column is complete: X of 10 Yes).

## Signal-quality classifier (S1)

TODO: not built yet (needs the labeling page and about 300 hand labels). Required report: precision, recall, ROC-AUC and confusion matrix on a held-out test set, against the always-credible baseline.
