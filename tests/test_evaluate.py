from datetime import timedelta

import pandas as pd

from tests.test_spikes import ARMED, DAY, add_events, seed_history
from tripwire import evaluate
from tripwire.evaluate import DetectorConfig


def gold_rows(*rows):
    return pd.DataFrame(
        rows, columns=["day", "country_code", "category", "verdict", "reason", "split"]
    )


def test_is_flagged_follows_the_config(conn):
    seed_history(conn)  # 10 articles a day for 29 days, country UP
    add_events(conn, DAY, 20)  # a jump to 20 today
    assert evaluate.is_flagged(conn, DAY, "UP", ARMED, DetectorConfig(z=3, min_count=10))
    assert not evaluate.is_flagged(
        conn, DAY, "UP", ARMED, DetectorConfig(z=3, min_count=25)
    )  # floor too high
    assert not evaluate.is_flagged(
        conn, DAY, "UP", ARMED, DetectorConfig(z=99, min_count=10)
    )  # z too high


def test_alert_precision_counts_yes_no_unclear_among_flagged(conn):
    seed_history(conn)
    add_events(conn, DAY, 20)  # UP flagged today
    add_events(conn, DAY - timedelta(days=40), 1)  # unrelated row so other groups exist
    gold = gold_rows(
        (DAY, "UP", ARMED, "Yes", "", "dev"),
        (DAY, "IS", ARMED, "No", "misread_type", "dev"),  # IS has no events: never flagged
        (
            DAY,
            "UP",
            "Mass violence",
            "Unclear",
            "",
            "dev",
        ),  # no events in that category: not flagged
        (DAY, "UP", ARMED, "", "", "dev"),  # not judged yet: ignored
    )
    r = evaluate.alert_precision(conn, gold, DetectorConfig())
    assert r["judged"] == 3  # the unjudged row is not counted
    assert (r["flagged"], r["yes"], r["no"], r["unclear"]) == (1, 1, 0, 0)
    assert r["precision"] == 1.0 and (r["kept_yes"], r["total_yes"]) == (1, 1)
    strict = evaluate.alert_precision(conn, gold, DetectorConfig(min_count=25))
    assert (
        strict["flagged"] == 0 and strict["precision"] is None
    )  # nothing flagged: precision undefined
    assert (strict["kept_yes"], strict["total_yes"]) == (0, 1)  # and the real alert was lost


def test_alerts_per_day_is_the_average_over_complete_days(conn):
    seed_history(conn, days_back=45)
    add_events(conn, DAY - timedelta(days=1), 20)  # one spike on one of the last 4 days
    assert evaluate.alerts_per_day(conn, DetectorConfig(), days=4, today=DAY) == 0.25


def test_alert_precision_with_nothing_judged_yet(conn):
    """The 'final' split starts with no verdicts; the report must still work."""
    gold = gold_rows((DAY, "UP", ARMED, "", "", "final"))
    r = evaluate.alert_precision(conn, gold, DetectorConfig())
    assert r == {
        "judged": 0,
        "flagged": 0,
        "yes": 0,
        "no": 0,
        "unclear": 0,
        "precision": None,
        "kept_yes": 0,
        "total_yes": 0,
    }
