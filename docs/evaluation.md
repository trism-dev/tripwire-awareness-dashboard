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

**Labels.** 312 hand labels (125 credible, 40%) from one labeler (the project owner), drawn from the last 30 days with the five mission categories taking turns: Protest & unrest 63 (54% credible), Threats & coercion 63 (54% credible), Armed conflict 62 (44% credible), Force posture 62 (42% credible), Mass violence 62 (6% credible). Because categories were balanced rather than sampled by real frequency, the credible rate is **not** the rate across all events. Split: stratified 70/30, seed 42: 218 train, 94 test.

### Result on the held-out test set (94 events, touched once)

| Predictor | Precision | Recall | F1 | ROC-AUC | TN / FP / FN / TP |
|---|---|---|---|---|---|
| Logistic regression | 0.56 | 0.58 | 0.57 | 0.71 | 39 / 17 / 16 / 22 |
| Always predict credible (baseline) | 0.40 | 1.00 | 0.58 | 0.50 | 0 / 56 / 0 / 38 |
| Rule: geo_type >= 3 | 0.50 | 0.79 | 0.61 | 0.63 | 26 / 30 / 8 / 30 |

ROC-AUC 95% interval for the model (bootstrap over the test set): **0.61 to 0.81**.

### 5-fold cross-validation inside the training split (mean +/- std over folds)

| Predictor | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|
| Logistic regression | 0.59 | 0.54 | 0.55 +/- 0.06 | 0.75 +/- 0.03 |
| Always predict credible | 0.40 | 1.00 | 0.57 +/- 0.01 | 0.50 |

### Honest reading

- **Success criterion "beat always-credible on F1": **NOT met**: test F1 is 0.57 against 0.58 for always-credible, and cross-validated F1 is 0.55 +/- 0.06 against 0.57.** F1 is a poor yardstick here: flagging everything gives perfect recall, so the baseline's F1 (0.58) is hard to beat when 40% of events are credible. The one-line rule `geo_type >= 3` reaches F1 0.61 by the same route (recall 0.79, precision only 0.50).
- **What the model does achieve is ranking and precision.** ROC-AUC 0.71 (interval 0.61 to 0.81, clearly above 0.5) against 0.63 for the rule, and precision 0.56 against 0.40 for flagging everything, at the cost of missing 42% of the credible events. For "show me the cleaner events first" that is useful; for "decide what is true" it is not.
- **Regularisation is not the limit.** Cross-validated AUC on the training split was flat across a 3000x range of regularisation strength (0.72 to 0.745), so the ceiling is the information in the available fields, not tuning. No tuning was applied to the final model.
- **Not ready to be trusted alone.** It should rank and de-emphasise events, not silently delete them.

### What it learned (standardized coefficients; positive = more credible)

| Feature | Coefficient |
|---|---|
| `avg_tone` | -0.85 |
| `cat_Mass violence` | -0.83 |
| `cat_Protest & unrest` | +0.49 |
| `log_sources` | -0.42 |
| `cat_Force posture` | +0.29 |
| `quad_class` | +0.28 |
| `geo_type` | +0.28 |
| `log_mentions` | +0.19 |
| `log_articles` | +0.17 |
| `log_domain_freq` | +0.15 |
| `has_actor2` | +0.15 |
| `goldstein` | +0.15 |
| `cat_Threats & coercion` | +0.03 |
| `cat_Armed conflict` | -0.01 |
| `has_actor1` | +0.01 |
| `is_root` | +0.00 |

Read with care: with 218 training rows these are not stable. `log_sources` is negative, which is backwards from reality: 305 of 312 labeled events have a single source and only 7 have two or more (1 of them credible), because GDELT writes an event row once with `NumSources` mostly 1. The feature has almost no spread, so the model cannot learn what extra sources are worth. Event category (Mass violence is almost never credible), average tone and place precision carry most of the signal.

### Limits and next steps

- One labeler, 312 labels, 94 test rows: wide uncertainty.
- "Other conflict" events are scored too, but that category had no labels, so those scores are extrapolated.
- After adding labels, rerun `make train` and `python -m tripwire.quality.score --all`. The saved model is refitted on all labels, so it has seen the test rows; the numbers above come from the train-split model and are the ones to quote.
- A labeling pass that deliberately over-samples multi-source events (about 40 would do) is the cheapest way to test whether sources help; the current queue cannot target them.

## Does the quality score fix the spike errors? (experiment, not adopted)

**Question.** The spike spot-check failed mostly because of misread event types. Would counting only articles above a minimum quality score fix that?

**Method.** Recompute each of the 10 hand-judged spikes (and the whole 32-day backtest) counting only articles scoring at or above a threshold, baseline included, then see which spikes are still flagged.

| Minimum quality | Yes kept (of 3) | No kept (of 6) | Unclear kept (of 1) | Spikes in the 32-day backtest |
|---|---|---|---|---|
| none (current) | 3 | 6 | 1 | 298 |
| 0.3 | 1 | 5 | 0 | 248 |
| 0.4 | 1 | 4 | 0 | 226 |
| 0.5 | 1 | 2 | 0 | 167 |

**Result: no improvement.** The filter removes misreads (Romania drops at 0.3) but also removes two of the three real spikes (Oman, West Bank), so the share of surviving spikes that were real stays near one in three at best. The model is too weak to tell real from misread events at the level a spike count needs. Only 10 judged spikes, so this is indicative, not conclusive. The quality score is therefore used for browsing (filter, detail, table), not for spike detection. The same labeled events may overlap with these spikes, which would flatter the model, not hurt it.

## Accuracy refinement round 1: richer event-model features (not adopted)

**Why.** The 312 labels showed that the specific event code and actor details seemed to matter (code 202 is 0% credible, 173 is 72%; an actor based in another country than the event is 26% credible against 43% when they match). Those fields were not stored, so the database gained 7 columns (migration 002) and the 58-day backfill was re-read (5,565 files, 797,968 events, all 312 labels intact).

**Setup.** The test set is now frozen: an event is in it if a hash of its id falls in 3 of 10 buckets, so adding labels never moves a test row into training (106 test rows, 206 training rows). Adoption rule, written **before** running: a variant is adopted only if cross-validated ROC-AUC >= 0.803 (baseline 0.763 + 0.04) **and** the test-AUC 95% interval's lower bound is above 0.55 (the baseline's); if several pass, the simplest wins.

| Variant | Features | CV ROC-AUC (5-fold, train) | Test ROC-AUC (95% interval) | Test precision at 60% recall | Rule |
|---|---|---|---|---|---|
| V0 plain: base + category (old model minus 3 constant features) | 13 | 0.767 +/- 0.050 | 0.676 (0.57 to 0.77) | 0.51 | fail |
| V1 + specific event codes (15 most common) | 29 | 0.743 +/- 0.071 | 0.666 (0.55 to 0.76) | 0.50 | fail |
| V2 + actor types and location mismatch | 21 | 0.750 +/- 0.051 | 0.677 (0.56 to 0.77) | 0.53 | fail |
| V3 + both | 37 | 0.730 +/- 0.085 | 0.661 (0.55 to 0.76) | 0.50 | fail |

**Result: no improvement. More features made the model slightly worse.** With 206 training rows, 21 to 37 columns overfit.

Two follow-up checks, both using **cross-validation on the training rows only** (the test rows were not touched):
- **Stronger regularisation does not rescue it.** Repeated 5x5 CV AUC by regularisation strength C (0.01 / 0.03 / 0.1 / 0.3 / 1): plain 0.775 / 0.779 / 0.780 / 0.779 / 0.776; plus codes 0.754 / 0.754 / 0.754 / 0.753 / 0.748; plus actors 0.759 / 0.765 / 0.764 / 0.758 / 0.753; both 0.744 / 0.741 / 0.741 / 0.737 / 0.732.
- **More labels would not close the gap either.** Learning curve (CV AUC at 49 / 74 / 98 / 131 / 164 training rows): plain 0.726 / 0.745 / 0.754 / 0.762 / 0.776; rich 0.674 / 0.690 / 0.705 / 0.710 / 0.721. The plain model is still improving slowly; the gap to the rich one (about 0.055) is not narrowing.

**Decision.** Production keeps the plain feature set (V0). It is equivalent to the old model but drops three features that never varied in the labeled data (root-event flag, actor 1 present, actor 2 present). The richer feature groups stay in the code and are tested, but are switched off; the new database columns stay stored. Number of variants tried against the frozen test set: 4 (all reported above). Not adopted: no re-score of anything changed except the removal of the constant features (scores are essentially unchanged).

**What this means.** The event-quality model is limited by the information available per label, not by which GDELT fields it sees. Per-event credibility from GDELT fields alone sits at about 0.67 to 0.77 AUC with this many labels. Larger gains would need much more labeled data or a different kind of signal (for example, whether other outlets corroborate the same event), not more columns.

## Accuracy refinement round 2: alerts

**A bigger audit corrected the headline number.** The first spot-check (10 alerts, 3 real) was an unlucky small sample. After judging 40 more alerts by hand, the gold set (`docs/spike_gold_set.csv`) holds 50 judged alerts: **30 real, 19 not, 1 unclear, so detector precision is 61%** (95% interval 47% to 74%). The earlier "3 of 10" in the section above is superseded by this figure. Split: 30 dev (used for experiments) and 20 final (opened once, at the end): dev 17 real / 12 not / 1 unclear = 59%; final 13 real / 7 not = 65%.

**Why the not-real ones are not real** (19 alerts; a few have two reasons): misread event type 10 (a court case, a military test, suspects detained in a plot coded as violence), old event rehashed 4, same story alerted again 5, wrong place 2.

**Experiments (rules fixed before running; all tried on dev only):**

| Idea | Rule to adopt | Dev result | Final result (opened once) | Decision |
|---|---|---|---|---|
| Stricter floor / score threshold (12 settings from floor 10 to 20 and score 3 to 6) | precision +10 points, keep at least 14 of 17 real alerts, at least 3 alerts/day | none passed; stricter settings lose real alerts about as fast as bad ones (floor 20: 8 of 17 real kept at 62% precision) | not tested | not adopted |
| Rank alerts by article count instead of score | AUC of "real vs not real" at least 0.10 better | score AUC 0.36 (worse than chance), count 0.59: passed | score 0.72, count 0.25: **reversed**, failed | not adopted |
| Count only articles with quality score >= 0.4 | precision +10 points, lose at most 2 real alerts | precision 57% to 74%, 14 of 16 real kept: passed | precision 62% (10 of 16), lost 3 real: **failed** | not adopted |
| Group alerts that share articles | n/a | same-day overlap is rare (13 of 307 spikes) and does not cover the multi-day duplicates that were judged | not built | not built |

**What this shows.** With 20 to 30 alerts per set, differences of this size are indistinguishable from chance: two ideas that "won" on dev lost or reversed on the untouched final set. That is exactly why the final set was held back. **The detector is left unchanged: roughly 60 to 65% of alerts are real, and no tested tweak reliably improves that.** The plan's target of 60% alert precision on the final set was already met by the baseline (65%), so it does not count as an improvement.

**Where the errors come from.** About half the false alerts are misread event types in the GDELT coding itself, which the model cannot repair with GDELT fields at this label count (see round 1). The practical lever is the analyst: each alert needs a fast way to verify the underlying articles before briefing. Further statistical tuning would need many more judged alerts (hundreds) to tell small improvements from noise. The 20 final alerts are now used and cannot serve as an untouched test again.

## Refinement round 3: "ongoing" label on alerts (adopted as a label and sort order, not a filter)

**Idea.** Nine of the 19 false alerts were an old event rehashed or the same story alerted again.
Mark an alert *ongoing* when the same country and category was also flagged on any of the previous
3 days, and list new stories first.

**Rule set before measuring** (from the plan): adopt if ongoing alerts are false at least 15 points
more often than new ones on the 50 judged alerts. Windows tried: 1, 2, 3 and 7 days (4 looks, so any
single p-value is optimistic). 3 days was the planned setting.

| Previous days checked | Ongoing: real | New: real |
|---|---|---|
| 1 | 8 of 17 (47%) | 22 of 33 (67%) |
| 2 | 8 of 19 (42%) | 22 of 31 (71%) |
| **3 (used)** | **9 of 21 (43%)** | **21 of 29 (72%)** |
| 7 | 11 of 23 (48%) | 19 of 27 (70%) |

The gap at 3 days is 29 points (Fisher exact p = 0.045; at 1 day p = 0.23). The direction is the same
at every window, which is some comfort, but this is 50 alerts that I had already looked at while
building the idea, and there is no unseen set left to confirm it. **Treat it as a hypothesis.** Because
of that it only labels and reorders: no alert is hidden and precision of the alert list as a whole is
unchanged (still about 61%, 50 judged). Whether new stories first really improves the top of the list
needs fresh audits (plan step P0).

## Refinement round 3b: URL-word cues for misread event types (tested, not built)

**Idea.** Ten of the 19 false alerts were misread event types (a court case or a military test coded as
violence). Look for non-combat words in the article URLs (court, trial, verdict, sentenced, lawsuit,
earnings, celebrity, concert, drill, exercise, test-launch) and badge an alert as a possible misread.
No article text is fetched; the URL is already stored.

**Rule set before measuring.** Badge an alert if more than half its (up to 8) best-sourced evidence
articles carry a cue. Adopt only if it catches at least 5 of the 10 misread alerts and badges at most
3 of the 30 real ones. One cue list and one rule were tried (no variants).

| | Badged |
|---|---|
| Misread alerts (10) | **0** |
| Real alerts (30) | 1 |
| Other false alerts (9) | 0 |

**Not adopted, and the signal is absent, not just weak.** Counting any alert with at least one cue
article: 2 of 10 misread alerts (20%) against 7 of 30 real alerts (23%). The only cue words that
appear are `court` and `trial` words, and real alerts contain them as often as misread ones (genuine
court coverage of a real conflict). Misread types are not visible in URL slugs with a keyword list, so
no code was added. Remaining ways to catch them would need article text, which the project does not
fetch, or many more labels so a model could learn it.
