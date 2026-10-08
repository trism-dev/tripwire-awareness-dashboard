"""Logic behind the labeling page (PRD S2): pick the next event, save a label, undo, progress.

The label question: "Is this record a real event of the coded type at roughly the coded place?"
1 = credible, 0 = not credible. Plain SQL, no page code, so it can be tested.
"""

import psycopg
from psycopg.rows import dict_row

from tripwire.gdelt.categories import DEFAULT_VISIBLE

TARGET = 300  # how many labels the PRD asks for
POOL_DAYS = 30  # label recent events: they are what the classifier will score
SEED = "tripwire-labels-1"  # fixes the "random" order, so everyone gets the same queue

# Only what the labeler needs to judge the record. Deliberately NOT num_sources, tone or Goldstein:
# those are classifier inputs, and seeing them would bias the labels toward the model's own features.
_FIELDS = """global_event_id, category, event_code, actor1_name, actor1_country, actor2_name,
             actor2_country, geo_fullname, country_code, event_date, source_url"""


def progress(conn: psycopg.Connection) -> tuple[int, int]:
    """(labels so far, how many of them are credible)."""
    total, credible = conn.execute(
        "SELECT count(*), count(*) FILTER (WHERE label = 1) FROM labels"
    ).fetchone()
    return total, credible


def event_for_labeling(conn: psycopg.Connection, event_id: int) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_FIELDS} FROM events WHERE global_event_id = %s", (event_id,))
        return cur.fetchone()


def next_event(conn: psycopg.Connection, skipped: list[int] | tuple[int, ...] = ()) -> dict | None:
    """The next unlabeled event, or None if the pool is empty.

    Categories take turns (so the sample is balanced), and inside a category the order is a fixed
    pseudo-random shuffle: md5 of the event id plus SEED. No new table is needed to remember it.
    """
    done, _ = progress(conn)
    for step in range(len(DEFAULT_VISIBLE)):
        category = DEFAULT_VISIBLE[(done + step) % len(DEFAULT_VISIBLE)]  # skip a dry category
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT {_FIELDS} FROM events
                WHERE category = %s
                  AND date_added >= now() - make_interval(days => %s)
                  AND global_event_id NOT IN (SELECT global_event_id FROM labels)
                  AND global_event_id <> ALL(%s)
                ORDER BY md5(global_event_id::text || %s)
                LIMIT 1
                """,
                (category, POOL_DAYS, list(skipped), SEED),
            )
            row = cur.fetchone()
        if row:
            return row
    return None


def save_label(conn: psycopg.Connection, event_id: int, label: int, note: str = "") -> None:
    """Store (or change) a label. 1 = credible, 0 = not credible."""
    if label not in (0, 1):
        raise ValueError("label must be 0 or 1")
    conn.execute(
        """
        INSERT INTO labels (global_event_id, label, note, labeled_at)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (global_event_id) DO UPDATE
            SET label = EXCLUDED.label, note = EXCLUDED.note, labeled_at = now()
        """,
        (event_id, label, note.strip() or None),
    )
    conn.commit()


def undo_last(conn: psycopg.Connection) -> int | None:
    """Delete the most recent label and return its event id (None if there are no labels)."""
    row = conn.execute(
        "DELETE FROM labels WHERE global_event_id = ("
        " SELECT global_event_id FROM labels ORDER BY labeled_at DESC, global_event_id DESC LIMIT 1)"
        " RETURNING global_event_id"
    ).fetchone()
    conn.commit()
    return row[0] if row else None
