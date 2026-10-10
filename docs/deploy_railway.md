# Deploying Tripwire to Railway

Goal: a public URL for the dashboard, with the worker keeping it fresh. About 30 minutes, most of it
clicking. Everything below that can be tested on your machine has been; the Railway-specific
dashboard steps are written from Railway's documentation and **could not be tested without your
account**, so check each one as you go.

## What you will have

Three services in one Railway project:

| Service | What it is | Settings that matter |
|---|---|---|
| **Postgres** | Railway's Postgres template | holds the data; keep it private |
| **worker** | this repo, `SERVICE=worker` | ingests every 15 minutes, spikes, scoring, retention |
| **app** | this repo, `SERVICE=app` | the Streamlit dashboard, with a public domain |

Both services use the same Dockerfile. `deploy/start.sh` starts the right program from the `SERVICE`
variable, so there are no per-service config files (Railway's config-as-code is deprecated and
stops working on 2026-12-01).

## What it costs (estimate, not a quote)

Railway Hobby is $5 a month and includes $5 of usage. Rates: memory $10 per GB-month, CPU $20 per
vCPU-month, storage $0.15 per GB-month, network $0.05 per GB.

Measured on your machine: worker about 150 MB, app about 160 MB idle (assume 300 MB with a few
viewers), database 836 MB on disk (61 MB compressed). Postgres memory on Railway is the least
certain number (assume 250 to 600 MB).

| Part | Rough usage | Rough cost per month |
|---|---|---|
| worker memory | 0.15 GB | $1.50 |
| app memory | 0.3 GB | $3.00 |
| Postgres memory | 0.25 to 0.6 GB | $2.50 to $6.00 |
| CPU, all three (mostly idle) | about 0.1 vCPU | about $2.00 |
| storage | 1 GB | $0.15 |
| **Total** | | **roughly $9 to $13** |

Above $5 you pay the difference, so expect about **$9 to $13 a month**. Check the real figure after
the first week (the PRD says to) and look at which service uses the most.

**Set a spending limit before anything else.** Railway's docs point to an FAQ titled "How do I
prevent spending more than I want to?" for this; I could not confirm where the setting lives, so
find it in your Railway account or project settings and set it to about $15.

## Steps

### 1. Put the code where Railway can read it
The repo is private. Either let Railway's GitHub app access it (choose the repo when asked), or
make the repo public first (`gh repo edit --visibility public --accept-visibility-change-consequences`;
the PRD wants it public in the end anyway). Check the repo contains no secrets first: `.env` is
ignored, and `.env.example` holds only local defaults.

### 2. Create the project and database
1. Railway dashboard, **New Project**, **Deploy PostgreSQL**. Name the service `Postgres`.
2. Open it and note its variables. The **private** connection string (usually `DATABASE_URL`) is
   what the services use. A **public** one (often `DATABASE_PUBLIC_URL`, needs the TCP proxy) is only
   for step 3.

### 3. Load your data (do this before starting the services)
The worker alone only fetches the last 24 hours, but spike detection needs 28+ days of history and
your 312 labels live only in your local database. So copy the local database up. In PowerShell, from
the project folder (Docker Desktop running, `make up` running):

```powershell
docker compose exec -T db pg_dump -U tripwire -Fc -f /tmp/tripwire.dump tripwire
docker compose cp db:/tmp/tripwire.dump ./tripwire.dump
```

(Do not use `>` to redirect `pg_dump` in PowerShell: it corrupts binary files.) The file is about
61 MB. Then in Railway, enable **public networking / TCP proxy** on the Postgres service, copy the
public connection URL, and restore (replace the URL):

```powershell
docker run --rm -v "${PWD}:/dump" postgres:16 pg_restore --no-owner --no-privileges --clean --if-exists -d "PASTE_PUBLIC_URL_HERE" /dump/tripwire.dump
```

Expect a few harmless "does not exist, skipping" notices on a fresh database. This exact dump and
restore was rehearsed locally into a scratch database: 795,516 events, 795,516 scored, 312 labels,
324 spikes, identical on both sides. After it finishes, **turn public networking off again** and delete
`tripwire.dump` (it is git-ignored).

### 4. Add the two services
For each, **New**, **GitHub Repo**, pick this repo. Railway builds the Dockerfile.

**worker**, Variables tab:
- `SERVICE` = `worker`
- `DATABASE_URL` = reference the Postgres private URL (Railway's variable picker: choose the
  `Postgres` service and its `DATABASE_URL`)
- `RETENTION_DAYS` = `60`

**app**, Variables tab:
- `SERVICE` = `app`
- `DATABASE_URL` = the same reference as the worker
- Settings: **Generate Domain** to get the public URL. Railway sets `PORT` itself and the start
  script uses it. Optional health check path: `/_stcore/health`.

**Do not set `ENABLE_LABELING` on either service.** That page writes to the database and the app has
no user accounts; without the variable it shows "switched off".

### 5. Check it works
- Open the app URL: the header should say the last GDELT update is minutes old (once the worker has
  run its first pass, a minute or two).
- Alerts tab shows spikes; Trend tab draws a chart; the Events table downloads a CSV.
- Open `/Label` on the public URL: it must say labeling is switched off.
- Worker logs show a pass every 15 minutes and "retention removed N old events" occasionally.
- If the app says "Cannot reach the database", the `DATABASE_URL` reference is wrong (the service
  name in the reference must match the Postgres service's name exactly).

### 6. After it is live
- Set the spending limit (above) if you did not already, and check usage after a week.
- Put the URL in the README, in `docs/mission_case.md` and on your resume.
- Keep your local database as the source for labels. The hosted copy is read-only in practice:
  new labels you make locally do not reach it unless you dump and restore again, then run
  `python -m tripwire.quality.score --all` against it if you retrain.

## Things to know

- **Public and unauthenticated.** Anyone with the URL can view the dashboard. It is read-only (no
  button changes data) and the database is not reachable from the internet. Heavy views are cached for
  60 seconds, but a flood of visitors would still cost compute, which is another reason for the
  spending limit.
- **Restarts are safe.** The worker now stops cleanly when Railway redeploys it (it handles the stop
  signal), and every write is repeatable, so a restart never duplicates or loses data.
- **GDELT keeps flowing without you.** If the worker is down for hours, its next pass fills the last 24
  hours; anything older than that needs `python -m tripwire.backfill --days N`.
- **Rollback:** delete the services or the project; nothing else depends on them. Your local setup is
  unchanged.
- **Data attribution** to The GDELT Project is already in the app footer and README.
