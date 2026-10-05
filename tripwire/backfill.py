"""Load the last N days of GDELT files, politely. Safe to stop and restart."""

import argparse
import logging
import time
from datetime import UTC, datetime, timedelta

from tripwire.db import connect
from tripwire.gdelt.fetch import download, file_url, slots_between
from tripwire.ingest import ingest_url

log = logging.getLogger(__name__)

# The newest slots may simply not be published yet. Leave them to the live cycle so a 404 there
# is not recorded as "missing" forever.
RECENT_MARGIN = timedelta(hours=1)


def backfill(conn, days=30, delay=0.5, fetch=download, now=None, sleep=time.sleep) -> dict:
    now = now or datetime.now(UTC)
    slots = slots_between(now - timedelta(days=days), now - RECENT_MARGIN)
    counts: dict[str, int] = {}
    for i, slot in enumerate(slots, 1):
        status = ingest_url(conn, file_url(slot), fetch=fetch)
        counts[status] = counts.get(status, 0) + 1
        if status != "skipped":
            sleep(delay)  # one request at a time, with a pause: be polite to GDELT
        if i % 50 == 0:
            log.info("%d/%d files  %s", i, len(slots), counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between downloads")
    args = ap.parse_args()
    with connect() as c:
        print(backfill(c, args.days, args.delay))
