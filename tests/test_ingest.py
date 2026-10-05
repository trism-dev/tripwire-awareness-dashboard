import datetime as dt

from tripwire.ingest import EVENT_COLUMNS, to_event_rows, upsert_events


def count(conn):
    return conn.execute("SELECT count(*) FROM events").fetchone()[0]


def test_to_event_rows_shape_and_types(kept_events):
    rows = to_event_rows(kept_events)
    assert len(rows) == 3
    rec = dict(zip(EVENT_COLUMNS, rows[0], strict=True))
    assert rec["global_event_id"] == 1326273973
    assert type(rec["global_event_id"]) is int
    assert rec["is_root_event"] is True
    assert rec["event_root_code"] == "18"
    assert rec["category"] == "Armed conflict"
    assert isinstance(rec["event_date"], dt.date)
    assert rec["date_added"].tzinfo is not None


def test_upsert_inserts_rows(conn, kept_events):
    assert upsert_events(conn, kept_events) == 3
    assert count(conn) == 3


def test_reingesting_same_data_adds_no_rows(conn, kept_events):
    upsert_events(conn, kept_events)
    upsert_events(conn, kept_events)
    assert count(conn) == 3


def test_upsert_updates_changed_fields_and_keeps_quality_score(conn, kept_events):
    upsert_events(conn, kept_events)
    conn.execute("UPDATE events SET quality_score = 0.9")
    conn.commit()
    changed = kept_events.copy()
    changed["NumSources"] = 99
    upsert_events(conn, changed)
    sources, score = conn.execute(
        "SELECT num_sources, quality_score FROM events WHERE global_event_id = 1326273973"
    ).fetchone()
    assert (sources, round(score, 1)) == (99, 0.9)
    assert count(conn) == 3
