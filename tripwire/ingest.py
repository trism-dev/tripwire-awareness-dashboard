"""Ingestion: turn parsed GDELT rows into `events` rows and upsert them."""

import logging
import urllib.error

import pandas as pd
import psycopg

from tripwire.config import load_settings
from tripwire.db import connect
from tripwire.gdelt.categories import add_category
from tripwire.gdelt.fetch import MANIFEST_URL, md5_matches, parse_manifest
from tripwire.gdelt.fetch import download as fetch_download
from tripwire.gdelt.filter import filter_events
from tripwire.gdelt.parse import parse_events

log = logging.getLogger(__name__)

# events column -> GDELT column
_COLUMN_MAP = {
    "global_event_id": "GLOBALEVENTID",
    "date_added": "DATEADDED",
    "actor1_name": "Actor1Name",
    "actor1_country": "Actor1CountryCode",
    "actor2_name": "Actor2Name",
    "actor2_country": "Actor2CountryCode",
    "event_code": "EventCode",
    "event_base_code": "EventBaseCode",
    "event_root_code": "EventRootCode",
    "quad_class": "QuadClass",
    "goldstein": "GoldsteinScale",
    "num_mentions": "NumMentions",
    "num_sources": "NumSources",
    "num_articles": "NumArticles",
    "avg_tone": "AvgTone",
    "geo_type": "ActionGeo_Type",
    "geo_fullname": "ActionGeo_FullName",
    "country_code": "ActionGeo_CountryCode",
    "lat": "ActionGeo_Lat",
    "lon": "ActionGeo_Long",
    "source_url": "SOURCEURL",
    "category": "category",
    "actor1_code": "Actor1Code",
    "actor2_code": "Actor2Code",
    "actor1_type1_code": "Actor1Type1Code",
    "actor2_type1_code": "Actor2Type1Code",
    "actor1_geo_country": "Actor1Geo_CountryCode",
    "actor2_geo_country": "Actor2Geo_CountryCode",
    "action_adm1_code": "ActionGeo_ADM1Code",
}
# event_date and is_root_event are derived, so they are added separately below.
EVENT_COLUMNS = ["event_date", "is_root_event", *_COLUMN_MAP]

# Re-ingesting a row refreshes the GDELT-derived fields. quality_score and ingested_at are kept.
_UPSERT_SQL = f"""
INSERT INTO events ({", ".join(EVENT_COLUMNS)})
VALUES ({", ".join(["%s"] * len(EVENT_COLUMNS))})
ON CONFLICT (global_event_id) DO UPDATE SET
{", ".join(f"{c} = EXCLUDED.{c}" for c in EVENT_COLUMNS if c != "global_event_id")}
"""


def _py(value):
    """pandas/numpy value -> plain Python value (NA/NaN/NaT -> None) that psycopg accepts."""
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value.item() if hasattr(value, "item") else value


def to_event_rows(df: pd.DataFrame) -> list[tuple]:
    """DataFrame (filtered, with a `category` column) -> tuples in EVENT_COLUMNS order."""
    rows = []
    for rec in df.to_dict("records"):
        values = {
            "event_date": rec["SQLDATE"].date() if pd.notna(rec["SQLDATE"]) else None,
            "is_root_event": None if pd.isna(rec["IsRootEvent"]) else rec["IsRootEvent"] == 1,
        }
        values.update({col: rec[src] for col, src in _COLUMN_MAP.items()})
        rows.append(tuple(_py(values[c]) for c in EVENT_COLUMNS))
    return rows


def upsert_events(conn: psycopg.Connection, df: pd.DataFrame) -> int:
    """Insert or update events. Safe to run twice on the same data. Returns rows submitted."""
    rows = to_event_rows(df)
    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, rows)
    conn.commit()
    return len(rows)


# ---- one ingestion cycle ---------------------------------------------------------------------


def _record(conn, url, status, md5=None, rows_raw=None, rows_kept=None, error=None):
    conn.execute(
        """
        INSERT INTO ingest_files (file_url, md5, rows_raw, rows_kept, status, error, processed_at)
        VALUES (%s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (file_url) DO UPDATE SET md5 = EXCLUDED.md5, rows_raw = EXCLUDED.rows_raw,
            rows_kept = EXCLUDED.rows_kept, status = EXCLUDED.status, error = EXCLUDED.error,
            processed_at = now()
        """,
        (url, md5, rows_raw, rows_kept, status, error),
    )
    conn.commit()


def ingest_url(conn, url, md5=None, fetch=fetch_download, settings=None, force=False) -> str:
    """Download, check, parse, filter, categorize and upsert one file.

    Never raises for a bad file: the problem is written to ingest_files and the status is returned
    ('ok', 'skipped', 'missing' or 'error'). Files already ok/missing are not downloaded again,
    unless force=True (used to re-read files after new columns were added).
    """
    settings = settings or load_settings()
    seen = conn.execute("SELECT status FROM ingest_files WHERE file_url = %s", (url,)).fetchone()
    if seen and seen[0] in ("ok", "missing") and not force:
        return "skipped"
    try:
        data = fetch(url)
        if md5 and not md5_matches(data, md5):
            raise ValueError("md5 mismatch")
        df, bad_rows = parse_events(data)
        kept = add_category(filter_events(df, country_allowlist=settings.region_allowlist))
        upsert_events(conn, kept)
        _record(conn, url, "ok", md5, len(df) + bad_rows, len(kept))
        if bad_rows:
            log.warning("%s: %d malformed rows skipped", url, bad_rows)
        return "ok"
    except urllib.error.HTTPError as e:
        conn.rollback()
        if e.code == 404:
            _record(conn, url, "missing", md5, error="404 not found")
            return "missing"
        _record(conn, url, "error", md5, error=f"HTTP {e.code}")
    except Exception as e:
        conn.rollback()
        log.exception("failed to ingest %s", url)
        _record(conn, url, "error", md5, error=f"{type(e).__name__}: {e}"[:500])
    return "error"


def run_cycle(conn, fetch=fetch_download) -> str:
    """Ingest the newest file listed in lastupdate.txt."""
    try:
        url, md5 = parse_manifest(fetch(MANIFEST_URL).decode("utf-8"))
    except Exception:
        log.exception("could not read GDELT manifest")
        return "error"
    return ingest_url(conn, url, md5, fetch)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with connect() as c:
        print(run_cycle(c))
