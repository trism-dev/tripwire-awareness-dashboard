"""Apply the trained classifier to events and store the result in events.quality_score (0 to 1)."""

import argparse
from pathlib import Path

import joblib
import pandas as pd
import psycopg

from tripwire.db import connect
from tripwire.quality.features import EVENT_COLUMNS, FEATURES, build_features
from tripwire.quality.train import MODEL_PATH


def load_artifact(path: Path = MODEL_PATH) -> dict | None:
    """The saved model bundle, or None if no model has been trained yet."""
    return joblib.load(path) if Path(path).exists() else None


def score_frame(artifact: dict, events: pd.DataFrame) -> pd.Series:
    """Probability each event is credible, indexed like `events`."""
    X = build_features(events, artifact["domain_counts"])
    assert list(X.columns) == artifact["features"] == FEATURES  # model and code must agree
    return pd.Series(artifact["model"].predict_proba(X)[:, 1], index=events.index)


def score_missing(
    conn: psycopg.Connection, artifact: dict, batch: int = 20_000, max_rows: int | None = None
) -> int:
    """Score events that have no quality_score yet, `batch` at a time. Returns how many were scored."""
    columns = ", ".join(EVENT_COLUMNS)
    scored = 0
    while max_rows is None or scored < max_rows:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {columns} FROM events WHERE quality_score IS NULL ORDER BY global_event_id LIMIT %s",
                (batch,),
            )
            rows = cur.fetchall()
            names = [c.name for c in cur.description]
        if not rows:
            break
        events = pd.DataFrame(rows, columns=names)
        scores = score_frame(artifact, events)
        conn.execute(
            """
            UPDATE events e SET quality_score = v.score
            FROM (SELECT unnest(%s::bigint[]) AS id, unnest(%s::real[]) AS score) v
            WHERE e.global_event_id = v.id
            """,
            (events["global_event_id"].tolist(), scores.tolist()),
        )
        conn.commit()
        scored += len(rows)
    return scored


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--all",
        action="store_true",
        help="forget old scores and rescore everything (after retraining)",
    )
    args = ap.parse_args()
    model = load_artifact()
    if model is None:
        raise SystemExit("No trained model. Run: make train")
    with connect() as c:
        if args.all:
            c.execute("UPDATE events SET quality_score = NULL")
            c.commit()
        print("scored", score_missing(c, model), "events")
