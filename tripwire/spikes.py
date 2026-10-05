"""Spike detection (PRD 5.4): is today's count for a country x category far above its norm?

For each (country, category) we compare one day's event count with the previous 28 days:
    robust z = (count - median) / (1.4826 * MAD)
The median and MAD (median absolute deviation) ignore a few extreme days, unlike mean and
standard deviation, so one earlier burst does not hide the next one.
"""

import argparse
import logging
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd

from tripwire.config import load_settings
from tripwire.db import connect
from tripwire.gdelt.categories import DEFAULT_VISIBLE

log = logging.getLogger(__name__)

WINDOW_DAYS = 28
MAD_TO_SIGMA = 1.4826  # makes MAD comparable to a standard deviation for bell-shaped data
KEYS = ["country_code", "category"]
SPIKE_COLUMNS = ["country_code", "category", "day", "count", "baseline_median", "baseline_mad", "z"]


def daily_counts(conn, start: date, end: date) -> pd.DataFrame:
    """Events per day x country x category (mission categories only). Days with none are absent."""
    rows = conn.execute(
        """
        SELECT event_date, country_code, category, count(*)
        FROM events
        WHERE event_date BETWEEN %s AND %s
          AND country_code IS NOT NULL
          AND category = ANY(%s)
        GROUP BY 1, 2, 3
        """,
        (start, end, DEFAULT_VISIBLE),
    ).fetchall()
    return pd.DataFrame(rows, columns=["day", *KEYS, "count"])


def detect(
    counts: pd.DataFrame,
    day: date,
    z_threshold: float = 3.0,
    min_count: int = 10,
    window: int = WINDOW_DAYS,
) -> pd.DataFrame:
    """Return the spikes on `day` (columns = SPIKE_COLUMNS), highest z first. Pure: no database."""
    empty = pd.DataFrame(columns=SPIKE_COLUMNS)
    if counts.empty:
        return empty
    day = pd.Timestamp(day)
    counts = counts.assign(day=pd.to_datetime(counts["day"]))

    today = counts[counts["day"] == day].set_index(KEYS)["count"]
    today = today[today >= min_count]  # the floor: small counts are never alerts
    if today.empty:
        return empty

    # Baseline matrix: one row per day in the window, one column per candidate group.
    # reindex + fill_value=0 is the important part: a day with no events counts as 0, not "missing".
    # The window ends the day BEFORE `day`, so today never judges itself.
    days = pd.date_range(day - pd.Timedelta(days=window), day - pd.Timedelta(days=1))
    base = (
        counts[counts["day"].isin(days)]
        .pivot_table(index="day", columns=KEYS, values="count", aggfunc="sum")
        .reindex(index=days, columns=today.index, fill_value=0)
        .fillna(0)
    )
    values = base.to_numpy(dtype=float)
    median = np.median(values, axis=0)
    mad = np.median(np.abs(values - median), axis=0)

    # MAD = 0 means more than half the days equal the median (typical for quiet places), so the
    # normal formula would divide by zero. Fall back to a Poisson-style spread: variance = mean.
    scale = np.where(mad > 0, MAD_TO_SIGMA * mad, np.sqrt(np.maximum(median, 1)))
    z = (today.to_numpy(dtype=float) - median) / scale

    out = today.reset_index()
    out["day"] = day.date()
    out["baseline_median"] = median
    out["baseline_mad"] = mad
    out["z"] = z
    out = out[out["z"] >= z_threshold]
    return out[SPIKE_COLUMNS].sort_values("z", ascending=False).reset_index(drop=True)


def has_full_baseline(conn, day: date, window: int = WINDOW_DAYS) -> bool:
    """True if we were ingesting before the baseline window began.

    Without this, a freshly started database would show every busy country as a spike because
    the empty days before we started collecting would count as zeros.
    """
    first = conn.execute("SELECT min(date_added)::date FROM events").fetchone()[0]
    return first is not None and first < day - timedelta(days=window)


def run(conn, day: date, z_threshold=None, min_count=None) -> pd.DataFrame:
    """Detect spikes for `day` and store them (replacing whatever was stored for that day)."""
    s = load_settings()
    z_threshold = s.spike_z if z_threshold is None else z_threshold
    min_count = s.spike_min_count if min_count is None else min_count

    if not has_full_baseline(conn, day):
        log.warning(
            "not enough history for a %d-day baseline before %s; skipping", WINDOW_DAYS, day
        )
        return pd.DataFrame(columns=SPIKE_COLUMNS)

    counts = daily_counts(conn, day - timedelta(days=WINDOW_DAYS), day)
    spikes = detect(counts, day, z_threshold, min_count)

    # Delete + insert so a spike that no longer qualifies does not linger (e.g. thresholds changed).
    conn.execute("DELETE FROM spikes WHERE day = %s", (day,))
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO spikes (country_code, category, day, count, baseline_median, baseline_mad, z)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    r.country_code,
                    r.category,
                    r.day,
                    int(r.count),
                    r.baseline_median,
                    r.baseline_mad,
                    r.z,
                )
                for r in spikes.itertuples()
            ],
        )
    conn.commit()
    return spikes


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--days", type=int, default=2, help="how many days back to recompute, ending today"
    )
    args = ap.parse_args()
    today = datetime.now(UTC).date()
    with connect() as c:
        for i in reversed(range(args.days)):
            d = today - timedelta(days=i)
            print(d, len(run(c, d)), "spikes")
