from tripwire.db import migrate


def test_migrate_creates_tables_and_is_rerunnable(conn):
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
        )
    }
    assert {"events", "ingest_files", "spikes", "labels", "schema_migrations"} <= tables
    assert migrate(conn) == []  # nothing new the second time
