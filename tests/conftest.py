import os
import uuid
from pathlib import Path

import psycopg
import pytest

from tripwire.db import migrate
from tripwire.gdelt.categories import add_category
from tripwire.gdelt.filter import filter_events
from tripwire.gdelt.parse import parse_text

FIXTURE = Path(__file__).parent / "fixtures" / "sample.export.CSV"


@pytest.fixture
def kept_events():
    """Fixture rows after filter + categorize (3 rows)."""
    df, _ = parse_text(FIXTURE.read_text(encoding="utf-8"))
    return add_category(filter_events(df))


@pytest.fixture
def conn():
    """A connection to a throwaway schema, fully migrated. Skipped if TEST_DATABASE_URL is unset."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    schema = f"test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f"CREATE SCHEMA {schema}")
    c = psycopg.connect(url, options=f"-c search_path={schema}")
    migrate(c)
    yield c
    c.close()
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f"DROP SCHEMA {schema} CASCADE")
