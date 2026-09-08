.PHONY: install seed ingest test run compose-up compose-logs lint

install:
	pip install -e ".[dev]"

seed:
	medassist seed-db

ingest:
	medassist ingest

test:
	pytest -q --cov=medassist --cov-report=term-missing

run:
	streamlit run src/medassist/ui/app_streamlit.py

compose-up:
	docker compose up app ollama

compose-logs:
	docker compose logs -f

lint:
	ruff check src tests
