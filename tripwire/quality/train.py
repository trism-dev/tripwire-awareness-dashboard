"""Train and honestly evaluate the signal-quality classifier (PRD 5.5, S1).

Label = 1 if a hand-labeled event is credible. Model = logistic regression. Every number reported
here is computed on data the model did not train on: 5-fold cross-validation inside the training
part, and a test part (about 30%) that is touched once. The test part is chosen by a hash of the
event id, so it is FROZEN: labeling more events never moves an old test row into training.
"""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from tripwire.db import connect
from tripwire.quality.features import (
    DEFAULT_GROUPS,
    EVENT_COLUMNS,
    build_features,
    feature_names,
    load_domain_counts,
    top_codes,
)

SEED = 42
MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_PATH = MODEL_DIR / "quality_model.joblib"
METRICS_PATH = MODEL_DIR / "quality_metrics.json"


TEST_BUCKETS = 3  # of 10: events whose id hashes into buckets 0-2 are the frozen test set


def is_test_event(event_id: int) -> bool:
    """True if this event belongs to the frozen test set. A pure function of the id."""
    bucket = int(hashlib.md5(str(int(event_id)).encode()).hexdigest(), 16) % 10
    return bucket < TEST_BUCKETS


def make_model() -> Pipeline:
    return Pipeline(
        [
            ("fill", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),  # puts features on one scale so coefficients compare
            ("model", LogisticRegression(max_iter=1000, random_state=SEED)),
        ]
    )


def load_labeled(conn) -> pd.DataFrame:
    """Labeled events: the events columns the features need, plus `label`."""
    columns = ", ".join(f"e.{c}" for c in EVENT_COLUMNS)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {columns}, l.label FROM labels l JOIN events e USING (global_event_id)"
        )
        rows = cur.fetchall()
        names = [c.name for c in cur.description]
    return pd.DataFrame(rows, columns=names)


def precision_at_recall(y_true, proba, recall_target: float = 0.6) -> float:
    """Best precision achievable while still finding at least `recall_target` of the credible events.
    'If I want most of the good events, how clean is my pile?'"""
    y_true = np.asarray(y_true)
    if len(set(y_true)) < 2:
        return 0.0
    precision, recall, _ = precision_recall_curve(y_true, proba)
    ok = precision[recall >= recall_target]
    return float(ok.max()) if ok.size else 0.0


def precision_in_top(y_true, proba, fraction: float = 0.2) -> float:
    """Share of credible events among the top `fraction` by score (ties are all included, so a
    model that scores everything the same gets the plain base rate)."""
    y_true, proba = np.asarray(y_true), np.asarray(proba)
    chosen = proba >= np.quantile(proba, 1 - fraction)
    return float(y_true[chosen].mean())


def evaluate(y_true, proba, threshold: float = 0.5) -> dict:
    """The standard report for one set of predictions (positive class = credible)."""
    y_true = np.asarray(y_true)
    pred = (np.asarray(proba) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    both_classes = len(set(y_true)) == 2
    return {
        "n": len(y_true),
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, pred)),
        "roc_auc": float(roc_auc_score(y_true, proba)) if both_classes else None,
        "precision_at_60_recall": precision_at_recall(y_true, proba, 0.6),
        "precision_top_20pct": precision_in_top(y_true, proba, 0.2),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def bootstrap_auc_interval(y_true, proba, rounds: int = 1000, seed: int = SEED) -> list[float]:
    """95% interval for ROC-AUC by resampling the test set. A small test set means a wide one."""
    y_true, proba = np.asarray(y_true), np.asarray(proba)
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(rounds):
        pick = rng.integers(0, len(y_true), len(y_true))
        if len(set(y_true[pick])) == 2:
            scores.append(roc_auc_score(y_true[pick], proba[pick]))
    return [float(np.percentile(scores, 2.5)), float(np.percentile(scores, 97.5))]


def _baselines(y, X) -> dict:
    """Two things the model must beat: always say credible, and a one-line rule."""
    return {
        "always_credible": evaluate(y, np.ones(len(y))),
        "rule_geo_type_at_least_3": evaluate(y, (X["geo_type"].fillna(0) >= 3).astype(float)),
    }


def _mean_std(per_fold: list[dict], key: str) -> dict:
    values = [f[key] for f in per_fold if f[key] is not None]
    return {"mean": float(np.mean(values)), "std": float(np.std(values))}


def train(
    conn,
    model_path: Path = MODEL_PATH,
    metrics_path: Path = METRICS_PATH,
    groups: tuple[str, ...] = DEFAULT_GROUPS,
) -> dict:
    df = load_labeled(conn)
    y = df["label"].to_numpy()
    if len(df) < 40 or len(set(y)) < 2:
        raise ValueError(f"need at least 40 labels of both kinds, have {len(df)}")
    counts = load_domain_counts(conn)
    codes = top_codes(conn) if "codes" in groups else ()
    X = build_features(df, counts, codes, groups)
    names = feature_names(codes, groups)

    # Frozen split: the test part is decided by a hash of the event id (see is_test_event).
    in_test = df["global_event_id"].map(is_test_event).to_numpy()
    X_train, X_test = X[~in_test], X[in_test]
    y_train, y_test = y[~in_test], y[in_test]

    # 5-fold cross-validation on the TRAINING part only: model vs always-credible, fold by fold.
    folds, base_folds = [], []
    for fit_idx, val_idx in StratifiedKFold(5, shuffle=True, random_state=SEED).split(
        X_train, y_train
    ):
        model = make_model().fit(X_train.iloc[fit_idx], y_train[fit_idx])
        proba = model.predict_proba(X_train.iloc[val_idx])[:, 1]
        folds.append(evaluate(y_train[val_idx], proba))
        base_folds.append(evaluate(y_train[val_idx], np.ones(len(val_idx))))

    # The test part is used once, with the model fitted on the training part.
    model = make_model().fit(X_train, y_train)
    test_proba = model.predict_proba(X_test)[:, 1]
    coefficients = dict(zip(names, model.named_steps["model"].coef_[0].round(3), strict=True))

    metrics = {
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "model": "logistic regression (median imputer + standard scaler)",
        "features": names,
        "feature_groups": list(groups),
        "event_codes": list(codes),
        "labels": {"total": len(y), "credible": int(y.sum()), "share_credible": float(y.mean())},
        "split": {"train": len(y_train), "test": len(y_test), "method": "hash of event id"},
        "cross_validation_on_train_5fold": {
            "model": {
                k: _mean_std(folds, k)
                for k in (
                    "precision",
                    "recall",
                    "f1",
                    "roc_auc",
                    "precision_at_60_recall",
                    "precision_top_20pct",
                )
            },
            "always_credible": {k: _mean_std(base_folds, k) for k in ("precision", "recall", "f1")},
        },
        "test": {
            "model": evaluate(y_test, test_proba),
            "roc_auc_95_interval": bootstrap_auc_interval(y_test, test_proba),
            **_baselines(y_test, X_test),
        },
        "coefficients_standardized": coefficients,
        "note": "Reported metrics come from the model fitted on the training split. The saved model "
        "is refitted on all labels, so it has seen the test rows and is not evaluated again.",
    }

    final = make_model().fit(X, y)  # the model that scores events: all the labels we have
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": final,
            "features": names,
            "groups": groups,
            "code_levels": codes,
            "domain_counts": counts,
            "seed": SEED,
        },
        model_path,
    )
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    with connect() as c:
        result = train(c)
    t, cv = result["test"], result["cross_validation_on_train_5fold"]
    print(f"labels: {result['labels']}   split: {result['split']}")
    print(
        f"CV (train, 5-fold) model F1 {cv['model']['f1']['mean']:.3f} +/- {cv['model']['f1']['std']:.3f}, "
        f"AUC {cv['model']['roc_auc']['mean']:.3f}; always-credible F1 {cv['always_credible']['f1']['mean']:.3f}"
    )
    for name in ("model", "always_credible", "rule_geo_type_at_least_3"):
        m = t[name]
        print(
            f"TEST {name:26s} P {m['precision']:.2f}  R {m['recall']:.2f}  F1 {m['f1']:.2f}  AUC {m['roc_auc']}  "
            f"P@60%recall {m['precision_at_60_recall']:.2f}  P@top20% {m['precision_top_20pct']:.2f}  {m['confusion_matrix']}"
        )
    print("TEST AUC 95% interval:", [round(x, 2) for x in t["roc_auc_95_interval"]])
    sys.stdout.flush()
