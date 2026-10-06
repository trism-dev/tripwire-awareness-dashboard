"""FIPS 10-4 country code -> country name.

GDELT uses FIPS codes, not ISO ones (UP is Ukraine, not UA). The names come from GDELT's own
lookup file, copied to tripwire/data/fips_countries.tsv.
"""

from functools import cache
from pathlib import Path

_FILE = Path(__file__).parent / "data" / "fips_countries.tsv"

# Codes that appear in GDELT's event data but not in its lookup file.
_EXTRA = {"RB": "Serbia", "OC": "Ocean (international waters)"}


@cache
def _names() -> dict[str, str]:
    names = {}
    for line in _FILE.read_text(encoding="utf-8-sig").splitlines():
        code, _, name = line.partition("\t")
        if code and name:
            names[code.strip()] = name.strip()
    return {**names, **_EXTRA}


def country_name(code: str | None) -> str:
    """Country name for a FIPS code; an unknown code is returned unchanged."""
    if not code:
        return "Unknown"
    return _names().get(code, code)
