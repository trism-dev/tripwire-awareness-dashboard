"""Talk to GDELT: manifest, file URLs, download, md5 check. No parsing here."""

import hashlib
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

BASE_URL = "https://data.gdeltproject.org/gdeltv2"
MANIFEST_URL = f"{BASE_URL}/lastupdate.txt"
SLOT = timedelta(minutes=15)
_HEADERS = {"User-Agent": "tripwire-awareness-dashboard (portfolio project)"}


def to_https(url: str) -> str:
    """The manifest lists http:// URLs, which redirect (empty 301) to https://."""
    return "https://" + url.removeprefix("http://").removeprefix("https://")


def parse_manifest(text: str) -> tuple[str, str]:
    """First line is '<size> <md5> <url>' for the newest export. Returns (url, md5)."""
    _size, md5, url = text.splitlines()[0].split()
    return to_https(url), md5


def file_url(slot: datetime) -> str:
    return f"{BASE_URL}/{slot:%Y%m%d%H%M%S}.export.CSV.zip"


def floor_to_slot(ts: datetime) -> datetime:
    return ts.replace(minute=ts.minute - ts.minute % 15, second=0, microsecond=0)


def slots_between(start: datetime, end: datetime) -> list[datetime]:
    """Every 15-minute slot from start to end (UTC), oldest first."""
    slot, out = floor_to_slot(start), []
    while slot <= end:
        out.append(slot)
        slot += SLOT
    return out


def download(url: str, retries: int = 3, timeout: int = 60) -> bytes:
    """GET with retries and backoff. A 404 is not retried: GDELT really does skip slots."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


def latest_manifest() -> tuple[str, str]:
    return parse_manifest(download(MANIFEST_URL).decode("utf-8"))


def md5_matches(data: bytes, expected: str) -> bool:
    return hashlib.md5(data).hexdigest() == expected.lower()
