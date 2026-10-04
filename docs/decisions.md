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
