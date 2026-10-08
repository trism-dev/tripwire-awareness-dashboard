"""CSV export of the current filtered view (PRD S5)."""

import pandas as pd

from tripwire.fips import country_name
from tripwire.gdelt.cameo import event_description

# Excel, Sheets and LibreOffice treat a cell starting with one of these as a FORMULA, and GDELT text
# (actor and place names, URLs) is untrusted. A leading apostrophe makes the cell plain text.
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")

TEXT_COLUMNS = ["category", "country", "place", "actor1", "actor2", "event_type", "source_url"]


def csv_safe(value):
    if isinstance(value, str) and value.startswith(_FORMULA_STARTS):
        return "'" + value
    return value


def events_csv(events: pd.DataFrame) -> bytes:
    """Event rows (from queries.export_events) -> CSV bytes with readable names and safe text.

    UTF-8 with a byte-order mark, so Excel shows accented names correctly.
    """
    out = pd.DataFrame(
        {
            "global_event_id": events["global_event_id"],
            "reported_utc": pd.to_datetime(events["date_added"], utc=True).dt.strftime(
                "%Y-%m-%d %H:%M"
            ),
            "event_date": events["event_date"],
            "category": events["category"],
            "country": events["country_code"].map(country_name),
            "country_code": events["country_code"],
            "place": events["geo_fullname"],
            "lat": events["lat"],
            "lon": events["lon"],
            "actor1": events["actor1_name"],
            "actor1_country": events["actor1_country"],
            "actor2": events["actor2_name"],
            "actor2_country": events["actor2_country"],
            "event_code": events["event_code"],
            "event_type": events["event_code"].map(event_description),
            "sources": events["num_sources"],
            "articles": events["num_articles"],
            "goldstein": events["goldstein"],
            "tone": events["avg_tone"],
            "quality_score": pd.to_numeric(events["quality_score"]).round(3),
            "source_url": events["source_url"],
        }
    )
    for column in TEXT_COLUMNS:
        out[column] = out[column].map(csv_safe)
    return out.to_csv(index=False).encode("utf-8-sig")
