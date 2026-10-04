"""Turn one GDELT events export (.zip of a tab-delimited file) into a DataFrame."""

import io
import zipfile

import pandas as pd

from tripwire.gdelt.schema import COLUMNS, FLOAT_COLUMNS, INT_COLUMNS


def parse_events(zip_bytes: bytes) -> tuple[pd.DataFrame, int]:
    """Return (events, bad_rows).

    bad_rows counts lines that did not have exactly 61 fields (e.g. a cut-off last line).
    A corrupt or truncated zip raises zipfile.BadZipFile; the caller decides what to do.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        text = zf.read(zf.namelist()[0]).decode("utf-8", errors="replace")
    return parse_text(text)


def parse_text(text: str) -> tuple[pd.DataFrame, int]:
    good, bad = [], 0
    for line in text.splitlines():
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) == len(COLUMNS):
            good.append(fields)
        else:
            bad += 1
    df = pd.DataFrame(good, columns=COLUMNS, dtype="string")
    df = df.replace("", pd.NA)
    return _cast(df), bad


def _cast(df: pd.DataFrame) -> pd.DataFrame:
    for col in INT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in FLOAT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["SQLDATE"] = pd.to_datetime(df["SQLDATE"], format="%Y%m%d", errors="coerce")
    df["DATEADDED"] = pd.to_datetime(
        df["DATEADDED"], format="%Y%m%d%H%M%S", utc=True, errors="coerce"
    )
    return df
