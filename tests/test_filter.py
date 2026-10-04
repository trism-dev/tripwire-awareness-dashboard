from pathlib import Path

from tripwire.gdelt.filter import filter_events
from tripwire.gdelt.parse import parse_text

FIXTURE = Path(__file__).parent / "fixtures" / "sample.export.CSV"


def events():
    return parse_text(FIXTURE.read_text(encoding="utf-8"))[0]


def kept_ids(**kwargs):
    return set(filter_events(events(), **kwargs)["GLOBALEVENTID"])


def test_default_keeps_only_root_conflict_with_coordinates():
    # ...973, ...993 (quad 4, root); ...893 (quad 3, root); ...907 is non-root, ...896 is cooperation
    assert kept_ids() == {1326273973, 1326273993, 1326273893}


def test_non_root_allowed_when_configured():
    # adds non-root conflict rows that have coordinates; the no-location row (...952) stays out
    assert kept_ids(root_only=False) == {
        1326273973,
        1326273993,
        1326273893,
        1326273907,  # country-centroid row (geo type 1) is kept at ingest
        1326273927,
    }


def test_country_allowlist():
    assert kept_ids(country_allowlist=frozenset({"US"})) == {1326273893}


def test_zero_zero_coordinates_dropped():
    df = events()
    df.loc[df["GLOBALEVENTID"] == 1326273973, ["ActionGeo_Lat", "ActionGeo_Long"]] = 0
    assert 1326273973 not in set(filter_events(df)["GLOBALEVENTID"])


def test_empty_input():
    assert filter_events(events().iloc[0:0]).empty
