"""Relevance filter applied at ingest (PRD 5.2)."""

import pandas as pd


def filter_events(
    df: pd.DataFrame,
    root_only: bool = True,
    country_allowlist: frozenset[str] = frozenset(),
) -> pd.DataFrame:
    """Keep conflict events (QuadClass 3 or 4) that have a usable place.

    ActionGeo_Type 1 (country centroid) is kept here on purpose; the map query hides it.
    """
    lat, lon = df["ActionGeo_Lat"], df["ActionGeo_Long"]
    keep = df["QuadClass"].isin([3, 4]) & lat.notna() & lon.notna() & ~((lat == 0) & (lon == 0))
    if root_only:
        keep &= df["IsRootEvent"] == 1
    if country_allowlist:
        keep &= df["ActionGeo_CountryCode"].isin(country_allowlist)
    return df[keep.fillna(False).astype(bool)].reset_index(drop=True)
