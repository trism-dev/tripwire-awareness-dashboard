"""The alert gold set: spikes a human has judged, used to measure alert accuracy before and after
every change. Stored as a CSV in docs/ so it is versioned and reproducible.

    python -m tripwire.gold draw     # pick new spikes to audit and write the checklist
"""

import random
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from tripwire import queries
from tripwire.db import connect
from tripwire.fips import country_name
from tripwire.gdelt.cameo import event_description

DOCS = Path(__file__).resolve().parent.parent / "docs"
GOLD_PATH = DOCS / "spike_gold_set.csv"
CHECKLIST_PATH = DOCS / "spike_audit_checklist.md"
COLUMNS = ["day", "country_code", "category", "verdict", "reason", "split"]
VERDICTS = ("Yes", "No", "Unclear")
REASONS = ("misread_type", "duplicate_story", "old_event", "wrong_place", "other")
SEED = 2026


def load_gold(path: Path = GOLD_PATH) -> pd.DataFrame:
    """The judged spikes. Rows still waiting for a verdict have an empty verdict."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df["day"] = pd.to_datetime(df["day"]).dt.date
    return df[COLUMNS]


def judged(gold: pd.DataFrame) -> pd.DataFrame:
    return gold[gold["verdict"].isin(VERDICTS)]


def draw_sample(
    spikes: list[tuple], n: int, exclude: set[tuple], seed: int = SEED
) -> list[tuple[tuple, str]]:
    """Pick n spikes (day, country, category, score), spread over the score ranking, and give each a
    dev/final label. Thirds of the ranking are sampled evenly so weak alerts are tested, not just the
    headline ones; within each third, dev and final alternate so both sets cover the whole range.

    Returns [((day, country, category), split), ...].
    """
    pool = [s for s in sorted(spikes, key=lambda s: -s[3]) if s[:3] not in exclude]
    third = len(pool) // 3
    parts = [pool[:third], pool[third : 2 * third], pool[2 * third :]]
    per_part = [n // 3 + (1 if i < n % 3 else 0) for i in range(3)]
    rng = random.Random(seed)
    out = []
    for p, (part, k) in enumerate(zip(parts, per_part, strict=True)):
        picked = rng.sample(part, k)
        for i, spike in enumerate(sorted(picked, key=lambda s: -s[3])):
            # the start alternates per third, so odd-sized thirds still balance overall
            out.append((spike[:3], "dev" if (i + p) % 2 == 0 else "final"))
    return out


def evidence(conn, day: date, country: str, category: str, limit: int = 3) -> list[tuple]:
    """The best-sourced distinct articles behind a spike: (url, event code, actor 1, actor 2, place,
    sources). The same query the Alerts tab uses."""
    df = queries.spike_evidence(conn, day, country, category, limit)
    return [
        tuple(
            None if pd.isna(v) else v
            for v in (
                r.source_url,
                r.event_code,
                r.actor1_name,
                r.actor2_name,
                r.geo_fullname,
                r.num_sources,
            )
        )
        for r in df.itertuples()
    ]


def write_checklist(conn, sample: list[tuple[tuple, str]], path: Path = CHECKLIST_PATH) -> None:
    lines = [
        "# Spike audit checklist",
        "",
        (
            "For each spike open the links and answer: **do these articles describe a real increase in this "
            "kind of event, in this country, on this day?** Reply with one line per number, e.g. "
            "`1 Y, 2 N misread_type, 3 U, 4 N duplicate_story`."
        ),
        "",
        "- **Y** (Yes): at least 2 of the 3 articles show a real event of the right type in the right country.",
        (
            "- **N** (No) plus a reason: `misread_type` (not really this kind of event, e.g. a court case coded "
            "as military force), `duplicate_story` (the same story already counted as another alert), "
            "`old_event` (an old event being rehashed), `wrong_place`, or `other`."
        ),
        "- **U** (Unclear): you cannot tell.",
        "",
    ]
    for i, ((day, country, category), _split) in enumerate(sample, 1):
        count, median, z = conn.execute(
            "SELECT count, baseline_median, z FROM spikes WHERE day = %s AND country_code = %s AND category = %s",
            (day, country, category),
        ).fetchone()
        lines.append(
            f"## {i}. {country_name(country)} - {category} - {day}  "
            f"({count} articles; typical day {median:.1f}; score {z:.1f})"
        )
        lines.append("")
        for url, code, a1, a2, place, ns in evidence(conn, day, country, category):
            lines.append(f"- {url}")
            lines.append(
                f"  coded as: {event_description(code)} | {a1 or '?'} -> {a2 or '?'} | {place} | {ns} source(s)"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def draw_and_write(n: int = 40) -> None:
    gold = load_gold()
    seen = {
        (d, c, k)
        for d, c, k in zip(gold["day"], gold["country_code"], gold["category"], strict=True)
    }
    with connect() as conn:
        today = datetime.now(UTC).date()
        spikes = conn.execute(
            "SELECT day, country_code, category, z FROM spikes WHERE day < %s", (today,)
        ).fetchall()
        sample = draw_sample(spikes, n, seen)
        write_checklist(conn, sample)
    new = pd.DataFrame(
        [
            {
                "day": d,
                "country_code": c,
                "category": k,
                "verdict": "",
                "reason": "",
                "split": split,
            }
            for (d, c, k), split in sample
        ]
    )
    pd.concat([gold, new]).to_csv(GOLD_PATH, index=False)
    print(f"drew {len(sample)} spikes; checklist: {CHECKLIST_PATH}")


if __name__ == "__main__":
    if sys.argv[1:] == ["draw"]:
        draw_and_write()
    else:
        sys.exit("usage: python -m tripwire.gold draw")
