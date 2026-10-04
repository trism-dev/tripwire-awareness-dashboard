.PHONY: up migrate backfill ingest spikes app test lint

up:
	docker compose up -d
migrate:
	uv run python -m tripwire.db migrate
backfill:
	uv run python -m tripwire.backfill --days $(or $(DAYS),30)
ingest:
	uv run python -m tripwire.ingest
spikes:
	uv run python -m tripwire.spikes
app:
	uv run streamlit run app/Home.py
test:
	uv run pytest -q
lint:
	uv run ruff check . && uv run ruff format --check .
