"""CAMEO root code -> mission category (PRD 5.3)."""

import pandas as pd

PROTEST = "Protest & unrest"
THREATS = "Threats & coercion"
FORCE = "Force posture"
ARMED = "Armed conflict"
MASS = "Mass violence"
OTHER_CONFLICT = "Other conflict"
COOPERATION = "Cooperation"  # roots 01-08; never kept at ingest, listed so 01-20 are all covered

_BUCKETS = {
    PROTEST: ["14"],
    THREATS: ["13", "17"],
    FORCE: ["15"],
    ARMED: ["18", "19"],
    MASS: ["20"],
    OTHER_CONFLICT: ["09", "10", "11", "12", "16"],
    COOPERATION: [f"{n:02d}" for n in range(1, 9)],
}

CATEGORY_BY_ROOT = {root: cat for cat, roots in _BUCKETS.items() for root in roots}

# Shown on the map by default. "Other conflict" is kept in the table but hidden.
DEFAULT_VISIBLE = [PROTEST, THREATS, FORCE, ARMED, MASS]


def add_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with a `category` column; unknown root codes get NULL."""
    out = df.copy()
    out["category"] = out["EventRootCode"].map(CATEGORY_BY_ROOT)
    return out
