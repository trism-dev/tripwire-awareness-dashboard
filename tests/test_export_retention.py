import io
import re

import pandas as pd

from tests.test_queries import add
from tripwire import queries
from tripwire.export import csv_safe, events_csv
from tripwire.queries import Filters
from tripwire.retention import purge

ALL = ("Armed conflict", "Protest & unrest", "Other conflict")


def read_csv(data: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", keep_default_na=False)


# ---- export ------------------------------------------------------------------------------------


def test_csv_safe_neutralises_spreadsheet_formulas():
    for evil in ['=HYPERLINK("http://x")', "+1+1", "-2+3", "@SUM(A1)", "\tcmd", "\rcmd"]:
        assert csv_safe(evil) == "'" + evil
    assert csv_safe("Kyiv") == "Kyiv"
    assert csv_safe(None) is None
    assert csv_safe(-6.5) == -6.5  # numbers are not text, so a negative score stays a number


def test_export_returns_every_event_in_view_not_just_dots(conn):
    add(conn, 1, lat=5.0)
    add(conn, 2, lat=5.0)  # same spot: one map dot, but two rows in the CSV
    add(conn, 3, hours_ago=30)  # outside the 24 h window
    df = queries.export_events(conn, Filters(24, ALL))
    assert set(df["global_event_id"]) == {1, 2}
    assert len(queries.export_events(conn, Filters(24, ALL), limit=1)) == 1


def test_export_follows_the_filters(conn):
    add(conn, 1, country="UP", quality=0.9)
    add(conn, 2, country="IS", quality=0.9)
    add(conn, 3, country="IS", quality=0.1)
    f = Filters(24, ALL, countries=("IS",), min_quality=0.5)
    assert set(queries.export_events(conn, f)["global_event_id"]) == {2}


def test_events_csv_content_and_safety(conn):
    add(conn, 1, place="=EVIL()", country="UP", sources=3, quality=0.8)
    conn.execute("UPDATE events SET actor1_name = '@actor', event_code = '190', goldstein = -6.5")
    conn.commit()
    data = events_csv(queries.export_events(conn, Filters(24, ALL)))
    assert data.startswith(b"\xef\xbb\xbf")  # byte-order mark, so Excel reads UTF-8
    row = read_csv(data).iloc[0]
    assert row["place"] == "'=EVIL()" and row["actor1"] == "'@actor"  # formulas defused
    assert row["country"] == "Ukraine" and row["country_code"] == "UP"
    assert "military force" in row["event_type"].lower()
    assert (row["sources"], row["goldstein"], row["quality_score"]) == (3, -6.5, 0.8)
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d", row["reported_utc"])  # a UTC timestamp
    assert list(read_csv(data).columns)[:3] == ["global_event_id", "reported_utc", "event_date"]


def test_empty_view_still_gives_a_header_row(conn):
    data = events_csv(queries.export_events(conn, Filters(24, ALL)))
    df = read_csv(data)
    assert df.empty and "source_url" in df.columns


# ---- retention ---------------------------------------------------------------------------------


def count(conn, table="events"):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_purge_deletes_old_events_but_keeps_recent_and_labeled(conn):
    add(conn, 1, hours_ago=24 * 70)  # old, unlabeled -> deleted
    add(conn, 2, hours_ago=24 * 70)  # old, LABELED -> kept (training data)
    add(conn, 3, hours_ago=24 * 59)  # inside the 60-day window -> kept
    add(conn, 4, hours_ago=1)
    conn.execute("INSERT INTO labels (global_event_id, label) VALUES (2, 1)")
    conn.commit()
    assert purge(conn, 60) == 1
    remaining = {r[0] for r in conn.execute("SELECT global_event_id FROM events")}
    assert remaining == {2, 3, 4}
    assert count(conn, "labels") == 1  # the label was not cascaded away


def test_purge_works_in_small_batches(conn):
    for i in range(1, 8):
        add(conn, i, hours_ago=24 * 90)
    assert purge(conn, 60, batch=3) == 7  # three rounds of 3, 3, 1
    assert count(conn) == 0


def test_purge_trims_the_ingestion_ledger_too(conn):
    conn.execute(
        "INSERT INTO ingest_files (file_url, status, processed_at) VALUES"
        " ('old', 'ok', now() - interval '90 days'), ('new', 'ok', now())"
    )
    conn.commit()
    purge(conn, 60)
    assert [r[0] for r in conn.execute("SELECT file_url FROM ingest_files")] == ["new"]


def test_purge_with_nothing_old_deletes_nothing(conn):
    add(conn, 1)
    assert purge(conn, 60) == 0
    assert count(conn) == 1
