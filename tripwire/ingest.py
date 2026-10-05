"""Ingestion: turn parsed GDELT rows into `events` rows and upsert them."""

import pandas as pd
import psycopg

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
