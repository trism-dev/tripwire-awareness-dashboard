"""Small helpers shared by the Streamlit pages."""


def safe_url(url) -> str | None:
    """GDELT URLs are untrusted input: only ever link http(s), never javascript: and the like."""
    return url if isinstance(url, str) and url.startswith(("http://", "https://")) else None
