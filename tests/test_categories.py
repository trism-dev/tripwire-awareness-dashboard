import pandas as pd

from tripwire.gdelt.categories import (
    _BUCKETS,
    ARMED,
    CATEGORY_BY_ROOT,
    COOPERATION,
    OTHER_CONFLICT,
    PROTEST,
    add_category,
)


def test_every_root_01_to_20_maps_to_exactly_one_category():
    roots = [f"{n:02d}" for n in range(1, 21)]
    assert set(CATEGORY_BY_ROOT) == set(roots)  # none missing, none extra
    # a dict can't hold a root twice, so check the source buckets don't overlap
    all_listed = [r for roots_ in _BUCKETS.values() for r in roots_]
    assert len(all_listed) == len(set(all_listed)) == 20


def test_known_mappings():
    assert CATEGORY_BY_ROOT["14"] == PROTEST
    assert CATEGORY_BY_ROOT["19"] == ARMED
    assert CATEGORY_BY_ROOT["16"] == OTHER_CONFLICT
    assert CATEGORY_BY_ROOT["05"] == COOPERATION


def test_add_category_and_unknown_root():
    df = pd.DataFrame({"EventRootCode": ["14", "20", "99", None]})
    out = add_category(df)
    assert out["category"].tolist()[:2] == [PROTEST, "Mass violence"]
    assert out["category"].isna().tolist() == [False, False, True, True]
    assert "category" not in df.columns  # input untouched
