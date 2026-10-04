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
