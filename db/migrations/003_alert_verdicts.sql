-- Hand verdicts on spike alerts ("is this alert about something real?"). They grow the judged set
-- that docs/spike_gold_set.csv started, so alert precision can be measured on more than 50 alerts.
-- Written only where ENABLE_LABELING=1; one verdict per alert, changeable.
CREATE TABLE alert_verdicts (
    day           DATE        NOT NULL,
    country_code  TEXT        NOT NULL,
    category      TEXT        NOT NULL,
    verdict       TEXT        NOT NULL CHECK (verdict IN ('Yes', 'No', 'Unclear')),
    reason        TEXT,                       -- why not: misread_type, duplicate_story, ...
    judged_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (day, country_code, category)
);
