"""Settings, read from environment variables only."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    retention_days: int
    spike_z: float
    spike_min_count: int
    region_allowlist: frozenset[str]  # FIPS country codes; empty means "all countries"


def load_settings() -> Settings:
    codes = os.environ.get("REGION_ALLOWLIST", "")
    return Settings(
        database_url=os.environ.get("DATABASE_URL", ""),
        retention_days=int(os.environ.get("RETENTION_DAYS", "60")),
        spike_z=float(os.environ.get("SPIKE_Z", "3")),
        spike_min_count=int(os.environ.get("SPIKE_MIN_COUNT", "10")),
        region_allowlist=frozenset(c.strip().upper() for c in codes.split(",") if c.strip()),
    )
