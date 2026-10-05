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
