"""Dashboard page tests: the page runs end to end against a throwaway database schema."""

import os
from pathlib import Path
from urllib.parse import quote

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app.Home import (
    age_text,
    alert_sentence,
    evidence_table,
    map_focus,
    minutes_ago,
    prepare_points,
    quality_text,
    restore_filters,
    safe_url,
    selected_ring,
    short_place,
    url_params,
)
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
    assert list(table["Story"]) == ["new", "new"]
    assert list(table["Score"]) == [9.5, 6.0]


def test_ongoing_stories_are_labelled_and_listed_after_new_ones(conn, app_env):
    from datetime import UTC, datetime, timedelta

    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    add(conn, 1)
    add_spike(conn, "UP", "Armed conflict", count=30, z=9.0, day=yesterday)
    add_spike(conn, "UP", "Armed conflict", count=30, z=9.0)  # same story, a day later
    add_spike(conn, "IS", "Protest & unrest", count=12, z=4.0)  # lower score but new
    table = alerts_table(run_app())
    assert list(table["Country"]) == ["Israel", "Ukraine"]
    assert list(table["Story"]) == ["new", "ongoing"]


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


def test_hide_low_quality_toggle(conn, app_env):
    add(conn, 1, quality=0.85)
    add(conn, 2, quality=0.1)
    at = run_app()
    assert metrics(at)["Events in view"] == "2"
    widget(at, "checkbox", "Hide low-quality events").check().run()
    assert metrics(at)["Events in view"] == "1"  # default minimum 0.4 hides the 0.1 event
    widget(at, "slider", "Minimum quality score").set_value(0.9).run()
    assert metrics(at)["Events in view"] == "0"  # 0.9 is the slider's top: now 0.85 is hidden too


# ---- helpers imported from the page ------------------------------------------------------------


def test_safe_url_only_allows_http_and_https():
    assert safe_url("https://example.com/a") == "https://example.com/a"
    assert safe_url("http://example.com/a") == "http://example.com/a"
    for bad in ["javascript:alert(1)", "data:text/html,x", "ftp://x", "", None, 42]:
        assert safe_url(bad) is None


def test_minutes_ago_is_never_negative_when_the_clock_is_behind():
    from datetime import UTC, datetime, timedelta

    assert minutes_ago(datetime.now(UTC) + timedelta(minutes=7)) == 0
    assert minutes_ago(datetime.now(UTC) - timedelta(minutes=7, seconds=5)) == 7


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


def test_quality_text_wording():
    assert quality_text(None) == "not scored yet"
    assert "likely credible" in quality_text(0.8)
    assert "uncertain" in quality_text(0.5)
    assert "likely not credible" in quality_text(0.1)


def test_evidence_table_shows_how_each_article_was_coded_and_only_safe_links():
    import pandas as pd

    evidence = pd.DataFrame(
        {
            "source_url": ["https://a.example/x", "javascript:alert(1)"],
            "event_code": ["190", None],
            "actor1_name": ["POLICE", None],
            "actor2_name": [None, "CROWD"],
            "geo_fullname": ["Kyiv", "Lviv"],
            "num_sources": [4, 1],
            "quality_score": [0.8123, None],
        }
    )
    shown = evidence_table(evidence)
    assert list(shown.columns) == ["Coded as", "Actors", "Place", "Sources", "Quality", "Article"]
    assert "military force" in shown.iloc[0]["Coded as"].lower()
    assert list(shown["Actors"]) == ["POLICE -> ?", "? -> CROWD"]
    assert shown.iloc[0]["Quality"] == 0.81
    assert shown.iloc[0]["Article"] == "https://a.example/x"
    assert pd.isna(shown.iloc[1]["Article"])  # a javascript: link is never shown as a link
    assert shown.iloc[1]["Coded as"] == "Unknown event type"


def test_alerts_tab_tells_the_user_to_select_a_row_for_evidence(conn, app_env):
    add(conn, 1)
    add_spike(conn, "UP", "Armed conflict", count=30, z=6.0)
    at = run_app()
    assert not at.exception
    assert any("Select a row to see the articles" in c.value for c in at.caption)


def test_short_place_keeps_city_and_country_and_survives_missing_values():
    assert short_place("Dubai, Dubayy, United Arab Emirates", "AE") == "Dubai, United Arab Emirates"
    assert short_place("Ukraine", "UP") == "Ukraine"  # country-level record: no repeated name
    assert short_place(float("nan"), "UP") == "Ukraine"  # pandas gives NaN, which is truthy
    assert short_place(None, "UP") == "Ukraine"


def test_alert_sentence_is_plain_and_handles_a_quiet_baseline():
    from datetime import date

    today = date(2026, 10, 12)
    text = alert_sentence("IZ", "Threats & coercion", 13, 5.0, today, today)
    assert text == "Iraq: 13 articles on threats & coercion so far today; a typical day has 5."
    older = alert_sentence("IZ", "Armed conflict", 21, 2.5, date(2026, 10, 10), today)
    assert "on 2026-10-10" in older and "typical day has 2.5" in older
    assert alert_sentence("IZ", "Armed conflict", 12, 0.0, today, today).endswith(
        "has almost none."
    )


def test_map_focus_sets_filters_and_refuses_days_the_map_does_not_hold():
    from datetime import date

    today = date(2026, 10, 12)
    assert map_focus("IZ", "Armed conflict", today, today) == {
        "countries": ["IZ"],
        "categories": ["Armed conflict"],
        "window": "Last 24 hours",
    }
    assert map_focus("IZ", "Armed conflict", date(2026, 10, 9), today)["window"] == "Last 7 days"
    assert map_focus("IZ", "Armed conflict", date(2026, 10, 1), today) is None


def test_selected_ring_only_for_a_dot_that_is_on_the_map():
    import pandas as pd

    df = pd.DataFrame(
        {"global_event_id": [7, 8], "lon": [1.0, 2.0], "lat": [3.0, 4.0], "radius": [5, 6]}
    )
    clicked = {"selection": {"objects": {"events": [{"global_event_id": 8}]}}}
    assert selected_ring(df, clicked, dark=False) is not None
    gone = {"selection": {"objects": {"events": [{"global_event_id": 99}]}}}
    assert selected_ring(df, gone, dark=False) is None
    assert selected_ring(df, None, dark=False) is None  # before any click
    assert selected_ring(df, {"selection": {"objects": {}}}, dark=False) is None


def test_filters_round_trip_through_the_page_address():
    from tripwire.gdelt.categories import DEFAULT_VISIBLE

    assert (
        url_params("Last 24 hours", list(DEFAULT_VISIBLE), []) == {}
    )  # defaults stay out of the URL
    params = url_params("Last 7 days", ["Armed conflict"], ["UP", "IS"])
    assert params == {"window": "Last 7 days", "categories": "Armed conflict", "countries": "UP,IS"}
    assert restore_filters(params, ["UP", "IS", "IR"]) == {
        "window": "Last 7 days",
        "categories": ["Armed conflict"],
        "countries": ["UP", "IS"],
    }


def test_restore_filters_ignores_anything_it_does_not_recognise():
    junk = {"window": "Last 99 years", "categories": "Nope,<script>", "countries": "ZZ,UP"}
    assert restore_filters(junk, ["UP"]) == {"countries": ["UP"]}
    assert restore_filters({}, ["UP"]) == {}


def test_page_address_sets_the_sidebar(conn, app_env):
    add(conn, 1)
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["window"] = "Last 7 days"
    at.query_params["countries"] = "UP"
    at.run()
    assert not at.exception
    assert widget(at, "selectbox", "Time window").value == "Last 7 days"
    assert widget(at, "multiselect", "Countries").value == ["UP"]
    # Writing the address back is checked in the browser: AppTest does not report it.


def _verdict_form():
    from app.Home import render_verdict

    render_verdict("2026-10-01", "UP", "Armed conflict")


def test_verdict_form_is_only_there_when_labeling_is_enabled(conn, app_env, monkeypatch):
    monkeypatch.delenv("ENABLE_LABELING", raising=False)
    at = AppTest.from_function(_verdict_form, default_timeout=30).run()
    assert not at.exception
    assert len(at.radio) == 0  # nothing to click, nothing can be written

    monkeypatch.setenv("ENABLE_LABELING", "1")
    at = AppTest.from_function(_verdict_form, default_timeout=30).run()
    assert not at.exception
    assert [o for o in at.radio[0].options] == ["Yes", "No", "Unclear"]
    assert at.button[0].disabled  # no verdict chosen yet


def test_verdict_form_saves_the_verdict_and_reason(conn, app_env, monkeypatch):
    monkeypatch.setenv("ENABLE_LABELING", "1")
    at = AppTest.from_function(_verdict_form, default_timeout=30).run()
    at.radio[0].set_value("No").run()
    at.selectbox[0].set_value("misread_type").run()
    at.button[0].click().run()
    assert not at.exception
    row = conn.execute(
        "SELECT day::text, country_code, verdict, reason FROM alert_verdicts"
    ).fetchone()
    assert row == ("2026-10-01", "UP", "No", "misread_type")
    again = AppTest.from_function(_verdict_form, default_timeout=30).run()
    assert again.radio[0].value == "No"  # remembered on reload


def test_top_alerts_sit_above_the_map_new_stories_first(conn, app_env):
    from datetime import UTC, datetime, timedelta

    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    add(conn, 1)
    add_spike(conn, "UP", "Armed conflict", count=30, z=9.0, day=yesterday)
    add_spike(conn, "UP", "Armed conflict", count=30, z=9.0)  # ongoing
    add_spike(conn, "IS", "Protest & unrest", count=12, z=4.0)  # new
    at = run_app()
    assert not at.exception
    sentences = [
        m.value for m in at.markdown if "articles on" in m.value and "so far today" in m.value
    ]
    # the same two sentences also appear in the Alerts tab; the first two are the top-alert cards
    assert sentences[0].startswith("Israel:")
    assert sentences[1].startswith("Ukraine:") and sentences[1].endswith("*(ongoing)*")
    # Only Ukraine has events in the test data, so only its card can offer Show on map.
    assert [b.label for b in at.button].count("Show on map") == 1
