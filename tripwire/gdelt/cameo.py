"""CAMEO event code -> plain-English description.

Descriptions come from GDELT's lookup file, copied to tripwire/data/cameo_eventcodes.tsv.
"""

from functools import cache
from pathlib import Path

_FILE = Path(__file__).resolve().parent.parent / "data" / "cameo_eventcodes.tsv"


@cache
def _descriptions() -> dict[str, str]:
    out = {}
    for line in _FILE.read_text(encoding="utf-8-sig").splitlines()[1:]:  # skip header row
        code, _, text = line.partition("\t")
        if code and text:
            out[code.strip()] = text.strip()
    return out


def event_description(code: str | None) -> str:
    """Description of a CAMEO code. A few codes in the data are missing from GDELT's lookup
    (e.g. 106), so we fall back to the parent code: 1213 -> 121 -> 12."""
    if not code or not code.isdigit():
        return "Unknown event type"
    descriptions = _descriptions()
    for length in range(len(code), 1, -1):
        found = descriptions.get(code[:length])
        if found:
            return found if length == len(code) else f"{found} (general)"
    return "Unknown event type"
