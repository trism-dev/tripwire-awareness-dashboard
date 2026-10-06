"""Read-only SQL for the dashboard. Every query is parameterized; filters never touch the SQL text."""

from dataclasses import dataclass

import pandas as pd
import psycopg
from psycopg.rows import dict_row

MAP_LIMIT = 50_000  # most points the map will draw; keeps the page fast


@dataclass(frozen=True)
class Filters:
    """What the analyst has selected. Frozen + tuples so Streamlit can cache on it."""

    hours: int
    categories: tuple[str, ...]
    countries: tuple[str, ...] = ()  # FIPS codes; empty means all countries
    min_sources: int = 1
    min_geo_type: int = 2  # 1 = country centroid only, hidden from the map by default (PRD 5.2)


def _where(f: Filters) -> tuple[str, list]:
    clauses = [
        "date_added >= now() - make_interval(hours => %s)",
        "category = ANY(%s)",
        "num_sources >= %s",
        "geo_type >= %s",
    ]
    params: list = [f.hours, list(f.categories), f.min_sources, f.min_geo_type]
    if f.countries:
        clauses.append("country_code = ANY(%s)")
        params.append(list(f.countries))
    return " AND ".join(clauses), params


def latest_update(conn: psycopg.Connection):
    """Newest GDELT timestamp we hold (UTC), or None for an empty database."""
    return conn.execute("SELECT max(date_added) FROM events").fetchone()[0]


def country_options(conn: psycopg.Connection, hours: int) -> list[tuple[str, int]]:
    """(FIPS code, event count) for countries with events in the window, busiest first."""
    return conn.execute(
        """
        SELECT country_code, count(*) FROM events
        WHERE date_added >= now() - make_interval(hours => %s) AND country_code IS NOT NULL
        GROUP BY 1 ORDER BY 2 DESC, 1
        """,
        (hours,),
    ).fetchall()


def category_counts(conn: psycopg.Connection, f: Filters) -> dict[str, int]:
    """Events in view per category. Their sum is the 'events in view' number."""
    where, params = _where(f)
    rows = conn.execute(f"SELECT category, count(*) FROM events WHERE {where} GROUP BY 1", params)
    return dict(rows.fetchall())


def map_events(conn: psycopg.Connection, f: Filters, limit: int = MAP_LIMIT) -> pd.DataFrame:
    """Just the columns needed to draw and label a point. Best-sourced events first if capped."""
    where, params = _where(f)
    cols = [
        "global_event_id",
        "lat",
        "lon",
        "category",
        "num_sources",
        "country_code",
        "geo_fullname",
        "to_char(date_added AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI') AS added",
    ]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {', '.join(cols)} FROM events WHERE {where} "
            "ORDER BY num_sources DESC, date_added DESC LIMIT %s",
            [*params, limit],
        )
        return pd.DataFrame(cur.fetchall(), columns=[*cols[:-1], "added"])


def table_events(conn: psycopg.Connection, f: Filters, limit: int = 500) -> pd.DataFrame:
    """Richer rows for the Events table tab: best-sourced first."""
    where, params = _where(f)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT date_added, category, country_code, geo_fullname, actor1_name, actor2_name,
                   event_code, num_sources, goldstein, avg_tone, source_url
            FROM events WHERE {where}
            ORDER BY num_sources DESC, date_added DESC LIMIT %s
            """,
            [*params, limit],
        )
        return pd.DataFrame(cur.fetchall())


def event_detail(conn: psycopg.Connection, event_id: int) -> dict | None:
    """Every stored field for one event (the detail panel, PRD M5)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM events WHERE global_event_id = %s", (event_id,))
        return cur.fetchone()
