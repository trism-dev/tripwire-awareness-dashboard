"""Keep the database small enough for hosting: delete old events, but never hand-labeled ones."""

import psycopg


def purge(conn: psycopg.Connection, days: int, batch: int = 20_000) -> int:
    """Delete events older than `days` days that nobody has labeled; returns how many.

    Labeled events are the classifier's training data and `labels` is deleted along with its
    event, so they must be skipped here. Deleting in batches keeps each transaction short, so the
    dashboard and the ingestion worker are never blocked for long. The ingestion ledger gets the
    same cut-off (re-running a very old backfill would simply download those files again).
    """
    total = 0
    while True:
        deleted = conn.execute(
            """
            DELETE FROM events WHERE global_event_id IN (
                SELECT e.global_event_id FROM events e
                WHERE e.date_added < now() - make_interval(days => %s)
                  AND NOT EXISTS (SELECT 1 FROM labels l WHERE l.global_event_id = e.global_event_id)
                LIMIT %s)
            """,
            (days, batch),
        ).rowcount
        conn.commit()
        total += deleted
        if deleted < batch:
            break
    conn.execute(
        "DELETE FROM ingest_files WHERE processed_at < now() - make_interval(days => %s)", (days,)
    )
    conn.commit()
    return total
