import numpy as np
import pandas as pd
import pytest

from tripwire.quality import score as score_module
from tripwire.quality import train as train_module
from tripwire.quality.features import FEATURES, build_features, domain_of
from tripwire.quality.train import (
    bootstrap_auc_interval,
    evaluate,
    is_test_event,
    precision_at_recall,
    precision_in_top,
)

# ---- features ----------------------------------------------------------------------------------


def test_domain_of():
    assert domain_of("https://www.bbc.com/news/x") == "bbc.com"
    assert domain_of("http://Sub.Example.org:8080/a") == "sub.example.org"
    assert domain_of(None) is None
    assert domain_of("not a url") is None


def event_row(**kw):
    row = {
        "num_sources": 3, "num_articles": 5, "num_mentions": 7, "geo_type": 4, "is_root_event": True,
        "goldstein": -6.5, "avg_tone": -2.0, "quad_class": 4, "actor1_name": "POLICE",
        "actor2_name": None, "source_url": "https://www.bbc.com/a", "category": "Armed conflict",
    }  # fmt: skip
    return {**row, **kw}


def test_build_features_hand_checked_values():
    X = build_features(pd.DataFrame([event_row()]), {"bbc.com": 9})
    assert list(X.columns) == FEATURES
    r = X.iloc[0]
    assert r["log_sources"] == pytest.approx(np.log(4))  # log(1 + 3)
    assert (r["geo_type"], r["is_root"], r["quad_class"]) == (4, 1, 4)
    assert (r["has_actor1"], r["has_actor2"]) == (1, 0)
    assert r["log_domain_freq"] == pytest.approx(np.log(10))  # log(1 + 9)
    assert r["cat_Armed conflict"] == 1 and r["cat_Protest & unrest"] == 0


def test_build_features_missing_values_stay_nan_and_unknown_domain_is_zero():
    X = build_features(pd.DataFrame([event_row(goldstein=None, source_url=None)]), {})
    assert np.isnan(X.iloc[0]["goldstein"])
    assert X.iloc[0]["log_domain_freq"] == 0


# ---- metrics -----------------------------------------------------------------------------------


def test_evaluate_hand_computed():
    y = [1, 1, 1, 0, 0, 0, 0, 0]
    proba = [0.9, 0.8, 0.2, 0.7, 0.1, 0.1, 0.1, 0.1]  # at 0.5: predicts 1,1,0,1,0,0,0,0
    m = evaluate(y, proba)
    assert m["confusion_matrix"] == {"tn": 4, "fp": 1, "fn": 1, "tp": 2}
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["recall"] == pytest.approx(2 / 3)
    assert m["f1"] == pytest.approx(2 / 3)
    assert m["accuracy"] == pytest.approx(6 / 8)
    assert m["roc_auc"] == pytest.approx(14 / 15)  # 14 of 15 credible/not pairs ranked right


def test_always_credible_baseline_numbers():
    y = [1, 0, 0, 0]
    m = evaluate(y, np.ones(4))
    assert (m["precision"], m["recall"]) == (0.25, 1.0)
    assert m["f1"] == pytest.approx(0.4)
    assert m["roc_auc"] == 0.5


def test_bootstrap_interval_is_ordered_and_repeatable():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 80)
    proba = np.clip(y * 0.3 + rng.random(80) * 0.7, 0, 1)
    lo, hi = bootstrap_auc_interval(y, proba)
    assert 0.5 < lo < hi <= 1.0
    assert (lo, hi) == tuple(bootstrap_auc_interval(y, proba))


# ---- train + score against the database ---------------------------------------------------------


def seed_labeled(conn, n=80):
    """n events; high geo_type + 'Protest & unrest' means credible. Gives the model real signal."""
    for i in range(n):
        credible = i % 2
        conn.execute(
            """
            INSERT INTO events (global_event_id, event_date, date_added, country_code, category,
                num_sources, num_articles, num_mentions, geo_type, is_root_event, goldstein,
                avg_tone, quad_class, actor1_name, source_url)
            VALUES (%s, current_date, now(), 'UP', %s, 1, 1, 1, %s, true, -5, -2, 4, 'X', %s)
            """,
            (
                i + 1,
                "Protest & unrest" if credible else "Armed conflict",
                4 if credible else 1,
                f"https://site{i % 7}.com/{i}",
            ),
        )
        conn.execute(
            "INSERT INTO labels (global_event_id, label) VALUES (%s, %s)", (i + 1, credible)
        )
    conn.commit()


def test_train_writes_model_and_honest_metrics(conn, tmp_path):
    seed_labeled(conn)
    metrics = train_module.train(conn, tmp_path / "m.joblib", tmp_path / "m.json")
    assert (tmp_path / "m.joblib").exists() and (tmp_path / "m.json").exists()
    n_test = metrics["split"]["test"]
    assert metrics["split"]["train"] + n_test == 80
    assert 10 <= n_test <= 40  # about 30% of 80, chosen by hashing ids
    assert metrics["labels"]["total"] == 80
    assert metrics["features"] == FEATURES
    test = metrics["test"]
    assert test["model"]["roc_auc"] > 0.9  # the planted signal is found
    assert test["always_credible"]["roc_auc"] == 0.5
    assert test["always_credible"]["recall"] == 1.0
    cm = test["model"]["confusion_matrix"]
    assert sum(cm.values()) == n_test  # every test row is counted exactly once


def test_train_refuses_too_few_labels(conn, tmp_path):
    seed_labeled(conn, n=10)
    with pytest.raises(ValueError, match="at least 40"):
        train_module.train(conn, tmp_path / "m.joblib", tmp_path / "m.json")


def test_score_missing_only_fills_empty_scores(conn, tmp_path):
    seed_labeled(conn)
    train_module.train(conn, tmp_path / "m.joblib", tmp_path / "m.json")
    artifact = score_module.load_artifact(tmp_path / "m.joblib")
    conn.execute("UPDATE events SET quality_score = 0.123 WHERE global_event_id <= 10")
    conn.commit()
    assert score_module.score_missing(conn, artifact, batch=25) == 70  # batches of 25, 10 skipped
    assert score_module.score_missing(conn, artifact) == 0  # nothing left to do
    kept = conn.execute(
        "SELECT count(*) FROM events WHERE round(quality_score::numeric, 3) = 0.123"
    ).fetchone()[0]
    assert kept == 10  # existing scores untouched
    high = conn.execute(
        "SELECT avg(quality_score) FROM events WHERE category = 'Protest & unrest' AND global_event_id > 10"
    ).fetchone()[0]
    low = conn.execute(
        "SELECT avg(quality_score) FROM events WHERE category = 'Armed conflict' AND global_event_id > 10"
    ).fetchone()[0]
    assert high > 0.8  # credible-looking events score high
    assert low < 0.2  # the others score low


def test_no_model_file_means_no_artifact(tmp_path):
    assert score_module.load_artifact(tmp_path / "missing.joblib") is None


# ---- frozen split and ranking metrics --------------------------------------------------------


def test_frozen_split_is_deterministic_about_30_percent_and_independent_of_other_rows():
    ids = list(range(1_326_000_000, 1_326_010_000))
    flags = [is_test_event(i) for i in ids]
    assert flags == [is_test_event(i) for i in ids]  # same answer every time
    assert 0.27 < sum(flags) / len(flags) < 0.33
    # an event's side never depends on which other events exist
    assert [is_test_event(i) for i in ids[:50]] == flags[:50]


def test_precision_at_recall_hand_computed():
    y = [1, 1, 0, 1, 0, 0]
    proba = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
    # top 2 are both credible: 2 of 3 credible found (recall 0.67 >= 0.6) at precision 1.0
    assert precision_at_recall(y, proba, 0.6) == pytest.approx(1.0)
    # to find all 3 credible you must go down to 0.6: 3 of 4 chosen are credible
    assert precision_at_recall(y, proba, 1.0) == pytest.approx(0.75)
    assert (
        precision_at_recall([1, 1, 1], [0.1, 0.2, 0.3]) == 0.0
    )  # one class: undefined, reported 0


def test_precision_in_top_hand_computed_and_ties():
    y = np.array([1, 1, 0, 1, 0, 0, 0, 0, 0, 0])
    proba = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05])
    assert precision_in_top(y, proba, 0.2) == pytest.approx(1.0)  # top 2: both credible
    assert precision_in_top(y, proba, 0.4) == pytest.approx(0.75)  # top 4: 3 credible
    assert precision_in_top(y, np.ones(10), 0.2) == pytest.approx(0.3)  # all tied: the base rate


def test_evaluate_reports_the_ranking_metrics():
    y = [1, 1, 0, 1, 0, 0]
    m = evaluate(y, [0.9, 0.8, 0.7, 0.6, 0.5, 0.4])
    assert m["precision_at_60_recall"] == pytest.approx(1.0)
    assert m["precision_top_20pct"] == pytest.approx(1.0)
