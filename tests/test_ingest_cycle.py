import io
import urllib.error
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from tripwire.backfill import backfill
from tripwire.config import Settings
from tripwire.gdelt.fetch import file_url
from tripwire.ingest import ingest_url, run_cycle

FIXTURE = Path(__file__).parent / "fixtures" / "sample.export.CSV"
URL = "https://data.gdeltproject.org/gdeltv2/20261004184500.export.CSV.zip"
SETTINGS = Settings("", 30, 3.0, 10, frozenset())


def good_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("x.export.CSV", FIXTURE.read_text(encoding="utf-8"))
    return buf.getvalue()


class FakeFetch:
    def __init__(self, data=None, error=None):
        self.data, self.error, self.calls = data, error, []

    def __call__(self, url):
        self.calls.append(url)
        if self.error:
            raise self.error
        return self.data


def ledger(conn, url=URL):
    return conn.execute(
        "SELECT status, rows_raw, rows_kept, error FROM ingest_files WHERE file_url = %s", (url,)
    ).fetchone()


def event_count(conn):
    return conn.execute("SELECT count(*) FROM events").fetchone()[0]


def test_good_file_is_ingested_and_logged(conn):
    assert ingest_url(conn, URL, fetch=FakeFetch(good_zip()), settings=SETTINGS) == "ok"
    assert ledger(conn) == ("ok", 7, 3, None)
    assert event_count(conn) == 3


def test_same_file_is_not_downloaded_twice(conn):
    fetch = FakeFetch(good_zip())
    ingest_url(conn, URL, fetch=fetch, settings=SETTINGS)
    assert ingest_url(conn, URL, fetch=fetch, settings=SETTINGS) == "skipped"
    assert len(fetch.calls) == 1
    assert event_count(conn) == 3


def test_truncated_file_is_logged_and_does_not_raise(conn):
    data = good_zip()
    assert ingest_url(conn, URL, fetch=FakeFetch(data[:100]), settings=SETTINGS) == "error"
    assert ledger(conn)[0] == "error"
    assert event_count(conn) == 0


def test_failed_file_is_retried_next_time(conn):
    ingest_url(conn, URL, fetch=FakeFetch(good_zip()[:100]), settings=SETTINGS)
    assert ingest_url(conn, URL, fetch=FakeFetch(good_zip()), settings=SETTINGS) == "ok"
    assert ledger(conn)[0] == "ok"


def test_md5_mismatch_is_an_error(conn):
    status = ingest_url(conn, URL, md5="0" * 32, fetch=FakeFetch(good_zip()), settings=SETTINGS)
    assert status == "error"
    assert "md5" in ledger(conn)[3]
    assert event_count(conn) == 0


def test_404_is_recorded_as_missing_and_not_retried(conn):
    err = urllib.error.HTTPError(URL, 404, "Not Found", None, None)
    assert ingest_url(conn, URL, fetch=FakeFetch(error=err), settings=SETTINGS) == "missing"
    fetch = FakeFetch(good_zip())
    assert ingest_url(conn, URL, fetch=fetch, settings=SETTINGS) == "skipped"
    assert fetch.calls == []


def test_run_cycle_uses_manifest_and_checks_md5(conn):
    import hashlib

    data = good_zip()
    manifest = f"{len(data)} {hashlib.md5(data).hexdigest()} {URL.replace('https', 'http')}\n"

    def fetch(url):
        return manifest.encode() if url.endswith("lastupdate.txt") else data

    assert run_cycle(conn, fetch=fetch) == "ok"
    assert ledger(conn)[0] == "ok"


def test_run_cycle_survives_unreadable_manifest(conn):
    assert run_cycle(conn, fetch=FakeFetch(error=OSError("network down"))) == "error"


def test_backfill_walks_slots_skips_done_files_and_pauses_politely(conn):
    now = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)  # 3h window minus 1h margin = 2h = 9 slots
    fetch = FakeFetch(good_zip())
    pauses = []
    counts = backfill(conn, days=1 / 8, fetch=fetch, now=now, sleep=pauses.append, delay=0.25)
    assert counts == {"ok": 9}
    assert len(fetch.calls) == 9
    assert fetch.calls[0] == file_url(datetime(2026, 10, 4, 9, 0, tzinfo=UTC))
    assert pauses == [0.25] * 9
    # second run: everything already logged, nothing downloaded, no pauses
    fetch2, pauses2 = FakeFetch(good_zip()), []
    assert backfill(conn, days=1 / 8, fetch=fetch2, now=now, sleep=pauses2.append) == {"skipped": 9}
    assert fetch2.calls == [] and pauses2 == []
    assert event_count(conn) == 3  # same 3 events in every file -> still 3 rows
