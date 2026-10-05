# Data notes

## Post-filter volume (measured 2026-10-05, 93-file / ~1 day backfill + 1 live file)
| Measure | Value |
|---|---|
| Files ingested | 94 (all ok) |
| Raw rows | 97,899 |
| Kept after filter (QuadClass 3/4, coords, root events) | 13,138 (13.4%) |
| Of kept: country-centroid (geo_type 1) / city-or-finer (geo_type 2+) | 2,636 / 10,502 |
| Median `num_sources` | 1 (mean 1.1) |
| `events` table size incl. indexes | about 5 MB per day |

Projection for 30 days: about 390k rows and about 150 MB. That fits a hosted Postgres; no region allowlist needed yet.

Observations
- Most kept events are single-source (median 1), so a "minimum sources" filter above 1 will cut the map sharply. This is the case for the quality score (S1).
- "Other conflict" is the biggest category (5,036 of 13,138) and is hidden by default. "Mass violence" is very rare (10 in a day), so its spike floor of 10 will almost never be met at country level.
- Backfill speed: 93 files in 83 s with a 0.5 s pause, so 30 days (about 2,900 files) takes about 45 min.
- GDELT can skip slots. A 404 is logged as `missing` and not retried.
