import urllib.error

from worker.run import tick


def test_tick_survives_total_outage(conn):
    """Every download fails: tick must log errors and return, not raise."""

    def down(url):
        raise urllib.error.URLError("network down")

    tick(conn, fetch=down, delay=0)
    statuses = {r[0] for r in conn.execute("SELECT status FROM ingest_files")}
    assert statuses <= {"error"}


def test_tick_stores_spikes_for_today(conn):
    """With history and a burst of events today, one worker pass records the spike."""
    from datetime import UTC, datetime, timedelta

    from tests.test_spikes import add_events

    today = datetime.now(UTC).date()
    for d in range(1, 31):
        add_events(conn, today - timedelta(days=d), 10)
    add_events(conn, today, 40)

    def down(url):
        raise urllib.error.URLError("network down")  # no real downloads in tests

    tick(conn, fetch=down, delay=0)
    rows = conn.execute(
        "SELECT country_code, count FROM spikes WHERE day = %s", (today,)
    ).fetchall()
    assert rows == [("UP", 40)]
