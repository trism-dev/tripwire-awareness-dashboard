"""Read-only SQL for the dashboard. Every query is parameterized; filters never touch the SQL text."""

from dataclasses import dataclass

import pandas as pd
import psycopg
from psycopg.rows import dict_row

MAP_LIMIT = 20_000  # most dots (places) the map will draw
EXPORT_LIMIT = 100_000  # most events one CSV download will contain


@dataclass(frozen=True)
class Filters:
    """What the analyst has selected. Frozen + tuples so Streamlit can cache on it."""

    hours: int
    categories: tuple[str, ...]
    countries: tuple[str, ...] = ()  # FIPS codes; empty means all countries
    min_sources: int = 1
    min_geo_type: int = 2  # 1 = country centroid only, hidden from the map by default (PRD 5.2)
    min_quality: float = 0.0  # 0 = no quality filter; otherwise hide events scoring below this


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
    if f.min_quality > 0:
        # an event the model has not scored yet is kept: we cannot call it low quality
        clauses.append("(quality_score IS NULL OR quality_score >= %s)")
        params.append(f.min_quality)
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
    """One row per place + category, because GDELT puts many events on exactly the same point.

    Drawing every event would stack dots invisibly and send ~6x more data to the browser.
    global_event_id is the best-sourced event at that spot (what a click opens); n_events says
    how many events the dot stands for. Best-sourced places first if capped.
    """
    where, params = _where(f)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT lat, lon, category,
                   count(*) AS n_events,
                   max(num_sources) AS num_sources,
                   (array_agg(global_event_id
                              ORDER BY num_sources DESC NULLS LAST, date_added DESC, global_event_id))[1]
                       AS global_event_id,
                   min(country_code) AS country_code,
                   min(geo_fullname) AS geo_fullname,
                   to_char(max(date_added) AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI') AS added
            FROM events WHERE {where}
            GROUP BY lat, lon, category
            ORDER BY max(num_sources) DESC NULLS LAST, lat, lon, category
            LIMIT %s
            """,
            [*params, limit],
        )
        columns = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)


def table_events(conn: psycopg.Connection, f: Filters, limit: int = 500) -> pd.DataFrame:
    """Richer rows for the Events table tab: best-sourced first."""
    where, params = _where(f)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT date_added, category, country_code, geo_fullname, actor1_name, actor2_name,
                   event_code, num_sources, goldstein, avg_tone, quality_score, source_url
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


def spike_days(conn: psycopg.Connection, limit: int = 7) -> list:
    """Days that have stored spikes, newest first."""
    rows = conn.execute("SELECT DISTINCT day FROM spikes ORDER BY day DESC LIMIT %s", (limit,))
    return [r[0] for r in rows.fetchall()]


ONGOING_DAYS = 3  # a spike is "ongoing" if the same country and category was flagged this recently


def spike_alerts(conn: psycopg.Connection, day) -> pd.DataFrame:
    """The spikes stored for one day, highest score first, with the numbers behind each one.

    `ongoing` is true when the same country and category was also flagged on any of the previous
    ONGOING_DAYS days: usually the same story continuing, not a new one (see docs/evaluation.md).
    """
    columns = [
        "country_code",
        "category",
        "count",
        "baseline_median",
        "baseline_mad",
        "z",
        "ongoing",
    ]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT s.country_code, s.category, s.count, s.baseline_median, s.baseline_mad, s.z,
                   EXISTS (
                       SELECT 1 FROM spikes p
                       WHERE p.country_code = s.country_code AND p.category = s.category
                         AND p.day BETWEEN s.day - %s AND s.day - 1
                   ) AS ongoing
            FROM spikes s WHERE s.day = %s ORDER BY s.z DESC, s.country_code, s.category
            """,
            (ONGOING_DAYS, day),
        )
        return pd.DataFrame(cur.fetchall(), columns=columns)


def export_events(conn: psycopg.Connection, f: Filters, limit: int = EXPORT_LIMIT) -> pd.DataFrame:
    """Every event in the current view (not grouped into dots), newest first, for the CSV."""
    where, params = _where(f)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT global_event_id, date_added, event_date, category, country_code, geo_fullname,
                   lat, lon, actor1_name, actor1_country, actor2_name, actor2_country, event_code,
                   num_sources, num_articles, goldstein, avg_tone, quality_score, source_url
            FROM events WHERE {where}
            ORDER BY date_added DESC, global_event_id LIMIT %s
            """,
            [*params, limit],
        )
        columns = [c.name for c in cur.description]  # keeps the headers even with no rows
        return pd.DataFrame(cur.fetchall(), columns=columns)


def spike_evidence(
    conn: psycopg.Connection, day, country: str, category: str, limit: int = 8
) -> pd.DataFrame:
    """The distinct articles behind one spike, best-sourced first, with how each was coded.

    One row per article (a source URL can carry several event rows; the best-sourced one is shown).
    This is the evidence an analyst opens to confirm or reject an alert.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT * FROM (
                SELECT DISTINCT ON (source_url)
                       source_url, event_code, actor1_name, actor2_name, geo_fullname,
                       num_sources, quality_score
                FROM events
                WHERE country_code = %s AND category = %s AND event_date = %s
                  AND source_url IS NOT NULL
                ORDER BY source_url, num_sources DESC NULLS LAST, global_event_id
            ) best
            ORDER BY num_sources DESC NULLS LAST, source_url
            LIMIT %s
            """,
            (country, category, day, limit),
        )
        columns = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)
