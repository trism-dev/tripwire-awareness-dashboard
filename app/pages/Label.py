"""Labeling tool (PRD S2): judge one event at a time; labels train the signal-quality classifier."""

import os
import sys
from pathlib import Path

# Pages live one level deeper than Home.py, so go up two levels to the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from tripwire import labeling
from tripwire.db import connect
from tripwire.fips import country_name
from tripwire.gdelt.cameo import event_description
from tripwire.web import safe_url

GUIDE = """
**Question:** is this record a *real event* of the *coded type* at *roughly the coded place*?

- **Credible (1):** the article describes a real event of about that type (a protest, an attack,
  a threat, an arrest...) happening in or near that place.
- **Not credible (0):** wrong type (a court case or business story coded as military force), wrong
  place, not an event at all, or an old event being rehashed.
- **Skip:** the link is dead or you cannot tell. Skips are forgotten when you reload the page.

Open the article, read enough to decide, then press a button. Keys: **1** credible, **2** not
credible, **3** skip.
"""


def with_db(function, *args):
    """Run one labeling function on a short-lived connection."""
    with connect() as conn:
        return function(conn, *args)


def finish(label: int | None):
    """Button callback: save the label (or skip) and move on to the next event."""
    event = st.session_state["current"]
    if label is None:
        st.session_state["skipped"].append(event["global_event_id"])
    else:
        with_db(labeling.save_label, event["global_event_id"], label, st.session_state["note"])
    st.session_state["current"] = None
    st.session_state["note"] = ""


def undo():
    undone = with_db(labeling.undo_last)
    # Show the event we just un-labeled again, so it can be re-judged.
    st.session_state["current"] = with_db(labeling.event_for_labeling, undone) if undone else None


def show_event(e: dict):
    # GDELT text is untrusted, so plain st.text only (never markdown or HTML).
    a1 = f"{e['actor1_name'] or 'unspecified'} ({e['actor1_country'] or '-'})"
    a2 = f"{e['actor2_name'] or 'unspecified'} ({e['actor2_country'] or '-'})"
    st.text(f"Category: {e['category']}")
    st.text(f"Coded event type: {event_description(e['event_code'])} (CAMEO {e['event_code']})")
    st.text(f"Actor 1: {a1}")
    st.text(f"Actor 2: {a2}")
    st.text(f"Place: {e['geo_fullname']} - {country_name(e['country_code'])}")
    st.text(f"Event date: {e['event_date']}")
    url = safe_url(e["source_url"])
    if url:
        st.link_button("Open article", url)
    else:
        st.caption("No usable link for this event. Skip it.")


def main():
    st.set_page_config(page_title="Label events - Tripwire", layout="centered")
    st.title("Label events")
    # Anyone who can open this page can write to the database, and there are no user accounts, so
    # it only works where ENABLE_LABELING=1 is set (local use). Leave it unset when hosting.
    if os.environ.get("ENABLE_LABELING") != "1":
        st.warning("Labeling is switched off here. Set ENABLE_LABELING=1 to use it locally.")
        st.stop()

    st.session_state.setdefault("skipped", [])
    st.session_state.setdefault("current", None)
    st.session_state.setdefault("note", "")

    done, credible = with_db(labeling.progress)
    st.progress(min(done / labeling.TARGET, 1.0))
    st.caption(f"{done} / {labeling.TARGET} labeled ({credible} credible, {done - credible} not)")
    with st.expander("How to label", expanded=done < 5):
        st.markdown(GUIDE)

    if st.session_state["current"] is None:
        st.session_state["current"] = with_db(
            labeling.next_event, tuple(st.session_state["skipped"])
        )
    event = st.session_state["current"]
    if event is None:
        st.success("No more events to label in the last 30 days.")
    else:
        show_event(event)
        st.text_input("Note (optional, e.g. 'court case, not fighting')", key="note")
        left, middle, right = st.columns(3)
        left.button("Credible", on_click=finish, args=(1,), shortcut="1", type="primary")
        middle.button("Not credible", on_click=finish, args=(0,), shortcut="2")
        right.button("Skip", on_click=finish, args=(None,), shortcut="3")
    if done:
        st.button("Undo last label", on_click=undo)


main()
