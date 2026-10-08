.PHONY: up migrate backfill ingest spikes train score app test lint

up:
	docker compose up -d
migrate:
	uv run --env-file .env python -m tripwire.db migrate
backfill:
	uv run --env-file .env python -m tripwire.backfill --days $(or $(DAYS),30)
ingest:
	uv run --env-file .env python -m tripwire.ingest
spikes:
	uv run --env-file .env python -m tripwire.spikes
train:
	uv run --env-file .env python -m tripwire.quality.train
score:
	uv run --env-file .env python -m tripwire.quality.score
app:
	uv run --env-file .env streamlit run app/Home.py
test:
	uv run pytest -q
lint:
	uv run ruff check . && uv run ruff format --check .
