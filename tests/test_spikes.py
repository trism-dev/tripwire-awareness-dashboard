"""Spike math checked against hand-computed numbers."""

from datetime import date, timedelta

import pandas as pd
import pytest

from tripwire.spikes import MAD_TO_SIGMA, detect, run

DAY = date(2026, 10, 1)
ARMED = "Armed conflict"


def counts_frame(series_by_group, day_count_by_group):
    """series_by_group: {(cc, cat): [28 baseline counts, oldest first]}; day_count: {(cc, cat): n}."""
    rows = []
    for (cc, cat), series in series_by_group.items():
        for i, n in enumerate(series):
            rows.append((DAY - timedelta(days=28 - i), cc, cat, n))
    for (cc, cat), n in day_count_by_group.items():
        rows.append((DAY, cc, cat, n))
    return pd.DataFrame(rows, columns=["day", "country_code", "category", "count"])


def one(series, today, **kw):
    key = ("UP", ARMED)
    return detect(counts_frame({key: series}, {key: today}), DAY, **kw)


def test_normal_mad_path_hand_computed():
    # 14 days of 8 and 14 of 12: median 10, every deviation is 2, so MAD 2 and sigma 1.4826 * 2.
    series = [8] * 14 + [12] * 14
    out = one(series, 20)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["baseline_median"] == 10 and row["baseline_mad"] == 2
    assert row["z"] == pytest.approx((20 - 10) / (MAD_TO_SIGMA * 2))  # about 3.372
    assert row["count"] == 20


def test_just_below_threshold_is_not_flagged():
    assert one([8] * 14 + [12] * 14, 18).empty  # z = 8 / 2.9652 = 2.70


def test_count_floor_blocks_small_counts():
    # median 0, MAD 0, count 9: z would be 9 but 9 < the floor of 10
    assert one([0] * 28, 9).empty
    assert len(one([0] * 28, 10)) == 1


def test_mad_zero_uses_poisson_fallback():
    # 20 days of 4, 4 of 3, 4 of 5: median 4, MAD 0. Fallback scale = sqrt(4) = 2.
    series = [4] * 20 + [3] * 4 + [5] * 4
    out = one(series, 12)
    assert out.iloc[0]["baseline_mad"] == 0
    assert out.iloc[0]["z"] == pytest.approx((12 - 4) / 2)  # 4.0
    assert len(one(series, 10)) == 1  # z = 3.0 exactly: the threshold is inclusive


def test_days_with_no_events_count_as_zero():
    # Only 5 of 28 baseline days have rows (10 events each). The other 23 are zeros, so the
    # median is 0 and 10 events today is a spike. Ignoring missing days would give median 10.
    key = ("UP", ARMED)
    rows = [(DAY - timedelta(days=d), *key, 10) for d in (3, 6, 9, 12, 15)] + [(DAY, *key, 10)]
    counts = pd.DataFrame(rows, columns=["day", "country_code", "category", "count"])
    out = detect(counts, DAY)
    assert len(out) == 1 and out.iloc[0]["baseline_median"] == 0


def test_today_and_future_days_are_not_in_the_baseline():
    key = ("UP", ARMED)
    base = counts_frame({key: [8] * 14 + [12] * 14}, {key: 20})
    future = pd.DataFrame([(DAY + timedelta(days=1), *key, 500)], columns=base.columns)
    same = detect(base, DAY).iloc[0]["z"]
    assert detect(pd.concat([base, future]), DAY).iloc[0]["z"] == pytest.approx(same)


def test_groups_are_independent_and_sorted_by_z():
    series = {("UP", ARMED): [8] * 14 + [12] * 14, ("IR", "Protest & unrest"): [8] * 14 + [12] * 14}
    out = detect(counts_frame(series, {("UP", ARMED): 20, ("IR", "Protest & unrest"): 30}), DAY)
    assert list(out["country_code"]) == ["IR", "UP"]
    assert out["z"].is_monotonic_decreasing


def test_empty_input():
    assert detect(pd.DataFrame(columns=["day", "country_code", "category", "count"]), DAY).empty


# ---- with the database -----------------------------------------------------------------------


def add_events(conn, day, n, country="UP", category=ARMED):
    conn.execute(
        """
        INSERT INTO events (global_event_id, event_date, date_added, country_code, category)
        SELECT (SELECT coalesce(max(global_event_id), 0) FROM events) + g, %s, %s, %s, %s
        FROM generate_series(1, %s) g
        """,
        (day, f"{day} 00:00+00", country, category, n),
    )
    conn.commit()


def seed_history(conn, days_back=29, per_day=10):
    for d in range(1, days_back + 1):
        add_events(conn, DAY - timedelta(days=d), per_day)


def spike_rows(conn):
    return conn.execute(
        "SELECT country_code, category, day, count, baseline_median FROM spikes"
    ).fetchall()


def test_run_stores_spike_with_its_inputs(conn):
    seed_history(conn)
    add_events(conn, DAY, 20)
    out = run(conn, DAY, z_threshold=3, min_count=10)
    assert len(out) == 1
    assert spike_rows(conn) == [("UP", ARMED, DAY, 20, 10.0)]  # flat 10/day -> median 10


def test_run_twice_does_not_duplicate_and_drops_stale_rows(conn):
    seed_history(conn)
    add_events(conn, DAY, 20)
    run(conn, DAY, z_threshold=3, min_count=10)
    run(conn, DAY, z_threshold=3, min_count=10)
    assert len(spike_rows(conn)) == 1
    run(conn, DAY, z_threshold=99, min_count=10)  # stricter: the stored spike must disappear
    assert spike_rows(conn) == []


def test_run_skips_when_history_is_too_short(conn):
    seed_history(conn, days_back=10)
    add_events(conn, DAY, 50)
    assert run(conn, DAY).empty
    assert spike_rows(conn) == []
