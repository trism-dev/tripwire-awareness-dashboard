"""Long-running worker: every 15 minutes ingest GDELT and refresh spikes. (Retention comes later.)"""

import logging
import time
from datetime import UTC, datetime, timedelta

from tripwire.backfill import backfill
from tripwire.config import load_settings
from tripwire.db import connect, migrate
from tripwire.ingest import run_cycle
from tripwire.quality.score import load_artifact, score_missing
from tripwire.retention import purge
from tripwire.spikes import run as run_spikes

log = logging.getLogger("worker")

POLL_SECONDS = 15 * 60
CATCH_UP_DAYS = 1  # re-check the last day so a laptop sleep or outage leaves no gaps


def tick(conn, fetch=None, delay=0.5) -> None:
    """One pass: fill any recent gaps (already-done files cost no download), then the newest file."""
    kwargs = {"fetch": fetch} if fetch else {}
    backfill(conn, days=CATCH_UP_DAYS, delay=delay, **kwargs)
    run_cycle(conn, **kwargs)
    # Yesterday (now complete) and today (partial, so its score can only rise). A spike failure
    # must never stop ingestion, so it gets its own try/except.
    try:
        today = datetime.now(UTC).date()
        for day in (today - timedelta(days=1), today):
            run_spikes(conn, day)
    except Exception:
        log.exception("spike detection failed")
    # Score new events with the quality model, if one has been trained. Also isolated: a scoring
    # problem must never stop ingestion.
    try:
        model = load_artifact()
        if model is not None:
            score_missing(conn, model, max_rows=50_000)
    except Exception:
        log.exception("quality scoring failed")
    # Old events are deleted, except hand-labeled ones. Cheap when there is nothing to delete.
    try:
        removed = purge(conn, load_settings().retention_days)
        if removed:
            log.info("retention removed %d old events", removed)
    except Exception:
        log.exception("retention failed")


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
