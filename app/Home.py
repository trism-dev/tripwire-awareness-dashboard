"""Tripwire dashboard (PRD 5.6): map, filters, event detail, events table."""

import sys
from datetime import UTC, datetime
from pathlib import Path

# `streamlit run app/Home.py` only puts app/ on the import path, so add the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import psycopg
import pydeck as pdk
import streamlit as st

from tripwire import queries
from tripwire.db import connect
from tripwire.fips import country_name
from tripwire.gdelt import categories as cat
from tripwire.gdelt.cameo import event_description
from tripwire.mapview import fit_view
from tripwire.queries import Filters

REPO_URL = "https://github.com/trism-dev/tripwire-awareness-dashboard"
GDELT_URL = "https://www.gdeltproject.org/"
STALE_AFTER_MIN = 30  # PRD section 4: data should be no more than 30 minutes behind GDELT

# Category colours: the dataviz palette's first six slots in its fixed order, as (light, dark).
# Checked with the skill's validate_palette.js: all pass on adjacent pairs in both modes. They do
# NOT pass the stricter "any two dots may touch" test, so colour is never the only cue: the
# legend, hover tooltip, category filter and the table all name the category in text.
CATEGORY_COLORS = {
    cat.ARMED: ("#2a78d6", "#3987e5"),
    cat.PROTEST: ("#eb6834", "#d95926"),
    cat.THREATS: ("#1baf7a", "#199e70"),
    cat.FORCE: ("#eda100", "#c98500"),
    cat.MASS: ("#e87ba4", "#d55181"),
    cat.OTHER_CONFLICT: ("#008300", "#008300"),
}
WINDOWS = {"Last 24 hours": 24, "Last 7 days": 168}

st.set_page_config(page_title="Tripwire", layout="wide")


# ---- helpers ---------------------------------------------------------------------------------


def is_dark() -> bool:
    try:
        return st.context.theme.type == "dark"
    except AttributeError:
        return False


def rgb(hex_color: str) -> list[int]:
    return [int(hex_color[i : i + 2], 16) for i in (1, 3, 5)]


def safe_url(url) -> str | None:
    """GDELT URLs are untrusted input: only ever link http(s), never javascript: and the like."""
    return url if isinstance(url, str) and url.startswith(("http://", "https://")) else None


def one_decimal(value) -> str:
    return "not given" if value is None else f"{value:.1f}"


def minutes_ago(ts) -> int:
    return int((datetime.now(UTC) - ts).total_seconds() // 60)


def age_text(minutes: int) -> str:
    return f"{minutes} min ago" if minutes < 120 else f"{minutes // 60} h ago"


def prepare_points(points: pd.DataFrame, dark: bool) -> pd.DataFrame:
    """Add colour, size and country name; order so the rarest categories draw on top."""
    df = points.copy()
    shade = 1 if dark else 0
    df["color"] = df["category"].map(lambda c: [*rgb(CATEGORY_COLORS[c][shade]), 190])
    df["radius"] = np.minimum(2.5 + 1.5 * np.sqrt(df["num_sources"].fillna(1).astype(float)), 14)
    df["country"] = df["country_code"].map(country_name)
    frequency = df["category"].map(df["category"].value_counts())
    return df.assign(_n=frequency).sort_values("_n", ascending=False).drop(columns="_n")


# ---- data access (cached for a minute; each call opens its own short connection) -------------


@st.cache_data(ttl=60, show_spinner=False)
def load_header():
    with connect() as conn:
        return queries.latest_update(conn), queries.country_options(conn, max(WINDOWS.values()))


@st.cache_data(ttl=60, show_spinner=False)
def load_view(f: Filters):
    with connect() as conn:
        return queries.category_counts(conn, f), queries.map_events(conn, f)


@st.cache_data(ttl=60, show_spinner=False)
def load_table(f: Filters):
    with connect() as conn:
        return queries.table_events(conn, f)


@st.cache_data(ttl=300, show_spinner=False)
def load_detail(event_id: int):
    with connect() as conn:
        return queries.event_detail(conn, event_id)


# ---- page sections ---------------------------------------------------------------------------


def render_header(latest, counts: dict, shown: int):
    st.title("Tripwire")
    st.caption("Open-source situational awareness, built on GDELT news events.")
    left, middle, right = st.columns(3)
    age = minutes_ago(latest)
    left.metric(
        "Last GDELT update", age_text(age), help="Newest 15-minute GDELT file we hold (UTC)."
    )
    total = sum(counts.values())
    middle.metric("Events in view", f"{total:,}")
    right.metric("Drawn on map", f"{shown:,}")
    if age > STALE_AFTER_MIN:
        st.warning(f"Data is {age_text(age)}; the target is under {STALE_AFTER_MIN} minutes.")


def render_legend(counts: dict):
    for name, (light, dark) in CATEGORY_COLORS.items():
        if name in counts:
            colour = dark if is_dark() else light
            st.markdown(
                f"<span style='color:{colour}'>●</span> {name} — {counts[name]:,}",
                unsafe_allow_html=True,
            )


def render_map(points: pd.DataFrame):
    dark = is_dark()
    df = prepare_points(points, dark)
    layer = pdk.Layer(
        "ScatterplotLayer",
        id="events",
        data=df[
            [
                "global_event_id",
                "lon",
                "lat",
                "color",
                "radius",
                "category",
                "country",
                "geo_fullname",
                "num_sources",
                "added",
            ]
        ],
        get_position=["lon", "lat"],
        get_fill_color="color",
        get_radius="radius",
        radius_units="pixels",
        stroked=True,
        get_line_color=[20, 20, 20, 200] if dark else [255, 255, 255, 230],
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )
    tooltip = {
        "text": "{category}\n{geo_fullname} ({country})\n{num_sources} source(s) · {added} UTC"
    }
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(**fit_view(df["lon"], df["lat"])),
        tooltip=tooltip,
        map_style="dark" if dark else "light",  # must match the palette shade chosen above
    )
    state = st.pydeck_chart(
        deck, on_select="rerun", selection_mode="single-object", key="map", height=560
    )
    picked = state.selection.objects.get("events") or []
    return int(picked[0]["global_event_id"]) if picked else None


def render_detail(event_id: int | None):
    st.subheader("Event detail")
    if event_id is None:
        st.info("Click a dot on the map to see who, where, what and the source article.")
        return
    e = load_detail(event_id)
    if e is None:
        st.warning("That event is no longer in the database.")
        return
    # GDELT strings are untrusted, so they go into a dataframe (plain text), never into markdown.
    rows = {
        "Category": e["category"] or "Uncategorised",
        "Event": f"{event_description(e['event_code'])} (CAMEO {e['event_code']})",
        "Where": f"{e['geo_fullname']} - {country_name(e['country_code'])} ({e['country_code']})",
        "Actor 1": f"{e['actor1_name'] or 'unspecified'} ({e['actor1_country'] or '-'})",
        "Actor 2": f"{e['actor2_name'] or 'unspecified'} ({e['actor2_country'] or '-'})",
        "Event date": str(e["event_date"]),
        "Reported (UTC)": e["date_added"].strftime("%Y-%m-%d %H:%M"),
        "Sources": str(e["num_sources"]),
        "Articles / mentions": f"{e['num_articles']} / {e['num_mentions']}",
        "Goldstein": f"{one_decimal(e['goldstein'])}  (-10 conflict ... +10 cooperation)",
        "Avg tone": f"{one_decimal(e['avg_tone'])}  (negative = negative coverage)",
    }
    detail = pd.DataFrame({"Field": list(rows), "Value": list(rows.values())})
    st.dataframe(detail, hide_index=True, width="stretch", height=(len(detail) + 1) * 35 + 3)
    url = safe_url(e["source_url"])
    if url:
        st.link_button("Open source article", url)
    else:
        st.caption("No usable source link.")


def render_table(f: Filters):
    table = load_table(f)
    if table.empty:
        st.info("No events match these filters.")
        return
    st.caption(f"The {len(table):,} best-sourced events in view.")
    out = pd.DataFrame(
        {
            "When (UTC)": table["date_added"].dt.strftime("%Y-%m-%d %H:%M"),
            "Category": table["category"],
            "Country": table["country_code"].map(country_name),
            "Place": table["geo_fullname"],
            "Actor 1": table["actor1_name"],
            "Actor 2": table["actor2_name"],
            "Event": table["event_code"].map(event_description),
            "Sources": table["num_sources"],
            "Goldstein": table["goldstein"],
            "Tone": table["avg_tone"],
            "Source": table["source_url"].map(safe_url),
        }
    )
    st.dataframe(
        out,
        hide_index=True,
        width="stretch",
        column_config={"Source": st.column_config.LinkColumn("Source", display_text="open")},
    )


def render_about():
    st.markdown(
        """
**What this is.** Tripwire reads the GDELT 2.0 event feed every 15 minutes, keeps conflict and unrest
events that have a usable location, groups them into mission categories, and plots them here.

**How to read it.** Each dot is one machine-coded news event. Dot size is the number of distinct news
sources; one-source events are common and should be verified before briefing. Click a dot for the
actors, event type and a link to the source article.

**Limits.**
- GDELT is automatic, so it contains duplicates, wrong places and misread articles.
- Country names use FIPS 10-4 codes, which differ from ISO (for example UP is Ukraine).
- Events marked at country level only (no city) are hidden from the map by default.
- Times are UTC.
        """
    )


# ---- main ------------------------------------------------------------------------------------


def main():
    try:
        latest, countries = load_header()
    except psycopg.Error as exc:
        st.error(f"Cannot reach the database: {exc}")
        st.stop()
    if latest is None:
        st.info("No data yet. Run `make backfill DAYS=1` to load some events.")
        st.stop()

    with st.sidebar:
        st.header("Filters")
        window = st.selectbox(
            "Time window", list(WINDOWS), help="Based on when GDELT reported the event."
        )
        chosen = st.multiselect(
            "Categories",
            list(CATEGORY_COLORS),
            default=cat.DEFAULT_VISIBLE,
            help="'Other conflict' is hidden by default.",
        )
        picked_countries = st.multiselect(
            "Countries",
            [code for code, _ in countries],
            format_func=lambda code: f"{country_name(code)} ({code})",
            help="GDELT uses FIPS 10-4 codes, not ISO. Leave empty for all countries.",
        )
        min_sources = st.slider(
            "Minimum sources",
            1,
            10,
            1,
            help="Events reported by more sources are more likely real.",
        )

    f = Filters(WINDOWS[window], tuple(chosen), tuple(picked_countries), min_sources)
    counts, points = load_view(f)

    render_header(latest, counts, len(points))
    with st.sidebar:
        st.subheader("Legend")
        render_legend(counts)

    if points.empty:
        st.info("No events match these filters. Try a longer window or fewer filters.")
    else:
        if sum(counts.values()) > len(points):
            st.caption(
                f"Showing the {len(points):,} best-sourced of {sum(counts.values()):,} events. "
                "Narrow the filters to see all."
            )
        map_col, detail_col = st.columns([5, 2])
        with map_col:
            selected = render_map(points)
        with detail_col:
            render_detail(selected)

    events_tab, about_tab = st.tabs(["Events table", "About"])
    with events_tab:
        render_table(f)
    with about_tab:
        render_about()

    st.divider()
    st.caption(
        f"Data: [The GDELT Project]({GDELT_URL}). GDELT is free to use with attribution. "
        f"· [Source code]({REPO_URL})"
    )


main()
