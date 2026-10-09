-- Fields GDELT already provides that help judge whether an event record is credible:
-- who the actors are (type codes such as JUD = judiciary, MED = media), and where each actor is
-- based versus where the event is placed (a mismatch often means a misplaced event).
ALTER TABLE events
    ADD COLUMN actor1_code         TEXT,
    ADD COLUMN actor2_code         TEXT,
    ADD COLUMN actor1_type1_code   TEXT,
    ADD COLUMN actor2_type1_code   TEXT,
    ADD COLUMN actor1_geo_country  TEXT,   -- FIPS 10-4
    ADD COLUMN actor2_geo_country  TEXT,   -- FIPS 10-4
    ADD COLUMN action_adm1_code    TEXT;
