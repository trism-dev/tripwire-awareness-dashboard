"""Long-running worker: ingest GDELT every 15 minutes. Spikes and retention are added in week 2."""

import logging
import time

from tripwire.backfill import backfill
from tripwire.db import connect, migrate
from tripwire.ingest import run_cycle

log = logging.getLogger("worker")

POLL_SECONDS = 15 * 60
CATCH_UP_DAYS = 1  # re-check the last day so a laptop sleep or outage leaves no gaps


def tick(conn, fetch=None) -> None:
    """One pass: fill any recent gaps (already-done files cost no download), then the newest file."""
    kwargs = {"fetch": fetch} if fetch else {}
    backfill(conn, days=CATCH_UP_DAYS, **kwargs)
    run_cycle(conn, **kwargs)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    while True:
        try:
            with connect() as conn:
                migrate(conn)
                tick(conn)
        except Exception:
            log.exception("worker pass failed")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
