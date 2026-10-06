"""Smoke tests: the dashboard page runs end to end against a throwaway database schema."""

from pathlib import Path
from urllib.parse import quote

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests.test_queries import add

APP = str(Path(__file__).resolve().parent.parent / "app" / "Home.py")


@pytest.fixture
def app_env(conn, monkeypatch):
    """Point the app at the test schema (DATABASE_URL = test URL + search_path option)."""
    schema = conn.execute("SELECT current_schema()").fetchone()[0]
    import os

    url = os.environ["TEST_DATABASE_URL"]
    sep = "&" if "?" in url else "?"
    monkeypatch.setenv("DATABASE_URL", f"{url}{sep}options={quote(f'-c search_path={schema}')}")
    st.cache_data.clear()  # the app caches query results for 60 s; start each test clean


def run_app():
    return AppTest.from_file(APP, default_timeout=30).run()


def test_empty_database_shows_helpful_message(conn, app_env):
    at = run_app()
    assert not at.exception
    assert any("No data yet" in i.value for i in at.info)


def test_page_renders_header_legend_and_footer(conn, app_env):
    add(conn, 1, category="Armed conflict", sources=3)
    add(conn, 2, category="Protest & unrest")
    at = run_app()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Events in view"] == "2"
    assert metrics["Last GDELT update"].endswith("min ago")
    assert any("Armed conflict" in m.value for m in at.sidebar.markdown)
    footer = " ".join(c.value for c in at.caption)
    assert "gdeltproject.org" in footer  # attribution is required (PRD M8)


def test_filters_change_the_count(conn, app_env):
    add(conn, 1, sources=1)
    add(conn, 2, sources=5)
    at = run_app()
    assert {m.label: m.value for m in at.metric}["Events in view"] == "2"
    at.sidebar.slider[0].set_value(3).run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Events in view"] == "1"


def test_no_matching_events_message(conn, app_env):
    add(conn, 1, sources=1)
    at = run_app()
    at.sidebar.slider[0].set_value(10).run()
    assert not at.exception
    assert any("No events match" in i.value for i in at.info)
