"""Dashboard page tests: the page runs end to end against a throwaway database schema."""

import os
from pathlib import Path
from urllib.parse import quote

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app.Home import age_text, prepare_points, safe_url
from tests.test_queries import add

APP = str(Path(__file__).resolve().parent.parent / "app" / "Home.py")


def point_app_at(url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url)
    st.cache_data.clear()  # the app caches query results for 60 s; start each test clean


@pytest.fixture
def app_env(conn, monkeypatch):
    """Point the app at the test schema (DATABASE_URL = test URL + search_path option)."""
    schema = conn.execute("SELECT current_schema()").fetchone()[0]
    url = os.environ["TEST_DATABASE_URL"]
    sep = "&" if "?" in url else "?"
    point_app_at(f"{url}{sep}options={quote(f'-c search_path={schema}')}", monkeypatch)


def run_app():
    return AppTest.from_file(APP, default_timeout=30).run()


def metrics(at):
    return {m.label: m.value for m in at.metric}


def widget(at, kind, label):
    return next(w for w in getattr(at.sidebar, kind) if w.label == label)


def test_empty_database_shows_helpful_message(conn, app_env):
    at = run_app()
    assert not at.exception
    assert any("No data yet" in i.value for i in at.info)


def test_unreachable_database_shows_fixed_message_without_details(monkeypatch):
    point_app_at(
        "postgresql://tripwire:tripwire@127.0.0.1:1/tripwire?connect_timeout=2", monkeypatch
    )
    at = run_app()
    assert [e.value for e in at.error] == ["Cannot reach the database. Is it running? (make up)"]


def test_page_renders_header_legend_and_attribution(conn, app_env):
    add(conn, 1, category="Armed conflict", sources=3, hours_ago=0)
    add(conn, 2, category="Protest & unrest", hours_ago=0)
    at = run_app()
    assert not at.exception
    assert metrics(at)["Events in view"] == "2"
    assert metrics(at)["Places on map"] == "2"
    assert metrics(at)["Last GDELT update"] == "0 min ago"
    assert not at.warning  # fresh data: no stale-data warning
    assert any("Armed conflict" in m.value for m in at.sidebar.markdown)
    assert any("gdeltproject.org" in m.value for m in at.markdown)  # attribution (PRD M8)


def test_stale_data_shows_warning(conn, app_env):
    add(conn, 1, hours_ago=3)
    at = run_app()
    assert metrics(at)["Last GDELT update"] == "3 h ago"
    assert any("Data is 3 h ago" in w.value for w in at.warning)


def test_events_at_one_spot_count_as_events_but_draw_one_place(conn, app_env):
    add(conn, 1, lat=5.0)
    add(conn, 2, lat=5.0)
    at = run_app()
    assert (metrics(at)["Events in view"], metrics(at)["Places on map"]) == ("2", "1")


def test_min_sources_filter(conn, app_env):
    add(conn, 1, sources=1)
    add(conn, 2, sources=5)
    at = run_app()
    assert metrics(at)["Events in view"] == "2"
    widget(at, "slider", "Minimum sources").set_value(3).run()
    assert metrics(at)["Events in view"] == "1"


def test_time_window_filter(conn, app_env):
    add(conn, 1, hours_ago=2)
    add(conn, 2, hours_ago=30)
    at = run_app()
    assert metrics(at)["Events in view"] == "1"
    widget(at, "selectbox", "Time window").select("Last 7 days").run()
    assert metrics(at)["Events in view"] == "2"


def test_country_filter(conn, app_env):
    add(conn, 1, country="UP")
    add(conn, 2, country="IS")
    at = run_app()
    widget(at, "multiselect", "Countries").set_value(["IS"]).run()
    assert metrics(at)["Events in view"] == "1"


def test_other_conflict_is_hidden_until_selected(conn, app_env):
    add(conn, 1, category="Armed conflict")
    add(conn, 2, category="Other conflict")
    at = run_app()
    assert metrics(at)["Events in view"] == "1"
    cats = widget(at, "multiselect", "Categories")
    cats.set_value([*cats.value, "Other conflict"]).run()
    assert metrics(at)["Events in view"] == "2"


def test_no_matching_events_message(conn, app_env):
    add(conn, 1, sources=1)
    at = run_app()
    widget(at, "slider", "Minimum sources").set_value(10).run()
    infos = [i.value for i in at.info]
    assert "No events match these filters. Try a longer window or fewer filters." in infos


def add_spike(conn, cc, category, count, z, mad=1.0, day="today"):
    conn.execute(
        "INSERT INTO spikes (country_code, category, day, count, baseline_median, baseline_mad, z)"
        " VALUES (%s, %s, CASE WHEN %s = 'today' THEN current_date ELSE %s::date END, %s, 2, %s, %s)",
        (cc, category, day, day, count, mad, z),
    )
    conn.commit()


def alerts_table(at):
    return next(d.value for d in at.dataframe if "Score" in d.value.columns)


def test_alerts_tab_lists_spikes_highest_score_first(conn, app_env):
    add(conn, 1)
    add_spike(conn, "UP", "Armed conflict", count=30, z=6.0)
    add_spike(conn, "IS", "Protest & unrest", count=12, z=9.5, mad=0.0)
    at = run_app()
    assert not at.exception
    table = alerts_table(at)
    assert list(table["Country"]) == ["Israel", "Ukraine"]
    assert list(table["Rule"]) == ["quiet baseline", "normal"]
    assert list(table["Score"]) == [9.5, 6.0]


def test_alerts_can_be_ranked_by_event_count(conn, app_env):
    add(conn, 1)
    add_spike(conn, "UP", "Armed conflict", count=30, z=6.0)
    add_spike(conn, "IS", "Protest & unrest", count=12, z=9.5)
    at = run_app()
    at.radio[0].set_value("Event count").run()
    assert list(alerts_table(at)["Country"]) == ["Ukraine", "Israel"]


def test_alerts_follow_the_sidebar_filters(conn, app_env):
    add(conn, 1)
    add_spike(conn, "UP", "Armed conflict", count=30, z=6.0)
    add_spike(conn, "IS", "Protest & unrest", count=12, z=9.5)
    at = run_app()
    widget(at, "multiselect", "Countries").set_value(["UP"]).run()
    assert list(alerts_table(at)["Country"]) == ["Ukraine"]


def test_no_spikes_yet_message(conn, app_env):
    add(conn, 1)
    at = run_app()
    assert any("No spikes yet" in i.value for i in at.info)


def test_trend_tab_renders_for_the_busiest_country(conn, app_env):
    add(conn, 1)
    at = run_app()
    assert not at.exception
    assert [s.label for s in at.selectbox if s.label in ("Country", "Category")] == [
        "Country",
        "Category",
    ]


# ---- helpers imported from the page ------------------------------------------------------------


def test_safe_url_only_allows_http_and_https():
    assert safe_url("https://example.com/a") == "https://example.com/a"
    assert safe_url("http://example.com/a") == "http://example.com/a"
    for bad in ["javascript:alert(1)", "data:text/html,x", "ftp://x", "", None, 42]:
        assert safe_url(bad) is None


def test_age_text():
    assert age_text(5) == "5 min ago"
    assert age_text(119) == "119 min ago"
    assert age_text(180) == "3 h ago"


def test_prepare_points_size_colour_and_draw_order():
    import pandas as pd

    pts = pd.DataFrame(
        {
            "category": ["Armed conflict"] * 3 + ["Mass violence"],
            "num_sources": [1, 4, 400, None],
            "country_code": ["UP"] * 4,
        }
    )
    light = prepare_points(pts, dark=False)
    assert light.iloc[-1]["category"] == "Mass violence"  # rarest category is drawn last (on top)
    assert light["radius"].max() == 14  # big events are capped
    assert light["radius"].min() == 4  # 1 source -> 2.5 + 1.5 * sqrt(1)
    assert list(light.iloc[0]["color"][:3]) != list(
        prepare_points(pts, dark=True).iloc[0]["color"][:3]
    )
