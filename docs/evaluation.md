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

**Spot-check (target: at least 7 of 10 match a real, reported change).** Sample drawn from the live version B alerts with seed 42, stratified: 4 from the top third by score, 3 from the middle, 3 from the bottom, so weak alerts are tested too. For each spike, open the links and answer one question: *do these articles describe a real increase in this kind of event in this country on this day?* Yes = at least 2 of the 3 articles show a real event of the right type in the right country; No = the articles are about something else (misread, wrong place, wrong type, not an event); Unclear = you cannot tell. Only the best-sourced 3 articles are shown, so judge the event type and place, not the exact count.

| # | Stratum | Day (UTC) | Country | Category | Articles | Typical day | Score | Verdict | Note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | top third by score | 2026-09-16 | Kosovo (KV) | Threats & coercion | 22 | 0.0 | 22.0 | Yes |  |
| 2 | top third by score | 2026-09-21 | Rwanda (RW) | Armed conflict | 11 | 0.5 | 14.2 | No | Mostly court verdicts about the 1994 Rwandan genocide, not a current armed conflict. |
| 3 | top third by score | 2026-10-06 | Romania (RO) | Armed conflict | 12 | 2.0 | 6.7 | No | Articles do not concern a current armed conflict (court case, business, celebrity news coded as military force). |
| 4 | top third by score | 2026-09-14 | Djibouti (DJ) | Threats & coercion | 10 | 1.0 | 6.1 | Unclear | Kind of: real conflict (Houthi rebels seizing Red Sea shipping routes), but see 6, 7, 8. |
| 5 | middle third | 2026-10-01 | Egypt (EG) | Armed conflict | 20 | 5.0 | 5.1 | No | No real armed event in the articles. |
| 6 | middle third | 2026-09-10 | Yemen (YM) | Threats & coercion | 18 | 3.0 | 5.1 | No | Duplicate of the situation in 4 (same Houthi story, counted again under Yemen). |
| 7 | middle third | 2026-09-12 | Saudi Arabia (SA) | Threats & coercion | 29 | 7.0 | 4.9 | No | Duplicate of the situation in 4 (same Houthi story, counted again under Saudi Arabia). |
| 8 | bottom third | 2026-09-11 | Yemen (YM) | Armed conflict | 60 | 12.5 | 3.8 | No | Also the Houthi seizure of Red Sea / Saudi shipping routes, the same story as 4. |
| 9 | bottom third | 2026-09-23 | Oman (MU) | Armed conflict | 13 | 2.0 | 3.7 | Yes |  |
| 10 | bottom third | 2026-09-29 | West Bank (WE) | Armed conflict | 30 | 12.0 | 3.0 | Yes |  |

### Evidence links (version B sample)

**1. Kosovo - Threats & coercion - 2026-09-16**  (22 articles that day; a typical day is 0.0; score 22.0)

- https://balkaninsight.com/2026/09/16/hague-court-convicts-kosovo-liberation-army-leaders-of-war-crimes/btj/
  coded as: Arrest, detain, or charge with legal action | LIBERATION ARMY -> ? | Kosovo | 1 source(s)
- https://balkaninsight.com/2026/09/16/kosovo-slams-unjust-conviction-of-hashim-thaci-serbian-minister-applauds/btj/
  coded as: Arrest, detain, or charge with legal action | CRIMINAL -> ? | Kosovo | 1 source(s)
- https://cyprus-mail.com/2026/09/16/former-kosovo-president-thaci-sentenced-to-25-years-in-prison-for-war-crimes
  coded as: Arrest, detain, or charge with legal action | PRESIDENT -> PRISON | Kosovo | 1 source(s)

**2. Rwanda - Armed conflict - 2026-09-21**  (11 articles that day; a typical day is 0.5; score 14.2)

- https://allafrica.com/stories/202609210001.html
  coded as: Physically assault, not specified below | RWANDA -> ? | Rubaya, Nord, Rwanda | 1 source(s)
- https://bdnews24.com/world/qstqxyzkx3
  coded as: Use conventional military force, not specified below | KIGALI -> BRITAIN | Kigali, (RW09), Rwanda | 1 source(s)
- https://brudirect.com/post/First-UK-charges-brought-over-1994-Rwanda-genocide
  coded as: Use conventional military force, not specified below | RWANDA -> ? | Rugenge, Sud, Rwanda | 1 source(s)

**3. Romania - Armed conflict - 2026-10-06**  (12 articles that day; a typical day is 2.0; score 6.7)

- https://actmedia.eu/daily/cooperation-between-romanian-and-danish-prosecutors-in-murder-and-desecration-of-corpses-case/121962
  coded as: Use conventional military force, not specified below | PROSECUTOR -> AUTHORITIES | Buzau, Buzau, Romania | 1 source(s)
- https://business-review.eu/business/pharmaceuticals/catalina-urse-bayer-romania-must-reduce-the-gap-in-access-to-modern-therapies-301566
  coded as: Use conventional military force, not specified below | ? -> INDUSTRY | Romania | 1 source(s)
- https://krcgtv.com/news/nation-world/andrew-tate-accused-of-possessing-bestiality-porn-involving-horse-eel-report-animal-extreme-pornography-rape-sex-trafficking-sexual-exploitation-social-media-influencer
  coded as: Sexually assault | ? -> UNITED KINGDOM | Romania | 1 source(s)

**4. Djibouti - Threats & coercion - 2026-09-14**  (10 articles that day; a typical day is 1.0; score 6.1)

- https://www.clickorlando.com/news/world/2026/09/14/yemens-houthi-rebels-seize-more-key-islands-in-southern-red-sea-tighten-grip-on-shipping-routes/
  coded as: Impose administrative sanctions, not specified below | YEMEN -> REBEL | Red Sea, Djibouti (general), Djibouti | 3 source(s)
- https://morningstaronline.co.uk/article/yemen-houthi-led-forces-seize-more-key-islands-southern-red-sea
  coded as: Arrest, detain, or charge with legal action | YEMEN -> DJIBOUTI | Bab El-Mandeb, , Djibouti | 1 source(s)
- https://www.arabnews.com/saudi-arabia/saudi-arabia-issues-lifts-alerts-as-houthi-attacks-raise-security-fears-3001619
  coded as: Threaten to use military force, not specified below | RIYADH -> YEMEN | Bab Al-Mandab, , Djibouti | 1 source(s)

**5. Egypt - Armed conflict - 2026-10-01**  (20 articles that day; a typical day is 5.0; score 5.1)

- https://alextimes.com/breaking-news/supreme-court-of-virginia-panel-rejects-301-n-fairfax-st-appeal/
  coded as: Use conventional military force, not specified below | VIRGINIA -> JUDGE | Alexandria, Al Iskandariyah, Egypt | 1 source(s)
- https://allafrica.com/stories/202610010039.html
  coded as: Use conventional military force, not specified below | EGYPTIAN -> ? | Egypt | 1 source(s)
- https://countercurrents.org/2026/10/denial-as-a-way-of-life-netanyahu-on-egyptian-warnings-about-october-7/
  coded as: Use unconventional violence, not specified below | EGYPT -> INTELLIGENCE | Egypt | 1 source(s)

**6. Yemen - Threats & coercion - 2026-09-10**  (18 articles that day; a typical day is 3.0; score 5.1)

- https://ktvz.com/news/national-world/cnn-world/2026/09/10/iran-backed-rebels-capture-red-sea-port-tightening-grip-on-a-key-global-chokepoint/
  coded as: Impose administrative sanctions, not specified below | IRAN -> DJIBOUTI | Sanaa, Sana', Yemen | 2 source(s)
- https://aa.com.tr/en/middle-east/houthis-shell-civilian-sites-key-road-in-yemens-taiz-casualties-reported/4053538
  coded as: Threaten, not specified below | YEMEN -> CIVILIAN | Al-Haql, Ma'rib, Yemen | 1 source(s)
- https://aa.com.tr/en/middle-east/un-envoy-says-yemens-renewed-war-risks-becoming-prolonged-wider-regional-conflict/4053740
  coded as: Threaten, not specified below | ? -> YEMEN | Sanaa, Sana', Yemen | 1 source(s)

**7. Saudi Arabia - Threats & coercion - 2026-09-12**  (29 articles that day; a typical day is 7.0; score 4.9)

- https://www.wral.com/news/ap/9c2b6-saudi-arabia-has-few-options-as-it-faces-mounting-threats-from-iran-and-its-allies/
  coded as: Threaten, not specified below | IRAN -> SAUDI ARABIA | Riyadh, Ar Riya?, Saudi Arabia | 2 source(s)
- http://www.philippinetimes.com/news/279303541/houthis-asked-us-to-stay-out-of-saudi-fight-trump
  coded as: Impose administrative sanctions, not specified below | SAUDI -> ? | Riyadh, Ar Riya?, Saudi Arabia | 2 source(s)
- https://aa.com.tr/en/americas/us-signals-no-imminent-strikes-on-houthis-but-points-to-intel-support-for-saudis-report/4054874
  coded as: Threaten to use military force, not specified below | RIYADH -> ? | Riyadh, Ar Riya?, Saudi Arabia | 1 source(s)

**8. Yemen - Armed conflict - 2026-09-11**  (60 articles that day; a typical day is 12.5; score 3.8)

- http://www.arabherald.com/news/279301318/houthis-seize-yemen-entire-western-coast-after-taking-bab-al-mandab-strait-area
  coded as: Occupy territory | MILITARY OFFICIAL -> YEMEN | Lahj, La?ij, Yemen | 3 source(s)
- https://economictimes.indiatimes.com/news/defence/trump-rejects-saudi-request-for-strikes-on-houthis-axios/articleshow/134063296.cms
  coded as: Use conventional military force, not specified below | SAUDI -> YEMEN | Mokha, Taizz, Yemen | 2 source(s)
- http://eng.chinamil.com.cn/2025xb/W/N/16485042.html
  coded as: Fight with artillery and tanks | MILITARY -> MEDIA | Bayda, Al Ma?wit, Yemen | 1 source(s)

**9. Oman - Armed conflict - 2026-09-23**  (13 articles that day; a typical day is 2.0; score 3.7)

- http://www.indiagazette.com/news/279327249/union-minister-sarbananda-sonowal-condoles-death-of-indian-seafarer-due-to-missile-attack-off-oman-coast
  coded as: Fight with artillery and tanks | MINIST -> OMAN | Oman | 2 source(s)
- https://aninews.in/news/world/asia/one-indian-national-killed-in-attack-on-commercial-vessel-off-oman-coast-19-rescued-india-says-targeting-of-seafarers-must-end-160-16020260923214842/
  coded as: Use conventional military force, not specified below | OMAN -> NEW DELHI | Oman | 1 source(s)
- https://ianslive.in/one-indian-seafarer-killed-19-rescued-in-attack-on-vessel-off-oman-coast--20260923215703
  coded as: Use conventional military force, not specified below | OMAN -> NEW DELHI | Oman | 1 source(s)

**10. West Bank - Armed conflict - 2026-09-29**  (30 articles that day; a typical day is 12.0; score 3.0)

- http://www.goskagit.com/news/nation/iran-tells-the-us-public-that-trumps-war-has-failed-and-other-mideast-developments/article_cc72a689-e7fc-5776-b811-759c926b0425.html
  coded as: Impose blockade, restrict movement | SETTLER -> ? | Jalud, West Bank (general), West Bank | 2 source(s)
- https://aa.com.tr/en/middle-east/israeli-occupiers-attack-3-west-bank-villages-torch-homes-vehicles/4072252
  coded as: Use unconventional violence, not specified below | ISRAELI -> ? | Ramallah, West Bank (general), West Bank | 1 source(s)
- https://english.wafa.ps/Pages/Details/175301
  coded as: Use unconventional violence, not specified below | COLONIST -> ? | Ramallah, West Bank (general), West Bank | 1 source(s)

**Result (version B sample, judged by hand, 2026-10-08): 3 Yes, 1 Unclear, 6 No. The target of 7 of 10 was NOT met.**

What went wrong, from the notes:

1. **Misread event types (spikes 2, 3, 5: three of the six No).** Court cases, business stories and celebrity news were coded as "use conventional military force" or similar and then counted as armed conflict. Counting articles instead of rows did not help, because these are different articles that are each wrongly coded. This is the error the signal-quality classifier (S1) exists to catch: "is this record a real event of the coded type?"
2. **One real story counted several times (spikes 4, 6, 7, 8: four of the ten).** The Houthi seizure of Red Sea shipping routes is a real event, but it raised separate spikes in Yemen (armed conflict and threats), Djibouti and Saudi Arabia. Counted as one story, that is arguably one correct alert plus three duplicates. The detector has no way to link related spikes.
3. **What worked:** the three Yes (Kosovo, Oman, West Bank) are real events in the right place and category.

Honest caveats: a sample of 10 is small, so 3 of 10 has a wide uncertainty (roughly 7% to 65% for the true rate), and the sample is stratified, not random over all alerts, so it over-represents weak alerts. Even so, it shows alerts are not yet trustworthy enough to brief from without the quality score.

Possible next steps (not applied): use the S1 classifier score to filter or weight the articles that count toward a spike; group spikes that share the same source articles into one incident; show the quality score next to each alert. The version A check was never done by hand, so no like-for-like comparison with version B exists.

## Signal-quality classifier (S1)

**What it predicts.** Whether an event record is a real event of the coded type at roughly the coded place (label 1 = credible), from GDELT fields only. Logistic regression (median imputer, standard scaler). Features: log sources / articles / mentions, place precision (`geo_type`), root-event flag, Goldstein score, average tone, quad class, whether each actor is named, log of how many events the same news site has, and category. Trained by `make train`, scores stored by `make score`.

**Labels.** 222 hand labels (87 credible, 39%) from one labeler (the project owner), drawn from the last 30 days with the five mission categories taking turns. Because categories were balanced rather than sampled by real frequency, the 39% credible rate is **not** the rate across all events. Split: stratified 70/30 with seed 42: 155 train, 67 test.

### Result on the held-out test set (67 events, touched once)

| Predictor | Precision | Recall | F1 | ROC-AUC | TN / FP / FN / TP |
|---|---|---|---|---|---|
| Logistic regression | 0.53 | 0.62 | 0.57 | 0.68 | 27 / 14 / 10 / 16 |
| Always predict credible (baseline) | 0.39 | 1.00 | 0.56 | 0.50 | 0 / 41 / 0 / 26 |
| Rule: geo_type >= 3 | 0.43 | 0.77 | 0.56 | 0.57 | 15 / 26 / 6 / 20 |

ROC-AUC 95% interval for the model (bootstrap over the test set): **0.54 to 0.81**.

### 5-fold cross-validation inside the training split (mean +/- std over folds)

| Predictor | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|
| Logistic regression | 0.61 | 0.62 | 0.61 +/- 0.07 | 0.75 +/- 0.08 |
| Always predict credible | 0.39 | 1.00 | 0.56 +/- 0.01 | 0.50 |

### Honest reading

- **Success criterion "beat always-credible on F1":** met on paper (test 0.57 vs 0.56; CV 0.61 vs 0.56), but the test margin is about 0.01 on 67 events, which is noise. F1 flatters the baseline because it gets perfect recall by flagging everything.
- **Where it genuinely helps is precision:** of the events it calls credible, 53% are, against 39% for flagging everything. That is the number that matters for "hide low-quality events", at the price of missing 38% of the credible ones.
- **The signal is real but modest.** ROC-AUC 0.68 on test (interval 0.54 to 0.81, which excludes 0.5 but only just) and 0.75 in cross-validation. The simple one-line rule is no better than guessing here (AUC 0.57).
- **Not ready to be trusted alone.** At this accuracy it should rank and de-emphasise events, not silently delete them.

### What it learned (standardized coefficients; positive = more credible)

| Feature | Coefficient |
|---|---|
| `quad_class` | +0.86 |
| `cat_Mass violence` | -0.79 |
| `cat_Protest & unrest` | +0.75 |
| `log_sources` | -0.65 |
| `geo_type` | +0.58 |
| `avg_tone` | -0.46 |
| `goldstein` | +0.40 |
| `log_mentions` | +0.07 |
| `cat_Threats & coercion` | -0.05 |
| `cat_Armed conflict` | +0.05 |
| `has_actor2` | +0.04 |
| `cat_Force posture` | +0.02 |
| `log_articles` | +0.01 |
| `log_domain_freq` | +0.01 |
| `has_actor1` | -0.01 |
| `is_root` | +0.00 |

Read with care: with 155 training rows these are unstable. **`log_sources` is negative, which is backwards from reality**, and comes from the data, not from a bug: 216 of the 222 labeled events have a single source, only 6 have two or more, and those few were mostly judged not credible. The feature has almost no spread in GDELT (a new event row is written once, with `NumSources` mostly 1), so the model cannot learn what extra sources are worth. `quad_class`, place precision and the Mass violence / Protest categories carry most of the signal.

### Limits and next steps

- One labeler, 222 labels, 67 test rows: wide uncertainty; more labels would tighten it (the PRD target is 300).
- "Other conflict" events are scored too, but that category had no labels, so those scores are extrapolated.
- If more labels are added, rerun `make train` and `python -m tripwire.quality.score --all`. The saved model is refitted on all labels, so it has seen the test rows; the numbers above are from the train-split model and are the ones to quote.
- Multi-source events are scarce, so a labeling pass that deliberately over-samples them would be the cheapest way to test whether sources help.
