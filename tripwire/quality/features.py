"""Turn event rows into model inputs (PRD 5.5). GDELT fields only: never article text.

Features come in groups so each group's value can be measured on its own:
    base    : sources, articles, mentions, place precision, tone, Goldstein, quad class, site volume
    category: the five mission categories
    codes   : the specific CAMEO event code (e.g. 173 arrest vs 202 mass killing) for common codes
    actors  : who the actors are (state / non-military sector) and whether actor and event locations agree
"""

from urllib.parse import urlparse

import numpy as np
import pandas as pd
import psycopg

from tripwire.gdelt.categories import DEFAULT_VISIBLE

BASE = [
    "log_sources",  # log(1 + NumSources): the jump from 1 to 2 sources matters more than 20 to 21
    "log_articles",
    "log_mentions",
    "geo_type",  # 1 = country centre only ... 4 = city; coarser places are less trustworthy
    "goldstein",
    "avg_tone",
    "quad_class",  # 3 = verbal conflict, 4 = material conflict
    "log_domain_freq",  # log(1 + events from the same news site): high-volume sites vs one-offs
]
CATEGORY_COLUMNS = [f"cat_{c}" for c in DEFAULT_VISIBLE]
ACTOR_COLUMNS = [
    "a1_has_type",
    "a2_has_type",
    "a1_state",  # government, military, police, spy, judiciary, legislature
    "a2_state",
    "nonmil_force",  # a business / media / court / school actor in a violence or force event
    "a1_geo_differs",  # actor 1 is based in another country than where the event is placed
    "a2_geo_differs",
    "a1_geo_known",
]
GROUPS = ("base", "category", "codes", "actors")  # every group that exists
# What the live model uses. "codes" and "actors" were measured and did NOT help with ~300 labels
# (docs/evaluation.md), so they stay available for experiments but are off.
DEFAULT_GROUPS = ("base", "category")

# CAMEO actor type codes. Civilians (CVL) are deliberately NOT "non-military": they are the usual
# victims in real attacks.
STATE_TYPES = {"GOV", "MIL", "COP", "SPY", "JUD", "LEG"}
NONMIL_TYPES = {"JUD", "MED", "BUS", "EDU", "HLH", "LAB", "AGR", "ENV", "REL"}
FORCE_ROOTS = {"15", "18", "19", "20"}  # posture, assault, fight, mass violence

# columns of the events table that build_features reads
EVENT_COLUMNS = [
    "global_event_id",
    "num_sources",
    "num_articles",
    "num_mentions",
    "geo_type",
    "goldstein",
    "avg_tone",
    "quad_class",
    "source_url",
    "category",
    "event_base_code",
    "event_root_code",
    "country_code",
    "actor1_type1_code",
    "actor2_type1_code",
    "actor1_geo_country",
    "actor2_geo_country",
]


def feature_names(
    code_levels: tuple[str, ...] = (), groups: tuple[str, ...] = DEFAULT_GROUPS
) -> list[str]:
    """The model's input columns, in a fixed order, for the chosen groups."""
    names: list[str] = []
    if "base" in groups:
        names += BASE
    if "category" in groups:
        names += CATEGORY_COLUMNS
    if "codes" in groups:
        names += [f"code_{c}" for c in code_levels] + ["code_other"]
    if "actors" in groups:
        names += ACTOR_COLUMNS
    return names


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


def top_codes(conn: psycopg.Connection, k: int = 15) -> tuple[str, ...]:
    """The k most common event codes among mission-category events. Chosen from ALL events (not
    from the labels), so which codes get their own column carries no label information."""
    rows = conn.execute(
        """
        SELECT event_base_code FROM events
        WHERE category = ANY(%s) AND event_base_code IS NOT NULL
        GROUP BY 1 ORDER BY count(*) DESC, 1 LIMIT %s
        """,
        (DEFAULT_VISIBLE, k),
    ).fetchall()
    return tuple(r[0] for r in rows)


def _has(series: pd.Series) -> pd.Series:
    return series.notna().astype(float)


def build_features(
    events: pd.DataFrame,
    domain_counts: dict[str, int],
    code_levels: tuple[str, ...] = (),
    groups: tuple[str, ...] = DEFAULT_GROUPS,
) -> pd.DataFrame:
    """One row of model inputs per event, columns = feature_names(code_levels, groups).
    Missing values stay NaN; the model's imputer fills them."""
    out = pd.DataFrame(index=events.index)

    for source, name in [
        ("num_sources", "log_sources"),
        ("num_articles", "log_articles"),
        ("num_mentions", "log_mentions"),
    ]:
        out[name] = np.log1p(pd.to_numeric(events[source], errors="coerce"))
    for column in ("geo_type", "goldstein", "avg_tone", "quad_class"):
        out[column] = pd.to_numeric(events[column], errors="coerce")
    domains = events["source_url"].map(domain_of)
    out["log_domain_freq"] = np.log1p(domains.map(lambda d: domain_counts.get(d, 0) if d else 0))

    for category, column in zip(DEFAULT_VISIBLE, CATEGORY_COLUMNS, strict=True):
        out[column] = (events["category"] == category).astype(float)

    base_code = events["event_base_code"]
    for code in code_levels:
        out[f"code_{code}"] = (base_code == code).astype(float)
    out["code_other"] = (~base_code.isin(code_levels)).astype(float)

    t1, t2 = events["actor1_type1_code"], events["actor2_type1_code"]
    out["a1_has_type"], out["a2_has_type"] = _has(t1), _has(t2)
    out["a1_state"], out["a2_state"] = (
        t1.isin(STATE_TYPES).astype(float),
        t2.isin(STATE_TYPES).astype(float),
    )
    nonmil = t1.isin(NONMIL_TYPES) | t2.isin(NONMIL_TYPES)
    out["nonmil_force"] = (nonmil & events["event_root_code"].isin(FORCE_ROOTS)).astype(float)
    g1, g2, country = (
        events["actor1_geo_country"],
        events["actor2_geo_country"],
        events["country_code"],
    )
    out["a1_geo_differs"] = (g1.notna() & (g1 != country)).astype(float)
    out["a2_geo_differs"] = (g2.notna() & (g2 != country)).astype(float)
    out["a1_geo_known"] = _has(g1)

    return out[feature_names(code_levels, groups)].astype(float)
