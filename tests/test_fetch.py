import hashlib
from datetime import UTC, datetime

from tripwire.gdelt.fetch import (
    file_url,
    floor_to_slot,
    md5_matches,
    parse_manifest,
    slots_between,
    to_https,
)

MANIFEST = (
    "30412 a77822bfea298e8e6c49fa539af5258c "
    "http://data.gdeltproject.org/gdeltv2/20261004184500.export.CSV.zip\n"
    "9999 bbb http://data.gdeltproject.org/gdeltv2/20261004184500.mentions.CSV.zip\n"
)


def test_parse_manifest_takes_first_line_and_upgrades_to_https():
    url, md5 = parse_manifest(MANIFEST)
    assert url == "https://data.gdeltproject.org/gdeltv2/20261004184500.export.CSV.zip"
    assert md5 == "a77822bfea298e8e6c49fa539af5258c"


def test_to_https_leaves_https_alone():
    assert to_https("https://x/y") == "https://x/y"


def test_file_url_and_slots():
    t = datetime(2026, 10, 4, 18, 52, 31, tzinfo=UTC)
    assert floor_to_slot(t) == datetime(2026, 10, 4, 18, 45, tzinfo=UTC)
    assert file_url(floor_to_slot(t)).endswith("/20261004184500.export.CSV.zip")
    slots = slots_between(
        datetime(2026, 10, 4, 0, 7, tzinfo=UTC), datetime(2026, 10, 4, 1, 0, tzinfo=UTC)
    )
    assert [s.strftime("%H%M") for s in slots] == ["0000", "0015", "0030", "0045", "0100"]


def test_md5_matches():
    data = b"hello"
    assert md5_matches(data, hashlib.md5(data).hexdigest())
    assert md5_matches(data, hashlib.md5(data).hexdigest().upper())
    assert not md5_matches(data, "0" * 32)
