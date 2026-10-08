# Tripwire

![CI](https://github.com/trism-dev/tripwire-awareness-dashboard/actions/workflows/ci.yml/badge.svg)

Open-source situational awareness dashboard built on GDELT 2.0 Events. It loads the GDELT feed every
15 minutes, keeps conflict and unrest events that have a usable location, groups them into mission
categories, flags unusual spikes by country, and shows everything on a map.

## Run it locally

You need Docker Desktop, [uv](https://docs.astral.sh/uv/) and `make`.

```bash
cp .env.example .env     # local settings (the database runs in Docker on port 5434)
make up                  # starts Postgres, the 15-minute ingestion worker and the dashboard
make migrate             # creates the tables (the worker also does this on start)
make backfill DAYS=7     # loads a week of events (about 10 minutes); 58 days is needed for spikes
                         # then open the dashboard at http://localhost:8501
make test && make lint
```

`make app` runs the dashboard from your working copy instead (for development). It uses the same
port as the Docker one, so run `docker compose stop app` first.

Other commands: `make ingest` (one cycle), `make spikes` (recompute spikes), `make train` (train the
quality classifier from your labels), `make score` (score events that have no quality score yet).

**Labeling (local only):** open the *Label* page in the sidebar to hand-label events for the quality
classifier. It writes to the database, so it only works when `ENABLE_LABELING=1` is set (on by default
in `.env.example` and the local Docker app; leave it unset on any public host).

## Data

Event data: [The GDELT Project](https://www.gdeltproject.org/). GDELT is free to use with attribution.
Country codes in the data are FIPS 10-4, not ISO.

Docs are in `docs/`: `decisions.md` (why things are built the way they are), `data_notes.md`
(measured data volumes), `gdelt_schema.md` (the 61 file columns).
