"""One command to measure accuracy: `make evaluate`.

Prints (1) the event-quality model's test metrics next to the saved baseline, (2) how the alert
detector does on the hand-judged gold set (dev and final reported separately), and (3) how many
alerts it raises per day. Every refinement is judged with this same report.
"""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import numpy as np
import pandas as pd

from tripwire import spikes
from tripwire.config import load_settings
from tripwire.db import connect
from tripwire.gold import judged, load_gold
from tripwire.quality.train import METRICS_PATH

BASELINE_PATH = METRICS_PATH.parent / "baseline_metrics.json"


@dataclass(frozen=True)
class DetectorConfig:
    """The alert detector's knobs. Defaults come from the environment settings."""

    z: float = 3.0
    min_count: int = 10


def current_config() -> DetectorConfig:
    s = load_settings()
    return DetectorConfig(z=s.spike_z, min_count=s.spike_min_count)


def is_flagged(conn, day: date, country: str, category: str, cfg: DetectorConfig) -> bool:
    """Would the detector, with this config, still raise an alert for this country/category/day?"""
    counts = spikes.daily_counts(conn, day - timedelta(days=60), day, country, category)
    row = spikes.trend(counts, day, 1, cfg.z, cfg.min_count).iloc[0]
    return bool(row["flagged"])


def alert_precision(conn, gold: pd.DataFrame, cfg: DetectorConfig) -> dict:
    """Among the judged spikes that this config still flags: how many are real?

    precision = Yes / (Yes + No) over flagged spikes ('Unclear' is reported, not counted);
    kept_yes = how many of the real spikes survive (recall on the gold set).
    """
    gold = judged(gold)
    flags = [
        is_flagged(conn, d, c, k, cfg)
        for d, c, k in zip(gold["day"], gold["country_code"], gold["category"], strict=True)
    ]
    kept = gold[np.array(flags, dtype=bool)]  # a boolean mask (an empty list would pick columns)
    yes, no, unclear = (int((kept["verdict"] == v).sum()) for v in ("Yes", "No", "Unclear"))
    total_yes = int((gold["verdict"] == "Yes").sum())
    return {
        "judged": len(gold),
        "flagged": len(kept),
        "yes": yes,
        "no": no,
        "unclear": unclear,
        "precision": yes / (yes + no) if yes + no else None,
        "kept_yes": yes,
        "total_yes": total_yes,
    }


def alerts_per_day(conn, cfg: DetectorConfig, days: int = 32, today: date | None = None) -> float:
    """Average number of alerts per day over the last `days` complete days."""
    today = today or datetime.now(UTC).date()
    counts = spikes.daily_counts(conn, today - timedelta(days=days + spikes.WINDOW_DAYS), today)
    total = sum(
        len(spikes.detect(counts, today - timedelta(days=i), cfg.z, cfg.min_count))
        for i in range(1, days + 1)
    )
    return total / days


def report(conn, cfg: DetectorConfig | None = None) -> dict:
    cfg = cfg or current_config()
    gold = load_gold()
    out = {"config": cfg.__dict__, "alerts_per_day": alerts_per_day(conn, cfg)}
    for split in ("dev", "final"):
        out[f"alerts_{split}"] = alert_precision(conn, gold[gold["split"] == split], cfg)
    return out


def _fmt(p) -> str:
    return "n/a" if p is None else f"{p:.0%}"


def print_report() -> None:
    base = json.loads(BASELINE_PATH.read_text(encoding="utf-8")) if BASELINE_PATH.exists() else None
    now = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    print("== Event quality model (frozen test set) ==")
    rows = [("test ROC-AUC", lambda m: m["test"]["model"]["roc_auc"]),
            ("test AUC lower bound", lambda m: m["test"]["roc_auc_95_interval"][0]),
            ("precision at 60% recall", lambda m: m["test"]["model"]["precision_at_60_recall"]),
            ("precision, top 20%", lambda m: m["test"]["model"]["precision_top_20pct"]),
            ("CV ROC-AUC (train)", lambda m: m["cross_validation_on_train_5fold"]["model"]["roc_auc"]["mean"])]  # fmt: skip
    print(f"{'':26s}{'baseline':>10s}{'now':>10s}")
    for name, get in rows:
        b = f"{get(base):.3f}" if base else "-"
        print(f"{name:26s}{b:>10s}{get(now):>10.3f}")

    print("\n== Alert detector on the hand-judged gold set ==")
    with connect() as conn:
        rep = report(conn)
    print(f"config: {rep['config']}   alerts per day: {rep['alerts_per_day']:.1f}")
    for split in ("dev", "final"):
        a = rep[f"alerts_{split}"]
        print(
            f"{split:6s} judged {a['judged']:>2d} | still flagged {a['flagged']:>2d} "
            f"(yes {a['yes']}, no {a['no']}, unclear {a['unclear']}) | precision {_fmt(a['precision'])} "
            f"| real alerts kept {a['kept_yes']}/{a['total_yes']}"
        )


if __name__ == "__main__":
    print_report()
