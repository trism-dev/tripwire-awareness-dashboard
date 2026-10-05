import urllib.error

from worker.run import tick


def test_tick_survives_total_outage(conn):
    """Every download fails: tick must log errors and return, not raise."""

    def down(url):
        raise urllib.error.URLError("network down")

    tick(conn, fetch=down)
    statuses = {r[0] for r in conn.execute("SELECT status FROM ingest_files")}
    assert statuses <= {"error"}
