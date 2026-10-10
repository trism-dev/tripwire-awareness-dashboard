# Resume bullet and numbers you can defend

*Drafts for Tristan to edit in his own words. Booz Allen bans AI help in interviews, so every line
below must be something you can explain from memory. Read the "how to explain it" column until you
can say each one without looking.*

Replace `[LIVE URL]` once the Railway deployment is up. Re-check any number that may have changed
(events, tests, alert precision) before you send the resume.

## Pick one bullet

**Short (two lines):**
> Built **Tripwire**, an open-source situational-awareness dashboard that ingests the GDELT news-event
> feed every 15 minutes (about 800,000 events), flags country-level spikes against a 28-day robust
> baseline, and scores event credibility with a model trained on 312 hand labels; hand-audited 50
> alerts (61% real) and published the failures. Python, Postgres, Streamlit, Docker, CI. [LIVE URL] ·
> github.com/trism-dev/tripwire-awareness-dashboard

**Rigor-first (three lines, for a statistics or ML-leaning role):**
> - Designed spike detection (median/MAD robust z-score per country and category, Poisson fallback for
>   quiet places) and measured it honestly: **61% of 50 hand-audited alerts were real** (95% interval
>   47% to 74%); tested four fixes against a held-back set and rejected all of them when they did not
>   replicate.
> - Trained and evaluated a credibility classifier on 312 hand labels with a frozen hash-based test
>   split, cross-validation and baselines (ROC-AUC 0.68, interval 0.57 to 0.77); documented that richer
>   features made it worse.
> - Built the pipeline end to end: idempotent 15-minute ingestion with failure handling, 158 automated
>   tests, GitHub Actions CI, Docker Compose, deployed on Railway.

**Product-first (for a data-product or analyst-facing role):**
> Built an open-source watch-floor dashboard for conflict and unrest events: live map, ranked spike
> alerts with the source articles behind each one, 30-day trend charts, a quality filter and CSV
> export, refreshed every 15 minutes from public GDELT data. Wrote a one-page mission case and an
> evaluation that states what it gets wrong.

## Numbers you can defend

| Claim | Where it comes from | How to explain it in one breath |
|---|---|---|
| About 800,000 events, 60 days | `events` table (795,516), 6,026 files ingested | "A 15-minute GDELT file is about a thousand relevant events; I keep 60 days so the 28-day baseline always exists." |
| Ingests every 15 minutes, data is minutes old | `worker/run.py`, header shows age | "A worker polls GDELT, loads new files idempotently, and the app shows how old the data is." |
| Median/MAD robust z-score | `tripwire/spikes.py`, `tests/test_spikes.py` | "Median and MAD ignore an earlier burst, unlike mean and standard deviation. If MAD is zero I use a Poisson spread." |
| Counts distinct articles, not rows | `daily_counts` | "One article often produces several event rows; counting rows made 40% of the first alerts look bigger than they were." |
| **61% of 50 alerts real** | `docs/spike_gold_set.csv`, `docs/evaluation.md` | "I judged 50 alerts by hand against their source articles: 30 real, 19 not, 1 unclear." |
| Four fixes tested and rejected | `docs/evaluation.md`, round 2 | "Two looked better on my development set and reversed on the 20 alerts I held back, so I adopted none." |
| ROC-AUC 0.68 (0.57 to 0.77) | `models/quality_metrics.json` | "The model ranks a random credible event above a random non-credible one about two times in three; that is modest and I say so." |
| 312 hand labels, frozen test split | `tripwire/quality/train.py` (`is_test_event`) | "Which events are test data is decided by a hash of the event id, so adding labels never leaks test rows into training." |
| 158 tests, CI | `tests/`, `.github/workflows/ci.yml` | "Every module has tests, including a hand-computed example for the spike math; CI runs them against a real Postgres." |
| Safe CSV export | `tripwire/export.py` | "GDELT text is untrusted; a cell starting with `=` would run as a formula in Excel, so I prefix it." |

## What not to claim

- Do **not** say the alerts are "accurate" or "99%": they are about 6 in 10.
- Do **not** say the quality model "predicts credibility well": it ranks modestly better than chance.
- Do **not** say it is "deployed" or give a live URL until Railway is actually serving it.
- Do **not** claim real-time: it is every 15 minutes (GDELT's own cadence).
- Say "hand-labeled by me" about the labels (one labeler, no agreement measure).

## Questions to expect (answer from your own understanding)

1. Why median and MAD instead of mean and standard deviation?
2. What happens when MAD is zero, and why a Poisson spread?
3. Why count articles, not event rows? What did it change?
4. How do you know the alerts are right? What was the sample, and how could it mislead you?
5. Why hold back 20 alerts, and what happened when you used them?
6. What does ROC-AUC 0.68 mean in plain words? Why did F1 not beat "always say credible"?
7. Why did adding features make the model worse?
8. How does the ingestion stay correct if a file arrives twice, late or corrupt?
9. What are the limits of GDELT as a source (bias, duplicates, misread events)?
10. What would you do next with another month?

For each, the answer is in `docs/decisions.md` and `docs/evaluation.md` in your own words; if you
cannot explain a line of code in `tripwire/`, read it until you can (that is rule one in CLAUDE.md).
