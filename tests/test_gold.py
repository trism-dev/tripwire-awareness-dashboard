import random
from datetime import date

import pandas as pd
import pytest

from tripwire import gold


def fake_spikes(n=90):
    rng = random.Random(1)
    return [
        (date(2026, 9, 1 + i % 28), f"C{i}", "Armed conflict", rng.random() * 30) for i in range(n)
    ]


def test_load_gold_reads_the_committed_file():
    df = gold.load_gold()
    assert list(df.columns) == gold.COLUMNS
    assert len(df) >= 10
    assert set(df["split"]) <= {"dev", "final"}
    assert set(df["verdict"]) <= {"Yes", "No", "Unclear", ""}
    tags = {tag for reason in df["reason"] for tag in reason.split("+") if reason}
    assert tags <= set(gold.REASONS)  # a spike can have several reasons, joined with "+"
    assert all(
        r == "" for r, v in zip(df["reason"], df["verdict"], strict=True) if v == "Yes"
    )  # a Yes has no reason
    keys = list(zip(df["day"], df["country_code"], df["category"], strict=True))
    assert len(keys) == len(set(keys))  # no spike judged twice


def test_judged_ignores_rows_without_a_verdict():
    df = pd.DataFrame({"verdict": ["Yes", "", "No", "Unclear"]})
    assert list(gold.judged(df)["verdict"]) == ["Yes", "No", "Unclear"]


def test_draw_sample_is_reproducible_excludes_seen_and_balances_splits():
    spikes = fake_spikes()
    exclude = {spikes[0][:3], spikes[1][:3]}
    a = gold.draw_sample(spikes, 40, exclude)
    assert a == gold.draw_sample(spikes, 40, exclude)  # same seed, same sample
    keys = [k for k, _ in a]
    assert len(keys) == 40 and len(set(keys)) == 40
    assert not exclude & set(keys)
    splits = [s for _, s in a]
    assert splits.count("dev") == splits.count("final") == 20


def test_draw_sample_covers_the_whole_score_range():
    spikes = fake_spikes(300)
    scores = {s[:3]: s[3] for s in spikes}
    picked = [scores[k] for k, _ in gold.draw_sample(spikes, 30, set())]
    ranked = sorted(scores.values(), reverse=True)
    top, bottom = ranked[99], ranked[199]  # last of the top third, last of the middle
    assert sum(p >= top for p in picked) == 10  # exactly a third from the top third
    assert sum(p < bottom for p in picked) == 10


def test_draw_sample_rejects_asking_for_more_than_exist():
    with pytest.raises(ValueError):
        gold.draw_sample(fake_spikes(6), 40, set())
