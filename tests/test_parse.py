import io
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from tripwire.gdelt.parse import parse_events, parse_text
from tripwire.gdelt.schema import COLUMNS

FIXTURE = Path(__file__).parent / "fixtures" / "sample.export.CSV"


def make_zip(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("20261004184500.export.CSV", text)
    return buf.getvalue()


def test_column_count_and_ends():
    assert len(COLUMNS) == 61
    assert len(set(COLUMNS)) == 61
    assert COLUMNS[0] == "GLOBALEVENTID"
    assert COLUMNS[25] == "IsRootEvent"
    assert COLUMNS[28] == "EventRootCode"
    assert COLUMNS[29] == "QuadClass"
    assert COLUMNS[51] == "ActionGeo_Type"
    assert COLUMNS[56] == "ActionGeo_Lat"
    assert COLUMNS[59] == "DATEADDED"
    assert COLUMNS[60] == "SOURCEURL"


def test_parses_fixture_rows():
    df, bad = parse_text(FIXTURE.read_text(encoding="utf-8"))
    assert bad == 0
    assert len(df) == 7
    assert list(df.columns) == COLUMNS


def test_cameo_codes_keep_leading_zeros():
    df, _ = parse_text(FIXTURE.read_text(encoding="utf-8"))
    row = df[df["GLOBALEVENTID"] == 1326273896].iloc[0]
    assert row["EventCode"] == "013"
    assert row["EventBaseCode"] == "013"
    assert row["EventRootCode"] == "01"


def test_empty_becomes_null_and_numbers_cast():
    df, _ = parse_text(FIXTURE.read_text(encoding="utf-8"))
    no_geo = df[df["GLOBALEVENTID"] == 1326273952].iloc[0]
    assert pd.isna(no_geo["ActionGeo_Lat"])
    assert pd.isna(no_geo["ActionGeo_CountryCode"])
    ok = df[df["GLOBALEVENTID"] == 1326273973].iloc[0]
    assert ok["ActionGeo_Lat"] == pytest.approx(48.2)
    assert ok["QuadClass"] == 4
    assert ok["DATEADDED"].tzinfo is not None


def test_zip_roundtrip():
    df, bad = parse_events(make_zip(FIXTURE.read_text(encoding="utf-8")))
    assert (len(df), bad) == (7, 0)


def test_malformed_and_cut_off_rows_are_counted_not_fatal():
    good = FIXTURE.read_text(encoding="utf-8").splitlines()
    text = "\n".join([good[0], "only\tthree\tfields", good[1][:200]]) + "\n"
    df, bad = parse_text(text)
    assert len(df) == 1
    assert bad == 2


def test_truncated_zip_raises():
    data = make_zip(FIXTURE.read_text(encoding="utf-8"))
    with pytest.raises(zipfile.BadZipFile):
        parse_events(data[: len(data) // 2])
