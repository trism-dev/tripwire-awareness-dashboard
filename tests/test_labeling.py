import os
from pathlib import Path
from urllib.parse import quote

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from tests.test_queries import add
from tripwire import labeling
from tripwire.gdelt.categories import DEFAULT_VISIBLE

PAGE = str(Path(__file__).resolve().parent.parent / "app" / "pages" / "Label.py")


def seed(conn, per_category=3):
    """per_category events in each of the five mission categories."""
    eid = 1
    for category in DEFAULT_VISIBLE:
        for _ in range(per_category):
            add(conn, eid, category=category)
            eid += 1


# ---- logic -----------------------------------------------------------------------------------


def test_categories_take_turns(conn):
    seed(conn)
    seen = []
    for _ in range(5):
        event = labeling.next_event(conn)
        seen.append(event["category"])
        labeling.save_label(conn, event["global_event_id"], 1)
    assert sorted(seen) == sorted(DEFAULT_VISIBLE)  # one of each, no repeats


def test_next_event_is_repeatable_and_skips_labeled_and_skipped(conn):
    seed(conn)
    first = labeling.next_event(conn)
    assert labeling.next_event(conn)["global_event_id"] == first["global_event_id"]  # stable order
    again = labeling.next_event(conn, skipped=[first["global_event_id"]])
    assert again["global_event_id"] != first["global_event_id"]
    labeling.save_label(conn, first["global_event_id"], 0)
    shown = {labeling.next_event(conn)["global_event_id"] for _ in range(3)}
    assert first["global_event_id"] not in shown


def test_old_events_and_other_conflict_are_not_in_the_pool(conn):
    add(conn, 1, hours_ago=24 * 40)  # older than 30 days
    add(conn, 2, category="Other conflict")
    assert labeling.next_event(conn) is None


def test_event_does_not_expose_classifier_features(conn):
    add(conn, 1, sources=9)
    event = labeling.next_event(conn)
    assert not {"num_sources", "num_mentions", "num_articles", "avg_tone", "goldstein"} & set(event)


def test_save_label_changes_an_existing_label_and_counts(conn):
    seed(conn, 1)
    labeling.save_label(conn, 1, 1, "  looks real ")
    labeling.save_label(conn, 2, 0)
    assert labeling.progress(conn) == (2, 1)
    labeling.save_label(conn, 2, 1)  # changed my mind: same row, new value
    assert labeling.progress(conn) == (2, 2)
    assert (
        conn.execute("SELECT note FROM labels WHERE global_event_id = 1").fetchone()[0]
        == "looks real"
    )


def test_label_must_be_0_or_1(conn):
    add(conn, 1)
    with pytest.raises(ValueError):
        labeling.save_label(conn, 1, 2)


def test_undo_removes_the_latest_label_only(conn):
    seed(conn, 1)
    labeling.save_label(conn, 1, 1)
    labeling.save_label(conn, 2, 0)
    assert labeling.undo_last(conn) == 2
    assert labeling.progress(conn) == (1, 1)
    assert labeling.undo_last(conn) == 1
    assert labeling.undo_last(conn) is None  # nothing left


# ---- the page --------------------------------------------------------------------------------


@pytest.fixture
def page_env(conn, monkeypatch):
    schema = conn.execute("SELECT current_schema()").fetchone()[0]
    url = os.environ["TEST_DATABASE_URL"]
    sep = "&" if "?" in url else "?"
    monkeypatch.setenv("DATABASE_URL", f"{url}{sep}options={quote(f'-c search_path={schema}')}")
    st.cache_data.clear()


def run_page():
    return AppTest.from_file(PAGE, default_timeout=30).run()


def button(at, label):
    return next(b for b in at.button if b.label == label)


def test_page_is_off_unless_enabled(page_env, monkeypatch):
    monkeypatch.delenv("ENABLE_LABELING", raising=False)
    at = run_page()
    assert any("switched off" in w.value for w in at.warning)
    assert len(at.button) == 0  # no way to write labels


def test_page_shows_the_event_and_hides_the_model_features(conn, page_env, monkeypatch):
    monkeypatch.setenv("ENABLE_LABELING", "1")
    add(conn, 1, sources=7, place="Kyiv")
    at = run_page()
    assert not at.exception
    text = " ".join(t.value for t in at.text)
    assert "Kyiv" in text and "Armed conflict" in text
    assert "source" not in text.lower() and "tone" not in text.lower()  # model features hidden
    assert [b.label for b in at.button] == ["Credible", "Not credible", "Skip"]


def test_clicking_credible_saves_the_label_and_shows_the_next_event(conn, page_env, monkeypatch):
    monkeypatch.setenv("ENABLE_LABELING", "1")
    seed(conn, 1)
    at = run_page()
    first_text = " ".join(t.value for t in at.text)
    at.text_input[0].set_value("clearly an attack")
    button(at, "Credible").click().run()
    assert labeling.progress(conn) == (1, 1)
    assert conn.execute("SELECT note FROM labels").fetchone()[0] == "clearly an attack"
    assert " ".join(t.value for t in at.text) != first_text  # a different event is on screen
    button(at, "Undo last label").click().run()
    assert labeling.progress(conn) == (0, 0)
    assert " ".join(t.value for t in at.text) == first_text  # the undone event is back


def test_skip_does_not_write_a_label(conn, page_env, monkeypatch):
    monkeypatch.setenv("ENABLE_LABELING", "1")
    seed(conn, 1)
    at = run_page()
    button(at, "Skip").click().run()
    assert labeling.progress(conn) == (0, 0)
    assert not at.exception
