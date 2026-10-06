from tripwire import queries
from tripwire.queries import Filters

ALL = ("Armed conflict", "Protest & unrest", "Other conflict")


def add(conn, eid, *, category="Armed conflict", country="UP", sources=1, geo_type=3, hours_ago=1):
    conn.execute(
        """
        INSERT INTO events (global_event_id, event_date, date_added, country_code, category,
                            num_sources, geo_type, lat, lon, geo_fullname, source_url)
        VALUES (%s, current_date, now() - make_interval(hours => %s), %s, %s, %s, %s,
                10.5, 20.5, 'Somewhere', 'https://example.com/a')
        """,
        (eid, hours_ago, country, category, sources, geo_type),
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


def test_cap_keeps_best_sourced_events(conn):
    for i, s in enumerate([1, 5, 3], start=1):
        add(conn, i, sources=s)
    assert ids(queries.map_events(conn, Filters(24, ALL), limit=2)) == {2, 3}


def test_hostile_filter_values_are_data_not_sql(conn):
    add(conn, 1)
    evil = "x'; DROP TABLE events; --"
    assert queries.map_events(conn, Filters(24, (evil,), countries=(evil,))).empty
    assert queries.latest_update(conn) is not None  # table still there


def test_detail_options_and_freshness(conn):
    assert queries.latest_update(conn) is None
    add(conn, 7, country="UP")
    add(conn, 8, country="UP")
    add(conn, 9, country="IS")
    assert queries.event_detail(conn, 7)["country_code"] == "UP"
    assert queries.event_detail(conn, 12345) is None
    assert queries.country_options(conn, 24) == [("UP", 2), ("IS", 1)]
    assert queries.latest_update(conn) is not None
    assert len(queries.table_events(conn, Filters(24, ALL))) == 3
