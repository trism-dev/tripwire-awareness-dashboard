from tripwire.config import load_settings


def test_defaults(monkeypatch):
    for k in ("DATABASE_URL", "RETENTION_DAYS", "SPIKE_Z", "SPIKE_MIN_COUNT", "REGION_ALLOWLIST"):
        monkeypatch.delenv(k, raising=False)
    s = load_settings()
    assert (s.retention_days, s.spike_z, s.spike_min_count) == (60, 3.0, 10)
    assert s.region_allowlist == frozenset()


def test_allowlist_parsing(monkeypatch):
    monkeypatch.setenv("REGION_ALLOWLIST", " us, uk ,,UP ")
    assert load_settings().region_allowlist == {"US", "UK", "UP"}
