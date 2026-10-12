# Decisions

## 2026-10-04: Parse by splitting lines, not pandas read_csv
- **Decision:** `parse_text` splits each line on tabs and keeps only rows with exactly 61 fields; the rest are counted as `bad_rows`.
- **Alternatives:** `pd.read_csv(..., on_bad_lines="skip")`.
- **Why:** read_csv pads short rows silently (a cut-off last line would look valid) and its quoting rules can misread GDELT text. Plain splitting is easy to explain and the bad-row count feeds `ingest_files`.

## 2026-10-04: Use https for GDELT URLs
- **Decision:** `fetch.py` will use `https://data.gdeltproject.org/...`.
- **Why:** the `http://` URLs in the PRD return an empty 301 redirect to https. The manifest `lastupdate.txt` still lists `http://` file URLs, so `fetch.py` must rewrite them to https.

## 2026-10-04: make installed via winget
- **Decision:** GNU make (ezwinports) so the Makefile in CLAUDE.md works on Windows. `.gitattributes` forces LF so CI on Linux can read the Makefile.

## 2026-10-04: "Cooperation" bucket for CAMEO roots 01-08
- **Decision:** `categories.py` maps roots 01-08 to a `Cooperation` category.
- **Alternatives:** leave 01-08 unmapped.
- **Why:** the PRD test requires every root 01-20 to map to exactly one bucket, but §5.3 only lists conflict roots. These rows never survive the QuadClass 3/4 filter, so the bucket is only for completeness.

## 2026-10-04: Country-centroid events (ActionGeo_Type 1) pass the ingest filter
- **Decision:** `filter_events` keeps them; the map query will exclude `geo_type < 2` by default.
- **Why:** PRD 5.2 says Type 1 stays in the table (they still count toward country-level spike detection) but is not drawn on the map.

## 2026-10-05: Postgres on host port 5434
- **Decision:** `docker-compose.yml` maps the db to 5434.
- **Why:** 5432 and 5433 are used by other local projects' containers. Inside Docker the app still uses 5432.

## 2026-10-05: Own migration runner, tests in throwaway schemas
- **Decision:** `db.migrate` applies `db/migrations/*.sql` in name order and records each in `schema_migrations`. DB tests create a random schema, migrate it, then drop it (`TEST_DATABASE_URL`; skipped if unset).
- **Alternatives:** Alembic/yoyo (new dependency, CLAUDE.md says ask first); one shared test database (tests could interfere).
- **Why:** about 20 lines, plain SQL, and tests can't touch real data.

## 2026-10-05: Upsert keeps quality_score and ingested_at
- **Decision:** `ON CONFLICT DO UPDATE` refreshes the GDELT fields only.
- **Why:** re-reading a file must not wipe a model score, and `ingested_at` should say when the row first arrived.

## 2026-10-05: ingest_files statuses and what gets retried
- **Decision:** a file is `ok`, `missing` (404) or `error`. `ok` and `missing` are skipped on later runs; `error` is retried.
- **Why:** GDELT really does skip slots, so retrying 404s forever wastes requests. Errors (network, corrupt zip, md5 mismatch) may be temporary.

## 2026-10-05: Backfill stops 1 hour before now, and has no md5 check
- **Decision:** backfill covers `now - N days` to `now - 1 hour`; the live cycle covers recent files. md5 is only checked for the live file.
- **Why:** an unpublished recent slot would 404 and be recorded as `missing` permanently. Historical file URLs follow a pattern with no md5 listed (only `lastupdate.txt` lists one); the large `masterfilelist.txt` would give md5s but I judged it not worth it for this project.

## 2026-10-05: urllib instead of a new HTTP library
- **Decision:** `fetch.py` uses `urllib.request` with 3 retries and exponential backoff.
- **Why:** stdlib, and CLAUDE.md says to ask before adding dependencies.

## 2026-10-05: Minimal worker now, app service later
- **Decision:** `worker/run.py` only ingests (a 2-hour catch-up pass, then the newest file, every 15 min). Spikes and retention come in week 2. Compose has `db` and `worker`; the `app` service is added when `app/Home.py` exists.
- **Why:** gets freshness running and fills gaps after outages without writing code ahead of its week. Each pass opens a fresh DB connection, so a Postgres restart can't leave the worker stuck.

## 2026-10-05: CI actions pinned to exact versions
- **Decision:** `checkout@v7.0.1`, `setup-uv@v10.2.0`.
- **Why:** `setup-uv` publishes no floating major tag; my first push with `@v10` failed to resolve.

## 2026-10-05: Spike detection design (spikes.py)
- **Decision:** counts per `event_date` x country x mission category; baseline = median/MAD of the 28 days before the day, excluding the day itself; flag z >= 3 and count >= 10 (inclusive). Missing days count as 0.
- **MAD = 0 fallback:** z = (count - median) / sqrt(max(median, 1)), a Poisson-style spread (variance = mean). `baseline_mad` is stored as 0 so an alert shows which rule fired. Alternative was to skip those groups, but quiet places are exactly where a jump from 0 to 10+ matters.
- **Guard:** `run` skips a day unless we were ingesting before the 28-day window started (`min(date_added)`). Otherwise a fresh database would flag every busy country, because the pre-collection days look like zeros.
- **Stored with delete + insert per day** so a spike that no longer qualifies disappears. Today's counts are partial until the day ends; they can only grow, so today's z is a lower bound.
- **Skipped:** the optional NumSources weighting (PRD marks it optional).

## 2026-10-05: RETENTION_DAYS default 30 -> 60
- **Decision:** keep 60 days of events.
- **Alternative:** a separate `daily_counts` table that outlives pruned events.
- **Why:** a 28-day baseline plus a 30-day backtest needs ~58 days; pruning at 30 would delete the baseline. Raw events at ~5 MB/day is ~300 MB, acceptable. Check the hosted cost at deploy time.

## 2026-10-06: Map colours and the "touching dots" limit
- **Decision:** categories use the first six slots of the dataviz skill's palette in fixed order (Armed conflict, Protest, Threats, Force posture, Mass violence, Other conflict), with separate light and dark shades, stroke ring on each dot, rarest categories drawn last (on top).
- **What was checked:** `validate_palette.js` passes the five default categories on adjacent pairs in light and dark mode. It FAILS the stricter all-pairs test (normal-vision floor 12.9 light / 10.6 dark, below the required 15), which is the right test for a scatter map because any two dots can touch. The documented palette only passes all-pairs for 3 series.
- **Alternatives:** fold to 3 colours (hides Mass violence and Force posture, the rarest and most important); facet into 5 small maps (too heavy); invent new hues (breaks the "documented palette only" rule).
- **Mitigation:** colour is never the only cue. The legend (with counts), hover tooltip, category filter and the events table all name the category in text. Revisit if users confuse categories on the map.

## 2026-10-06: Reference lookups copied from GDELT into the repo
- **Decision:** `tripwire/data/fips_countries.tsv` and `cameo_eventcodes.tsv` are GDELT's own lookup files (downloaded once from gdeltproject.org/data/lookups/). Two country codes (RB = Serbia, OC = ocean) and three event codes (`---`, 106, 1213) in real data are missing from them. Countries are patched in `fips.py`; event codes fall back to the parent code ("... (general)").
- **Why:** a hand-typed table of 270 countries would have errors; the official file is the source of truth and the test checks it.

## 2026-10-06: App design choices
- **One short connection per cached query** (60 s cache) instead of a shared connection: Streamlit runs scripts on threads, and a shared psycopg connection is not thread-safe. Cost is a few ms locally.
- **Map query loads only the columns needed to draw a point;** full detail for one event is fetched on click. Capped at 50,000 points (best-sourced first) with a visible "showing N of M" message.
- **Detail and tooltip text is plain text,** never HTML or markdown, because actor and place names come from GDELT. Source links must start with http:// or https://.
- **Measured:** 7-day view (46,593 events) = 66 ms count + 231 ms map query on the server; the page switched from 24 h to 7 days in about 0.9 s in the browser (target < 3 s).
- **Worker catch-up window raised from 2 h to 24 h** after the laptop slept overnight and left a 12 h gap.

## 2026-10-07: Map draws one dot per place and category (review fix)
- **Decision:** `queries.map_events` groups events by (lat, lon, category). Each dot carries the best-sourced event's id (what a click opens) and an event count. The header says "Events in view" (events) and "Places on map" (dots).
- **Why:** an independent review found that GDELT puts many events on exactly the same point (39,179 events sat on 6,809 distinct place+category spots in 7 days). Drawing all of them hid most dots under others and made the map spec 18.3 MB, 2.5 s to serialize on every rerun. Grouped: 3.2 MB, 0.12 s. My first timing (0.9 s) was wrong because it measured when the header numbers rendered, not when the map finished.
- **Also fixed from the review:**
  - A map selection is remembered by position in the data, so after a filter change it could show an unrelated event. The map key now changes with the filters and the data, and a selection is only trusted if that event is on the map.
  - The Countries filter cleared itself whenever the option order changed (needs a widget key).
  - Every DB connection sets the session time zone to UTC, so "UTC" labels are true on any Postgres.
  - Visitors see a fixed message, not DB host/port/stack traces (`showErrorDetails = "none"`).
  - Detail text is plain `st.text` lines that wrap; the footer is regular text, not a faint caption.
- **Not fixed (judged not worth it now):** a country spanning the antimeridian opens zoomed out (known limit); tie-breaking in the ordering is already deterministic after grouping.
- **Process note:** review agents are expensive. After this one hit the session limit, remaining checks were done by hand.

## 2026-10-07: Alerts and Trend tabs
- **Decision:** the Alerts tab reads stored spikes (`spikes` table) for one UTC day, ranked by Score by default with a "Rank by event count" switch; it follows the sidebar category and country filters. Selecting a row pre-fills the Trend tab's country and category pickers (only on a new click, so the pickers still work afterwards).
- **Trend chart** uses `spikes.trend()`, which shares the scale formula with `detect()` (`_scale`) and has a test that both flag the same days, so the chart can't disagree with the alert list. Chart shows events per day, a grey band from the typical day to the flag threshold, orange diamonds on flagged days, plus a "Show the numbers" table (colour is never the only cue).
- **Worker now refreshes spikes** for yesterday and today every pass, in its own try/except so a spike error can never stop ingestion.
- **Known weakness:** with the floor at 10 events, a place that goes from 0 to 11 scores 11-14 and tops a Score ranking above much larger real surges (Israel armed conflict: 362 vs typical 212 scores 3.8). This is why there is a count ranking. The S3 spot-check should decide whether to raise the floor or rank by a blend.
- **Today is partial,** so its score can only rise; the day picker labels it "(so far today)".

## 2026-10-08: Spikes count distinct articles, not event rows
- **Decision:** `daily_counts` uses `count(DISTINCT coalesce(source_url, global_event_id::text))`. The floor (10) and threshold (score 3) now mean 10 articles. The Alerts and Trend tabs say "Articles".
- **Alternatives:** weight rows by `num_sources` (the PRD's optional idea; it rewards well-reported events but does not stop one article's many rows), or keep rows and raise the floor (hides small real surges and still inflates big ones).
- **Why:** the S3 backtest showed 40% of spikes rested on fewer than 10 distinct articles and the median spike had about 2 rows per article. After the change, 502 spikes became 298 and the three suspected duplicate-article spikes in the sample disappeared.
- **Cost:** a few small genuine spikes drop out (e.g. Pakistan protests at 10 articles). "Events in view" and the map still count event rows; only spike detection changed.
- **Open:** a clean version-B accuracy figure needs a fresh spot-check sample.

## 2026-10-08: Labeling page design (S2)
- **Queue:** events from the last 30 days in the five mission categories, categories taking turns, inside each a fixed shuffle (`md5(id || seed)`). Repeatable, balanced, and needs no new table. Skips live in the browser session only (a skipped event can return after a reload).
- **Hidden from the labeler:** number of sources, tone, Goldstein score, articles, mentions. They are classifier inputs; seeing them would make labels echo the model's own features.
- **Label meaning:** 1 = the article shows a real event of about the coded type at roughly the coded place; 0 = wrong type, wrong place, not an event, or an old event rehashed (the S3 spot-check errors were all of this kind).
- **Safety:** the page does nothing unless `ENABLE_LABELING=1`. There are no user accounts, so on a public host anyone could otherwise write labels. Do not set it on Railway.
- **Shared helper:** `safe_url` moved to `tripwire/web.py` so Home and Label use the same link check.

## 2026-10-08: Signal-quality classifier (S1)
- **Decision:** logistic regression on the PRD's GDELT-only features, trained on 222 hand labels; evaluation = stratified 70/30 split (seed 42), 5-fold CV inside the training part, test set used once, plus two baselines (always credible; rule geo_type >= 3) and a bootstrap interval for test AUC. Metrics and the feature list are saved next to the model (`models/quality_metrics.json`).
- **Result, honestly:** modest. Test F1 0.57 vs 0.56 for always-credible (noise); precision 0.53 vs 0.39; ROC-AUC 0.68 (interval 0.54-0.81). See `docs/evaluation.md`.
- **The saved model is refitted on all labels** (more data for scoring); the reported numbers come from the train-split model, so the saved model is never evaluated on rows it saw.
- **Scores are stored in `events.quality_score`** (0 to 1). `make score` fills empty ones; the worker scores new events every pass (isolated try/except, never blocks ingestion). After retraining, `python -m tripwire.quality.score --all`.
- **The model file is committed** (150 KB, mostly the news-site frequency table) because the hosted worker needs it; `.gitignore` no longer excludes `models/*.joblib`.
- **Not done on purpose:** no extra features beyond the PRD list (222 labels cannot support more), no gradient-boosted comparison (stretch item), no threshold tuning (would need more data than the test set holds).
- **Open risk:** labeled events can be deleted by a future retention job (`labels` cascades from `events`). Retention must skip labeled events, or the training data disappears.

## 2026-10-08: Quality score used for browsing, not for spike detection
- **Decision:** the map and events table get a "Hide low-quality events" toggle (minimum score slider, default 0.4, off by default; unscored events are kept) and the detail panel and table show the score. Spike detection does NOT use the score.
- **Why not for spikes:** experiment in `docs/evaluation.md`: filtering spike counts by quality kept 1 of 3 real spikes and 2-5 of 6 bad ones; no gain. Not worth the extra complexity or the loss of real alerts.
- **Why off by default:** the model is modest (AUC about 0.71) and a default of 0.4 hides over half of all events; the analyst should opt in knowingly.
- **Bug caught by tests:** the table's quality column crashed when every row in view was unscored (all-NULL column has object dtype), which would have hit users briefly after each ingest.

## 2026-10-08: CSV export (S5) and retention
- **CSV:** one row per event (not per map dot) for the current filters, newest first, capped at 100,000 rows. Built only when the button is clicked (a callable passed to `st.download_button`), so normal page loads don't pay for it. A 7-day view is about 47k rows / 15 MB, built in about 2 s. Includes readable country and event-type names plus the quality score; UTF-8 with a byte-order mark so Excel shows accents correctly.
- **Formula injection:** GDELT text is untrusted and a spreadsheet treats a cell starting with `=`, `+`, `-` or `@` as a formula, so text columns get a leading apostrophe. Numeric columns (a negative Goldstein score) are left alone.
- **Attribution:** carried in the file name (`tripwire-gdelt-events-...csv`) and the button help text; a CSV has no place for a footer.
- **Retention:** every worker pass deletes events older than `RETENTION_DAYS` (60) that have no label, in batches of 20,000, and trims `ingest_files` to the same age. Labeled events are kept forever because they are the classifier's training data (this closes the risk logged on 2026-10-08). First run removes the roughly 7,500 events from the first backfill day.

## 2026-10-09: Diagrams
- **Decision:** three Mermaid sources in `docs/diagrams/` (architecture, ERD, ingestion flow) rendered to `docs/*.png` with the Mermaid CLI through `npx`, using the installed Chrome. Nothing was added to the project's dependencies.
- **Re-render:** `npx @mermaid-js/mermaid-cli -i docs/diagrams/X.mmd -o docs/X.png -s 2 -b white` (set `PUPPETEER_SKIP_DOWNLOAD=1` and a puppeteer config pointing at Chrome).
- **Ingestion flow** is a flowchart with BPMN-style start/end events and gateways rather than strict BPMN notation. The first version was 5,356 px tall; merging the linear parse/filter/categorize/upsert steps cut it to 3,628.
- **Keep in sync:** the diagrams describe the current code (24 h catch-up, 60-day retention, 61-field rows, ledger statuses ok/missing/error). Change them with the code.

## 2026-10-10: Richer event features measured and rejected; frozen test split
- **Decision:** keep the plain feature set (base + category) for the quality model. Event codes and actor/location features were built, tested and measured (4 variants, rule fixed beforehand) and made the model worse (CV AUC 0.767 down to 0.730 with everything).
- **Frozen split:** test set = events whose id hashes into buckets 0-2 of 10 (`is_test_event`). Metrics are now comparable across runs and across label counts. The test estimate moves by about +/-0.04 with which events land in it, so only larger improvements count.
- **Kept anyway:** migration 002 columns and the `codes`/`actors` feature groups (off by default, tested end to end). Cheap to keep, and they are the starting point if many more labels arrive.
- **Cost of the experiment:** the 58-day re-ingest (about 80 min of downloads); `backfill --reingest` stays as a tool.

## 2026-10-10: Alert detector left unchanged after a 50-alert audit
- **Decision:** no change to the floor (10 articles), score threshold (3), ranking or counting. The default ranking stays "Score".
- **Why:** hand-judged precision is 61% (30 of 49); every tested tweak either lost real alerts or failed on the untouched final set (table in `docs/evaluation.md`). Two ideas passed their pre-set rule on the dev set and then failed on the final set, which is the intended safeguard working.
- **Process:** adoption rules were written before each run; the final split (20 alerts) was opened exactly once; no labeled event lies inside any dev spike (checked), so the quality-filter test had no leakage.
- **Limit:** 50 judged alerts cannot detect improvements smaller than about 15 points. The final split is spent.
- **Not built:** grouping alerts by shared articles (the judged duplicates are on different days, so it would not help).

## 2026-10-10: Alert evidence panel
- **Decision:** selecting a row in the Alerts table shows the best-sourced distinct articles behind that alert (what GDELT coded each as, actors, place, sources, quality score, a safe link), under the table. It uses `queries.spike_evidence`, which the audit checklist (`gold.evidence`) now reuses, so the analyst sees exactly what the audits judged.
- **Why:** the 50-alert audit showed about 4 in 10 alerts are false, mostly misread event types that a person spots in seconds by opening two articles. The panel makes verification the default step instead of a hunt.
- **Bugs found while building it (pandas turns a missing text value into NaN, which is truthy):** `event_description(NaN)` crashed, and `a or "?"` printed "nan" for missing actor names. Both fixed and tested; the audit checklist had the same latent problem.

## 2026-10-10: Deployment design (one image, SERVICE variable)
- **Decision:** one Docker image; `deploy/start.sh` starts the dashboard (`SERVICE=app`, port from `PORT`) or the worker (`SERVICE=worker`). The Dockerfile has a default `CMD`; Compose still overrides it explicitly.
- **Alternatives:** Railway config files per service (config-as-code is deprecated, legacy files stop working 2026-12-01; and per-service file paths are not documented); typing start commands in the dashboard (Railway does not expand `$PORT` in a plain start command, so it would need a `sh -c` wrapper, and it is untestable locally).
- **Why:** it is testable on this machine. Verified: no `SERVICE` exits with a clear message; `SERVICE=app` serves health 200 on a custom `PORT` with labeling off and stops in 1.5 s; the worker runs a pass.
- **Bug found by that test:** the worker was force-killed (exit 137) on stop because Python as PID 1 ignores SIGTERM. Added a handler (`worker/run.py: handle_sigterm`); now exits 0 in 1.6 s. Matters on any host that redeploys by stopping the container.
- **Data transfer:** dump and restore (61 MB), rehearsed into a scratch database with identical counts. It carries the labels, which exist nowhere else. A re-backfill on the host would take about 80 minutes and would lose the labels.
- **Binary-safe dump:** use `pg_dump -f` then `docker compose cp`; PowerShell's `>` corrupts binary output.
- **Cost:** about $9 to $13 a month estimated from measured memory and Railway's published rates (Hobby: $5 including $5 usage). Postgres memory is the uncertain part. A spending limit must be set by the owner; where exactly could not be confirmed from the docs.

## Tables fit their container (no horizontal scrollbars)

Streamlit grids scroll sideways when their columns are wider than the page. The events table (12
columns) did, and the Alerts and Evidence tables clipped. Fix: fixed pixel widths on every column,
and only the columns that fit a 1024 px window are shown. The events table drops Country (merged into
Place, shortened to "city, country"), actors, Goldstein, tone, source count and the event type; the
Evidence table hides Actors. All of these are still in the CSV export. Alerts shorten "quiet
baseline" to "quiet". Verified in the browser at 1024 px. At phone width (390 px) the page does not
scroll sideways but the tables still scroll inside their own box; a card layout would be needed to
fix that.

## Alerts: "ongoing" label, sort order, and short sentences

- **Ongoing label.** `queries.spike_alerts` adds `ongoing` (same country and category flagged in the
  previous 3 days; one SQL `EXISTS`). The Alerts table shows it as Story = new / ongoing and lists new
  stories first. It replaced the Rule column to keep the table inside its container; the quiet-baseline
  note moved to a caption under a selected alert. Evidence and caveats: `docs/evaluation.md`, round 3.
- **Plain sentence per alert** (`alert_sentence`): "Iraq: 13 articles on threats & coercion so far
  today; a typical day has 5." Shown for the top alert and for the selected row.
- **Show on map** sets the sidebar window, category and country from an alert (`map_focus`), through a
  button callback because Streamlit only lets you change a widget's value before it is drawn. Alerts
  older than 7 days cannot be shown (the map window is 7 days). It narrows the alerts list to that one
  alert too, because the Alerts tab follows the same filters; that is the existing design.
- **Map dots** are sized in metres with pixel limits (4 to 14 px) so they spread as you zoom, and a
  ring marks the clicked dot. pydeck turns a bare string like `meters` into a JavaScript variable, so the
  value is passed with inner quotes.
