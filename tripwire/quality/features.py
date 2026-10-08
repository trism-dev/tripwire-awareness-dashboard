"""Turn event rows into model inputs (PRD 5.5). GDELT fields only: never article text."""

from urllib.parse import urlparse

import numpy as np
import pandas as pd
import psycopg

from tripwire.gdelt.categories import DEFAULT_VISIBLE

NUMERIC = [
    "log_sources",  # log(1 + NumSources): the jump from 1 to 2 sources matters more than 20 to 21
    "log_articles",
    "log_mentions",
    "geo_type",  # 1 = country centre only ... 4 = city; coarser places are less trustworthy
    "is_root",  # GDELT says the article is mainly about this event
    "goldstein",
    "avg_tone",
    "quad_class",  # 3 = verbal conflict, 4 = material conflict
    "has_actor1",
    "has_actor2",
    "log_domain_freq",  # log(1 + events from the same news site): high-volume sites vs one-offs
]
CATEGORY_COLUMNS = [f"cat_{c}" for c in DEFAULT_VISIBLE]
FEATURES = NUMERIC + CATEGORY_COLUMNS

# columns of the events table that build_features reads
EVENT_COLUMNS = [
    "global_event_id",
    "num_sources",
    "num_articles",
    "num_mentions",
    "geo_type",
    "is_root_event",
    "goldstein",
    "avg_tone",
    "quad_class",
    "actor1_name",
    "actor2_name",
    "source_url",
    "category",
]


def domain_of(url) -> str | None:
    """'https://www.bbc.com/news/x' -> 'bbc.com'."""
    if not isinstance(url, str):
        return None
    host = urlparse(url).hostname
    return host.removeprefix("www.") if host else None


def load_domain_counts(conn: psycopg.Connection) -> dict[str, int]:
    """How many events each news site has in the database. Computed from ALL events, not just the
    labeled ones, so it carries no label information."""
    rows = conn.execute(
        """
        SELECT substring(source_url from '^https?://(?:www\\.)?([^/:]+)') AS domain, count(*)
        FROM events WHERE source_url IS NOT NULL GROUP BY 1
        """
    ).fetchall()
    return {domain.lower(): n for domain, n in rows if domain}


def build_features(events: pd.DataFrame, domain_counts: dict[str, int]) -> pd.DataFrame:
    """One row of FEATURES per event, in a fixed column order. Missing values stay NaN; the model's
    imputer fills them."""
    out = pd.DataFrame(index=events.index)
    for source, name in [
        ("num_sources", "log_sources"),
        ("num_articles", "log_articles"),
        ("num_mentions", "log_mentions"),
    ]:
        out[name] = np.log1p(pd.to_numeric(events[source], errors="coerce"))
    out["geo_type"] = pd.to_numeric(events["geo_type"], errors="coerce")
    out["is_root"] = events["is_root_event"].map({True: 1.0, False: 0.0})
    out["goldstein"] = pd.to_numeric(events["goldstein"], errors="coerce")
    out["avg_tone"] = pd.to_numeric(events["avg_tone"], errors="coerce")
    out["quad_class"] = pd.to_numeric(events["quad_class"], errors="coerce")
    out["has_actor1"] = events["actor1_name"].notna().astype(float)
    out["has_actor2"] = events["actor2_name"].notna().astype(float)
    domains = events["source_url"].map(domain_of)
    out["log_domain_freq"] = np.log1p(domains.map(lambda d: domain_counts.get(d, 0) if d else 0))
    for category, column in zip(DEFAULT_VISIBLE, CATEGORY_COLUMNS, strict=True):
        out[column] = (events["category"] == category).astype(float)
    return out[FEATURES].astype(float)
