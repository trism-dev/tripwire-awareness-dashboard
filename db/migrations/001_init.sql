CREATE TABLE events (
    global_event_id BIGINT PRIMARY KEY,
    event_date      DATE,
    date_added      TIMESTAMPTZ NOT NULL,
    actor1_name     TEXT,
    actor1_country  TEXT,
    actor2_name     TEXT,
    actor2_country  TEXT,
    event_code      TEXT,
    event_base_code TEXT,
    event_root_code TEXT,
    quad_class      SMALLINT,
    goldstein       REAL,
    num_mentions    INT,
    num_sources     INT,
    num_articles    INT,
    avg_tone        REAL,
    geo_type        SMALLINT,
    geo_fullname    TEXT,
    country_code    TEXT,           -- FIPS 10-4, not ISO
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    is_root_event   BOOLEAN,
    source_url      TEXT,
    category        TEXT,
    quality_score   REAL,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX events_date_added_idx ON events (date_added);
CREATE INDEX events_country_cat_date_idx ON events (country_code, category, event_date);
CREATE INDEX events_category_idx ON events (category);

CREATE TABLE ingest_files (
    file_url     TEXT PRIMARY KEY,
    md5          TEXT,
    rows_raw     INT,
    rows_kept    INT,
    status       TEXT NOT NULL,
    error        TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE spikes (
    id              SERIAL PRIMARY KEY,
    country_code    TEXT NOT NULL,
    category        TEXT NOT NULL,
    day             DATE NOT NULL,
    count           INT NOT NULL,
    baseline_median REAL,
    baseline_mad    REAL,
    z               REAL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (country_code, category, day)
);

CREATE TABLE labels (
    global_event_id BIGINT PRIMARY KEY REFERENCES events (global_event_id) ON DELETE CASCADE,
    label           SMALLINT NOT NULL CHECK (label IN (0, 1)),
    note            TEXT,
    labeled_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
