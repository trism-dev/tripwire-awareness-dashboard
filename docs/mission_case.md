# Tripwire: mission case

*One page. Draft for Tristan to edit in his own words.*

## The user

A regional watch analyst: a staff officer, a humanitarian desk officer or a corporate security lead
who watches one region and has to brief a supervisor in under five minutes. They start a shift, or
get alerted, and need to know what changed.

## The problem

Open-source news is the earliest public signal of trouble: protests spreading, clashes crossing a
border, a jump in coercion against civilians. But it arrives as tens of thousands of
machine-coded records a day, and most are repetitive, mis-placed or simply wrong. The analyst has to
answer three questions quickly: **what is happening where, what is unusual for that place, and how
much can I trust it?**

## How Tripwire helps

- **One map, fresh.** It loads the GDELT 2.0 event feed every 15 minutes and keeps conflict and
  unrest events with a usable location, grouped into five mission categories. New data appears on
  the dashboard within minutes of GDELT publishing it (the header shows its age and warns past 30 minutes).
- **What is unusual.** Each country and category is compared with its own last 28 days. An
  alert needs a real jump above that normal level, counted in **distinct news articles**, not event
  rows, because one article often produces several rows.
- **How much to trust it.** A small model, trained on 312 events hand-labeled by the author, gives each
  event a 0 to 1 quality score. Analysts can hide low-quality events, see the score on the event
  detail panel, and click through to the source article before briefing anyone.
- **Hand-off.** The current filtered view exports to CSV.

## What it honestly achieves

Measured, and written up with the numbers in `docs/evaluation.md`:

- **Spike alerts:** about 10 fire a day. In a hand audit of 50 alerts, **30 were real, 19 not,
  1 unclear: roughly 6 in 10 are real** (95% interval 47% to 74%). The false ones are mostly event
  types misread in the source data (court cases, tests or arrests coded as violence), old events
  being rehashed, and the same story alerted again on later days. Counting distinct articles instead
  of event rows already removed 40% of the earlier alerts, including a Tunisia alert that was 17 rows
  from a single article. Every tested tweak (stricter thresholds, other rankings, filtering by the
  quality score) either lost real alerts or failed on a held-back test set, so none was adopted.
- **Quality model:** ranks events better than chance (ROC-AUC 0.71, plausible range 0.61 to 0.81)
  and is right 56% of the time when it calls an event credible, against 40% by chance. It did **not**
  meet the target of beating "always say credible" on F1.
- Treat both as **aids to prioritise**, not as a verdict on what is true. Always open the article.

## Limits

- GDELT is automatic: duplicates, wrong places and misread articles are in the source data.
- One labeler, 312 labels, a 94-event test set: wide uncertainty.
- Country codes are FIPS 10-4, not ISO. Times are UTC.
- Links out only: no article text is fetched or stored. Data: The GDELT Project (gdeltproject.org).

## Next steps

1. Make verification faster: show each alert's best-sourced articles and event types right in the
   Alerts tab, so the analyst can confirm or reject it in seconds.
2. Use the quality score on the alert list, once a stronger model exists. Filtering by it today
   did not improve the alerts.
3. More and more varied labels, especially events reported by several sources, which the model
   has almost no examples of.
4. Add a second source (for example ReliefWeb) for corroboration.
