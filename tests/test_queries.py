from datetime import timedelta

from tripwire import queries
from tripwire.queries import Filters

ALL = ("Armed conflict", "Protest & unrest", "Other conflict")


def add(
    conn,
    eid,
    *,
    category="Armed conflict",
    country="UP",
    sources=1,
    geo_type=3,
    hours_ago=0.1,
    lat=None,
    place="Somewhere",
    quality=None,
):
    """Insert one event. By default every event gets its own spot (lat = eid)."""
    conn.execute(
        """
        INSERT INTO events (global_event_id, event_date, date_added, country_code, category,
                            num_sources, geo_type, lat, lon, geo_fullname, source_url, quality_score)
        VALUES (%s, current_date, now() - make_interval(secs => %s), %s, %s, %s, %s,
                %s, 20.5, %s, 'https://example.com/a', %s)
        """,
        (
            eid,
            hours_ago * 3600,
            country,
            category,
            sources,
            geo_type,
            lat or float(eid),
            place,
            quality,
        ),
    )
    conn.commit()


def ids(df):
    return set(df["global_event_id"])


def test_time_window(conn):
    add(conn, 1, hours_ago=2)
    add(conn, 2, hours_ago=30)
    assert ids(queries.map_events(conn, Filters(24, ALL))) == {1}
    assert ids(queries.map_events(conn, Filters(168, ALL))) == {1, 2}


def test_category_filter_and_counts(conn):
    add(conn, 1, category="Armed conflict")
    add(conn, 2, category="Protest & unrest")
    add(conn, 3, category="Protest & unrest")
    f = Filters(24, ("Protest & unrest",))
    assert ids(queries.map_events(conn, f)) == {2, 3}
    assert queries.category_counts(conn, Filters(24, ALL)) == {
        "Armed conflict": 1,
        "Protest & unrest": 2,
    }
    assert queries.map_events(conn, Filters(24, ())).empty  # no category selected -> nothing


def test_country_filter(conn):
    add(conn, 1, country="UP")
    add(conn, 2, country="IS")
    assert ids(queries.map_events(conn, Filters(24, ALL, countries=("IS",)))) == {2}
    assert ids(queries.map_events(conn, Filters(24, ALL))) == {1, 2}


def test_min_sources(conn):
    add(conn, 1, sources=1)
    add(conn, 2, sources=4)
    assert ids(queries.map_events(conn, Filters(24, ALL, min_sources=3))) == {2}


def test_country_centroids_hidden_by_default(conn):
    add(conn, 1, geo_type=1)
    add(conn, 2, geo_type=2)
    assert ids(queries.map_events(conn, Filters(24, ALL))) == {2}
    assert ids(queries.map_events(conn, Filters(24, ALL, min_geo_type=1))) == {1, 2}


def test_events_at_the_same_spot_become_one_dot(conn):
    # three events at one place (two Armed conflict, one Protest) + one elsewhere
    add(conn, 1, sources=2, lat=5.0, place="Kyiv")
    add(conn, 2, sources=7, lat=5.0, place="Kyiv")
    add(conn, 3, sources=1, lat=5.0, place="Kyiv", category="Protest & unrest")
    add(conn, 4, sources=1, lat=9.0, place="Lviv")
    pts = queries.map_events(conn, Filters(24, ALL)).set_index(["lat", "category"])
    assert len(pts) == 3  # (5, Armed), (5, Protest), (9, Armed): one dot each
    kyiv = pts.loc[(5.0, "Armed conflict")]
    assert (kyiv["n_events"], kyiv["num_sources"], kyiv["global_event_id"]) == (2, 7, 2)
    assert queries.category_counts(conn, Filters(24, ALL)) == {  # counts still count events
        "Armed conflict": 3,
        "Protest & unrest": 1,
    }


def test_cap_keeps_best_sourced_places(conn):
    for i, s in enumerate([1, 5, 3], start=1):
        add(conn, i, sources=s)
    assert ids(queries.map_events(conn, Filters(24, ALL), limit=2)) == {2, 3}


def test_hostile_filter_values_are_data_not_sql(conn):
    add(conn, 1)
    evil = "x'; DROP TABLE events; --"
    assert queries.map_events(conn, Filters(24, (evil,), countries=(evil,))).empty
    assert queries.latest_update(conn) is not None  # table still there


def test_latest_update_is_the_newest_event(conn):
    assert queries.latest_update(conn) is None
    add(conn, 1, hours_ago=5)
    add(conn, 2, hours_ago=2)
    newest = queries.latest_update(conn)
    assert (
        timedelta(hours=1.9)
        < conn.execute("SELECT now()").fetchone()[0] - newest
        < timedelta(hours=2.1)
    )


def test_event_detail_returns_the_requested_event(conn):
    add(conn, 7, country="UP", place="Kyiv")
    add(conn, 8, country="IS", place="Haifa")
    assert queries.event_detail(conn, 8)["geo_fullname"] == "Haifa"
    assert queries.event_detail(conn, 12345) is None


def test_country_options_respect_window_and_skip_null(conn):
    add(conn, 1, country="UP")
    add(conn, 2, country="UP")
    add(conn, 3, country="IS")
    add(conn, 4, country="GM", hours_ago=30)
    add(conn, 5, country=None)
    assert queries.country_options(conn, 24) == [("UP", 2), ("IS", 1)]
    assert ("GM", 1) in queries.country_options(conn, 168)


def test_table_events_filters_and_orders_by_sources(conn):
    for i, (s, cat) in enumerate(
        [
            (1, "Armed conflict"),
            (5, "Armed conflict"),
            (3, "Other conflict"),
            (4, "Armed conflict"),
        ],
        start=1,
    ):
        add(conn, i, sources=s, category=cat)
    f = Filters(24, ("Armed conflict",))
    assert list(queries.table_events(conn, f)["num_sources"]) == [
        5,
        4,
        1,
    ]  # Other conflict excluded
    assert len(queries.table_events(conn, f, limit=2)) == 2


def test_times_are_utc_even_if_the_session_is_not(conn):
    add(conn, 1)
    expected = conn.execute(
        "SELECT to_char(date_added AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI') FROM events"
    ).fetchone()[0]
    conn.execute("SET TIME ZONE 'America/New_York'")
    added = queries.map_events(conn, Filters(24, ALL)).iloc[0]["added"]
    assert added == expected  # still the UTC wall-clock time, not New York time


def test_spike_days_and_alerts(conn):
    for day, cc, z in [
        ("2026-10-01", "UP", 5.0),
        ("2026-10-02", "UP", 4.0),
        ("2026-10-02", "IS", 9.0),
    ]:
        conn.execute(
            "INSERT INTO spikes (country_code, category, day, count, baseline_median, baseline_mad, z)"
            " VALUES (%s, 'Armed conflict', %s, 20, 2, 1, %s)",
            (cc, day, z),
        )
    conn.commit()
    days = queries.spike_days(conn)
    assert [str(d) for d in days] == ["2026-10-02", "2026-10-01"]  # newest first
    alerts = queries.spike_alerts(conn, days[0])
    assert list(alerts["country_code"]) == ["IS", "UP"]  # highest score first
    assert list(alerts["ongoing"]) == [False, True]  # UP was also flagged the day before
    assert queries.spike_alerts(conn, "2026-09-01").empty


def test_quality_filter_hides_low_scores_but_keeps_unscored(conn):
    add(conn, 1, quality=0.9)
    add(conn, 2, quality=0.2)
    add(conn, 3, quality=None)  # not scored yet: we cannot call it low quality
    assert ids(queries.map_events(conn, Filters(24, ALL))) == {1, 2, 3}  # off by default
    assert ids(queries.map_events(conn, Filters(24, ALL, min_quality=0.5))) == {1, 3}
    assert ids(queries.map_events(conn, Filters(24, ALL, min_quality=0.2))) == {
        1,
        2,
        3,
    }  # inclusive
    assert queries.category_counts(conn, Filters(24, ALL, min_quality=0.5)) == {"Armed conflict": 2}


def test_table_includes_the_quality_score(conn):
    add(conn, 1, quality=0.77)
    table = queries.table_events(conn, Filters(24, ALL))
    assert round(float(table.iloc[0]["quality_score"]), 2) == 0.77


def add_article(
    conn, eid, url, *, sources=1, day="2026-10-01", country="UP", category="Armed conflict"
):
    conn.execute(
        "INSERT INTO events (global_event_id, event_date, date_added, country_code, category, num_sources,"
        " source_url, event_code, geo_fullname) VALUES (%s, %s, now(), %s, %s, %s, %s, '190', 'Kyiv')",
        (eid, day, country, category, sources, url),
    )
    conn.commit()


def test_spike_evidence_is_one_row_per_article_best_sourced_first(conn):
    add_article(conn, 1, "https://a.example/x", sources=1)
    add_article(conn, 2, "https://a.example/x", sources=4)  # same article, better-sourced row wins
    add_article(conn, 3, "https://b.example/y", sources=2)
    add_article(conn, 4, None, sources=9)  # no link: cannot be opened, so not evidence
    add_article(conn, 5, "https://c.example/z", sources=9, day="2026-10-02")  # another day
    add_article(conn, 6, "https://d.example/w", sources=9, country="IS")  # another country
    df = queries.spike_evidence(conn, "2026-10-01", "UP", "Armed conflict")
    assert list(df["source_url"]) == ["https://a.example/x", "https://b.example/y"]
    assert list(df["num_sources"]) == [4, 2]
    assert len(queries.spike_evidence(conn, "2026-10-01", "UP", "Armed conflict", limit=1)) == 1
    assert queries.spike_evidence(conn, "2026-10-01", "UP", "Protest & unrest").empty
    assert list(queries.spike_evidence(conn, "2026-10-09", "UP", "Armed conflict").columns) == list(
        df.columns
    )
